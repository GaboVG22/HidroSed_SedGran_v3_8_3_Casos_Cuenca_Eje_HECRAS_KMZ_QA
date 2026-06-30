import unittest
import pandas as pd
from modules.scour_protection import general_scour_methods, local_scour_preliminary, protection_design_preliminary
class TestScour(unittest.TestCase):
    def test_scour_positive(self):
        prof = pd.DataFrame({'section_id':[1], 'pk_m':[0], 'T_anios':[100], 'tirante_max_m':[2], 'velocidad_m_s':[3], 'Froude':[0.7], 'radio_hidraulico_m':[1.5], 'pendiente_energia':[0.01], 'cota_fondo_m':[10]})
        out = general_scour_methods(prof, 0.05, 0.15)
        self.assertEqual(out['metodo_socavacion_general'].nunique(), 4)
        loc = local_scour_preliminary(prof.iloc[0].to_dict(), 'pila', 1.0)
        self.assertGreater(loc['socavacion_local_m'], 0)
        prot = protection_design_preliminary(3, 40)
        self.assertFalse(prot.empty)
if __name__ == '__main__': unittest.main()
