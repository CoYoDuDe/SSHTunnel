#!/usr/bin/env python3

from __future__ import print_function

import logging
import os
import signal
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
SUPPORTED_SETTINGS = {
    "enabled": ["{}/Enabled".format(SETTINGS_PATH), 0, 0, 1],
    "server": ["{}/Server".format(SETTINGS_PATH), "", 0, 0],
    "username": ["{}/Username".format(SETTINGS_PATH), "root", 0, 0],
    "key_path": ["{}/KeyPath".format(SETTINGS_PATH), "", 0, 0],
    "strict_host_key_checking": ["{}/StrictHostKeyChecking".format(SETTINGS_PATH), 1, 0, 1],
    "reconnect_delay": ["{}/ReconnectDelay".format(SETTINGS_PATH), 5, 1, 600],
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
    def __init__(self, config, process):
        self.config = config
        self.process = process
        self.retry_after = 0


class TunnelManager(object):
    def __init__(self):
        self._bus = dbus.SystemBus()
        self._settings = SettingsDevice(self._bus, SUPPORTED_SETTINGS, self._handle_setting_change)
        self._desired = {}
        self._states = {}
        self._mainloop = GLib.MainLoop()
        self._stopping = False
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
        key_path = self._as_text(self._setting("key_path"), "")
        if not key_path:
            logging.info("SSH tunnel disabled until a key path is configured")
            return False
        if not os.path.isfile(key_path):
            logging.warning("SSH tunnel disabled until key file exists: %s", key_path)
            return False
        return True

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
        key_path = self._as_text(self._setting("key_path"), "")
        strict = "yes" if self._as_bool(self._setting("strict_host_key_checking")) else "no"
        reverse = "{remote}:localhost:{local}".format(remote=config.remote_port, local=config.local_port)
        if config.local_host and config.local_host != "localhost":
            reverse = "{remote}:{host}:{local}".format(
                remote=config.remote_port,
                host=config.local_host,
                local=config.local_port,
            )

        return [
            "ssh",
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
            "{user}@{server}".format(user=username, server=server),
        ]

    def _reload(self):
        desired = self._build_desired()

        for name in list(self._states.keys()):
            if name not in desired or self._states[name].config != desired[name]:
                self._stop(name)

        self._desired = desired

        for name in self._desired:
            if name not in self._states:
                self._start(name)

        return False

    def _start(self, name):
        config = self._desired.get(name)
        if config is None:
            return
        command = self._build_command(config)
        logging.info("Starting %s: %s", name, " ".join(command))
        self._states[name] = TunnelState(config, subprocess.Popen(command))

    def _stop(self, name):
        state = self._states.pop(name, None)
        if state is None:
            return
        if state.process is not None and state.process.poll() is None:
            state.process.terminate()
            try:
                state.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                state.process.kill()
                state.process.wait(timeout=5)

    def _poll(self):
        reconnect_delay = max(1, self._as_int(self._setting("reconnect_delay"), 5))
        now = time.time()
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
        for name in self._desired:
            if name not in self._states:
                self._start(name)

        return True

    def stop(self):
        if self._stopping:
            return
        self._stopping = True
        for name in list(self._states.keys()):
            self._stop(name)
        self._mainloop.quit()

    def run(self):
        self._reload()
        self._mainloop.run()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    DBusGMainLoop(set_as_default=True)
    manager = TunnelManager()

    def handle_signal(_signum, _frame):
        manager.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    manager.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
