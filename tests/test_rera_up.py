"""
Tests for ReraUpAdapter — no live network calls.

Mock strategy:
  _search_with_playwright → returns fake row dicts directly (bypasses browser + CAPTCHA)
  _fetch_cert_pdf         → returns fake detail dict (bypasses HTTP + PDF parsing)
  geocode_nominatim       → fixed coords keyed on village/name
"""
from __future__ import annotations

from unittest.mock import patch

from roci_scraper.portals.rera_up import ReraUpAdapter

LAT, LNG = 26.7954, 82.1942

_ROWS_AYODHYA = [
    {
        'reg_number': 'UPRERAPRJ15615',
        'reg_date': '1/10/2025',
        'name': 'Shri Ram Residency',
        'promoter': 'ABC Builders',
        'district': 'Ayodhya',
        'project_type': 'Residential',
        'cert_url': 'https://uprera.azurewebsites.net/ViewDocument?Param=111.pdf',
    },
    {
        'reg_number': 'UPRERAPRJ82351',
        'reg_date': '7/06/2025',
        'name': 'Ram Nagar Heights',
        'promoter': 'XYZ Realty',
        'district': 'Ayodhya',
        'project_type': 'Residential',
        'cert_url': 'https://uprera.azurewebsites.net/ViewDocument?Param=222.pdf',
    },
    {
        'reg_number': 'UPRERAPRJ75640',
        'reg_date': '1/11/2025',
        'name': 'Far Away Township',
        'promoter': 'GHI Developers',
        'district': 'Ayodhya',
        'project_type': 'Commercial',
        'cert_url': 'https://uprera.azurewebsites.net/ViewDocument?Param=333.pdf',
    },
]

_DETAILS = {
    'https://uprera.azurewebsites.net/ViewDocument?Param=111.pdf': {
        'Project Address': 'Civil Lines, Ayodhya',
        'Village/Locality/Sector': 'Civil Lines',
        'Tehsil': 'Sadar',
        'District/State': 'Ayodhya/Uttar Pradesh',
        'Proposed Completion Date': '01-01-2027',
        'Validity Period': '3 years',
    },
    'https://uprera.azurewebsites.net/ViewDocument?Param=222.pdf': {
        'Project Address': 'Naya Ghat, Ayodhya',
        'Village/Locality/Sector': 'Naya Ghat',
        'Tehsil': 'Sadar',
        'District/State': 'Ayodhya/Uttar Pradesh',
        'Proposed Completion Date': '01-06-2027',
        'Validity Period': '3 years',
    },
    'https://uprera.azurewebsites.net/ViewDocument?Param=333.pdf': {
        'Project Address': 'Distant location',
        'Village/Locality/Sector': 'Far Away',
        'Tehsil': 'Distant',
        'District/State': 'Ayodhya/Uttar Pradesh',
        'Proposed Completion Date': '01-01-2030',
        'Validity Period': '5 years',
    },
}


def _mock_geocode(query: str, **_kwargs):
    q = query.lower()
    if 'civil lines' in q:
        return (26.797, 82.196)   # ~0.3 km
    if 'naya ghat' in q:
        return (26.802, 82.201)   # ~1.0 km
    if 'far away' in q or 'distant' in q:
        return (26.900, 82.500)   # ~40 km
    return None


def _mock_fetch_cert(session, cert_url: str):
    return _DETAILS.get(cert_url, {})


@patch('roci_scraper.portals.rera_up._fetch_cert_pdf', side_effect=_mock_fetch_cert)
@patch('roci_scraper.portals.rera_up.geocode_nominatim', side_effect=_mock_geocode)
@patch('roci_scraper.portals.rera_up._search_with_playwright', return_value=_ROWS_AYODHYA)
def test_rera_filters_by_radius(mock_search, mock_geocode, mock_cert):
    result = ReraUpAdapter().scrape(lat=LAT, lng=LNG, district='Ayodhya')

    assert result.status == 'OK'
    projects = result.data['rera_projects']
    assert len(projects) == 2
    names = [p['name'] for p in projects]
    assert 'Shri Ram Residency' in names
    assert 'Ram Nagar Heights' in names
    assert all(p['distance_km'] <= 5.0 for p in projects)


@patch('roci_scraper.portals.rera_up._fetch_cert_pdf', side_effect=_mock_fetch_cert)
@patch('roci_scraper.portals.rera_up._search_with_playwright', return_value=_ROWS_AYODHYA)
def test_rera_detail_fields_captured(mock_search, mock_cert):
    result = ReraUpAdapter().scrape(lat=LAT, lng=LNG, district='Ayodhya', radius_km=None)

    projects = {p['name']: p for p in result.data['rera_projects']}
    sr = projects['Shri Ram Residency']
    assert sr['reg_number'] == 'UPRERAPRJ15615'
    assert sr['reg_date'] == '1/10/2025'
    assert sr['promoter'] == 'ABC Builders'
    assert sr['project_type'] == 'Residential'
    assert 'Civil Lines' in sr['detail'].get('Project Address', '')
    assert sr['detail'].get('Proposed Completion Date') == '01-01-2027'
    assert sr['cert_url'] == 'https://uprera.azurewebsites.net/ViewDocument?Param=111.pdf'


@patch('roci_scraper.portals.rera_up._search_with_playwright', return_value=[])
def test_rera_empty_search_returns_empty(mock_search):
    result = ReraUpAdapter().scrape(lat=LAT, lng=LNG, district='Ayodhya')

    assert result.status == 'EMPTY_PAGE'
    assert result.data['rera_projects'] == []