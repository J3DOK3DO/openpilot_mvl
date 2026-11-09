import unittest

from tools.release.combined_device_gate import evaluate, FROZEN_SOURCE


GOOD = f'''AGNOS_VERSION=19.9
ARCH=aarch64
ACTIVE_COMMIT={FROZEN_SOURCE}
OFFROAD_FLAG=1
ONROAD_FLAG=0
IGNITION_FLAG=0
/sys/class/power_supply/usb/online=1
/dev/sda12 94618759168 80194441216 10000000000 90% /data
MemAvailable: 3000000 kB
crw-rw---- 1 root gpu 235, 0 Nov 9 /dev/kgsl-3d0
'''


class DeviceGateTest(unittest.TestCase):
    def test_even_good_snapshot_is_not_live_qualification(self):
        result = evaluate(GOOD)
        self.assertFalse(result['device_compile_allowed'])
        self.assertEqual(result['gates']['independent_live_parked']['status'], 'UNKNOWN')
        self.assertEqual(result['gates']['hard_quota_and_scratch_peak']['status'], 'UNKNOWN')

    def test_windows_crlf_fields_are_parsed_without_relaxing_gate(self):
        result = evaluate(GOOD.replace('\n', '\r\n'))
        self.assertEqual(result['gates']['agnos_and_arch']['status'], 'PASS')
        self.assertEqual(result['gates']['active_source_identity']['status'], 'PASS')
        self.assertEqual(result['observations']['external_supply_online_values'], ['1'])
        self.assertFalse(result['device_compile_allowed'])

    def test_negative_inputs_fail_closed(self):
        cases = [
            (GOOD.replace('ARCH=aarch64', 'ARCH=x86_64'), 'agnos_and_arch', 'FAIL'),
            (GOOD.replace('10000000000', '7000000000'), 'data_free_8gib_reserve', 'FAIL'),
            (GOOD.replace('OFFROAD_FLAG=1\n', 'OFFROAD_FLAG=1IGNITION_FLAG=UNKNOWN\n'), 'independent_live_parked', 'UNKNOWN'),
            (GOOD.replace('usb/online=1', 'usb/online=0'), 'external_sustained_power', 'FAIL'),
            (GOOD.replace(FROZEN_SOURCE, '0' * 40), 'active_source_identity', 'FAIL'),
        ]
        for raw, name, expected in cases:
            with self.subTest(name=name):
                result = evaluate(raw)
                self.assertEqual(result['gates'][name]['status'], expected)
                self.assertFalse(result['device_compile_allowed'])


if __name__ == '__main__':
    unittest.main()
