import unittest
import pandas as pd
from modules.hydrology_general import idf_from_p24_duration, interpolate_intensity
class TestIdfModule(unittest.TestCase):
    def test_idf_formula(self):
        p24 = pd.DataFrame({'T_anios':[10], 'P24_mm':[100]})
        cd = pd.DataFrame({'duracion_h':[2], 'Cd':[0.5]})
        df = idf_from_p24_duration(p24, cd, periods=[10], durations_h=[2])
        self.assertAlmostEqual(df.iloc[0]['intensidad_mm_h'], 25.0)
        self.assertAlmostEqual(interpolate_intensity(df,10,2),25.0)
if __name__ == '__main__': unittest.main()
