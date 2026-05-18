from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from loguru import logger

from ..browser import BrowserSession, detect_blocker
from ..extractors import best_table, extract_key_values_from_text, extract_table_records
from ..portal_utils import save_portal_json

class PortalResult:
    def __init__(self, portal: str, status: str, url: str, query: Dict[str, Any], data: Dict[str, Any], note: str = ''):
        self.portal = portal
        self.status = status
        self.url = url
        self.query = query
        self.data = data
        self.note = note

class PortalAdapter:
    portal_name: str = 'portal'
    url: str = ''

    def scrape(self, *, lat: float, lng: float, district: str, gatta_number: str | None = None, output_dir: Path | None = None, headless: bool = True) -> PortalResult:
        raise NotImplementedError

    def _snapshot(self, url: str, headless: bool = True):
        snap = BrowserSession(headless=headless).snapshot(url)
        blocker = detect_blocker(snap.html, snap.text)
        return snap, blocker

    def _save(self, output_dir: Path | None, result: PortalResult) -> None:
        save_portal_json(output_dir, result.portal, {
            'portal': result.portal,
            'status': result.status,
            'url': result.url,
            'query': result.query,
            'data': result.data,
            'note': result.note,
        })

    def _generic_parse(self, html: str, text: str, keywords: Iterable[str]) -> Dict[str, Any]:
        table = best_table(html, keywords)
        data = {
            'table_records': extract_table_records(table) if table is not None else [],
            'key_values': extract_key_values_from_text(text),
            'html_length': len(html),
            'body_length': len(text),
        }
        return data
