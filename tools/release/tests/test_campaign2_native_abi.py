import hashlib
from pathlib import Path
import tempfile
import unittest
from tools.release import campaign2_native_abi as abi


class NativeAbiTest(unittest.TestCase):
    def test_version_needs_are_scoped_to_each_library(self):
        output='''Version needs section '.gnu.version_r' contains 2 entries:
          0x0010: Version: 1  File: libc.so.6  Cnt: 1
          0x0020:   Name: GLIBC_2.38  Flags: none  Version: 5
          0x0030: Version: 1  File: libstdc++.so.6  Cnt: 1
          0x0040:   Name: GLIBCXX_3.4.30  Flags: none  Version: 6
'''
        self.assertEqual(abi.version_needs(output),{
            'libc.so.6':['GLIBC_2.38'], 'libstdc++.so.6':['GLIBCXX_3.4.30']})

    def test_wrong_arch_and_absent_sysroot_dependencies_hold(self):
        binary=Path('/bin/true')
        with tempfile.TemporaryDirectory() as tmp:
            report=abi.inspect(binary,Path(tmp),hashlib.sha256(binary.read_bytes()).hexdigest())
        self.assertEqual(report['classification'],'REPRESENTATIVE_STATIC_ABI_ONLY')
        self.assertEqual(report['static_decision'],'HOLD_STATIC_ABI_ISSUES')
        self.assertIn('not an ELF64 AArch64 binary',report['issues'])
        self.assertEqual(report['complete_product'],'NOT_BUILT')

    def test_invalid_hash_and_name_rejected(self):
        with self.assertRaisesRegex(ValueError,'binary hash mismatch'):
            abi.inspect(Path('/bin/true'),Path('/tmp'),'0'*64)
        with self.assertRaisesRegex(ValueError,'invalid shared library name'):
            abi.resolve_needed(Path('/tmp'),'../libc.so.6')


if __name__=='__main__':unittest.main()
