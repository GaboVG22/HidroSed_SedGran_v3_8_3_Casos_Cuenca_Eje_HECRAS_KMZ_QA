import unittest
from modules.external_audit_score import audit_external_report
class TestExternalAudit(unittest.TestCase):
    def test_missing_items(self):
        out = audit_external_report({'datos_cuenca': True, 'idf': False})
        self.assertIn('OBSERVADO', set(out['estado']))
if __name__ == '__main__': unittest.main()
