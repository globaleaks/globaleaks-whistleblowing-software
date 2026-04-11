import re
import random
import string

INVISIBLE_CHARS = ['\u200b', '\u200c', '\u200d', '\ufeff']
DEFANGED_SEQS = ['[://]', '[:/]', '[:]', '[@]', '[.]']

def _random_placeholder(length=12):
    return '__DEFANG_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length)) + '__'

def defang(text: str) -> str:
    """
    Fully idempotent defanging of URLs/emails:
    - Removes invisible characters
    - Protects existing defanged sequences
    - Replaces '://', ':/', ':', '.', '@'
    - Random placeholders prevent collisions
    """
    # 1. Remove invisible characters
    for ch in INVISIBLE_CHARS:
        text = text.replace(ch, '')

    # 2. Protect existing defanged sequences
    protected = {}
    for seq in DEFANGED_SEQS:
        placeholder = _random_placeholder()
        text = text.replace(seq, placeholder)
        protected[placeholder] = seq

    # 3. Replace URL/email patterns in longest-first order
    # Use regex negative lookbehind to avoid double-defanging
    text = re.sub(r'(?<!\[)://', '[://]', text, count=1)  # first only
    text = re.sub(r'(?<!\[):/', '[:/]', text)             # remaining
    text = re.sub(r'(?<!\[):', '[:]', text)               # remaining colons
    text = re.sub(r'(?<!\[)\.', '[.]', text)              # dots
    text = re.sub(r'(?<!\[)@', '[@]', text)              # at signs

    # 4. Restore protected sequences
    for placeholder, seq in protected.items():
        text = text.replace(placeholder, seq)

    return text

