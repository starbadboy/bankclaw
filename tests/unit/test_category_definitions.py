import pytest
import pandas as pd


def test_build_effective_categories_returns_defaults_when_no_custom_categories():
    from webapp.category_definitions import DEFAULT_CATEGORIES, build_effective_categories

    assert build_effective_categories([]) == DEFAULT_CATEGORIES


def test_build_effective_categories_appends_active_custom_categories_before_other():
    from webapp.category_definitions import build_effective_categories

    custom_categories = [
        {"name": "Pet Care", "is_active": True},
        {"name": "Side Hustle", "is_active": True},
    ]

    effective_categories = build_effective_categories(custom_categories)

    assert "Pet Care" in effective_categories
    assert "Side Hustle" in effective_categories
    assert effective_categories[-1] == "Other"
    assert effective_categories.index("Pet Care") < effective_categories.index("Other")
    assert effective_categories.index("Side Hustle") < effective_categories.index("Other")


def test_build_effective_categories_ignores_inactive_and_duplicate_custom_categories():
    from webapp.category_definitions import build_effective_categories

    custom_categories = [
        {"name": "Pet Care", "is_active": True},
        {"name": " pet care ", "is_active": True},
        {"name": "Transport", "is_active": True},
        {"name": "Archived", "is_active": False},
        {"name": "Other", "is_active": True},
        {"name": "Bad Flag", "is_active": "false"},
    ]

    effective_categories = build_effective_categories(custom_categories)

    assert effective_categories.count("Pet Care") == 1
    assert effective_categories.count("Transport") == 1
    assert "Archived" not in effective_categories
    assert "Bad Flag" not in effective_categories
    assert effective_categories.count("Other") == 1


@pytest.mark.parametrize(
    ("name", "existing_categories"),
    [
        ("", ["Pet Care"]),
        ("   ", ["Pet Care"]),
        ("Transport", ["Pet Care"]),
        (" pet care ", ["Pet Care"]),
        (None, ["Pet Care"]),
        (123, ["Pet Care"]),
    ],
)
def test_validate_custom_category_name_rejects_blank_and_duplicate_names(name, existing_categories):
    from webapp.category_definitions import validate_custom_category_name

    with pytest.raises(ValueError):
        validate_custom_category_name(name, existing_categories)


def test_validate_custom_category_name_normalizes_valid_name():
    from webapp.category_definitions import validate_custom_category_name

    assert validate_custom_category_name("  Pet Care  ", ["Transport"]) == "Pet Care"


def test_get_effective_categories_reads_active_custom_categories_from_repository():
    from webapp.category_definitions import get_effective_categories

    custom_categories = [
        {"name": "Pet Care", "is_active": True},
        {"name": "Transport", "is_active": True},
        {"name": "Archived", "is_active": False},
    ]

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "webapp.repository.get_custom_categories",
            lambda user_email: pd.DataFrame(custom_categories),
        )
        effective_categories = get_effective_categories("u@example.com")

    assert "Pet Care" in effective_categories
    assert effective_categories.count("Transport") == 1
    assert "Archived" not in effective_categories
    assert effective_categories[-1] == "Other"


def test_get_effective_categories_propagates_repository_lookup_failures():
    from webapp.category_definitions import get_effective_categories

    with pytest.MonkeyPatch.context() as monkeypatch:
        def _raise(_user_email):  # noqa: ANN001
            raise RuntimeError("db unavailable")

        monkeypatch.setattr("webapp.repository.get_custom_categories", _raise)
        with pytest.raises(RuntimeError, match="db unavailable"):
            get_effective_categories("u@example.com")
