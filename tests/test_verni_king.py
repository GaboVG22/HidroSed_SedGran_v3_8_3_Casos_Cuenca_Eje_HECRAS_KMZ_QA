import unittest
import pandas as pd
from modules.hydrology_general import verni_king_modified
class TestVerniKing(unittest.TestCase):
    def test_vk_positive(self):
        df = verni_king_modified(10, pd.DataFrame({'T_anios':[10], 'P24_mm':[80]}), c10=1.0, periods=[10])
        self.assertGreater(df.iloc[0]['Q_m3s'], 0)
        self.assertEqual(df.iloc[0]['metodo'], 'Verni-King Modificado')
if __name__ == '__main__': unittest.main()
