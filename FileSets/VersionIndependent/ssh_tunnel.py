#!/usr/bin/env python3

from __future__ import print_function

import logging
import errno
import grp
import ipaddress
import json
import os
from pathlib import Path
import re
import pwd
import signal
import stat
import subprocess
import sys
import time


def extend_python_path():
    candidates = [
        "/opt/victronenergy/ext/velib_python",
        "/opt/victronenergy/dbus-systemcalc-py/ext/velib_python",
        "/data/SetupHelper/velib_python",
        "/opt/victronenergy/SetupHelper/velib_python",
    ]
    for candidate in candidates:
        if os.path.isdir(candidate) and candidate not in sys.path:
            sys.path.insert(0, candidate)


extend_python_path()

import dbus  # type: ignore
from dbus.mainloop.glib import DBusGMainLoop  # type: ignore
from gi.repository import GLib  # type: ignore
from settingsdevice import SettingsDevice  # type: ignore


SETTINGS_PATH = "/Settings/SSHTunnel"
# A Wi-Fi association, DHCP lease and VPN revalidation can outlast a brief
# observer gap. Keep only an already-running, source-bound tunnel during that
# transition; _reload still stops it immediately on any settings/identity
# change and never launches a new child without a current route proof.
MANAGEMENT_OBSERVER_GRACE_SECONDS = 90
# Each VPN-route observation starts a separate Python interpreter. Observing every
# 2 s poll cost ~25 % of a Pi 4 core (measured 2026-11-17). The 90 s grace makes a
# 10 s observation interval sufficient; settings changes and every tunnel (re)start
# still observe immediately.
ROUTE_OBSERVE_INTERVAL_SECONDS = 10
MANAGEMENT_HELPER = Path('/data/RoadLink/src/management_route.py')
DEFAULT_KEY_PATH_CANDIDATES = (
    "/data/keys/ssh_host_rsa_key",
    "/data/keys/id_rsa",
    "/data/SSHTunnel/id_rsa",
)
SUPPORTED_SETTINGS = {
    "enabled": ["{}/Enabled".format(SETTINGS_PATH), 0, 0, 1],
    "server": ["{}/Server".format(SETTINGS_PATH), "", 0, 0],
    "server_port": ["{}/ServerPort".format(SETTINGS_PATH), 22, 1, 65535],
    "username": ["{}/Username".format(SETTINGS_PATH), "root", 0, 0],
    "key_path": ["{}/KeyPath".format(SETTINGS_PATH), "/data/keys/ssh_host_rsa_key", 0, 0],
    "strict_host_key_checking": ["{}/StrictHostKeyChecking".format(SETTINGS_PATH), 1, 0, 1],
    "reconnect_delay": ["{}/ReconnectDelay".format(SETTINGS_PATH), 5, 1, 600],
    "management_mode": ["{}/ManagementMode".format(SETTINGS_PATH), 0, 0, 1],
    "management_ipv4": ["{}/ManagementIPv4".format(SETTINGS_PATH), "", 0, 0],
    "tunnel1_enabled": ["{}/Tunnel1Enabled".format(SETTINGS_PATH), 0, 0, 1],
    "tunnel1_remote_port": ["{}/Tunnel1RemotePort".format(SETTINGS_PATH), 2201, 1, 65535],
    "tunnel1_local_host": ["{}/Tunnel1LocalHost".format(SETTINGS_PATH), "localhost", 0, 0],
    "tunnel1_local_port": ["{}/Tunnel1LocalPort".format(SETTINGS_PATH), 22, 1, 65535],
    "tunnel2_enabled": ["{}/Tunnel2Enabled".format(SETTINGS_PATH), 0, 0, 1],
    "tunnel2_remote_port": ["{}/Tunnel2RemotePort".format(SETTINGS_PATH), 8081, 1, 65535],
    "tunnel2_local_host": ["{}/Tunnel2LocalHost".format(SETTINGS_PATH), "localhost", 0, 0],
    "tunnel2_local_port": ["{}/Tunnel2LocalPort".format(SETTINGS_PATH), 80, 1, 65535],
}


class TunnelConfig(object):
    def __init__(self, name, remote_port, local_host, local_port):
        self.name = name
        self.remote_port = remote_port
        self.local_host = local_host
        self.local_port = local_port

    def __eq__(self, other):
        return (
            isinstance(other, TunnelConfig)
            and self.name == other.name
            and self.remote_port == other.remote_port
            and self.local_host == other.local_host
            and self.local_port == other.local_port
        )


class TunnelState(object):
    def __init__(self, config, process, command, transport_identity=None):
        self.config = config
        self.process = process
        self.command = tuple(command)
        self.retry_after = 0
        self.transport_identity = transport_identity


def trusted_source_mode(info, path):
    if info.st_uid != 0 or info.st_mode & 0o002:
        return False
    if not info.st_mode & 0o020:
        return True
    # SetupHelper may use group-writable root:root package directories.
    # Accept that specific case only if group 0 contains exclusively UID 0
    # accounts and no extended ACL grants a different principal access.
    if info.st_gid != 0:
        return False
    try:
        if any(user.pw_uid != 0 and user.pw_gid == 0 for user in pwd.getpwall()):
            return False
        if any(pwd.getpwnam(name).pw_uid != 0 for name in grp.getgrgid(0).gr_mem):
            return False
        try:
            os.getxattr(path, 'system.posix_acl_access', follow_symlinks=False)
        except OSError as error:
            return error.errno in (errno.ENODATA, errno.ENOTSUP, errno.EOPNOTSUPP)
        return False
    except (OSError, KeyError):
        return False


def management_route(endpoint, helper=MANAGEMENT_HELPER):
    """Execute only a held, root-owned RoadLink observer, without importing it."""
    descriptor = None
    try:
        helper = Path(helper)
        for folder in helper.parents:
            info = folder.lstat()
            if not stat.S_ISDIR(info.st_mode) or not trusted_source_mode(info, folder):
                return None
        descriptor = os.open(str(helper), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or not trusted_source_mode(before, helper)
                or before.st_nlink != 1 or not 0 < before.st_size <= 65536):
            return None
        source = os.read(descriptor, 65537)
        def stamp(info):
            return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns
        if (len(source) != before.st_size or stamp(before) != stamp(os.fstat(descriptor))
                or stamp(before) != stamp(helper.lstat())):
            return None
        compile(source, str(helper), 'exec')
        result = subprocess.run(['python3', '-I', '-', '--endpoint', endpoint], input=source,
                                capture_output=True, timeout=5)
        if result.returncode or len(result.stdout) > 4096:
            return None
        def pairs(items):
            value = {}
            for key, item in items:
                if key in value:
                    raise ValueError('Duplicate observer field')
                value[key] = item
            return value
        return json.loads(result.stdout, object_pairs_hook=pairs)
    except (OSError, ValueError, TypeError, SyntaxError, subprocess.SubprocessError):
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def route_transport(value, endpoint, server):
    """Constrain the observer's private projection before building SSH argv."""
    try:
        if (type(value) is not dict or set(value) != {'schema', 'mode', 'endpoint', 'address',
                'interface', 'ifindex', 'controller', 'guard', 'runtime'}
                or type(value['schema']) is not int or value['schema'] != 1
                or value['mode'] != 'VPN' or value['endpoint'] != endpoint
                or value['interface'] != 'wgroadlink'
                or type(value['ifindex']) is not int or value['ifindex'] <= 0):
            return None
        address = str(ipaddress.IPv4Address(value['address']))
        if not any(ipaddress.IPv4Address(address) in ipaddress.IPv4Network(block)
                   for block in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
            return None
        identities = []
        for name in ('controller', 'guard'):
            item = value[name]
            if (type(item) is not dict or set(item) != {'pid', 'start'}
                    or type(item['pid']) is not int or not 0 < item['pid'] < 2147483648
                    or type(item['start']) is not str or not item['start'].isdigit()
                    or not 0 < len(item['start']) <= 20):
                return None
            identities.append((item['pid'], item['start']))
        runtime = value['runtime']
        if (type(runtime) is not list or len(runtime) != 2
                or any(type(item) is not int or item < 0 for item in runtime) or runtime[1] == 0):
            return None
        identity = (endpoint, address, value['ifindex'], tuple(runtime), tuple(identities))
        options = ['-4', '-b', address, '-o', 'BindInterface=wgroadlink',
                   '-o', 'HostKeyAlias=' + server, '-o', 'CheckHostIP=no']
        return options, endpoint, identity
    except (KeyError, ValueError, TypeError):
        return None


class TunnelManager(object):
    def __init__(self):
        self._bus = dbus.SystemBus()
        self._settings = SettingsDevice(self._bus, SUPPORTED_SETTINGS, self._handle_setting_change)
        self._desired = {}
        self._states = {}
        self._mainloop = GLib.MainLoop()
        self._stopping = False
        self._stop_requested = False
        self._transport_plan = None
        self._waiting_for_management_route = False
        self._observer_unavailable = False
        self._route_loss_since = None
        GLib.timeout_add_seconds(2, self._poll)

    def _handle_setting_change(self, setting, old_value, new_value):
        logging.info("Setting changed: %s=%r -> %r", setting, old_value, new_value)
        GLib.idle_add(self._reload)

    def _setting(self, key):
        return self._settings[key]

    def _as_bool(self, value):
        try:
            return bool(int(value))
        except Exception:
            return False

    def _as_int(self, value, default):
        try:
            return int(value)
        except Exception:
            return default

    def _as_text(self, value, default=""):
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default

    def _is_enabled(self):
        if not self._as_bool(self._setting("enabled")):
            return False
        if not self._as_text(self._setting("server"), ""):
            logging.info("SSH tunnel disabled until a server is configured")
            return False
        key_path = self._resolved_key_path()
        if not os.path.isfile(key_path):
            logging.warning("SSH tunnel disabled until key file exists: %s", key_path)
            return False
        return True

    def _resolved_key_path(self):
        configured = self._as_text(self._setting("key_path"), "")
        if configured:
            return configured
        for candidate in DEFAULT_KEY_PATH_CANDIDATES:
            if os.path.isfile(candidate):
                return candidate
        return ""

    def _build_desired(self):
        desired = {}
        if not self._is_enabled():
            return desired

        tunnel_specs = [
            ("tunnel1", "tunnel1_enabled", "tunnel1_remote_port", "tunnel1_local_host", "tunnel1_local_port"),
            ("tunnel2", "tunnel2_enabled", "tunnel2_remote_port", "tunnel2_local_host", "tunnel2_local_port"),
        ]

        for name, enabled_key, remote_key, host_key, local_key in tunnel_specs:
            if not self._as_bool(self._setting(enabled_key)):
                continue
            desired[name] = TunnelConfig(
                name,
                self._as_int(self._setting(remote_key), 1),
                self._as_text(self._setting(host_key), "localhost"),
                self._as_int(self._setting(local_key), 1),
            )

        return desired

    def _build_command(self, config):
        server = self._as_text(self._setting("server"), "")
        username = self._as_text(self._setting("username"), "root")
        key_path = self._resolved_key_path()
        strict = "yes" if self._as_bool(self._setting("strict_host_key_checking")) else "no"
        reverse = "{remote}:localhost:{local}".format(remote=config.remote_port, local=config.local_port)
        if config.local_host and config.local_host != "localhost":
            reverse = "{remote}:{host}:{local}".format(
                remote=config.remote_port,
                host=config.local_host,
                local=config.local_port,
            )

        plan = self._transport_plan
        if plan is None:
            return None
        options, destination, _identity = plan
        if _identity is not None:
            # Management consumers use IPv4 loopback. A dual-stack request can
            # otherwise succeed on IPv6 while an old IPv4 listener still owns
            # the port, despite ExitOnForwardFailure=yes.
            reverse = '127.0.0.1:' + reverse
        return [
            "ssh",
        ] + options + [
            "-p", str(self._as_int(self._setting("server_port"), 22)),
            "-i", key_path,
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=20",
            "-o", "StrictHostKeyChecking={}".format(strict),
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "TCPKeepAlive=yes",
            "-nNT",
            "-R", reverse,
            "-l", username,
            "--", destination,
        ]

    def _transport(self):
        self._observer_unavailable = False
        server = self._as_text(self._setting('server'), '')
        mode = self._as_int(self._setting('management_mode'), -1)
        if mode == 0:
            return [], server, None
        if mode != 1 or not self._as_bool(self._setting('strict_host_key_checking')):
            return None
        # HostKeyAlias preserves the original identity even when the destination
        # is a pinned numeric IPv4 address. Never learn a replacement key here.
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]{0,252}', server):
            return None
        try:
            endpoint = ipaddress.IPv4Address(self._as_text(self._setting('management_ipv4'), ''))
            if not endpoint.is_global or endpoint.is_multicast or endpoint.is_reserved:
                return None
            endpoint = str(endpoint)
        except ValueError:
            return None
        observed = management_route(endpoint)
        if observed is None:
            self._observer_unavailable = True
            return None
        return route_transport(observed, endpoint, server)

    def _reload(self):
        if self._stopping or getattr(self, "_stop_requested", False):
            return False
        desired = self._build_desired()
        previous_plan = self._transport_plan
        observation_started = time.monotonic()
        self._last_observation = observation_started
        self._transport_plan = self._transport() if desired else None
        if self._stopping or getattr(self, "_stop_requested", False):
            return False
        if self._transport_plan is None:
            # A transient observer gap must not tear down an already-running,
            # source/interface-bound tunnel. No new connection may start here.
            loss_since = getattr(self, '_route_loss_since', None)
            if loss_since is None:
                loss_since = observation_started
            if (desired and getattr(self, '_observer_unavailable', False)
                    and previous_plan is not None and previous_plan[2] is not None
                    and 'HostKeyAlias=' + self._as_text(self._setting('server'), '')
                        in previous_plan[0]
                    and self._as_text(self._setting('management_ipv4'), '')
                        == previous_plan[1]
                    and set(self._states) == set(desired)
                    and all(state.config == desired[name]
                            and state.transport_identity == previous_plan[2]
                            and state.process is not None
                            and state.process.poll() is None
                            for name, state in self._states.items())):
                self._transport_plan = previous_plan
                unchanged = all(state.command == tuple(self._build_command(desired[name]))
                                for name, state in self._states.items())
                self._transport_plan = None
                if unchanged and time.monotonic() - loss_since < MANAGEMENT_OBSERVER_GRACE_SECONDS:
                    if getattr(self, '_route_loss_since', None) is None:
                        logging.info('Management route observation missing; retaining bound tunnels')
                    self._route_loss_since = loss_since
                    self._transport_plan = previous_plan
                    self._desired = desired
                    return False
            self._route_loss_since = None
            if desired and not getattr(self, '_waiting_for_management_route', False):
                logging.warning('Management route unavailable; no tunnel started')
            self._waiting_for_management_route = bool(desired)
            desired = {}
        else:
            if getattr(self, '_route_loss_since', None) is not None:
                logging.info('Management route observation recovered after %.1fs',
                             time.monotonic() - self._route_loss_since)
            self._route_loss_since = None
            if getattr(self, '_waiting_for_management_route', False):
                logging.info('Management route validated')
            self._waiting_for_management_route = False

        for name in list(self._states.keys()):
            if (name not in desired
                    or self._states[name].config != desired[name]
                    or self._states[name].command != tuple(self._build_command(desired[name]))
                    or self._states[name].transport_identity != self._transport_plan[2]):
                self._stop(name)

        self._desired = desired

        for name in self._desired:
            if name not in self._states:
                self._start(name)

        return False

    def _start(self, name):
        if (self._stopping or getattr(self, "_stop_requested", False)
                or getattr(self, '_route_loss_since', None) is not None):
            return
        config = self._desired.get(name)
        if config is None:
            return
        command = self._build_command(config)
        if command is None:
            return
        logging.info("Starting %s", name)
        state = TunnelState(config, None, command, self._transport_plan[2])
        self._states[name] = state
        try:
            state.process = subprocess.Popen(command)
            if self._stopping or getattr(self, "_stop_requested", False):
                self._states[name] = state
                self._stop(name)
        except OSError as exc:
            logging.error("Unable to start %s: %s", name, exc)
            state.retry_after = time.monotonic() + max(
                1, self._as_int(self._setting("reconnect_delay"), 5))

    def _stop(self, name):
        state = self._states.get(name)
        if state is None:
            return
        if state.process is not None and state.process.poll() is None:
            state.process.terminate()
            try:
                state.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                state.process.kill()
                try:
                    state.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logging.error("Tunnel %s did not reap after kill; retaining child handle", name)
                    return False
        if self._states.get(name) is state:
            del self._states[name]
        return True

    def _poll(self):
        if self._stopping:
            return False
        observe_due = (self._as_int(self._setting('management_mode'), -1) != 1
                       or time.monotonic() - getattr(self, '_last_observation', float('-inf'))
                       >= ROUTE_OBSERVE_INTERVAL_SECONDS)
        if observe_due:
            self._reload()
        reconnect_delay = max(1, self._as_int(self._setting("reconnect_delay"), 5))
        now = time.monotonic()
        for name in list(self._states.keys()):
            state = self._states[name]
            if state.process is None:
                continue
            if state.process.poll() is None:
                continue
            logging.warning("Tunnel %s exited with code %s", name, state.process.returncode)
            state.retry_after = now + reconnect_delay
            self._states[name] = state
            self._states[name].process = None
        for name in list(self._states.keys()):
            state = self._states[name]
            if state.process is not None:
                continue
            if now < state.retry_after:
                continue
            del self._states[name]
        if any(name not in self._states for name in self._desired):
            # Never (re)start a tunnel on a route proof older than this poll.
            if not observe_due:
                self._reload()
            for name in self._desired:
                if name not in self._states:
                    self._start(name)

        return True

    def request_stop(self):
        # Signal admission closes immediately; cleanup runs outside Popen and
        # route observation, in the GLib main loop.
        if self._stopping or getattr(self, "_stop_requested", False):
            return
        self._stop_requested = True
        GLib.idle_add(self.stop)

    def stop(self):
        if self._stopping:
            return
        self._stopping = True
        for name in list(self._states.keys()):
            self._stop(name)
        if self._states:
            # An unconfirmed reap is not successful shutdown. Keep admission
            # closed and the main loop alive until the retained handles drain.
            GLib.timeout_add(100, self._drain_stop)
        else:
            self._mainloop.quit()

    def _drain_stop(self):
        for name in list(self._states.keys()):
            state = self._states[name]
            if state.process is not None and state.process.poll() is None:
                continue
            del self._states[name]
        if self._states:
            return True
        self._mainloop.quit()
        return False

    def run(self):
        self._reload()
        self._mainloop.run()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    DBusGMainLoop(set_as_default=True)
    manager = TunnelManager()

    def handle_signal(_signum, _frame):
        manager.request_stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    manager.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
