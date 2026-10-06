#!/usr/bin/env python3
"""One-time interactive setup. Password entry is handled by OpenSSH, never stored."""
import argparse
import base64
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time


def valid_server(value):
    value = value.strip()
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        if len(value) <= 253 and re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', value):
            return value
    raise ValueError('Server must be a hostname or IP address, without a URL or port.')


def valid_user(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*\$?', value):
        raise ValueError('Invalid SSH username.')
    return value


def valid_port(value):
    value = int(value)
    if not 1 <= value <= 65535:
        raise ValueError('Port must be between 1 and 65535.')
    return value


def fingerprint(key):
    fields = key.split()
    raw = base64.b64decode(fields[1], validate=True)
    return 'SHA256:' + base64.b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')


def select_host_key(scan, expected):
    for line in scan.splitlines():
        fields = line.split()
        if len(fields) >= 3 and not line.startswith('#'):
            key = ' '.join(fields[1:3])
            if fingerprint(key) == expected:
                return key
    raise ValueError('Fingerprint mismatch. No host key was trusted.')


def scan_host(server, port):
    if shutil.which('ssh-keyscan'):
        return subprocess.run(['ssh-keyscan', '-T', '5', '-p', str(port), server],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20).stdout
    # Venus may omit ssh-keyscan. Collect a key in an isolated temporary file
    # using an unauthenticated probe. No password/key authentication is allowed.
    # Only the independently verified fingerprint is later trusted for login.
    keys = []
    with tempfile.TemporaryDirectory(prefix='sshtunnel-probe-') as folder:
        for algorithm in ('ssh-ed25519', 'ecdsa-sha2-nistp256', 'rsa-sha2-512'):
            target = Path(folder) / algorithm
            subprocess.run(['ssh', '-p', str(port), '-N', '-T',
                            '-o', 'BatchMode=yes', '-o', 'PreferredAuthentications=none',
                            '-o', 'IdentityAgent=none', '-o', 'IdentityFile=none',
                            '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=accept-new',
                            '-o', 'GlobalKnownHostsFile=/dev/null', '-o', 'HashKnownHosts=no',
                            '-o', 'UserKnownHostsFile=' + str(target),
                            '-o', 'HostKeyAlgorithms=' + algorithm, '--', server],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
            if target.exists():
                keys.append(target.read_text())
    return '\n'.join(keys)


def authorized_line(public_key, ports):
    fields = public_key.split()
    if len(fields) < 2 or fields[0] != 'ssh-ed25519':
        raise ValueError('Expected the generated Ed25519 public key.')
    base64.b64decode(fields[1], validate=True)
    limits = ['restrict', 'port-forwarding', 'command="/bin/false"', 'permitopen="localhost:1"']
    limits.extend('permitlisten="localhost:%d"' % valid_port(p) for p in sorted(set(ports)))
    return ','.join(limits) + ' ' + ' '.join(fields[:2]) + ' sshtunnel-venus\n'


def provision_command(line):
    # Only public data is transmitted; this command never contains a password.
    public_blob = line.split()[-2]
    return ('set -eu; umask 077; mkdir -p "$HOME/.ssh"; touch "$HOME/.ssh/authorized_keys"; '
            'chmod 700 "$HOME/.ssh"; '
            'exec 9>"$HOME/.ssh/sshtunnel-setup.lock"; flock -x 9; '
            'task_keyfile=$(mktemp "$HOME/.ssh/sshtunnel-keys.XXXXXX"); '
            'trap \'rm -f "$task_keyfile"\' EXIT; '
            'awk -v key={blob} \'{{for(i=1;i<=NF;i++) if($i==key) next; print}}\' '
            '"$HOME/.ssh/authorized_keys" > "$task_keyfile"; '
            "printf '%s\\n' {key} >> \"$task_keyfile\"; "
            'chmod 600 "$task_keyfile"; mv "$task_keyfile" "$HOME/.ssh/authorized_keys"'
            ).format(blob=shlex.quote(public_blob), key=shlex.quote(line.strip()))


def trust_key(server, port, key, path):
    name = server if port == 22 else '[%s]:%d' % (server, port)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists():
        found = subprocess.run(['ssh-keygen', '-F', name, '-f', str(path)],
                               stdout=subprocess.PIPE, text=True, check=False).stdout
        for line in found.splitlines():
            fields = line.split()
            if len(fields) < 3 or line.startswith('#'):
                continue
            old = ' '.join(fields[1:3])
            if old == key:
                return
            if fields[1] == key.split()[0]:
                raise ValueError('A different host key is already stored. Investigate the change first.')
    with path.open('a', encoding='ascii') as handle:
        handle.write(name + ' ' + key + '\n')
    path.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server')
    parser.add_argument('--user')
    parser.add_argument('--port', type=valid_port, default=22)
    parser.add_argument('--remote-ssh-port', type=valid_port, default=2201)
    parser.add_argument('--remote-web-port', type=valid_port,
                        help='Optional: requires authentication at the server proxy before enabling.')
    parser.add_argument('--fingerprint', help='Server fingerprint verified independently, e.g. at its console.')
    parser.add_argument('--prepare-only', action='store_true', help='Print administrator command; do not log in or enable tunnels.')
    parser.add_argument('--skip-provision', action='store_true', help='Public key was already installed by administrator.')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run this on the Venus device as root.')
    server = valid_server(args.server or input('SSH server: '))
    user = valid_user(args.user or input('SSH user [root]: ').strip() or 'root')
    ports = [args.remote_ssh_port]
    if args.remote_web_port:
        if args.remote_web_port == args.remote_ssh_port:
            parser.error('SSH and web remote ports must be different.')
        ports.append(args.remote_web_port)
    scan = scan_host(server, args.port)
    expected = args.fingerprint
    if not expected:
        print('Verify the fingerprint independently on the server (ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub).')
        print('Observed fingerprints are NOT proof of identity:')
        for line in scan.splitlines():
            fields = line.split()
            if len(fields) >= 3 and not line.startswith('#'):
                print(fields[1], fingerprint(' '.join(fields[1:3])))
        expected = input('Enter the independently verified SHA256 fingerprint: ').strip()
    key = select_host_key(scan, expected)
    known_hosts = Path.home() / '.ssh' / 'known_hosts'
    trust_key(server, args.port, key, known_hosts)
    identity = Path('/data/keys/sshtunnel_ed25519')
    identity.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not identity.exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'sshtunnel-venus', '-f', str(identity)], check=True)
    identity.chmod(0o600)
    public = subprocess.check_output(['ssh-keygen', '-y', '-f', str(identity)], text=True)
    entry = authorized_line(public, ports)
    command = provision_command(entry)
    if args.prepare_only:
        print('Run this command on the server as the selected SSH user; it contains only the PUBLIC key:')
        print(command)
        print('Then repeat this assistant with --skip-provision.')
        return
    base = ['ssh', '-p', str(args.port), '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=15',
            '-o', 'UserKnownHostsFile=' + str(known_hosts)]
    if not args.skip_provision:
        print('OpenSSH may now ask once for the existing server login password. It is not saved.')
        subprocess.run(base + ['-l', user, '--', server, command], check=True)
    # Check key authentication without executing a remote command (the key is forwarding-only).
    auth_log = tempfile.TemporaryFile(mode='w+t')
    process = subprocess.Popen(base + ['-v', '-i', str(identity), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
                                      '-N', '-T', '-l', user, '--', server], stderr=auth_log, text=True)
    try:
        deadline = time.monotonic() + 25
        while True:
            auth_log.seek(0)
            log = auth_log.read()
            if 'Authenticated to ' in log and 'publickey' in log:
                break
            if process.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError('Key login was not confirmed. Check the server authorized_keys and SSH policy.')
            time.sleep(0.1)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        auth_log.close()
    import dbus
    bus = dbus.SystemBus()
    def setting(name, value):
        item = dbus.Interface(bus.get_object('com.victronenergy.settings', '/Settings/SSHTunnel/' + name),
                              'com.victronenergy.BusItem')
        if int(item.SetValue(value)) != 0:
            raise RuntimeError('Could not save setting ' + name)
    setting('Enabled', dbus.Int32(0))
    values = dict(Server=server, ServerPort=dbus.Int32(args.port), Username=user, KeyPath=str(identity),
                  StrictHostKeyChecking=dbus.Int32(1), Tunnel1Enabled=dbus.Int32(1),
                  Tunnel1RemotePort=dbus.Int32(args.remote_ssh_port), Tunnel1LocalHost='localhost',
                  Tunnel1LocalPort=dbus.Int32(22), Tunnel2Enabled=dbus.Int32(bool(args.remote_web_port)),
                  Tunnel2RemotePort=dbus.Int32(args.remote_web_port or 8081), Tunnel2LocalHost='localhost',
                  Tunnel2LocalPort=dbus.Int32(80))
    for name, value in values.items():
        setting(name, value)
    setting('Enabled', dbus.Int32(1))
    print('Key login verified; tunnel manager enabled. Check remote listeners and service log for port conflicts.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, subprocess.SubprocessError, OSError) as exc:
        raise SystemExit(str(exc))
