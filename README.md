# said-vs-sent

**English** | [简体中文](README.zh-CN.md)

An agent skill that checks whether a website keeps its own privacy promises. It compares what the privacy notice, cookie banner, and forms **say** with what the browser actually **sent** in four consent states, and writes a dated ledger of every mismatch, with evidence and a fix.

## Why

A privacy notice can be carefully written and still be wrong about the site it describes. Tag managers load scripts nobody remembers adding. A "reject all" button can save the choice and still leave a session-replay script running. A checkout form starts asking for a birthday the notice never mentions. None of this is visible from the text alone, and reading HAR files by hand is slow.

said-vs-sent makes the comparison repeatable:

- what the site **says**: the vendors named in the notice, the consent promises, and the data categories,
- what it **sent**: hosts contacted and cookies set with the banner untouched, after accept, after reject, and with Global Privacy Control on,
- the **ledger**: one row per mismatch, giving who, when, what URL (query removed), which state, and how to fix it.

It does not judge legality. It checks the site against its own words, so it works for any country. If you name a law or guideline, the agent maps rows to it in the report, quoting the source and its date.

## Features

- **Four-state capture plan** (baseline, accept, reject, GPC) with a clean profile per state, plus a manual and a scripted way to record it.
- **Claims file** built from the notice, with a short verbatim quote for every named recipient, so each row can be traced back to the sentence it tests.
- **`gapcheck.py`**: standard-library Python, works offline, reads HAR files, and reports eight row types: undeclared recipient, fires before choice, cookie before choice, fires after reject, ignores GPC, undeclared form field, declared but not seen, and missing capture.
- **Three levels**: *mismatch* (the site breaks a stated promise), *check* (the notice is silent, so a human decides), and *note* (information only).
- **A built-in vendor map** for common analytics, ad, session-replay, chat, font, CDN, and consent-tool hosts, which the notice can override per recipient.
- **Safe evidence**: query strings are removed so identifiers do not leak into the report.
- **CI mode**: `--fail-on-mismatch` exits 1 when any mismatch exists.
- **Before and after**: re-run with new captures to prove a fix and close rows.

## Installation

Copy the folder into the place your agent reads skills from.

| Agent | Where to put it |
|---|---|
| Claude Code | `~/.claude/skills/said-vs-sent/` (personal) or `.claude/skills/said-vs-sent/` (project) |
| Codex CLI | `~/.codex/skills/said-vs-sent/`, or reference `SKILL.md` from your `AGENTS.md` |
| Cursor | `.cursor/skills/said-vs-sent/`, or point a project rule at `SKILL.md` |
| Other agents | Load `SKILL.md` (or `SKILL.zh-CN.md`) as instructions and make `scripts/gapcheck.py` available |

```bash
git clone https://github.com/fangdididi/said-vs-sent.git ~/.claude/skills/said-vs-sent
```

The script needs Python 3.8 or newer and nothing else.

## Usage

Ask your agent in plain words, for example:

- "Does the cookie banner on my shop actually block anything before people click?"
- "Compare our privacy policy with what the site really loads, for the home, product, and checkout pages."
- "We switched tag-manager containers. Check that reject and GPC still work."

The agent writes a scope card, turns the notice into `notice.json`, tells you how to capture (or captures with a browser it controls), and then runs:

```bash
python3 scripts/gapcheck.py --notice notice.json --captures captures/ --forms forms.json --out report/
```

## Example

The fictional tea shop in `examples/demo/` says "analytics only after you agree" and "we respect Global Privacy Control":

```bash
python3 examples/demo/make_demo.py
python3 scripts/gapcheck.py --notice examples/demo/notice.json --captures examples/demo/captures \
  --forms examples/demo/forms.json --out examples/demo/output
```

```
7 rows, 6 mismatch
| 1 | mismatch | COOKIE_BEFORE_CHOICE | baseline | Google Analytics | set _ga from https://www.google-analytics.com/g/collect |
| 2 | mismatch | FIRES_AFTER_REJECT   | reject   | Microsoft Clarity | https://www.clarity.ms/tag/abc after reject |
| 3 | mismatch | FIRES_BEFORE_CHOICE  | baseline | Google Analytics | https://www.google-analytics.com/g/collect with the banner untouched |
| 4 | mismatch | IGNORES_GPC          | gpc      | Meta Pixel | https://connect.facebook.net/en_US/fbevents.js with Sec-GPC: 1 |
| 5 | mismatch | UNDECLARED_FIELD     | -        | - | form 'checkout' on /checkout collects 'birthday' (date-of-birth) |
| 6 | mismatch | UNDECLARED_RECIPIENT | accept,reject | Microsoft Clarity | session-replay host not named in the notice |
| 7 | note     | DECLARED_NOT_SEEN    | -        | - | Klaviyo is in the notice but no capture reached klaviyo.com |
```

The full table, with fixes, is in `examples/demo/output/ledger.md`.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## File structure

```
said-vs-sent/
├── SKILL.md                    # skill instructions (English)
├── SKILL.zh-CN.md              # skill instructions (Chinese)
├── README.md / README.zh-CN.md
├── scripts/gapcheck.py         # notice vs HAR comparison, writes ledger.md + ledger.json
├── references/
│   ├── notice-format.md        # notice.json and forms.json format
│   └── capture-guide.md        # how to record the four states, manual or scripted
├── examples/demo/              # fictional shop: notice, forms, HAR generator, sample output
├── tests/test_gapcheck.py      # 34 unit and end-to-end tests
└── LICENSE
```

## Limits

This is a factual comparison of documents and observed traffic, not legal advice. Results cover only the pages, states, region, and date you captured. Keep raw HAR files private, because they contain cookies and tokens.

## License

MIT © fangdididi
