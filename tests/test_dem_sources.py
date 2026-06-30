from modules.dem_sources import (
    dem_source_registry,
    copernicus_tile_id,
    copernicus_tile_url,
    copernicus_tiles_for_bbox,
)


def test_dem_source_auth_matrix():
    reg = dem_source_registry()
    assert reg["opentopography"].requires_api_key is True
    assert reg["opentopography"].direct_in_app is True
    assert reg["copernicus_public_cog"].requires_api_key is False
    assert reg["copernicus_public_cog"].requires_login is False
    assert reg["copernicus_public_cog"].direct_in_app is True
    assert reg["nasa_earthdata"].requires_login is True
    assert reg["usgs_earthexplorer"].direct_in_app is False


def test_copernicus_tile_id_chile():
    assert copernicus_tile_id(-30, -71) == "Copernicus_DSM_COG_10_S30_00_W071_00_DEM"
    assert copernicus_tile_url(-30, -71).endswith(
        "/Copernicus_DSM_COG_10_S30_00_W071_00_DEM/Copernicus_DSM_COG_10_S30_00_W071_00_DEM.tif"
    )


def test_copernicus_tiles_for_bbox_crosses_degrees():
    bbox = {"south": -30.2, "north": -28.9, "west": -71.4, "east": -70.2}
    tiles = copernicus_tiles_for_bbox(bbox)
    ids = {t["tile_id"] for t in tiles}
    assert "Copernicus_DSM_COG_10_S30_00_W071_00_DEM" in ids
    assert "Copernicus_DSM_COG_10_S29_00_W071_00_DEM" in ids
    assert "Copernicus_DSM_COG_10_S31_00_W072_00_DEM" in ids
    assert "Copernicus_DSM_COG_10_S30_00_W072_00_DEM" in ids
    assert len(tiles) == 6
