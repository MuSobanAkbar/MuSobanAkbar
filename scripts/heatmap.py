"""Build an animated contribution heatmap (heatmap.svg) from GitHub's GraphQL API.

Runs in GitHub Actions once a day. Uses only the Python standard library.
"""

import json
import os
import urllib.request

USERNAME = os.environ["USERNAME"]
TOKEN = os.environ["GH_TOKEN"]
OUTPUT = "heatmap.svg"

CELL = 11  # size of one square, in pixels
GAP = 3  # space between squares
STEP = CELL + GAP
TOP = 4
CAPTION_HEIGHT = 28

# How many milliseconds later each column and row starts its animation.
# Bigger numbers = slower sweep across the grid.
WEEK_DELAY_MS = 22
DAY_DELAY_MS = 15

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { contributionLevel weekday }
        }
      }
    }
  }
}
"""


def fetch_calendar() -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    if "errors" in data:
        raise SystemExit(f"GitHub API error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def build_svg(calendar: dict) -> str:
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    width = len(weeks) * STEP
    grid_height = 7 * STEP
    height = TOP + grid_height + CAPTION_HEIGHT

    cells = []
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            level = LEVELS.get(day["contributionLevel"], 0)
            x = week_index * STEP
            y = TOP + day["weekday"] * STEP
            delay = week_index * WEEK_DELAY_MS + day["weekday"] * DAY_DELAY_MS
            cells.append(
                f'<rect class="c l{level}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2" style="animation-delay:{delay}ms"/>'
            )

    caption_delay = len(weeks) * WEEK_DELAY_MS + 300
    caption_y = TOP + grid_height + 18

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{total} contributions in the last year">
  <style>
    .c {{ opacity: 0; transform-box: fill-box; transform-origin: center;
          animation: pop 0.45s cubic-bezier(0.2, 0.8, 0.2, 1.2) forwards; }}
    .l0 {{ fill: #ebedf0; }} .l1 {{ fill: #9be9a8; }} .l2 {{ fill: #40c463; }}
    .l3 {{ fill: #30a14e; }} .l4 {{ fill: #216e39; }}
    .caption {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: 12px; fill: #59636e; opacity: 0;
                animation: fade 0.6s ease-out {caption_delay}ms forwards; }}
    @media (prefers-color-scheme: dark) {{
      .l0 {{ fill: #161b22; }} .l1 {{ fill: #0e4429; }} .l2 {{ fill: #006d32; }}
      .l3 {{ fill: #26a641; }} .l4 {{ fill: #39d353; }}
      .caption {{ fill: #8b949e; }}
    }}
    @keyframes pop {{ from {{ opacity: 0; transform: scale(0.3); }} to {{ opacity: 1; transform: scale(1); }} }}
    @keyframes fade {{ to {{ opacity: 1; }} }}
  </style>
  {"".join(cells)}
  <text class="caption" x="0" y="{caption_y}">{total} contributions in the last year</text>
</svg>
"""


def main() -> None:
    calendar = fetch_calendar()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(build_svg(calendar))
    print(f"Wrote {OUTPUT}: {calendar['totalContributions']} contributions")


if __name__ == "__main__":
    main()
