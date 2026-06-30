import unittest
from modules.external_audit_score import audit_external_report, technical_score
class TestScore(unittest.TestCase):
    def test_cap(self):
        aud = audit_external_report({'datos_cuenca': True, 'idf': True, 'criterio_promedio': True, 'adopta_maximo': True})
        sc = technical_score(aud)
        summary = sc[sc['tipo']=='resumen'].iloc[0]
        self.assertLessEqual(summary['nota_global'], 8.4)
if __name__ == '__main__': unittest.main()
