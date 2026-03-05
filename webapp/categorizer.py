import os

import pandas as pd
from openai import OpenAI

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


def categorize_transactions(df: pd.DataFrame, batch_size: int = 75) -> pd.DataFrame:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is not set")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    descriptions = df["description"].tolist()
    categories = []
    for start_idx in range(0, len(descriptions), batch_size):
        batch_descriptions = descriptions[start_idx : start_idx + batch_size]
        user_content = "\n".join(f"{i + 1}. {desc}" for i, desc in enumerate(batch_descriptions))

        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
        )
        categories.extend(
            _sanitize_categories(
                completion.choices[0].message.content,
                expected_count=len(batch_descriptions),
            )
        )

    result = df.copy()
    result["category"] = categories
    return result
