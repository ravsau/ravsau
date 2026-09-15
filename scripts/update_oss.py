#!/usr/bin/env python3
"""Rewrite the open source section of README.md from merged PRs on GitHub.

Needs the gh CLI with a token (GH_TOKEN in Actions). Only the text between
the OSS markers changes.
"""
import json
import re
import subprocess
from pathlib import Path

AUTHOR = "ravsau"
SKIP_OWNERS = {"ravsau", "sanjiblamichhane"}  # own repos and co-founder repos
MIN_STARS = 50
MAX_ROWS = 8
README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- OSS:START -->", "<!-- OSS:END -->"


def gh(*args):
    return json.loads(subprocess.check_output(["gh", *args], text=True))


def rows():
    query = ["--", *(f"-user:{o}" for o in SKIP_OWNERS)]
    prs = gh("search", "prs", "--author", AUTHOR, "--merged", "--limit", "100",
             "--json", "repository,title,url,closedAt", *query)
    stars = {}
    out = []
    for pr in sorted(prs, key=lambda p: p["closedAt"], reverse=True):
        repo = pr["repository"]["nameWithOwner"]
        if repo not in stars:
            stars[repo] = gh("api", f"repos/{repo}")["stargazers_count"]
        if stars[repo] < MIN_STARS:
            continue
        out.append(f"- **[{repo}](https://github.com/{repo})** ({stars[repo]:,} ★): "
                   f"[{pr['title']}]({pr['url']}) · merged {pr['closedAt'][:10]}")
    return out[:MAX_ROWS]


def main():
    body = "\n".join(rows()) or "- Nothing merged yet."
    text = README.read_text()
    new = re.sub(f"{re.escape(START)}.*?{re.escape(END)}",
                 f"{START}\n{body}\n{END}", text, flags=re.S)
    if new != text:
        README.write_text(new)
        print("README updated")
    else:
        print("no change")


if __name__ == "__main__":
    main()
