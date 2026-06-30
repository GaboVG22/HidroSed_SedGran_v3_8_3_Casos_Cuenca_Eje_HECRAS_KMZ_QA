import unittest
from modules.hydrology_general import tc_methods, select_tc_value
class TestTcMethods(unittest.TestCase):
    def test_tc_valid(self):
        df = tc_methods(10, 500, 30, rector_method='Mediana de métodos')
        self.assertGreater(df['tc_h'].dropna().median(), 0)
        val, name = select_tc_value(df, 'Mediana de métodos')
        self.assertGreater(val, 0)
        self.assertIn('Mediana', name)
if __name__ == '__main__': unittest.main()
