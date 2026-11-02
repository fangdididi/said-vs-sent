#!/usr/bin/env python3
"""gapcheck: compare what a website's privacy notice SAYS with what the browser SENT.

Inputs
  --notice notice.json   the claims you extracted from the notice / banner (see references/notice-format.md)
  --captures DIR         HAR files, one per consent state:
                           baseline.har  page loaded, banner untouched
                           accept.har    "accept all" clicked
                           reject.har    "reject all" clicked (or every toggle off)
                           gpc.har       fresh profile with Global Privacy Control on (optional)
  --forms forms.json     optional: fields each form collects, with a data category
  --out DIR              where ledger.md and ledger.json are written

Only the Python standard library is used. Nothing is fetched from the network.
Findings describe mismatches between documents and observed traffic. They are
not legal conclusions.
"""
import argparse
import json
import os
import sys
from urllib.parse import urlsplit

STATES = ("baseline", "accept", "reject", "gpc")

# Small, hand-kept map of well-known third-party hosts -> (vendor, category).
# Categories: analytics, advertising, session-replay, tag-manager, social, cdn,
# fonts, payments, support-chat, error-tracking, consent-tool, other.
VENDORS = {
    "google-analytics.com": ("Google Analytics", "analytics"),
    "analytics.google.com": ("Google Analytics", "analytics"),
    "googletagmanager.com": ("Google Tag Manager", "tag-manager"),
    "doubleclick.net": ("Google Ads / DoubleClick", "advertising"),
    "googleadservices.com": ("Google Ads", "advertising"),
    "googlesyndication.com": ("Google AdSense", "advertising"),
    "connect.facebook.net": ("Meta Pixel", "advertising"),
    "facebook.com": ("Meta", "advertising"),
    "analytics.tiktok.com": ("TikTok Pixel", "advertising"),
    "snap.licdn.com": ("LinkedIn Insight", "advertising"),
    "px.ads.linkedin.com": ("LinkedIn Insight", "advertising"),
    "bat.bing.com": ("Microsoft Advertising", "advertising"),
    "clarity.ms": ("Microsoft Clarity", "session-replay"),
    "hotjar.com": ("Hotjar", "session-replay"),
    "hotjar.io": ("Hotjar", "session-replay"),
    "fullstory.com": ("FullStory", "session-replay"),
    "mixpanel.com": ("Mixpanel", "analytics"),
    "segment.io": ("Segment", "analytics"),
    "segment.com": ("Segment", "analytics"),
    "amplitude.com": ("Amplitude", "analytics"),
    "posthog.com": ("PostHog", "analytics"),
    "plausible.io": ("Plausible", "analytics"),
    "hm.baidu.com": ("Baidu Tongji", "analytics"),
    "cnzz.com": ("CNZZ / Umeng", "analytics"),
    "sentry.io": ("Sentry", "error-tracking"),
    "intercom.io": ("Intercom", "support-chat"),
    "intercomcdn.com": ("Intercom", "support-chat"),
    "crisp.chat": ("Crisp", "support-chat"),
    "js.stripe.com": ("Stripe", "payments"),
    "fonts.googleapis.com": ("Google Fonts", "fonts"),
    "fonts.gstatic.com": ("Google Fonts", "fonts"),
    "cdn.jsdelivr.net": ("jsDelivr", "cdn"),
    "cdnjs.cloudflare.com": ("cdnjs", "cdn"),
    "unpkg.com": ("unpkg", "cdn"),
    "cookielaw.org": ("OneTrust", "consent-tool"),
    "onetrust.com": ("OneTrust", "consent-tool"),
    "cookiebot.com": ("Cookiebot", "consent-tool"),
    "youtube.com": ("YouTube embed", "social"),
    "ytimg.com": ("YouTube embed", "social"),
    "platform.twitter.com": ("X embed", "social"),
}

# Categories that normally need opt-in where consent rules apply. The notice
# can override this per recipient with "needs_consent".
CONSENT_CATEGORIES = {"analytics", "advertising", "session-replay", "social"}


def host_of(url):
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def matches(host, domain):
    domain = domain.lower().lstrip(".")
    return host == domain or host.endswith("." + domain)


def vendor_for(host):
    best = None
    for dom, info in VENDORS.items():
        if matches(host, dom) and (best is None or len(dom) > len(best[0])):
            best = (dom, info)
    return best[1] if best else None


def strip_query(url):
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}{p.path}"


def load_har(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    entries = data.get("log", {}).get("entries", [])
    out = []
    for e in entries:
        req = e.get("request", {})
        url = req.get("url", "")
        if not url.startswith(("http://", "https://")):
            continue
        set_cookies = []
        for h in e.get("response", {}).get("headers", []):
            if h.get("name", "").lower() == "set-cookie":
                name = h.get("value", "").split("=", 1)[0].strip()
                if name:
                    set_cookies.append(name)
        for c in e.get("response", {}).get("cookies", []) or []:
            if c.get("name") and c["name"] not in set_cookies:
                set_cookies.append(c["name"])
        out.append({
            "url": url,
            "host": host_of(url),
            "time": e.get("startedDateTime", ""),
            "set_cookies": set_cookies,
        })
    return out


class Notice:
    def __init__(self, data):
        self.site = data.get("site", "")
        self.first_party = [d.lower() for d in data.get("first_party", [])]
        if self.site and self.site.lower() not in self.first_party:
            self.first_party.append(self.site.lower())
        self.recipients = data.get("recipients", [])
        self.claims = data.get("consent_claims", {})
        self.categories = set(data.get("data_categories", []))
        self.as_of = data.get("as_of", "")
        self.source = data.get("notice_url", "")

    def is_first_party(self, host):
        return any(matches(host, d) for d in self.first_party)

    def recipient_for(self, host):
        best = None
        for r in self.recipients:
            for d in r.get("domains", []):
                if matches(host, d) and (best is None or len(d) > best[0]):
                    best = (len(d), r)
        return best[1] if best else None

    def needs_consent(self, host):
        r = self.recipient_for(host)
        if r is not None and "needs_consent" in r:
            return bool(r["needs_consent"])
        v = vendor_for(host)
        if v:
            return v[1] in CONSENT_CATEGORIES
        if r is not None:
            return r.get("purpose", "") in CONSENT_CATEGORIES
        return False


def is_ad(host, notice):
    r = notice.recipient_for(host)
    if r is not None and r.get("purpose"):
        return r["purpose"] == "advertising"
    v = vendor_for(host)
    return bool(v and v[1] == "advertising")


def label(host, notice):
    r = notice.recipient_for(host)
    if r:
        return r.get("name", host)
    v = vendor_for(host)
    return v[0] if v else host


def analyse(notice, captures, forms=None):
    findings = []
    seen_hosts = {}

    def add(code, level, state, host, evidence, fix):
        findings.append({
            "code": code, "level": level, "state": state, "host": host,
            "who": label(host, notice) if host else "",
            "evidence": evidence, "fix": fix,
        })

    third = {}
    for state, entries in captures.items():
        hosts = {}
        for e in entries:
            if notice.is_first_party(e["host"]) or not e["host"]:
                continue
            hosts.setdefault(e["host"], e)
        third[state] = hosts
        for h in hosts:
            seen_hosts.setdefault(h, []).append(state)

    # 1. Third parties contacted that the notice never names.
    for host, states in sorted(seen_hosts.items()):
        if notice.recipient_for(host) is None:
            v = vendor_for(host)
            kind = v[1] if v else "unknown"
            first = third[states[0]][host]
            add("UNDECLARED_RECIPIENT", "mismatch", ",".join(states), host,
                f"{strip_query(first['url'])} ({kind}) first seen {first['time']}",
                "Name this recipient and its purpose in the notice, or remove the tag that calls it.")

    # 2. Consent-gated recipients reached before any choice.
    blocks = notice.claims.get("blocks_before_consent", True)
    for host, e in sorted(third.get("baseline", {}).items()):
        if notice.needs_consent(host):
            lvl = "mismatch" if blocks else "check"
            add("FIRES_BEFORE_CHOICE", lvl, "baseline", host,
                f"{strip_query(e['url'])} at {e['time']} with the banner untouched",
                "Hold this tag until the visitor opts in (consent-mode default denied, or load it from the consent callback).")

    # 3. Consent-gated recipients still reached after reject.
    honours_reject = notice.claims.get("honors_reject", True)
    for host, e in sorted(third.get("reject", {}).items()):
        if notice.needs_consent(host):
            lvl = "mismatch" if honours_reject else "check"
            add("FIRES_AFTER_REJECT", lvl, "reject", host,
                f"{strip_query(e['url'])} at {e['time']} after reject",
                "Make the reject path tear down or never load this tag; re-test in a fresh profile.")

    # 4. GPC signal ignored.
    if "gpc" in third:
        honours_gpc = notice.claims.get("honors_gpc")
        for host, e in sorted(third["gpc"].items()):
            if is_ad(host, notice):
                lvl = "mismatch" if honours_gpc else "check"
                add("IGNORES_GPC", lvl, "gpc", host,
                    f"{strip_query(e['url'])} at {e['time']} with Sec-GPC: 1",
                    "Treat Sec-GPC: 1 / navigator.globalPrivacyControl as an opt-out of sale/sharing before loading ad tags.")

    # 5. Cookies set by third parties before a choice.
    for e in captures.get("baseline", []):
        if e["set_cookies"] and not notice.is_first_party(e["host"]) and notice.needs_consent(e["host"]):
            add("COOKIE_BEFORE_CHOICE", "mismatch" if blocks else "check", "baseline", e["host"],
                f"set {', '.join(sorted(set(e['set_cookies'])))} from {strip_query(e['url'])}",
                "Stop this response from setting cookies until opt-in.")

    # 6. Declared recipients never observed (informational: maybe stale notice).
    all_seen = set(seen_hosts)
    for r in notice.recipients:
        if not any(any(matches(h, d) for d in r.get("domains", [])) for h in all_seen):
            add("DECLARED_NOT_SEEN", "note", "", "",
                f"{r.get('name', '?')} is in the notice but no capture reached {', '.join(r.get('domains', []))}",
                "Either the pages tested never load it, or the notice is stale. Test the page that uses it, or drop it from the notice.")

    # 7. Form fields whose category the notice never mentions.
    for form in (forms or []):
        for f in form.get("fields", []):
            cat = f.get("category")
            if cat and cat not in notice.categories:
                add("UNDECLARED_FIELD", "mismatch", "", "",
                    f"form '{form.get('name', '?')}' on {form.get('page', '?')} collects '{f.get('name')}' ({cat})",
                    f"Add '{cat}' to the categories the notice says you collect, or stop asking for it.")

    if not captures.get("baseline"):
        add("MISSING_CAPTURE", "note", "baseline", "", "no baseline.har given", "Capture the untouched page first; most checks depend on it.")
    if "reject" not in captures:
        add("MISSING_CAPTURE", "note", "reject", "", "no reject.har given", "Capture the reject path; FIRES_AFTER_REJECT was not tested.")

    findings.sort(key=lambda f: ({"mismatch": 0, "check": 1, "note": 2}[f["level"]], f["code"], f["host"]))
    return findings


def render(notice, captures, findings):
    counts = {k: sum(1 for f in findings if f["level"] == k) for k in ("mismatch", "check", "note")}
    lines = [
        f"# Said vs sent: {notice.site or 'site'}",
        "",
        f"Notice: {notice.source or '(not given)'}; read as of {notice.as_of or '(no date)'}",
        "States captured: " + ", ".join(f"{s} ({len(captures[s])} requests)" for s in STATES if s in captures),
        f"Result: {counts['mismatch']} mismatch, {counts['check']} check, {counts['note']} note",
        "",
        "These rows compare documents with observed traffic. They are facts to fix or explain, not a legal opinion.",
        "",
        "| # | level | code | state | who | evidence | fix |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, f in enumerate(findings, 1):
        ev = f["evidence"].replace("|", "\\|")
        lines.append(f"| {i} | {f['level']} | {f['code']} | {f['state'] or '-'} | {f['who'] or '-'} | {ev} | {f['fix']} |")
    if not findings:
        lines.append("| - | - | - | - | - | nothing to report for the states captured | - |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--notice", required=True)
    ap.add_argument("--captures", required=True)
    ap.add_argument("--forms")
    ap.add_argument("--out", default=".")
    ap.add_argument("--fail-on-mismatch", action="store_true", help="exit 1 when any mismatch row exists (for CI)")
    a = ap.parse_args(argv)

    with open(a.notice, encoding="utf-8") as fh:
        notice = Notice(json.load(fh))
    captures = {}
    for s in STATES:
        p = os.path.join(a.captures, f"{s}.har")
        if os.path.exists(p):
            captures[s] = load_har(p)
    forms = None
    if a.forms:
        with open(a.forms, encoding="utf-8") as fh:
            forms = json.load(fh)
    findings = analyse(notice, captures, forms)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "ledger.md"), "w", encoding="utf-8") as fh:
        fh.write(render(notice, captures, findings))
    with open(os.path.join(a.out, "ledger.json"), "w", encoding="utf-8") as fh:
        json.dump({"site": notice.site, "as_of": notice.as_of, "findings": findings}, fh, indent=2, ensure_ascii=False)
    n = sum(1 for f in findings if f["level"] == "mismatch")
    print(f"{len(findings)} rows, {n} mismatch -> {os.path.join(a.out, 'ledger.md')}")
    return 1 if (a.fail_on_mismatch and n) else 0


if __name__ == "__main__":
    sys.exit(main())
