import re


def format_passage_ref(passage_ref) -> str:
    """
    Formats a passage reference string to work with YouTube descriptions.

    Args:
      passage_ref (str): The passage reference string to be formatted.

    Returns:
      str: The formatted passage reference string.

    Examples:
    - format_passage_ref("1 john 3:16-18") returns "1 John 3, verses 16-18"
    - format_passage_ref("john 3:16") returns "John 3, verse 16"
    - format_passage_ref("John 3") returns "John 3"
    """
    passage_ref = passage_ref.strip()

    # Regex to split the reference properly considering multi-word book names (eg: John vs 1 John)
    match = re.match(
        r"(\d*\s*[A-Za-z]+\s*[A-Za-z]*)\s+(\d+)(?::(\d+)(?:-(\d+))?)?", passage_ref
    )
    if not match:
        return passage_ref.title()

    book = match.group(1).title()
    chapter = match.group(2)
    verse_start = match.group(3)
    verse_end = match.group(4)

    # Formatting the string based on the amount of verses
    if verse_start:
        if verse_end:
            return f"{book} {chapter}, verses {verse_start}-{verse_end}"
        else:
            return f"{book} {chapter}, verse {verse_start}"
    else:
        return f"{book} {chapter}"
