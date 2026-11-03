"""Categorisation of bank transaction descriptions using user-defined rules only."""

UNSORTED = "Unsorted"

def normalise_text(value):
    return " ".join(str(value or "").lower().split())


def categorise(description, tx_type, kind, user_rules=()):
    """Return a category name, or UNSORTED when no rule matches.

    user_rules is an iterable of (pattern, category) with normalised patterns; they take
    There are no built-in rules; everything unmatched stays in Unsorted.
    """
    text = normalise_text(description)
    for pattern, category in user_rules:
        if pattern and pattern in text:
            return category
    return UNSORTED
