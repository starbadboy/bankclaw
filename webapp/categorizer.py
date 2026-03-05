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


def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is not set")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    descriptions = df["description"].tolist()
    user_content = "\n".join(f"{i + 1}. {desc}" for i, desc in enumerate(descriptions))

    completion = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.0,
    )

    raw_lines = completion.choices[0].message.content.strip().splitlines()

    categories = []
    for line in raw_lines:
        line = line.strip()
        # Strip leading numbering like "1. " if model adds it
        if ". " in line:
            line = line.split(". ", 1)[-1].strip()
        categories.append(line if line in VALID_CATEGORIES else "Other")

    # Pad or truncate to match DataFrame length
    while len(categories) < len(df):
        categories.append("Other")
    categories = categories[: len(df)]

    result = df.copy()
    result["category"] = categories
    return result
