"""Pure template substitution shared by the resolver."""
import re
from collections.abc import Mapping

TOKEN = re.compile(r"@@([A-Z_]+)@@")


def fill(text: str, tokens: Mapping[str, str]) -> str:
    """Replace known tokens, preserving unknown tokens for validation."""
    return TOKEN.sub(lambda match: tokens.get(match.group(1), match.group(0)), text)
