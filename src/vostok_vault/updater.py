import json
import logging
import urllib.request
from importlib.metadata import PackageNotFoundError, version

log = logging.getLogger(__name__)

_RELEASES_URL = "https://api.github.com/repos/jonigirl/vostok-vault/releases/latest"
_TIMEOUT = 5


def get_current_version() -> str:
    try:
        return version("vostok-vault")
    except PackageNotFoundError:
        return "0.0.0"


def _parse_semver(tag: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in tag.lstrip("v").split("."))
    except (ValueError, AttributeError):
        return (0,)


def check_for_update() -> dict | None:
    """Hit the GitHub releases API and return update info if a newer version exists.

    Returns a dict with 'version', 'notes', and 'url', or None if up-to-date
    or if the check fails (network errors are swallowed silently).
    """
    try:
        current = _parse_semver(get_current_version())
        req = urllib.request.Request(
            _RELEASES_URL,
            headers={
                "User-Agent": "vostok-vault-updater",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        if not tag:
            return None
        if _parse_semver(tag) > current:
            return {
                "version": tag,
                "notes": data.get("body", ""),
                "url": data.get(
                    "html_url",
                    "https://github.com/jonigirl/vostok-vault/releases",
                ),
            }
    except Exception as e:
        log.debug("Update check failed: %s", e)
    return None
