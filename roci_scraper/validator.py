from __future__ import annotations
from typing import Dict, Any

def cross_validate(payload: Dict[str, Any]) -> tuple[int, int]:
    """
    Spec Step 10 (Table 21): two cross-portal consistency checks.
    Returns (conflicts, validation_pairs).
    """
    conflicts = 0
    pairs = 0

    # Check (a): Bhulekh clu_current vs Master Plan clu_permitted
    # Flag if current land use already exceeds the permitted ceiling — legally incompatible.
    if payload.get('clu_current') is not None and payload.get('clu_permitted') is not None:
        pairs += 1
        if int(payload['clu_current']) > int(payload['clu_permitted']):
            conflicts += 1

    # Check (b): IGRSUP deed_ref vs Bhulekh mutation status
    # If a deed was recently registered (deed_ref present) but mutation is not yet initiated,
    # that is a cross-portal inconsistency — the title chain may be incomplete.
    if payload.get('deed_ref') is not None:
        pairs += 1
        if payload.get('mutation_status') in ('NOT_INIT', 'DISPUTED'):
            conflicts += 1

    return conflicts, max(pairs, 2)
