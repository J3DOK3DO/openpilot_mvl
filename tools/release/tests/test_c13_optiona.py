"""Campaign 13 fail-closed inventory and non-installable handoff checks."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('c13_optiona', Path(__file__).parents[1] / 'c13_optiona.py')
kit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kit)


class OptionATests(unittest.TestCase):
    def test_actual_source_inventory_hold(self):
        report = kit.inventory()
        self.assertEqual(report['release_status'], 'HOLD')
        self.assertFalse(report['install_allowed'])
        self.assertFalse(report['actuation_allowed'])
        self.assertFalse(report['ui_test_ready'])
        self.assertEqual(len(report['ui_files']), 4)

    def test_no_unplanned_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(kit, 'ARTIFACTS', Path(tmp)), patch.object(kit, 'inventory', return_value={'release_status': 'HOLD'}):
                self.assertEqual(kit.main(['preflight']), 0)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_path_traversal_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(kit, 'ARTIFACTS', root):
                for name in ('../escape', 'sub/entry', 'relative'):
                    with self.assertRaises(ValueError):
                        kit.checked_output(root / name if name != 'relative' else Path(name))
                target = root / 'target'
                target.write_text('x')
                link = root / 'link'
                link.symlink_to(target)
                with self.assertRaises(FileExistsError):
                    kit.checked_output(link)
                with self.assertRaises(ValueError):
                    kit.safe_file(link)

    def test_tampered_source_rejected(self):
        original = kit.safe_file
        def altered(path):
            data = original(path)
            return data + b'bad' if path.name == 'ui.py' else data
        with patch.object(kit, 'safe_file', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'differs from commit'):
                kit.inventory()

    def test_wrong_branch_or_source_identity_rejected(self):
        actual = kit.run_git
        for bad in ('branch', 'source'):
            def fake(repo, *args):
                if bad == 'branch' and args == ('branch', '--show-current'):
                    return 'wrong'
                if bad == 'source' and repo == kit.SOURCE and args == ('rev-parse', 'HEAD'):
                    return 'wrong'
                return actual(repo, *args)
            with patch.object(kit, 'run_git', side_effect=fake):
                with self.assertRaisesRegex(ValueError, 'wrong'):
                    kit.inventory()

    def test_missing_dependencies_never_green(self):
        report = kit.inventory(dependencies={'pytest': True, 'pyray': False, 'cffi': True})
        self.assertFalse(report['ui_test_ready'])
        self.assertFalse(report['literal_ui_preview_verified'])
        self.assertEqual(report['release_status'], 'HOLD')

    def test_package_is_non_installable_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(kit, 'ARTIFACTS', root):
                package = root / 'handoff'
                result = kit.make_package(kit.inventory(), package)
                self.assertFalse(result['install_allowed'])
                self.assertEqual(result['entrypoint_sha256'], kit.sha((package / 'status.py').read_bytes()))
                manifest = json.loads((package / 'manifest.json').read_text())
                self.assertEqual(manifest['release_status'], 'HOLD')
                self.assertEqual(sorted(x.name for x in package.iterdir()), ['README.txt', 'manifest.json', 'status.py'])
                with self.assertRaises(FileExistsError):
                    kit.make_package(result, package)

    def test_forged_preflight_cannot_claim_install_or_actuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(kit, 'ARTIFACTS', root):
                fake = kit.inventory()
                fake['install_allowed'] = True
                fake['actuation_allowed'] = True
                fake['release_status'] = 'GO'
                with self.assertRaisesRegex(ValueError, 'preflight'):
                    kit.make_package(fake, root / 'forged')
                self.assertFalse((root / 'forged').exists())
