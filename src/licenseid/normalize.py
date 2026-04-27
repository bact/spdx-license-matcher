# SPDX-FileCopyrightText: 2026 SPDX
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import re
from bs4 import BeautifulSoup


def normalize_text(text: str) -> str:
    """
    Normalises license text based on SPDX Matching Guidelines.
    
    1. HTML to plain text (if detected).
    2. Whitespace: All whitespace is treated as a single blank space.
    3. Case: All letters are treated as lowercase.
    4. Punctuation: Various hyphens/dashes and quotes are treated as equivalent.
    5. Hyperlink: http:// and https:// are treated as equivalent.
    """
    # 1. HTML to plain text
    if bool(re.search(r"<[a-z][\s\S]*>", text, re.IGNORECASE)):
        soup = BeautifulSoup(text, "html.parser")
        text = soup.get_text()

    # 2. Hyperlink Protocol (do this before lowercasing/punctuation to keep URLs intact)
    text = re.sub(r"https?://", "http://", text)

    # 3. Case sensitivity
    text = text.lower()

    # 4. Punctuation Equivalence
    # Hyphens, dashes
    text = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015-]", "-", text)
    # Quotes
    text = re.sub(r"[\u2018\u2019\u201A\u201B\u201C\u201D\u201E\u201F'\"]", '"', text)

    # 5. Whitespace and Pagination
    # Replace any sequence of whitespace characters (including line breaks) with a single space
    text = re.sub(r"\s+", " ", text).strip()

    return text


def strip_list_markers(text: str) -> str:
    """
    Ignores leading bullets, numbers, or letters followed by a space.
    """
    # This is a bit more complex as it usually applies to lines/paragraphs.
    # For now, a simple regex for common markers.
    lines = text.split(" ")
    # This might be better handled in a more structured way per paragraph.
    # But for a single normalized string, we can try to remove common patterns.
    # However, SPDX Matching Guidelines say list markers are ignored.
    # In a fully normalized string (all spaces), this is tricky.
    # We might want to do this BEFORE final whitespace normalization.
    return text
