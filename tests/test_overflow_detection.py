import unittest
import pandas as pd
from modules.hydraulic_visuals import detect_overflow_sections
class TestOverflow(unittest.TestCase):
    def test_overflow_true(self):
        prof = pd.DataFrame({'section_id':[1], 'pk_m':[0], 'T_anios':[100], 'cota_agua_m':[15]})
        pts = pd.DataFrame({'section_id':[1,1,1], 'pk_m':[0,0,0], 'offset_m':[-5,0,5], 'z_m':[12,10,12]})
        out = detect_overflow_sections(prof, pts)
        self.assertTrue(bool(out.iloc[0]['desborde_bool']))
if __name__ == '__main__': unittest.main()
