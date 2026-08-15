#!/usr/bin/env python3
"""
Generates a 'Top Languages' SVG card in Tokyo Night theme
using the GitHub REST API and the built-in GITHUB_TOKEN.
"""

import json
import os
import sys
import requests

USERNAME = "hugopereira-cs"
LIMIT = 8
OUTPUT_PATH = "stats/top-langs.svg"

HEADERS = {
    "Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}",
    "Accept": "application/vnd.github.v3+json",
}

# Language colors matching github-readme-stats
LANG_COLORS = {
    "JavaScript":  "#f1e05a",
    "TypeScript":  "#3178c6",
    "Python":      "#3572A5",
    "HTML":        "#e34c26",
    "CSS":         "#563d7c",
    "SCSS":        "#c6538c",
    "Shell":       "#89e051",
    "Java":        "#b07219",
    "C":           "#555555",
    "C++":         "#f34b7d",
    "C#":          "#178600",
    "Ruby":        "#701516",
    "Go":          "#00ADD8",
    "Rust":        "#dea584",
    "PHP":         "#4F5D95",
    "Swift":       "#ffac45",
    "Kotlin":      "#A97BFF",
    "Dart":        "#00B4AB",
    "Vue":         "#41b883",
    "Svelte":      "#ff3e00",
    "Dockerfile":  "#384d54",
    "Markdown":    "#083fa1",
}
DEFAULT_COLOR = "#8b949e"

# Tokyo Night theme
THEME = {
    "bg":         "#1a1b27",
    "border":     "#414868",
    "title":      "#38bdae",
    "text":       "#a9b1d6",
    "subtext":    "#565f89",
}


def get_all_repos() -> list:
    repos = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            headers=HEADERS,
            params={"page": page, "per_page": 100, "type": "owner"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos


def get_repo_languages(repo_name: str) -> dict:
    resp = requests.get(
        f"https://api.github.com/repos/{USERNAME}/{repo_name}/languages",
        headers=HEADERS,
        timeout=15,
    )
    if resp.status_code != 200:
        return {}
    return resp.json()


def aggregate_languages(repos: list) -> dict:
    totals: dict = {}
    for repo in repos:
        if repo.get("fork"):
            continue  # skip forked repos
        for lang, byte_count in get_repo_languages(repo["name"]).items():
            totals[lang] = totals.get(lang, 0) + byte_count
    return totals


def generate_svg(languages: dict) -> str:
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:LIMIT]
    if not sorted_langs:
        raise ValueError("No language data available.")

    total_bytes = sum(b for _, b in sorted_langs)

    # Layout constants
    SVG_W = 300
    PADDING = 25
    BAR_Y = 55
    BAR_H = 8
    BAR_W = SVG_W - 2 * PADDING
    ITEMS_START_Y = 85
    ITEM_H = 25
    COLS = 2

    num = len(sorted_langs)
    rows = (num + COLS - 1) // COLS
    SVG_H = ITEMS_START_Y + rows * ITEM_H + 20

    # Progress bar
    bar_segs = []
    cur_x = 0.0
    for i, (lang, b) in enumerate(sorted_langs):
        pct = b / total_bytes
        w = max(BAR_W * pct, 0.5)
        color = LANG_COLORS.get(lang, DEFAULT_COLOR)
        rx = 4 if i == 0 else (4 if i == len(sorted_langs) - 1 else 0)
        bar_segs.append(
            f'<rect x="{cur_x:.2f}" y="0" width="{w:.2f}" height="{BAR_H}" '
            f'rx="{rx}" fill="{color}" />'
        )
        cur_x += w

    bar_segs_str = "\n    ".join(bar_segs)

    # Language items (2 columns)
    FONT = "Segoe UI, Ubuntu, Sans-Serif"
    lang_items = []
    col_width = (SVG_W - 2 * PADDING) // COLS

    for i, (lang, b) in enumerate(sorted_langs):
        pct = b / total_bytes * 100
        color = LANG_COLORS.get(lang, DEFAULT_COLOR)
        col = i % COLS
        row = i // COLS
        x = PADDING + col * col_width
        y = ITEMS_START_Y + row * ITEM_H

        lang_items.append(
            f'<g transform="translate({x},{y})">'
            f'<circle cx="5" cy="6" r="5" fill="{color}" />'
            f'<text x="15" y="10" font-family="{FONT}" font-size="11" fill="{THEME["text"]}">'
            f'{lang}'
            f'</text>'
            f'<text x="108" y="10" font-family="{FONT}" font-size="11" fill="{THEME["subtext"]}">'
            f'{pct:.2f}%'
            f'</text>'
            f'</g>'
        )

    lang_items_str = "\n  ".join(lang_items)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_W} {SVG_H}" width="{SVG_W}" height="{SVG_H}">
  <rect x="0.5" y="0.5" rx="4.5" height="{SVG_H - 1}" width="{SVG_W - 1}"
        fill="{THEME['bg']}" stroke="{THEME['border']}" stroke-opacity="0.4" />
  <text x="{PADDING}" y="35"
        font-family="{FONT}" font-size="13" font-weight="600"
        fill="{THEME['title']}">Most Used Languages</text>
  <svg x="{PADDING}" y="{BAR_Y}" width="{BAR_W}" height="{BAR_H}">
    {bar_segs_str}
  </svg>
  {lang_items_str}
</svg>"""

    return svg


if __name__ == "__main__":
    print("Fetching repositories...")
    repos = get_all_repos()
    print(f"Found {len(repos)} repositories")

    print("Aggregating language data...")
    langs = aggregate_languages(repos)

    if not langs:
        print("No language data found.", file=sys.stderr)
        sys.exit(1)

    top = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:LIMIT]
    print("Top languages:")
    total = sum(b for _, b in top)
    for lang, b in top:
        print(f"  {lang}: {b / total * 100:.1f}%")

    print("Generating SVG...")
    svg_content = generate_svg(langs)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"Saved to {OUTPUT_PATH}")
