import unittest
import pandas as pd
from modules.hydrology_general import idf_from_p24_duration, rational_method_design
class TestRational(unittest.TestCase):
    def test_q(self):
        idf = idf_from_p24_duration(pd.DataFrame({'T_anios':[10],'P24_mm':[72]}), pd.DataFrame({'duracion_h':[1], 'Cd':[0.5]}), [10], [1])
        q = rational_method_design(1.0, idf, 1.0, 0.5, [10]).iloc[0]['Q_m3s']
        self.assertAlmostEqual(q, 5.0)
if __name__ == '__main__': unittest.main()
