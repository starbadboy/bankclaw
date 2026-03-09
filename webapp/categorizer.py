import os
from difflib import SequenceMatcher

import pandas as pd
from openai import OpenAI

from webapp.repository import get_category_memory, normalize_description

VALID_CATEGORIES = [
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

_SYSTEM_PROMPT = """You are a bank transaction categoriser. Given a list of bank transaction descriptions,
return exactly one category per line in the same order. Output ONLY the category names, one per line, nothing else.

Valid categories: {categories}
""".format(
    categories=", ".join(VALID_CATEGORIES)
)
_MEMORY_MATCH_THRESHOLD = 0.70
_GENERIC_MEMORY_TOKENS = {
    "fast",
    "payment",
    "transfer",
    "to",
    "from",
    "received",
    "via",
}


def _sanitize_categories(raw_text: str, expected_count: int) -> list[str]:
    raw_lines = raw_text.strip().splitlines()
    categories = []
    for line in raw_lines:
        line = line.strip()
        # Strip leading numbering like "1. " if model adds it
        if ". " in line:
            line = line.split(". ", 1)[-1].strip()
        categories.append(line if line in VALID_CATEGORIES else "Other")

    # Pad or truncate to match expected batch size
    while len(categories) < expected_count:
        categories.append("Other")
    return categories[:expected_count]


def _token_overlap_ratio(left: str, right: str) -> float:
    left_tokens = {token for token in left.split() if token not in _GENERIC_MEMORY_TOKENS}
    right_tokens = {token for token in right.split() if token not in _GENERIC_MEMORY_TOKENS}
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))


def _match_memory_category(description: str, memory_df: pd.DataFrame) -> str | None:
    if memory_df.empty:
        return None

    normalized_description = normalize_description(description)
    if not normalized_description:
        return None

    exact_matches = memory_df.loc[memory_df["normalized_description"] == normalized_description]
    if not exact_matches.empty:
        return str(exact_matches.iloc[-1]["category"])

    best_category = None
    best_score = 0.0
    best_updated_at = ""

    for _, row in memory_df.iterrows():
        candidate_description = str(row.get("normalized_description", ""))
        if not candidate_description:
            continue

        score = SequenceMatcher(None, normalized_description, candidate_description).ratio()
        token_overlap = _token_overlap_ratio(normalized_description, candidate_description)
        updated_at = str(row.get("updated_at", ""))
        if token_overlap < _MEMORY_MATCH_THRESHOLD:
            continue

        if score > best_score or (score == best_score and updated_at > best_updated_at):
            best_score = score
            best_category = str(row["category"])
            best_updated_at = updated_at

    if best_score >= _MEMORY_MATCH_THRESHOLD:
        return best_category

    return None


def categorize_transactions(
    df: pd.DataFrame,
    batch_size: int = 75,
    user_email: str | None = None,
) -> pd.DataFrame:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    try:
        memory_df = get_category_memory(user_email) if user_email else pd.DataFrame()
    except Exception:  # pylint: disable=broad-except  # noqa: BLE001
        memory_df = pd.DataFrame()
    descriptions = df["description"].tolist()
    categories: list[str | None] = [None] * len(descriptions)
    unmatched_descriptions: list[str] = []
    unmatched_indices: list[int] = []

    for idx, description in enumerate(descriptions):
        matched_category = _match_memory_category(str(description), memory_df)
        if matched_category is None:
            unmatched_indices.append(idx)
            unmatched_descriptions.append(str(description))
            continue
        categories[idx] = matched_category

    if unmatched_descriptions:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

    for start_idx in range(0, len(unmatched_descriptions), batch_size):
        batch_descriptions = unmatched_descriptions[start_idx : start_idx + batch_size]
        batch_indices = unmatched_indices[start_idx : start_idx + batch_size]
        user_content = "\n".join(f"{i + 1}. {desc}" for i, desc in enumerate(batch_descriptions))

        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
        )
        batch_categories = _sanitize_categories(
            completion.choices[0].message.content,
            expected_count=len(batch_descriptions),
        )
        for original_idx, category in zip(batch_indices, batch_categories, strict=False):
            categories[original_idx] = category

    result = df.copy()
    result["category"] = categories
    return result
