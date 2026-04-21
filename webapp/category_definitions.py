DEFAULT_CATEGORIES = [
    "Food & Dining",
    "Transport",
    "Shopping",
    "Entertainment",
    "Utilities",
    "Healthcare",
    "Travel",
    "Income",
    "Transfer",
    "Other",
]


def _normalize_category_name(name: str) -> str:
    return " ".join(str(name).split()).casefold()


def validate_custom_category_name(name: str, existing_categories: list[str]) -> str:
    if not isinstance(name, str):
        raise ValueError("Category name must be a string")

    cleaned_name = " ".join(name.split())
    if not cleaned_name:
        raise ValueError("Category name cannot be blank")

    known_names = {
        _normalize_category_name(category)
        for category in [*DEFAULT_CATEGORIES, *existing_categories]
    }
    if _normalize_category_name(cleaned_name) in known_names:
        raise ValueError("Category name already exists")

    return cleaned_name


def build_effective_categories(custom_categories: list[dict]) -> list[str]:
    base_categories = [category for category in DEFAULT_CATEGORIES if category != "Other"]
    effective_categories = list(base_categories)
    seen_names = {_normalize_category_name(category) for category in DEFAULT_CATEGORIES}

    for category in custom_categories:
        if category.get("is_active", True) is not True:
            continue

        cleaned_name = " ".join(str(category.get("name", "")).split())
        normalized_name = _normalize_category_name(cleaned_name)
        if not cleaned_name or normalized_name in seen_names:
            continue

        effective_categories.append(cleaned_name)
        seen_names.add(normalized_name)

    effective_categories.append("Other")
    return effective_categories


def get_effective_categories(user_email: str | None) -> list[str]:
    if not user_email:
        return DEFAULT_CATEGORIES

    from webapp.repository import get_custom_categories

    custom_categories = get_custom_categories(user_email).to_dict("records")
    return build_effective_categories(custom_categories)


# Built-in glyphs (kept in sync with the frontend CATEGORIES list)
DEFAULT_CATEGORY_GLYPHS: dict[str, str] = {
    "Food & Dining": "🍽",
    "Transport": "🚕",
    "Shopping": "🛍",
    "Entertainment": "🎬",
    "Utilities": "⚡",
    "Healthcare": "✚",
    "Travel": "✈",
    "Income": "↑",
    "Transfer": "⇄",
    "Other": "•",
}


def get_effective_categories_full(user_email: str | None) -> list[dict]:
    """Returns categories with glyph + custom flag — used by the React dashboard."""
    if not user_email:
        return [
            {"name": name, "glyph": DEFAULT_CATEGORY_GLYPHS.get(name, "•"), "custom": False}
            for name in DEFAULT_CATEGORIES
        ]

    from webapp.repository import get_custom_categories

    custom_records = get_custom_categories(user_email).to_dict("records")
    out: list[dict] = []
    seen: set[str] = set()
    for name in DEFAULT_CATEGORIES:
        if name == "Other":
            continue
        out.append({"name": name, "glyph": DEFAULT_CATEGORY_GLYPHS[name], "custom": False})
        seen.add(_normalize_category_name(name))

    for rec in custom_records:
        if rec.get("is_active", True) is not True:
            continue
        cleaned = " ".join(str(rec.get("name", "")).split())
        norm = _normalize_category_name(cleaned)
        if not cleaned or norm in seen:
            continue
        out.append({
            "name": cleaned,
            "glyph": rec.get("glyph") or "•",
            "custom": True,
        })
        seen.add(norm)

    out.append({"name": "Other", "glyph": DEFAULT_CATEGORY_GLYPHS["Other"], "custom": False})
    return out
