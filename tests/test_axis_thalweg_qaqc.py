
import unittest
import pandas as pd

from modules.axis_thalweg_qaqc import verify_and_snap_axis_to_section_minima, summarize_axis_thalweg_qa


class TestAxisThalwegQAQC(unittest.TestCase):
    def test_auto_axis_is_recentered_to_lowest_point(self):
        sec = pd.DataFrame({
            "section_id": [1],
            "pk_m": [0.0],
            "lon_eje": [-71.0],
            "lat_eje": [-30.0],
            "cota_fondo_m": [100.0],
        })
        pts = pd.DataFrame({
            "section_id": [1, 1, 1],
            "pk_m": [0.0, 0.0, 0.0],
            "offset_m": [-10.0, 5.0, 10.0],
            "z_m": [101.0, 98.0, 102.0],
            "lon": [-71.001, -71.0005, -70.999],
            "lat": [-30.0, -30.0005, -30.0],
        })
        sec2, pts2, qa, axis = verify_and_snap_axis_to_section_minima(
            sec, pts, axis_source="automatico_preliminar", tolerance_m=0.5
        )
        self.assertTrue(bool(qa.iloc[0]["correccion_aplicada"]))
        # El punto más bajo queda ahora en offset 0.
        min_row = pts2.loc[pts2["z_m"].idxmin()]
        self.assertAlmostEqual(float(min_row["offset_m"]), 0.0, places=6)
        self.assertAlmostEqual(float(sec2.iloc[0]["cota_fondo_m"]), 98.0, places=6)
        self.assertEqual(sec2.iloc[0]["criterio_eje_thalweg"], "eje_automatico_recentrado_al_punto_mas_bajo")

    def test_manual_axis_only_reports_difference(self):
        sec = pd.DataFrame({"section_id": [1], "pk_m": [0.0], "lon_eje": [-71.0], "lat_eje": [-30.0]})
        pts = pd.DataFrame({
            "section_id": [1, 1, 1],
            "pk_m": [0.0, 0.0, 0.0],
            "offset_m": [-10.0, 5.0, 10.0],
            "z_m": [101.0, 98.0, 102.0],
            "lon": [-71.001, -71.0005, -70.999],
            "lat": [-30.0, -30.0005, -30.0],
        })
        sec2, pts2, qa, axis = verify_and_snap_axis_to_section_minima(
            sec, pts, axis_source="manual_kmz", tolerance_m=0.5
        )
        self.assertFalse(bool(qa.iloc[0]["correccion_aplicada"]))
        self.assertEqual(str(qa.iloc[0]["estado"]), "REVISAR")
        # Offset no se cambia en eje manual.
        min_row = pts2.loc[pts2["z_m"].idxmin()]
        self.assertAlmostEqual(float(min_row["offset_m"]), 5.0, places=6)
        self.assertIsNone(axis)
        summary = summarize_axis_thalweg_qa(qa)
        self.assertEqual(summary["n_revisar"], 1)


if __name__ == "__main__":
    unittest.main()
