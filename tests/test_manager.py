"""Controller regression tests without requiring the Venus D-Bus runtime."""
import ast
import logging
from pathlib import Path
import subprocess
import time
import unittest
from unittest.mock import Mock, patch

source = Path(__file__).resolve().parents[1] / 'FileSets/VersionIndependent/ssh_tunnel.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
classes = ast.Module(body=[n for n in tree.body if isinstance(n, ast.ClassDef)], type_ignores=[])
ns = dict(logging=logging, subprocess=subprocess, time=time)
exec(compile(classes, str(source), 'exec'), ns)
TunnelManager, TunnelConfig, TunnelState = (ns[n] for n in ('TunnelManager', 'TunnelConfig', 'TunnelState'))


class ManagerTests(unittest.TestCase):
    def manager(self):
        manager = TunnelManager.__new__(TunnelManager)
        manager._settings = dict(server='old.example', username='root', key_path='/key',
                                 strict_host_key_checking=1, reconnect_delay=5)
        manager._states = {}
        config = TunnelConfig('tunnel1', 2201, 'localhost', 22)
        manager._desired = {'tunnel1': config}
        manager._build_desired = Mock(return_value=manager._desired.copy())
        return manager, config

    def test_connection_settings_restart_existing_process(self):
        for key, value in [('server', 'new.example'), ('username', 'tunnel'),
                           ('key_path', '/new-key'), ('strict_host_key_checking', 0)]:
            with self.subTest(setting=key):
                manager, config = self.manager()
                old = Mock()
                old.poll.return_value = None
                manager._states['tunnel1'] = TunnelState(config, old, manager._build_command(config))
                manager._settings[key] = value
                with patch.object(subprocess, 'Popen') as launch:
                    manager._reload()
                old.terminate.assert_called_once()
                launch.assert_called_once_with(manager._build_command(config))

    def test_unchanged_settings_preserve_connection(self):
        manager, config = self.manager()
        old = Mock()
        manager._states['tunnel1'] = TunnelState(config, old, manager._build_command(config))
        with patch.object(subprocess, 'Popen') as launch:
            manager._reload()
        old.terminate.assert_not_called()
        launch.assert_not_called()

    def test_spawn_failure_retries_after_delay(self):
        manager, config = self.manager()
        with patch.object(time, 'monotonic', return_value=100), \
                patch.object(subprocess, 'Popen', side_effect=OSError('unavailable')):
            manager._start('tunnel1')
        self.assertEqual(manager._states['tunnel1'].retry_after, 105)
        with patch.object(time, 'monotonic', return_value=104), \
                patch.object(subprocess, 'Popen') as launch:
            manager._poll()
            launch.assert_not_called()
        with patch.object(time, 'monotonic', return_value=105), \
                patch.object(subprocess, 'Popen') as launch:
            manager._poll()
            launch.assert_called_once()


if __name__ == '__main__':
    unittest.main()
