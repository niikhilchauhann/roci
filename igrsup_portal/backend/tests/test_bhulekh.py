import pytest

from app.models.api import BhulekhRequest
from app.scrapers.bhulekh import BhulekhScraper


def test_parse_html_extracts_hindi_fields() -> None:
    scraper = BhulekhScraper()
    payload = BhulekhRequest(gatta_number="241", village="अयोध्या", tehsil="सदर", captcha_token="demo")
    html = """
    <table>
        <tr><td>गाटा संख्या</td><td>241</td></tr>
        <tr><td>ग्राम</td><td>अयोध्या</td></tr>
        <tr><td>तहसील</td><td>सदर</td></tr>
        <tr><td>नामांतरण की स्थिति</td><td>स्वीकृत</td></tr>
        <tr><td>भूमि प्रकार</td><td>आवासीय संभावित कृषि</td></tr>
        <tr><td>खातेदार</td><td>डेमो धारक</td></tr>
    </table>
    """

    record, metadata = scraper._parse_html(payload, html)

    assert record.gatta_number == "241"
    assert record.village == "अयोध्या"
    assert record.tehsil == "सदर"
    assert record.mutation_status == "स्वीकृत"
    assert record.bhoomi_prakar == "आवासीय संभावित कृषि"
    assert record.owner_name == "डेमो धारक"
    assert metadata["label_count"] >= 5


@pytest.mark.asyncio
async def test_lookup_returns_captcha_placeholder_without_token() -> None:
    scraper = BhulekhScraper()

    response = await scraper.lookup(BhulekhRequest(gatta_number="241", village="अयोध्या", tehsil="सदर"))

    assert response.status == "OK"
    assert response.record.mutation_status == "CAPTCHA_REQUIRED"
    assert response.scrape_metadata["captcha_required"] is True
    assert "portal_selectors" in response.scrape_metadata


@pytest.mark.asyncio
async def test_lookup_parses_mock_payload_when_token_present() -> None:
    scraper = BhulekhScraper()

    response = await scraper.lookup(
        BhulekhRequest(gatta_number="241", village="अयोध्या", tehsil="सदर", captcha_token="solver-token")
    )

    assert response.status == "OK"
    assert response.record.gatta_number == "241"
    assert response.record.village == "अयोध्या"
    assert response.record.tehsil == "सदर"
    assert response.scrape_metadata["captcha_used"] is True
