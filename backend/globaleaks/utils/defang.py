import re

# Characters considered invisible / dangerous
INVISIBLE_CHARS = [
    '\u200b',  # zero-width space
    '\u200c',  # zero-width non-joiner
    '\u200d',  # zero-width joiner
    '\ufeff',  # BOM
]

def remove_invisible(text: str) -> str:
    """Remove invisible/control characters from text."""
    for ch in INVISIBLE_CHARS:
        text = text.replace(ch, '')
    return text


def defang_uris(text: str) -> str:
    """
    Defangs URLs by:
    - Removing invisible characters
    - Wrapping protocol:// in [ ] if present
    - Replacing dots with [.] only if not already defanged
    """

    text = remove_invisible(text)

    url_pattern = re.compile(
        r'\b(?:([a-zA-Z][a-zA-Z0-9+.-]*://)?'
        r'([\w.-]+\.[\w]{2,}(?:[^\s]*)?))',
        re.UNICODE
    )


    def replace_url(match):
        protocol = match.group(1) or ''
        rest = match.group(2) or ''

        # Defang protocol only if not already wrapped
        if protocol and not protocol.startswith('['):
            protocol_defanged = f'[{protocol}]'
        else:
            protocol_defanged = protocol

        # Replace only dots not already inside [ ]
        rest_defanged = re.sub(r'(?<!\[)\.(?!\])', '[.]', rest)

        return protocol_defanged + rest_defanged

    return url_pattern.sub(replace_url, text)


def defang_emails(text: str) -> str:
    """
    Defangs emails by:
    - Removing invisible characters
    - Replacing @ and . only if not already defanged
    """

    text = remove_invisible(text)

    email_pattern = re.compile(
        r'\b([\w._%+-]+@[\w.-]+\.[\w]{2,})\b',
        re.UNICODE
    )

    def replace_email(match):
        email = match.group(0)

        # Replace only if NOT already defanged
        email = re.sub(r'(?<!\[)@(?!\])', '[@]', email)
        email = re.sub(r'(?<!\[)\.(?!\])', '[.]', email)

        return email

    return email_pattern.sub(replace_email, text)


def defang_text(text: str) -> str:
    """Defang both URLs and emails, remove invisible chars."""
    text = remove_invisible(text)
    text = defang_emails(text)
    text = defang_uris(text)
    return text
