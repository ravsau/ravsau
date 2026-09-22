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
EMAILS = ["sauravsharma011@gmail.com", "22568316+ravsau@users.noreply.github.com"]
SKIP_OWNERS = {"ravsau", "sanjiblamichhane"}  # own repos and co-founder repos
MIN_STARS = 50
MAX_ROWS = 8
README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- OSS:START -->", "<!-- OSS:END -->"


def gh(*args):
    return json.loads(subprocess.check_output(["gh", *args], text=True))


def coauthored():
    """Merged work where Saurav is a Co-authored-by trailer, not the PR author."""
    trailer = re.compile(r"co-authored-by:.*(" + "|".join(map(re.escape, EMAILS)) + ")", re.I)
    found = {}
    for email in EMAILS:
        for c in gh("search", "commits", email, "--limit", "100",
                    "--json", "repository,commit,url"):
            repo = c["repository"]["fullName"]
            msg = c["commit"]["message"]
            if repo.split("/")[0] in SKIP_OWNERS or not trailer.search(msg):
                continue
            title = msg.split("\n")[0]
            m = re.search(r"\(#(\d+)\)$", title)
            url = f"https://github.com/{repo}/pull/{m.group(1)}" if m else c["url"]
            found[url] = {"repository": {"nameWithOwner": repo}, "url": url,
                          "title": re.sub(r"\s*\(#\d+\)$", "", title) + " (co-author)",
                          "closedAt": c["commit"]["committer"]["date"]}
    return list(found.values())


def rows():
    query = ["--", *(f"-user:{o}" for o in SKIP_OWNERS)]
    prs = gh("search", "prs", "--author", AUTHOR, "--merged", "--limit", "100",
             "--json", "repository,title,url,closedAt", *query)
    authored = {pr["url"] for pr in prs}
    prs += [c for c in coauthored() if c["url"] not in authored]
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
