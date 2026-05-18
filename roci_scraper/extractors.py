from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Tuple
import re

import pandas as pd
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

def html_tables(html: str) -> list[pd.DataFrame]:
    try:
        return pd.read_html(html)
    except Exception:
        return []

def table_text_score(df: pd.DataFrame, keywords: Iterable[str]) -> int:
    hay = ' '.join([str(c) for c in df.columns]) + ' ' + ' '.join(df.astype(str).fillna('').head(10).astype(str).values.flatten().tolist())
    hay = hay.lower()
    score = 0
    for kw in keywords:
        if kw.lower() in hay:
            score += 10
        score += max(fuzz.partial_ratio(kw.lower(), hay) // 10, 0)
    return score

def best_table(html: str, keywords: Iterable[str]) -> pd.DataFrame | None:
    tables = html_tables(html)
    if not tables:
        return None
    ranked = sorted(((table_text_score(df, keywords), df) for df in tables), key=lambda x: x[0], reverse=True)
    best_score, best_df = ranked[0]
    return best_df if best_score > 0 else None

def extract_key_values_from_text(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in [l.strip() for l in text.splitlines() if l.strip()]:
        if ':' in line:
            a, b = line.split(':', 1)
            a = re.sub(r'\s+', ' ', a).strip()
            b = re.sub(r'\s+', ' ', b).strip()
            if 1 <= len(a) <= 80 and 1 <= len(b) <= 200:
                out[a] = b
    return out

def extract_table_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None:
        return []
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df.fillna('').to_dict(orient='records')

def find_links(html: str, keywords: Iterable[str]) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    kws = [k.lower() for k in keywords]
    for a in soup.find_all('a', href=True):
        txt = ' '.join(a.get_text(' ', strip=True).split())
        low = txt.lower()
        if any(k in low for k in kws):
            out.append((txt, a['href']))
    return out
