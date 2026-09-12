import html
import re

_SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def strip_html_and_scripts(text: str) -> str:
    text = _SCRIPT_RE.sub("", text)
    text = _TAG_RE.sub("", text)
    return html.unescape(text).strip()


def wrap_untrusted(data: str) -> str:
    cleaned = strip_html_and_scripts(data)
    return f"<untrusted_data>{cleaned}</untrusted_data>"
