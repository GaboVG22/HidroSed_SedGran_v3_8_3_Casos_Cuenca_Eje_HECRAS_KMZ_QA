import unittest
import pandas as pd
from modules.boundary_conditions import downstream_scenarios, audit_downstream_influence
class TestBoundary(unittest.TestCase):
    def test_scenarios(self):
        sc = downstream_scenarios(0, mean_sea_level_m=0.1, design_tide_m=1.0, storm_surge_m=0.2)
        self.assertGreaterEqual(len(sc), 3)
        prof = pd.DataFrame({'pk_m':[0,900,1000], 'T_anios':[100,100,100], 'cota_agua_m':[0.5,0.7,0.8]})
        aud = audit_downstream_influence(prof, sc, 200)
        self.assertFalse(aud.empty)
if __name__ == '__main__': unittest.main()
