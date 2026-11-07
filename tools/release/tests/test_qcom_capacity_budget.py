import unittest
from tools.release import qcom_capacity_budget as b
class CapacityBudgetTest(unittest.TestCase):
 def test_unknown_peak_never_goes_green(self):
  result=b.calculate(9*b.GIB)
  self.assertEqual(result['classification'],'REQUIRED_CAPACITY_UNKNOWN')
  self.assertEqual(len(result['scenarios']),6)
  self.assertTrue(all(row['decision'].startswith('NO_GO_') for row in result['scenarios']))
 def test_low_disk_and_copy_accounting(self):
  low=b.calculate(1*b.GIB)
  self.assertTrue(all(row['decision']=='NO_GO_ESTIMATE_EXCEEDS_FREE' for row in low['scenarios']))
  a=b.calculate(9*b.GIB);c=b.calculate(9*b.GIB,include_archive_copy=True)
  self.assertEqual(c['scenarios'][0]['scenario_total_bytes']-a['scenarios'][0]['scenario_total_bytes'],b.ARCHIVE_BYTES+b.EXTRACTED_BYTES)
 def test_invalid_observation(self):
  for value in (-1,True,None):
   with self.assertRaises(ValueError):b.calculate(value)
if __name__=='__main__':unittest.main()
