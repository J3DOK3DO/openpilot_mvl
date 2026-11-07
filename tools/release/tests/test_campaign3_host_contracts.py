import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.release import campaign3_host_contracts as c
from tools.release.tests.test_campaign3_offline import frames


class HostContractsTest(unittest.TestCase):
    @staticmethod
    def _mountinfo_line(mount_id, parent_id, mount):
        escaped = (str(mount).replace('\\', r'\134').replace(' ', r'\040')
                   .replace('\t', r'\011').replace('\n', r'\012'))
        return f'{mount_id} {parent_id} 0:1 / {escaped} rw - tmpfs tmpfs rw'

    def test_escaped_mountinfo_parent_and_same_device_child_bind(self):
        for awkward in (' ', '\t', '\n', '\\'):
            with self.subTest(awkward=repr(awkward)):
                with tempfile.TemporaryDirectory(prefix=f'campaign3{awkward}parent-') as name:
                    root = Path(name) / 'pilot-0123456789abcdef'
                    root.mkdir()
                    paths = {area: root / area for area in c.WRITE_AREAS}
                    for path in paths.values():
                        path.mkdir()
                    child = paths['cache']
                    self.assertEqual(child.stat().st_dev, root.stat().st_dev)
                    lines = [self._mountinfo_line(1, 0, '/'),
                             self._mountinfo_line(2, 1, name)]
                    with patch.object(Path, 'read_text', return_value='\n'.join(lines)):
                        result = c.validate_write_coverage(root, paths)
                    self.assertEqual(result['coverage'], 'SIX_AREAS_ONE_ACTUAL_MOUNT')
                    lines.append(self._mountinfo_line(3, 2, child))
                    with patch.object(Path, 'read_text', return_value='\n'.join(lines)):
                        with self.assertRaisesRegex(ValueError, 'crosses filesystem or mount'):
                            c.validate_write_coverage(root, paths)

    def test_malformed_mountinfo_fails_closed_with_awkward_paths(self):
        with tempfile.TemporaryDirectory(prefix='campaign3 awkward\t\\-') as name:
            root = Path(name) / 'pilot-0123456789abcdef'
            root.mkdir()
            paths = {area: root / area for area in c.WRITE_AREAS}
            for path in paths.values():
                path.mkdir()
            valid = [self._mountinfo_line(1, 0, '/'),
                     self._mountinfo_line(2, 1, name)]
            malformed = ('3 2 0:1 / /unexpected\\999 rw - tmpfs tmpfs rw',
                         '3 2 0:1 / /unexpected\\04 rw - tmpfs tmpfs rw',
                         '3 2 0:1 / /unexpected\\000 rw - tmpfs tmpfs rw',
                         '3 2 0:1 /unexpected\\999 /other rw - tmpfs tmpfs rw',
                         '3 2 0:1 / /unexpected rw tmpfs tmpfs rw',
                         'bad 2 0:1 / /unexpected rw - tmpfs tmpfs rw')
            for line in malformed:
                with self.subTest(line=line):
                    with patch.object(Path, 'read_text', return_value='\n'.join(valid + [line])):
                        with self.assertRaisesRegex(ValueError, 'mountinfo'):
                            c.validate_write_coverage(root, paths)

    def test_actual_write_path_coverage_and_symlink_escape(self):
        with tempfile.TemporaryDirectory(prefix='campaign3-') as name:
            root = Path(name) / 'pilot-0123456789abcdef'
            root.mkdir()
            paths = {area: root / area for area in c.WRITE_AREAS}
            for path in paths.values():
                path.mkdir()
            result = c.validate_write_coverage(root, paths)
            self.assertEqual(result['coverage'], 'SIX_AREAS_ONE_ACTUAL_MOUNT')
            self.assertFalse(result['hard_limit_proven'])
            paths['cache'].rmdir()
            paths['cache'].symlink_to(paths['source'], target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                c.validate_write_coverage(root, paths)
            paths['cache'].unlink()
            paths['cache'].mkdir()
            paths['tmp'] = root.parent / 'escape'
            with self.assertRaisesRegex(ValueError, 'exact direct child'):
                c.validate_write_coverage(root, paths)

    def test_supervisor_failure_traces(self):
        scope = 'campaign3-test-scope'
        for failure in ('guardian_sigkill', 'supervisor_disconnect'):
            events = [{'at': 0.0, 'kind': failure, 'scope': scope},
                      {'at': 0.2, 'kind': 'abort', 'scope': scope},
                      {'at': 0.3, 'kind': 'scope_empty', 'scope': scope}]
            self.assertEqual(c.supervisor_trace(events, scope=scope)['decision'],
                             'SYNTHETIC_CONTRACT_PASS_DEVICE_HOLD')
            for bad in (events[:-1], [events[0], dict(events[1], at=5.1), dict(events[2], at=5.2)],
                        [events[0], dict(events[1], scope='session-7.scope'), events[2]]):
                self.assertEqual(c.supervisor_trace(bad, scope=scope)['decision'], 'NO_GO')

    def test_fresh_acquisition_and_independent_verifier(self):
        stream = frames()
        records = [{'run_id': 'run-1', 'observer_id': 'observer-1', 'acquired_at': float(i),
                    'feeds': {service: {'source_id': service + '-source', 'sequence': i,
                                       'proof': 'synthetic'} for service in c.SERVICES}}
                   for i in range(31)]
        check = lambda *args: True
        self.assertEqual(c.acquisition_contract(stream, records, run_id='run-1',
                          observer_id='observer-1', verify_provenance=check)['decision'],
                         'MONITOR_CONTRACT_PASS_DEVICE_HOLD')
        self.assertFalse(c.acquisition_contract(stream, records, run_id='run-1',
                         observer_id='observer-1', verify_provenance=check)['device_qualified'])
        self.assertIn('PROVENANCE_UNAUTHENTICATED', c.acquisition_contract(stream, records,
                      run_id='run-1', observer_id='observer-1',
                      verify_provenance=lambda *args: False)['reasons'])
        for mutate in (lambda r: r[15].update(acquired_at=14.0),
                       lambda r: r[15]['feeds']['carState'].update(sequence=14),
                       lambda r: r[15]['feeds']['carState'].update(source_id='switched'),
                       lambda r: r[15]['feeds']['carState'].update(source_id='pandaStates-source')):
            altered = copy.deepcopy(records)
            mutate(altered)
            self.assertEqual(c.acquisition_contract(stream, altered, run_id='run-1',
                             observer_id='observer-1', verify_provenance=check)['decision'], 'NO_GO')


if __name__ == '__main__':
    unittest.main()
