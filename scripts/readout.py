"""regenerate README.md from real github activity. stdlib only.

needs GH_TOKEN with read access to the account's private repos and its orgs.
runs daily from launchd on the mac (scripts/refresh.sh), not from actions: a
fine-grained token can't span the personal account and the work org.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

USER = "hackspaces"
TOKEN = os.environ["GH_TOKEN"]
NOW = datetime.now(timezone.utc)
DAYS = 30
SINCE = NOW - timedelta(days=DAYS)
WORK_ORG = "ASU-LE"  # private work repos, shown only as one aggregate row

PROCS = [
    ("forge", "agent runtime for the terminal. local model or frontier, same loop."),
    ("helm", "native mac front end for claude code. every write waits for approval."),
    ("pane", "file browser. folder sizes, git branches, agent sessions, inline."),
    ("bench", "mcp tools so an agent can capture, build and wait on a mac unseen."),
    ("pulse", "reads tempo, key and energy straight off apple music's audio."),
    ("*-connect-mcp", "read-only data servers. hubspot, airtable, o*net, ipeds, ahrefs."),
    ("finstack-mcp", "nse/bse market data over mcp."),
    ("blueshark", "small moe coding model, reference arch, live activation viewer."),
]
# display name -> repo, where they differ
REPO_OF = {"forge": "blueshark-forge"}
LINKS = ["blueshark-forge", "finstack-mcp", "blueshark", "PortWatch", "AppTrail", "DiskPulse"]


def api(path):
    out, url = [], f"https://api.github.com{path}"
    while url:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
        })
        try:
            with urllib.request.urlopen(req) as r:
                data = json.load(r)
                link = r.headers.get("Link", "")
        except urllib.error.HTTPError as e:
            if e.code == 409:  # empty repo
                return []
            raise
        if not isinstance(data, list):
            return data
        out += data
        url = next((p.split(";")[0].strip("<> ") for p in link.split(",") if 'rel="next"' in p), None)
    return out


def ago(ts):
    d = (NOW - datetime.fromisoformat(ts.replace("Z", "+00:00"))).days
    return "today" if d == 0 else "yesterday" if d == 1 else f"{d} days ago"


repos = api("/user/repos?affiliation=owner&per_page=100")
visibility = {r["name"]: ("private" if r["private"] else "public") for r in repos}
repos = [r for r in repos if not r["fork"]]

counts, work_repos, releases = {}, set(), []
q = urllib.parse.quote(f"author:{USER} author-date:>{SINCE:%Y-%m-%d}")
page = 1
while True:
    items = api(f"/search/commits?q={q}&per_page=100&page={page}")["items"]
    for c in items:
        full = c["repository"]["full_name"]
        owner, name = full.split("/")
        if full == f"{USER}/{USER}":
            continue
        if owner == WORK_ORG:
            work_repos.add(name)
            name = "work @ asu"
        counts[name] = counts.get(name, 0) + 1
    if len(items) < 100 or page == 10:
        break
    page += 1

latest = None
for r in repos:
    for rel in api(f"/repos/{USER}/{r['name']}/releases?per_page=5"):
        if rel["draft"] or not rel["published_at"]:
            continue
        if rel["published_at"] >= SINCE.isoformat():
            releases.append(rel)
        if not latest or rel["published_at"] > latest[1]["published_at"]:
            latest = (r["name"], rel)

top = sorted(counts.items(), key=lambda kv: -kv[1])[:7]
peak = top[0][1] if top else 1
width = max((len(n) for n, _ in top), default=0)

L = ["```console", "hackspaces ~ $ whoami",
     "ai engineer, learning enterprise @ asu.",
     "agents write the code. i decide what they may touch, and i check what they did.", "",
     f"hackspaces ~ $ git log --since={DAYS}.days --author=me --all-repos"]
if top:
    nrepos = len(counts) - (1 if work_repos else 0) + len(work_repos)
    rel = f" · {len(releases)} releases" if releases else ""
    L.append(f"  {sum(counts.values())} commits · {nrepos} repos{rel}")
    L.append("")
    for name, n in top:
        note = f"  ({len(work_repos)} private repos)" if name == "work @ asu" else ""
        L.append(f"  {'▇' * max(1, round(12 * n / peak)):<12}  {name:<{width}}  {n:>3}{note}")
else:
    L.append("  quiet week. thinking, probably.")
L += ["", "hackspaces ~ $ last shipped"]
if latest:
    name, rel = latest
    L.append(f"  {name} {rel['tag_name']} · {ago(rel['published_at'])}")
L += ["", "hackspaces ~ $ ps --user hackspaces", f"{'NAME':<15}{'REPO':<10}WHAT"]
for name, what in PROCS:
    vis = visibility.get(REPO_OF.get(name, name), "private")
    L.append(f"{name:<15}{vis:<10}{what}")
L += ["", "hackspaces ~ $ uptime",
      "one t3.micro and a home lab. an agent on slack that never sleeps, a game server,",
      "a watchpost on every machine. smallest thing that works, then stop.", "",
      "hackspaces ~ $ ls ~/old", "PortWatch  AppTrail  DiskPulse  mcp-suite", "",
      "hackspaces ~ $ █", "```", ""]
L.append(" ·\n".join(f"[{'forge' if n == 'blueshark-forge' else n}](https://github.com/{USER}/{n})" for n in LINKS)
         + " ·\n[topk1.com](https://topk1.com)")
L += ["", f"<sub>numbers are real, regenerated daily by a bot. last run {NOW:%Y-%m-%d %H:%M} utc.</sub>", ""]

open("README.md", "w").write("\n".join(L))
