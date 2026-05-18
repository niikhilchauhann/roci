from __future__ import annotations
from typing import Dict, Any

def cross_validate(payload: Dict[str, Any]) -> tuple[int, int]:
    conflicts = 0
    pairs = 0
    if payload.get('clu_current') is not None and payload.get('clu_permitted') is not None:
        pairs += 1
        if int(payload['clu_current']) > int(payload['clu_permitted']):
            conflicts += 1
    if payload.get('mutation_status') == 'DISPUTED':
        pairs += 1
        conflicts += 1
    return conflicts, max(pairs, 2)
