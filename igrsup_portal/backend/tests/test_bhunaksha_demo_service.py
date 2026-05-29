from app.scrapers.bhunaksha import BhunakshaScraper


def test_get_villages_returns_demo_rows() -> None:
    scraper = BhunakshaScraper()

    villages = scraper.get_villages(district="Ayodhya", tehsil="Sadar")

    assert villages
    assert any(row["gis_code"] == "14600766124649" for row in villages)


def test_generate_gis_code_resolves_demo_village() -> None:
    scraper = BhunakshaScraper()

    gis_code = scraper.generate_gis_code(district="Ayodhya", tehsil="Sadar", village="Demo Village")

    assert gis_code == "14600766124649"


def test_parse_plot_info_extracts_expected_fields() -> None:
    scraper = BhunakshaScraper()
    response_text = (
        "Khata No: 00215 Plot No: 30 Area : 0.7070 Hectare "
        "Owner Details For Khata No.:- 00215 1 :- नाम : घनश्याम संरक्षक का नाम : सीताराम भारद्वाज"
    )

    parsed = scraper.parse_plot_info(response_text)

    assert parsed["plot_number"] == "30"
    assert parsed["khata_number"] == "00215"
    assert parsed["owner_name"] == "घनश्याम"
    assert parsed["area"] == "0.7070"
