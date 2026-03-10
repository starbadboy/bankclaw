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
