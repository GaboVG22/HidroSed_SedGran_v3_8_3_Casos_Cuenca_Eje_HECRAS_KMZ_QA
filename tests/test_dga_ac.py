import unittest
from modules.hydrology_general import dga_ac_design
class TestDgaAc(unittest.TestCase):
    def test_qinst(self):
        df = dga_ac_design(10, alpha=1.2, ratios={10:1.0}, periods=[10])
        self.assertAlmostEqual(df.iloc[0]['Q_m3s'], 12.0)
if __name__ == '__main__': unittest.main()
