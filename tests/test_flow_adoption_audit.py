import unittest
import pandas as pd
from modules.hydrology_general import adopt_design_flows
class TestAdoption(unittest.TestCase):
    def test_average_contradiction(self):
        a = pd.DataFrame({'T_anios':[10], 'metodo':['A'], 'Q_m3s':[10]})
        b = pd.DataFrame({'T_anios':[10], 'metodo':['B'], 'Q_m3s':[20]})
        out = adopt_design_flows([a,b], criterion='Máximo', declared_criterion='Promedio')
        self.assertEqual(out.iloc[0]['semaforo'], 'rojo')
if __name__ == '__main__': unittest.main()
