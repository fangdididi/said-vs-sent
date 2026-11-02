"""Builds the small fictional HAR captures used in the README example."""
import json, os
HERE = os.path.dirname(__file__)
def har(rows):
    entries = []
    for i, (url, cookies) in enumerate(rows):
        entries.append({
            "startedDateTime": f"2026-11-02T10:00:{i:02d}Z",
            "request": {"method": "GET", "url": url, "headers": []},
            "response": {"status": 200, "headers": [{"name": "Set-Cookie", "value": f"{c}=1; Path=/"} for c in cookies]},
        })
    return {"log": {"version": "1.2", "entries": entries}}
site = "https://shop.example-tea.test"
common = [(site + "/", []), (site + "/app.js", []), ("https://fonts.gstatic.com/s/inter.woff2", []), ("https://cdn.cookielaw.org/consent.js", [])]
states = {
    "baseline": common + [("https://www.googletagmanager.com/gtm.js?id=GTM-X", []), ("https://www.google-analytics.com/g/collect?v=2&cid=1", ["_ga"])],
    "accept": common + [("https://www.googletagmanager.com/gtm.js?id=GTM-X", []), ("https://www.google-analytics.com/g/collect?v=2", ["_ga"]), ("https://connect.facebook.net/en_US/fbevents.js", []), ("https://www.clarity.ms/tag/abc", [])],
    "reject": common + [("https://www.googletagmanager.com/gtm.js?id=GTM-X", []), ("https://www.clarity.ms/tag/abc", [])],
    "gpc": common + [("https://connect.facebook.net/en_US/fbevents.js", [])],
}
os.makedirs(os.path.join(HERE, "captures"), exist_ok=True)
for name, rows in states.items():
    with open(os.path.join(HERE, "captures", name + ".har"), "w") as fh:
        json.dump(har(rows), fh, indent=1)
print("wrote", ", ".join(states))
