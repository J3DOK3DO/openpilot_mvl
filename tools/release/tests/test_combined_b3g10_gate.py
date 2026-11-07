"""Windows/Python 3.9 offline tests. Temp files remain inside the campaign checkout."""
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tools.release import combined_b3g10_gate as gate


class CombinedGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='combined-b3g10-', dir=gate.ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, value, name='claims.json'):
        path = self.root / name
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def blocked(self, result):
        self.assertEqual(result['decision'], gate.DECISION)
        self.assertEqual(result['b3_status'], 'B3_NATIVE_PROVIDER_MISSING')
        self.assertEqual(result['g10_status'], 'G10_PRODUCT_BUILD_INCOMPLETE')
        self.assertEqual(result['rc_status'], 'RC_NOT_INSTALLABLE')
        self.assertEqual(result['device_status'], 'DEVICE_NOT_QUALIFIED')
        self.assertEqual(result['b3_verified_artifact_count'], 0)
        self.assertEqual(result['b3_static_candidate_count'], 0)
        self.assertEqual(result['physical_checks_passed'], 0)
        self.assertFalse(result['install_allowed'])

    def test_pinned_defaults_and_six_absences(self):
        result = gate.evaluate(artifacts=self.root)
        self.blocked(result)
        self.assertEqual(set(result['artifact_inventory']), set(gate.NAMES))
        self.assertEqual(set(result['artifact_inventory'].values()), {'ABSENT_IN_LOCAL_CHECKOUT'})
        self.assertEqual(result['b3_local_present_count'], 0)
        self.assertEqual(result['b2_safety_status'], 'NOT_SAFETY_ACCEPTED_NOT_PASSED')

    def test_forged_six_records_and_bytes_remain_unverified(self):
        records = []
        for name in gate.NAMES:
            (self.root / name).write_bytes(b'not a genuine capture')
            records.append({'artifact': name, 'sha256': '0' * 64,
                            'gpu_backend': 'QCOM', 'compiler_exit_code': 0,
                            'quality_result': 'PASS_INDEPENDENT_REVIEW'})
        claim = self.write({'source_commit': gate.SOURCE, 'records': records})
        result = gate.evaluate(claims=claim, artifacts=self.root)
        self.blocked(result)
        self.assertEqual(result['b3_local_present_count'], 6)
        self.assertIn('EXTERNAL_CLAIMS_UNAUTHENTICATED_NO_TRUST_ROOT', result['issues'])

    def test_fake_safety_booleans_cannot_override(self):
        for value in (True, 'PASS', 1, {'passed': True}):
            with self.subTest(value=value):
                claim = self.write({'source_commit': gate.SOURCE, 'b2_safety_status': value,
                                    'install_allowed': True, 'g10_promotion': True})
                result = gate.evaluate(claims=claim, artifacts=self.root)
                self.blocked(result)
                self.assertEqual(result['b2_safety_status'], 'NOT_SAFETY_ACCEPTED_NOT_PASSED')

    def test_false_cold_build_claim(self):
        claim = self.write({'source_commit': gate.SOURCE, 'cold_arm64_product': 'PASS',
                            'g10_status': 'COMPLETE', 'full_product_build': True})
        result = gate.evaluate(claims=claim, artifacts=self.root)
        self.blocked(result)
        self.assertEqual(result['g10_cold_build'], 'NOT_BUILT')

    def test_bogus_independent_review(self):
        claim = self.write({'source_commit': gate.SOURCE, 'independent_review': 'PASS',
                            'review_sha256': 'a' * 64, 'physical_checks_passed': 10})
        result = gate.evaluate(claims=claim, artifacts=self.root)
        self.blocked(result)
        self.assertEqual(result['independent_combined_review'], 'PENDING')

    def test_syntactic_hashes_and_fake_signature_are_not_authority(self):
        claim = self.write({'source_commit': gate.SOURCE, 'sha256': 'f' * 64,
                            'signature': 'valid', 'public_key': 'attacker-selected',
                            'signature_verified': True})
        self.blocked(gate.evaluate(claims=claim, artifacts=self.root))

    def test_stale_external_source(self):
        for source in ('0' * 40, None, gate.SOURCE.upper()):
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, 'source'):
                    gate.evaluate(claims=self.write({'source_commit': source}))

    def test_every_altered_plan_field_rejected(self):
        plan = gate.load(gate.PLAN)
        for field in plan:
            with self.subTest(field=field):
                altered = dict(plan, **{field: None})
                with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    gate.evaluate(plan=self.write(altered))

    def test_same_semantics_changed_plan_bytes_rejected(self):
        path = self.root / 'plan.json'
        path.write_bytes(gate.PLAN.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            gate.evaluate(plan=path)

    def test_changed_recovery_cannot_approve(self):
        state = gate.load(gate.RECOVERY)
        state['b3_verified_artifact_count'] = 6
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            gate.evaluate(recovery=self.write(state))

    def test_json_rejections(self):
        for raw in (b'{', b'[]', b'{"x":1,"x":2}', b'{"x":NaN}',
                    b'{"x":Infinity}', b'\xff', b'{"nested":{"x":1,"x":2}}'):
            with self.subTest(raw=raw):
                path = self.root / 'bad.json'
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    gate.load(path)

    def test_oversized_json(self):
        path = self.root / 'large.json'
        path.write_bytes(b' ' * (gate.LIMIT + 1))
        with self.assertRaisesRegex(ValueError, 'oversized'):
            gate.load(path)

    def test_directory_is_not_json(self):
        with self.assertRaises((OSError, ValueError)):
            gate.load(self.root)

    def test_missing_json(self):
        with self.assertRaises(OSError):
            gate.load(self.root / 'absent.json')

    def test_network_device_and_parent_paths_rejected_before_metadata_access(self):
        paths = ['//untrusted/share/claims.json', '../claims.json']
        if os.name == 'nt':
            paths += [r'\\.\NUL', 'NUL', 'claims.json:stream', r'\\?\D:\claims.json']
        for path in paths:
            with self.subTest(path=path), patch.object(Path, 'lstat', side_effect=AssertionError('metadata access')):
                with self.assertRaises(ValueError):
                    gate.load(path)

    def test_reparse_attribute_rejected(self):
        info = SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
        with patch.object(Path, 'lstat', return_value=info):
            with self.assertRaisesRegex(ValueError, 'reparse'):
                gate.regular(self.root / 'junction')

    def test_symlink_rejected_without_privilege_requirement(self):
        if os.name != 'nt':
            (self.root / 'link.json').symlink_to(self.write({'safe': True}))
            with self.assertRaises((ValueError, OSError)):
                gate.load(self.root / 'link.json')
        else:
            info = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
            with patch.object(Path, 'lstat', return_value=info):
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    gate.load(self.root / 'link.json')

    def test_artifact_link_rejected(self):
        if os.name != 'nt':
            (self.root / gate.NAMES[0]).symlink_to(self.write({'safe': True}))
            with self.assertRaisesRegex(ValueError, 'symlink'):
                gate.evaluate(artifacts=self.root)
        else:
            original = gate.regular
            def check(path, directory=False):
                if path.name == gate.NAMES[0]:
                    raise ValueError('symlink/reparse point refused')
                return original(path, directory)
            with patch.object(gate, 'regular', side_effect=check):
                with self.assertRaisesRegex(ValueError, 'reparse'):
                    gate.evaluate(artifacts=self.root)

    def test_cli_always_nonzero_and_json_hold(self):
        with redirect_stdout(io.StringIO()) as output:
            code = gate.main(['--artifacts', str(self.root)])
        self.assertEqual(code, 2)
        self.blocked(json.loads(output.getvalue()))

    def test_cli_bad_input_is_nonzero_json(self):
        with redirect_stdout(io.StringIO()) as output:
            code = gate.main(['--plan', str(self.root / 'missing')])
        self.assertEqual(code, 2)
        result = json.loads(output.getvalue())
        self.assertEqual(result['decision'], gate.DECISION)
        self.assertFalse(result['install_allowed'])
        self.assertIn('input_error', result)


    def test_safe_regular_file_native_read(self):
        self.assertEqual(gate.load(self.write({'safe': True})), {'safe': True})

    def test_inventory_network_paths_no_filesystem_access(self):
        for path in ('//arbitrary.invalid/share/models', r'\\arbitrary.invalid\share\models',
                     r'\\?\UNC\arbitrary.invalid\share'):
            with self.subTest(path=path), patch.object(gate, 'WindowsLocks') as api, \
                    patch.object(gate.os, 'open', side_effect=AssertionError('open')), \
                    patch.object(Path, 'lstat', side_effect=AssertionError('lstat')):
                with self.assertRaises(ValueError):
                    gate.inventory_artifacts(path)
                api.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Windows handle contract')
    def test_missing_sparse_component_stops_all_child_lookups(self):
        api = Mock()
        api.open.side_effect = [10, FileNotFoundError('sparse')]
        with patch.object(gate, 'WindowsLocks', return_value=api), \
                patch.object(Path, 'lstat', side_effect=AssertionError('child access')):
            result = gate.inventory_artifacts(self.root / 'missing' / 'deeper')
        self.assertEqual(set(result.values()), {'ABSENT_IN_LOCAL_CHECKOUT'})
        self.assertEqual(api.open.call_count, 2)
        api.close.assert_called_once_with(10)

    @unittest.skipUnless(os.name == 'nt', 'Windows handle contract')
    def test_windows_createfile_directory_read_share_only_contract(self):
        api = gate.WindowsLocks()
        api.kernel = Mock()
        api.kernel.GetDriveTypeW.return_value = 3
        api.create = Mock(return_value=123)
        self.assertEqual(api.open(self.root, True), 123)
        args = api.create.call_args[0]
        self.assertEqual(args[1], 0x81)
        self.assertEqual(args[2], 1)  # no FILE_SHARE_WRITE or FILE_SHARE_DELETE
        self.assertEqual(args[5], 0x02200000)
        api.kernel.GetDriveTypeW.return_value = 4
        api.create.reset_mock()
        with self.assertRaisesRegex(ValueError, 'local drive'):
            api.open(self.root, True)
        api.create.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Windows handle contract')
    def test_windows_all_ancestor_handles_retained_for_six_checks(self):
        api = Mock()
        api.open.side_effect = range(100, 200)
        expected = len(self.root.parents) + 1
        def metadata(path, directory=False):
            self.assertEqual(api.open.call_count, expected)
            api.close.assert_not_called()
        with patch.object(gate, 'WindowsLocks', return_value=api), \
                patch.object(gate, 'regular', side_effect=metadata) as check:
            result = gate.inventory_artifacts(self.root)
        self.assertEqual(check.call_count, 6)
        self.assertEqual(api.close.call_count, expected)
        self.assertEqual(api.validate.call_count, 2 * expected)
        self.assertEqual(set(result.values()), {'PRESENT_UNVERIFIED'})

    @unittest.skipUnless(os.name == 'nt', 'Windows handle contract')
    def test_windows_sharing_violation_fails_closed_and_closes_ancestors(self):
        api = Mock()
        api.open.side_effect = [10, OSError(32, 'sharing violation')]
        with patch.object(gate, 'WindowsLocks', return_value=api), \
                patch.object(gate, 'regular') as check:
            with self.assertRaises(OSError):
                gate.inventory_artifacts(self.root)
        check.assert_not_called()
        api.close.assert_called_once_with(10)

    @unittest.skipUnless(os.name == 'nt', 'Windows handle contract')
    def test_windows_ancestor_swap_reparse_and_final_path_race(self):
        for stage in ('acquire', 'release'):
            with self.subTest(stage=stage):
                api = Mock()
                api.open.side_effect = range(100, 200)
                count = len(self.root.parents) + 1
                calls = [None] * (1 if stage == 'acquire' else count)
                api.validate.side_effect = calls + [ValueError('reparse/final path mismatch')] + [None] * (2 * count)
                with patch.object(gate, 'WindowsLocks', return_value=api):
                    with self.assertRaisesRegex(ValueError, 'reparse/final path'):
                        gate.inventory_artifacts(self.root)
                self.assertEqual(api.close.call_count, api.open.call_count)

    @unittest.skipUnless(os.name == 'nt', 'Windows handle contract')
    def test_windows_handle_reparse_and_final_path_validation(self):
        api = gate.WindowsLocks()
        def attrs(handle, kind, data, size):
            data[0] = 0x410
            return 1
        api.kernel = Mock()
        api.kernel.GetFileInformationByHandleEx.side_effect = attrs
        with self.assertRaisesRegex(ValueError, 'reparse'):
            api.validate(123, self.root, True)
        def normal_attrs(handle, kind, data, size):
            data[0] = 0x10
            return 1
        def final_path(handle, buf, size, flags):
            buf.value = r'\\?\UNC\untrusted.invalid\share'
            return len(buf.value)
        api.kernel.GetFileInformationByHandleEx.side_effect = normal_attrs
        api.kernel.GetFinalPathNameByHandleW.side_effect = final_path
        with self.assertRaisesRegex(ValueError, 'nonlocal'):
            api.validate(123, self.root, True)

    def test_posix_inventory_uses_held_fd_after_simulated_ancestor_swap(self):
        @contextmanager
        def held(path, missing_ok=False):
            yield 71  # ancestor pathname now points elsewhere; fd remains original
        with patch.object(gate.os, 'name', 'posix'), \
                patch.object(gate, 'locked_directory', held), \
                patch.object(gate.os, 'stat', return_value=SimpleNamespace(st_mode=stat.S_IFREG)) as lookup, \
                patch.object(Path, 'lstat', side_effect=AssertionError('unpinned path')):
            result = gate.inventory_artifacts(PurePosixPath('/local/models'))
        self.assertEqual(set(result.values()), {'PRESENT_UNVERIFIED'})
        self.assertEqual(lookup.call_count, 6)
        for call, name in zip(lookup.call_args_list, gate.NAMES):
            self.assertEqual(call[0], (name,))
            self.assertEqual(call[1], {'dir_fd': 71, 'follow_symlinks': False})

    def test_posix_nonregular_rejected_before_any_final_open(self):
        @contextmanager
        def held(path):
            yield 71
        for mode in (stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFLNK):
            with self.subTest(mode=mode), patch.object(gate.os, 'name', 'posix'), \
                    patch.object(gate, 'local_path', return_value=PurePosixPath('/local/input')), \
                    patch.object(gate, 'locked_directory', held), \
                    patch.object(gate.os, 'stat', return_value=SimpleNamespace(st_mode=mode)), \
                    patch.object(gate.os, 'open', side_effect=AssertionError('device open')) as opened:
                with self.assertRaises(ValueError):
                    gate.load('/local/input')
                opened.assert_not_called()

    def test_posix_raced_device_only_path_pinned_never_read_opened(self):
        @contextmanager
        def held(path):
            yield 71
        with patch.object(gate.os, 'name', 'posix'), \
                patch.object(gate, 'local_path', return_value=PurePosixPath('/local/input')), \
                patch.object(gate, 'locked_directory', held), \
                patch.object(gate.os, 'O_PATH', 0x200000, create=True), \
                patch.object(gate.os, 'O_NOFOLLOW', 0x20000, create=True), \
                patch.object(gate.os, 'stat', return_value=SimpleNamespace(st_mode=stat.S_IFREG)), \
                patch.object(gate.os, 'fstat', return_value=SimpleNamespace(st_mode=stat.S_IFCHR)), \
                patch.object(gate.os, 'open', return_value=72) as opened, \
                patch.object(gate.os, 'close') as closed:
            with self.assertRaisesRegex(ValueError, 'nonregular'):
                gate.load('/local/input')
            opened.assert_called_once_with('input', 0x220000, dir_fd=71)
            closed.assert_called_once_with(72)

    @unittest.skipIf(hasattr(os, 'O_PATH'), 'O_PATH is available on this host')
    def test_posix_no_opath_fails_closed(self):
        @contextmanager
        def held(path):
            yield 71
        with patch.object(gate.os, 'name', 'posix'), \
                patch.object(gate, 'local_path', return_value=PurePosixPath('/local/input')), \
                patch.object(gate, 'locked_directory', held), \
                patch.object(gate.os, 'stat', return_value=SimpleNamespace(st_mode=stat.S_IFREG)), \
                patch.object(gate.os, 'open', side_effect=AssertionError('unsafe fallback')):
            # Windows host has no O_PATH: exercise portable fail-closed branch.
            self.assertFalse(hasattr(gate.os, 'O_PATH'))
            with self.assertRaisesRegex(ValueError, 'O_PATH'):
                gate.load('/local/input')


    @unittest.skipUnless(os.name == 'nt', 'Windows sharing contract')
    def test_native_directory_lock_denies_generic_write_during_read(self):
        import ctypes
        api = gate.WindowsLocks()
        path = self.write({'safe': True})
        with gate.locked_path(path) as stream:
            for component in (self.root, path):
                handle = api.create(str(component), 0x40000000, 7, None, 3, 0x02200000, None)
                if handle != api.invalid:
                    api.close(handle)
                    self.fail('held path allowed GENERIC_WRITE access')
                self.assertEqual(ctypes.get_last_error(), 32)
            self.assertEqual(json.loads(stream.read()), {'safe': True})

    def test_posix_exact_held_regular_inode_reopen_and_mismatch(self):
        @contextmanager
        def held(path):
            yield 71
        for mismatch in (False, True):
            with self.subTest(mismatch=mismatch):
                stream = Mock()
                stream.fileno.return_value = 73
                stream.read.return_value = b'{}'
                stream.__enter__ = Mock(return_value=stream)
                stream.__exit__ = Mock(return_value=False)
                info = SimpleNamespace(st_mode=stat.S_IFREG, st_dev=1, st_ino=2, st_size=2)
                other = SimpleNamespace(st_mode=stat.S_IFREG, st_dev=1, st_ino=3, st_size=2)
                with patch.object(gate.os, 'name', 'posix'), \
                        patch.object(gate, 'local_path', return_value=PurePosixPath('/local/input')), \
                        patch.object(gate, 'locked_directory', held), \
                        patch.object(gate.os, 'O_PATH', 0x200000, create=True), \
                        patch.object(gate.os, 'O_NOFOLLOW', 0x20000, create=True), \
                        patch.object(gate.os, 'O_NONBLOCK', 0x800, create=True), \
                        patch.object(gate.os, 'stat', return_value=info), \
                        patch.object(gate.os, 'fstat', side_effect=[info, other if mismatch else info, info]), \
                        patch.object(gate.os, 'open', side_effect=[72, 73]) as opened, \
                        patch.object(gate.os, 'fdopen', return_value=stream), \
                        patch.object(gate.os, 'close') as closed:
                    if mismatch:
                        with self.assertRaisesRegex(ValueError, 'inode mismatch'):
                            gate.load('/local/input')
                        stream.read.assert_not_called()
                    else:
                        self.assertEqual(gate.load('/local/input'), {})
                    self.assertEqual(opened.call_args_list[1][0], ('/proc/self/fd/72', os.O_RDONLY | 0x800))
                    closed.assert_called_once_with(72)

    def test_posix_missing_procfs_fails_closed_without_path_fallback(self):
        @contextmanager
        def held(path):
            yield 71
        info = SimpleNamespace(st_mode=stat.S_IFREG)
        with patch.object(gate.os, 'name', 'posix'), \
                patch.object(gate, 'local_path', return_value=PurePosixPath('/local/input')), \
                patch.object(gate, 'locked_directory', held), \
                patch.object(gate.os, 'O_PATH', 0x200000, create=True), \
                patch.object(gate.os, 'O_NOFOLLOW', 0x20000, create=True), \
                patch.object(gate.os, 'O_NONBLOCK', 0x800, create=True), \
                patch.object(gate.os, 'stat', return_value=info), \
                patch.object(gate.os, 'fstat', return_value=info), \
                patch.object(gate.os, 'open', side_effect=[72, FileNotFoundError('no procfs')]) as opened, \
                patch.object(gate.os, 'close') as closed:
            with self.assertRaises(FileNotFoundError):
                gate.load('/local/input')
            self.assertEqual(opened.call_count, 2)
            closed.assert_called_once_with(72)


    @unittest.skipUnless(os.name == 'nt', 'Windows sharing contract')
    def test_native_existing_directory_writer_refuses_inventory(self):
        api = gate.WindowsLocks()
        handle = api.create(str(self.root), 0x40000000, 7, None, 3, 0x02200000, None)
        self.assertNotEqual(handle, api.invalid)
        try:
            with self.assertRaises(OSError) as error:
                gate.inventory_artifacts(self.root)
            self.assertEqual(error.exception.winerror, 32)
        finally:
            api.close(handle)

    def test_artifact_metadata_never_opens_artifact_bytes(self):
        for name in gate.NAMES:
            (self.root / name).write_bytes(b'never unpickle')
        original = gate.WindowsLocks.open
        def only_directories(api, path, directory):
            self.assertTrue(directory)
            self.assertNotIn(path.name, gate.NAMES)
            return original(api, path, directory)
        posix_open = gate.os.open
        def no_artifact_open(path, *args, **kwargs):
            self.assertNotIn(str(path), gate.NAMES)
            return posix_open(path, *args, **kwargs)
        with patch.object(gate.WindowsLocks, 'open', only_directories), \
                patch.object(gate.os, 'open', side_effect=no_artifact_open):
            result = gate.inventory_artifacts(self.root)
        self.assertEqual(set(result.values()), {'PRESENT_UNVERIFIED'})


if __name__ == '__main__':
    unittest.main()
