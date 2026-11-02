---
name: said-vs-sent
description: Check whether a website's privacy notice and cookie banner match what the browser actually sends. Capture the site in four consent states (untouched, accept, reject, Global Privacy Control), turn the notice into a claims file, and produce a dated ledger of mismatches such as undeclared third parties, tags that fire before a choice or after reject, ignored GPC, and form fields the notice never mentions. Use for "does my cookie banner really work", "audit my privacy policy against the site", "what does my site send before consent", or before a launch, redesign, or tag-manager change.
---

# Said vs sent

## What this is

Most privacy problems on a website are not about wording. The notice says "we load analytics only after you agree", and the tag manager loads it on the first paint anyway. The banner has a reject button, and a session-replay script keeps running after it is pressed. The notice lists five vendors, and the browser talks to nine.

This skill puts the two side by side. On one side is what the site **says**: the privacy notice, the cookie banner, the consent settings, and what the forms ask for. On the other side is what the browser **sent**: every host contacted and every cookie set, recorded separately for each consent state. The result is a ledger in which every row is a concrete mismatch with evidence (a URL with its query string removed, a timestamp, and a cookie name) and a suggested fix.

It works in any jurisdiction because it does not try to decide what the law requires. It checks whether the site keeps its own promises. If the user names a law or a regulator's guidance, you map rows to it in the report. You never declare a site "compliant" or "in violation".

## When to use it

- The site owner asks whether their cookie banner really blocks anything.
- Before a launch, a redesign, a new tag-manager container, or a new analytics or ads vendor.
- After a complaint, an audit request, or a vendor change, to see what really changed.
- When writing or rewriting a privacy notice, to list the recipients the site really uses.
- In CI, so that a build fails when a new undeclared third party appears.

Do not use it to scrape or attack sites. Only capture pages any visitor can open, at normal speed, or a staging site you are allowed to test.

## Steps

### 1. Write the scope card
Record the following before you capture anything:
- the site and the exact pages to test (home, a product or article page, sign-up, checkout, the contact form; consent bugs often live on a single template),
- the date, the region you browse from (banners often change by country), and the browser,
- who asked and their relationship to the site (owner, agency, auditor, or curious visitor),
- any law or guidance the user wants rows mapped to, with the link they trust and the date you read it.

### 2. Turn the notice into claims
Read the privacy notice, the cookie notice, and the banner text. Write `notice.json` (the format is in `references/notice-format.md`):
- `recipients`: each named vendor or category with its domains, its purpose, and a **short verbatim quote** from the notice that names it,
- `consent_claims`: whether the notice or banner says tags wait for consent, whether reject is honoured, and whether GPC is honoured. If the text does not say, leave the key out; the script then reports "check" instead of "mismatch",
- `data_categories`: the kinds of personal data the notice says are collected,
- `as_of` and `notice_url`.

Do not add domains the notice does not name just to make the result look cleaner. A vague phrase like "trusted partners" names nobody.

### 3. Capture four states
Use a fresh browser profile for each state (see `references/capture-guide.md`):
1. **baseline**: open the page and leave the banner alone; wait about 10 seconds and scroll once,
2. **accept**: click "accept all",
3. **reject**: click "reject all", or switch every optional toggle off and save,
4. **gpc**: turn on Global Privacy Control (with a browser that supports it or an extension), then load the page without touching the banner.

Save each state as a HAR file named `baseline.har`, `accept.har`, `reject.har`, and `gpc.har`. Use the same pages in the same order every time. If forms matter, list their fields in `forms.json`, giving each field a category.

### 4. Run the comparison
```
python3 scripts/gapcheck.py --notice notice.json --captures captures/ --forms forms.json --out report/
```
You get `report/ledger.md` and `report/ledger.json`. Row codes:

| code | meaning |
|---|---|
| UNDECLARED_RECIPIENT | a third-party host was contacted that the notice never names |
| FIRES_BEFORE_CHOICE | a consent-gated recipient was reached with the banner untouched |
| COOKIE_BEFORE_CHOICE | such a recipient set a cookie before any choice |
| FIRES_AFTER_REJECT | a consent-gated recipient was still reached after reject |
| IGNORES_GPC | an advertising recipient loaded with GPC on |
| UNDECLARED_FIELD | a form collects a data category the notice never lists |
| DECLARED_NOT_SEEN | the notice names a vendor no capture reached (a stale notice or an untested page) |
| MISSING_CAPTURE | a state was not captured, so its checks did not run |

The levels are **mismatch** (the site breaks its own stated promise), **check** (the notice says nothing either way, so a human decides), and **note** (information only).

### 5. Review every row by hand
The script works on host names. Before reporting:
- open each UNDECLARED_RECIPIENT and decide what it is (a CDN, a payment frame, or a tracker); add it to the notice file if the notice really does name it under another name,
- for FIRES_BEFORE_CHOICE, confirm what was sent. A consent-mode "cookieless ping" sent with consent denied is still a request, so record what the request carried rather than waving it away,
- re-capture any row that looks accidental (for example a cached service worker or a browser extension).

### 6. Write the report
Start with one sentence on the result, then the ledger, then the fix list grouped by who can fix each item (the tag-manager owner, the developer, or whoever writes the notice). If the user named a law or guidance, add a column with the clause each row relates to, quoting the source and its date. Close with the limits: which pages, states, and region were tested, and that this is a factual comparison, not legal advice.

### 7. Prove the fix
After changes, capture the same states and pages again and re-run the script. A row is closed only when a new capture no longer shows it. Keep both ledgers, the old one and the new one.

## Example

A tea shop says "analytics only after you agree" and "we respect Global Privacy Control". The demo in `examples/demo/` finds six mismatches and one note:
- Google Analytics hit `/g/collect` and set `_ga` on the untouched page,
- Microsoft Clarity (session replay) is not named in the notice and keeps loading after reject,
- the Meta Pixel loads with GPC on,
- checkout asks for a birthday although the notice lists no date-of-birth data,
- Klaviyo is named in the notice but no tested page reached it (a note: test the newsletter page or update the notice).

## Tips

- Banners differ by region. Say where you browsed from, and capture again from another region if the site serves visitors from several.
- Use a clean profile for every state, because a consent cookie left over from an earlier state ruins the next one.
- Check single-page-app route changes as well. Some tags load only on the second page view.
- Query strings can carry identifiers. The script removes them from evidence; keep the raw HAR files private.
- Treat "check" rows as questions for the site owner, not as findings against them.
- In CI, run with `--fail-on-mismatch` against captures from a scripted browser on staging.
