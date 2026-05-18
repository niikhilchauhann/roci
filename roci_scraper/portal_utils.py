from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Dict
from urllib.parse import urljoin

from .browser import BrowserSession, detect_blocker
from .extractors import best_table, extract_key_values_from_text, extract_table_records, find_links, html_tables
from .utils import save_json

def portal_snapshot(url: str, headless: bool = True) -> dict[str, Any]:
    snap = BrowserSession(headless=headless).snapshot(url)
    blocker = detect_blocker(snap.html, snap.text)
    return {'snapshot': snap, 'blocker': blocker}

def try_follow_keywords(url: str, keywords: Iterable[str], headless: bool = True) -> dict[str, Any]:
    snap = BrowserSession(headless=headless).click_text(url, keywords)
    blocker = detect_blocker(snap.html, snap.text)
    return {'snapshot': snap, 'blocker': blocker}

def parse_generic_page(html: str, text: str, keywords: Iterable[str]) -> dict[str, Any]:
    table = best_table(html, keywords)
    kv = extract_key_values_from_text(text)
    return {
        'table': extract_table_records(table) if table is not None else [],
        'columns': list(table.columns) if table is not None else [],
        'key_values': kv,
        'table_count': len(html_tables(html)),
    }

def save_portal_json(output_dir: Path | None, portal: str, payload: dict[str, Any]) -> None:
    if output_dir is None:
        return
    save_json(output_dir / f'{portal}.json', payload)
