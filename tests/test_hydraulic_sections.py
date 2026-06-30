import unittest
import pandas as pd
from modules.hydraulic_hecras_like import hecras_like_steady_profile
class TestHydraulicSections(unittest.TestCase):
    def test_profile_runs(self):
        sec = pd.DataFrame({'section_id':[1,2], 'pk_m':[0,100]})
        pts = []
        for sid, pk, z in [(1,0,10),(2,100,9)]:
            for x,zz in [(-5,z+2),(0,z),(5,z+2)]: pts.append({'section_id':sid,'pk_m':pk,'offset_m':x,'z_m':zz})
        q = pd.DataFrame({'T_anios':[10], 'Q_m3s':[5]})
        out = hecras_like_steady_profile(sec, pd.DataFrame(pts), q, n_manning=0.035, slope_energy=0.01)
        self.assertEqual(len(out), 2)
        self.assertIn('cota_agua_m', out.columns)
if __name__ == '__main__': unittest.main()
