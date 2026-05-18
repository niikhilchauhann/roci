from pathlib import Path
from roci_scraper.normalize import map_bhoomi_prakar


def test_bhoomi_mapping_fuzzy():
    ref_dir = Path("roci_scraper/ref_data")
    assert map_bhoomi_prakar("Aabadi residential plot", ref_dir) == 4
    assert map_bhoomi_prakar("unknown text", ref_dir) == 2
