import unicodedata


def normalize_hindi_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    return " ".join(normalized.split())


def hindi_key_variants(value: str) -> set[str]:
    normalized = normalize_hindi_text(value)
    compact = normalized.replace(" ", "")
    return {normalized, compact}
