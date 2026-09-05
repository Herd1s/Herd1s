#!/usr/bin/env python3
"""Build local profile cards from public GitHub data, with no dependencies.

Run: python scripts/update-stats.py
GITHUB_TOKEN is optional and used only with api.github.com. No local credentials
are read. Repository metrics exclude forks and private repositories. Contribution
counts follow the anonymously visible profile, which can include private activity
counts if the account owner has chosen to show them; no private details are read.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree


USERNAME = "Herd1s"
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
CACHE = ASSETS / "stats.json"
PROFILE_URL = f"https://github.com/users/{USERNAME}/contributions"
REPOS_URL = f"https://api.github.com/users/{USERNAME}/repos"
TIMEOUT = 25
ATTEMPTS = 3


def fetch(url: str) -> str:
    """Retry transient errors only, with a bounded timeout and backoff."""
    headers = {"User-Agent": f"{USERNAME}-profile-stats", "Accept-Language": "en-US"}
    if urlparse(url).netloc == "api.github.com":
        headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        if token := os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"
    for attempt in range(ATTEMPTS):
        try:
            with urlopen(Request(url, headers=headers), timeout=TIMEOUT) as response:
                return response.read().decode("utf-8")
        except HTTPError as error:
            if error.code not in (403, 408, 429, 500, 502, 503, 504) or attempt == ATTEMPTS - 1:
                raise RuntimeError(f"GitHub returned HTTP {error.code} for {urlparse(url).path}") from error
        except (URLError, TimeoutError, OSError) as error:
            if attempt == ATTEMPTS - 1:
                raise RuntimeError(f"Could not fetch {urlparse(url).path}: {type(error).__name__}") from error
        time.sleep(2 ** attempt)
    raise RuntimeError("Request attempts exhausted")


def collect_repositories() -> list[dict]:
    """Page the public user endpoint rather than relying on a first-page total."""
    repositories = {}
    for page in range(1, 101):
        query = urlencode({"per_page": 100, "page": page, "type": "owner", "sort": "full_name"})
        batch = json.loads(fetch(f"{REPOS_URL}?{query}"))
        if not isinstance(batch, list):
            raise ValueError("Unexpected repository API response")
        for repo in batch:
            if not isinstance(repo, dict) or not {"id", "name", "owner", "private", "fork", "stargazers_count", "language"} <= repo.keys():
                raise ValueError("Incomplete repository API response")
            if repo["private"] or repo["fork"] or repo["owner"].get("login", "").casefold() != USERNAME.casefold():
                continue
            stars = repo["stargazers_count"]
            if type(stars) is not int or stars < 0:
                raise ValueError("Invalid repository star count")
            repositories[repo["id"]] = {
                "name": repo["name"], "language": repo["language"], "stars": stars,
            }
        if len(batch) < 100:
            return sorted(repositories.values(), key=lambda repo: repo["name"].casefold())
    raise ValueError("Repository pagination limit reached; refusing a partial total")


class ContributionsParser(HTMLParser):
    """Parse the public profile's calendar and English accessible tooltips."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cells: dict[str, dict] = {}
        self.tooltips: dict[str, str] = {}
        self.heading: list[str] = []
        self.in_heading = False
        self.tooltip_id: str | None = None
        self.tooltip_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "h2" and values.get("id") == "js-contribution-activity-description":
            self.in_heading = True
        if "ContributionCalendar-day" in (values.get("class") or "").split() and values.get("data-date"):
            cell_id = values.get("id")
            if not cell_id or cell_id in self.cells:
                raise ValueError("Missing or duplicate contribution cell identifier")
            self.cells[cell_id] = {"date": values["data-date"], "level": int(values.get("data-level", "-1"))}
        if tag == "tool-tip":
            self.tooltip_id = values.get("for")
            self.tooltip_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_heading:
            self.heading.append(data)
        if self.tooltip_id:
            self.tooltip_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2":
            self.in_heading = False
        if tag == "tool-tip":
            if self.tooltip_id:
                self.tooltips[self.tooltip_id] = "".join(self.tooltip_parts)
            self.tooltip_id = None

    def result(self, today: date) -> dict:
        heading = " ".join(" ".join(self.heading).split())
        total_match = re.fullmatch(r"([\d,]+) contributions? in the last year", heading)
        if not total_match:
            raise ValueError("Public contribution total was not found")
        days = []
        for cell_id, cell in self.cells.items():
            tooltip = self.tooltips.get(cell_id, "").strip()
            count_match = re.match(r"^(No|[\d,]+) contributions? on\b", tooltip)
            if not count_match:
                raise ValueError("A contribution day has no readable count")
            count_text = count_match.group(1)
            days.append({**cell, "count": 0 if count_text == "No" else int(count_text.replace(",", ""))})
        result = {
            "status": "current", "retrieved_on": today.isoformat(),
            "total": int(total_match.group(1).replace(",", "")),
            "period": "last year, as displayed by GitHub",
            "source": PROFILE_URL,
            "days": sorted(days, key=lambda day: day["date"]),
        }
        validate_contributions(result)
        last_day = date.fromisoformat(result["days"][-1]["date"])
        if abs((today - last_day).days) > 1:
            raise ValueError("The public contribution calendar is not current")
        return result


def validate_contributions(data: dict) -> None:
    if type(data.get("total")) is not int or data["total"] < 0:
        raise ValueError("Invalid contribution total")
    date.fromisoformat(data["retrieved_on"])
    days = data["days"]
    if not 365 <= len(days) <= 372:
        raise ValueError("Incomplete yearly contribution calendar")
    previous = None
    for day in days:
        current = date.fromisoformat(day["date"])
        if previous is not None and current != previous + timedelta(days=1):
            raise ValueError("Contribution dates are not contiguous")
        if type(day["level"]) is not int or day["level"] not in range(5):
            raise ValueError("Invalid contribution intensity")
        if type(day["count"]) is not int or day["count"] < 0:
            raise ValueError("Invalid daily contribution count")
        previous = current


def collect_contributions(today: date) -> dict:
    try:
        parser = ContributionsParser()
        parser.feed(fetch(PROFILE_URL))
        return parser.result(today)
    except (RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"Warning: profile activity unavailable ({error}); checking previous valid data.", file=sys.stderr)
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            if cached.get("username") != USERNAME:
                raise ValueError("Cache belongs to another account")
            contributions = cached["contributions"]
            validate_contributions(contributions)
            return {**contributions, "status": "cached"}
        except (OSError, ValueError, KeyError, TypeError):
            return {"status": "unavailable", "total": None, "source": PROFILE_URL, "days": []}


def render(data: dict, dark: bool) -> str:
    palette = ({"bg": "#10191c", "text": "#edf4ee", "muted": "#a9bfba", "accent": "#78d4bc", "line": "#30433f", "levels": ["#253632", "#285b50", "#3f8976", "#60b59c", "#78d4bc"]}
               if dark else {"bg": "#f4f7f5", "text": "#172b2a", "muted": "#526e65", "accent": "#19776b", "line": "#d5e1d9", "levels": ["#e0e9e2", "#b0d7c2", "#79b89d", "#3d947a", "#19776b"]})
    activity = data["contributions"]
    total = f'{activity["total"]:,}' if activity["total"] is not None else "N/A"
    activity_state = " / CACHED" if activity["status"] == "cached" else ""
    summary = f'{USERNAME}: {data["public_repositories"]} non-fork public repositories, {data["stars"]} stars received. '
    summary += (f'{activity["total"]} profile contributions in the last year.' if activity["total"] is not None else "Profile contributions unavailable.")
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="400" viewBox="0 0 1000 400" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(USERNAME)} / Open-source activity</title>',
        f'<desc id="desc">{escape(summary)} Language counts describe repositories, not proficiency. Updated {data["updated_on"]} UTC.</desc>',
        f'<rect x="1" y="1" width="998" height="398" rx="18" fill="{palette["bg"]}" stroke="{palette["line"]}" stroke-width="2"/>',
        f'<g font-family="Segoe UI, Arial, sans-serif" fill="{palette["text"]}">',
        f'<path d="M48 146H952" stroke="{palette["line"]}"/>',
    ]

    def text(x: int, y: int, value: str, size: int, color: str | None = None, weight: str = "400", **attrs: str) -> None:
        extra = "".join(f' {key.replace("_", "-")}="{escape(value, quote=True)}"' for key, value in attrs.items())
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color or palette["text"]}"{extra}>{escape(value)}</text>')

    for x, value, label in [(48, f'{data["public_repositories"]:,}', "Public repos"), (368, f'{data["stars"]:,}', "Stars received"), (680, total, "Contributions")]:
        text(x, 79, value, 56, palette["accent"], "600")
        text(x, 121, label, 28)
    text(48, 178, "PROFILE ACTIVITY / LAST YEAR" + activity_state, 20, palette["muted"], "500", letter_spacing="1")
    if activity["days"]:
        first = date.fromisoformat(activity["days"][0]["date"])
        sunday_offset = (first.weekday() + 1) % 7
        total_columns = (len(activity["days"]) + sunday_offset + 6) // 7
        step = min(17, 902 / total_columns)
        for day in activity["days"]:
            when = date.fromisoformat(day["date"])
            offset = (when - first).days + sunday_offset
            x, y = 48 + (offset // 7) * step, 193 + (offset % 7) * 16
            label = f'{day["date"]}: {day["count"]} contributions'
            parts.append(f'<rect x="{x:g}" y="{y}" width="{step - 3:g}" height="13" rx="2" fill="{palette["levels"][day["level"]]}"><title>{label}</title></rect>')
    else:
        text(48, 255, "Profile activity unavailable", 30, palette["muted"])
    languages = data["languages_by_repository"]
    visible = languages[:5]
    language_line = " / ".join(f'{entry["language"]} {entry["repositories"]}' for entry in visible)
    # Keep the single-line summary bounded even if future repository languages change.
    while len(language_line) > 48 and len(visible) > 1:
        visible = visible[:-1]
        language_line = " / ".join(f'{entry["language"]} {entry["repositories"]}' for entry in visible)
    if len(visible) < len(languages):
        language_line += f" / +{len(languages) - len(visible)} more"
    text(48, 344, "REPO LANGUAGES", 20, palette["muted"], "500")
    text(250, 344, language_line or "Not available", 23)
    footer = f'Updated {data["updated_on"]} UTC · Repository counts exclude forks'
    if activity["status"] == "cached":
        footer = f'Repos: {data["updated_on"]} UTC · Activity cached: {activity["retrieved_on"]}'
    text(48, 379, footer, 20, palette["muted"])
    parts.extend(["</g>", "</svg>"])
    svg = "\n".join(parts) + "\n"
    ElementTree.fromstring(svg)
    return svg


def write_atomic(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    today = datetime.now(timezone.utc).date()
    try:
        # A failed repository request is fatal: never publish zero/partial totals.
        repositories = collect_repositories()
        contributions = collect_contributions(today)
        languages = Counter(repo["language"] for repo in repositories if repo["language"])
        data = {
            "schema_version": 1, "username": USERNAME, "updated_on": today.isoformat(),
            "public_repositories": len(repositories), "stars": sum(repo["stars"] for repo in repositories),
            "repository_scope": "Owned public repositories, excluding forks; archived repositories included.",
            "repository_source": REPOS_URL,
            "language_scope": "GitHub primary language, counted by non-fork public repository; not a proficiency score.",
            "languages_by_repository": [{"language": language, "repositories": count} for language, count in sorted(languages.items(), key=lambda item: (-item[1], item[0].casefold()))],
            "contribution_scope": "Anonymously visible GitHub profile activity, possibly including private contribution counts enabled by the owner; no private details accessed.",
            "contributions": contributions, "repositories": repositories,
        }
        # Render and validate both documents before replacing any existing file.
        light, dark = render(data, dark=False), render(data, dark=True)
        cache = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        ASSETS.mkdir(parents=True, exist_ok=True)
        write_atomic(ASSETS / "stats-light.svg", light)
        write_atomic(ASSETS / "stats-dark.svg", dark)
        write_atomic(CACHE, cache)
        print(f'Updated {USERNAME}: {len(repositories)} public non-fork repos, {data["stars"]} stars, profile contributions={contributions["total"]} ({contributions["status"]}).')
        return 0
    except (RuntimeError, ValueError, KeyError, TypeError, OSError, ElementTree.ParseError) as error:
        print(f"Stats update failed; existing cards kept: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
