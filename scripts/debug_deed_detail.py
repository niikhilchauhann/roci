"""
Debug: fetch one deed detail page for each failing SRO and print raw text.
Usage: python scripts/debug_deed_detail.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roci_scraper.portals.igrsup import (
    _load_cookies, _load_villages, _fetch_all_villages,
    _filter_90_days, _fetch_deed_detail, _DISTRICT_CODE,
)
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import requests

FAILING_SROS = {"074": "Rudauli", "121": "Bikapur", "122": "Milkipur", "123": "Sohawal"}

def main():
    cookies = _load_cookies()
    villages = _load_villages()
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=90)

    for sro_code, sro_name in FAILING_SROS.items():
        print(f"\n{'='*60}")
        print(f"SRO {sro_code} ({sro_name})")
        all_rows = _fetch_all_villages(cookies, villages, sro_code)
        current_rows = _filter_90_days(all_rows, current_start, now)
        print(f"  {len(current_rows)} current-window deeds")
        if not current_rows:
            print("  No current rows — skipping")
            continue

        # Grab the first deed with _detail
        for row in current_rows[:5]:
            detail = row.get("_detail")
            if not detail:
                continue
            print(f"  Fetching deed detail for: {row.get('registration_no')}")
            from roci_scraper.portals.igrsup import _DETAIL_URL, _HEADERS
            try:
                resp = requests.post(
                    _DETAIL_URL, data=detail,
                    cookies=cookies, headers=_HEADERS, timeout=20,
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                lines = [l.strip() for l in soup.get_text(separator="\n").splitlines() if l.strip()]
                print(f"  Total lines: {len(lines)}")
                # Print lines containing area/consideration keywords
                kws = ["क्षेत्रफल", "area", "Area", "sqft", "sqm", "बिस्वा", "वर्ग", "प्रतिफल",
                       "विचार", "amount", "मूल्य", "रुपये"]
                found_any = False
                for i, line in enumerate(lines):
                    if any(kw in line for kw in kws):
                        found_any = True
                        print(f"    [{i}] >>> {line}")
                        for j in range(i+1, min(i+5, len(lines))):
                            print(f"    [{j}]     {lines[j]}")
                if not found_any:
                    print("  No keyword matches! First 60 lines:")
                    for i, l in enumerate(lines[:60]):
                        print(f"    [{i}] {l}")
                # Save HTML for inspection
                out_path = Path(f"out/debug_deed_{sro_code}.html")
                out_path.write_text(resp.text, encoding="utf-8")
                print(f"  Saved → {out_path}")
            except Exception as exc:
                print(f"  Error: {exc}")
            break  # just one deed per SRO

if __name__ == "__main__":
    main()
