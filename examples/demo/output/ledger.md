# Said vs sent: shop.example-tea.test

Notice: https://shop.example-tea.test/privacy; read as of 2026-11-02
States captured: baseline (6 requests), accept (8 requests), reject (6 requests), gpc (5 requests)
Result: 6 mismatch, 0 check, 1 note

These rows compare documents with observed traffic. They are facts to fix or explain, not a legal opinion.

| # | level | code | state | who | evidence | fix |
|---|---|---|---|---|---|---|
| 1 | mismatch | COOKIE_BEFORE_CHOICE | baseline | Google Analytics | set _ga from https://www.google-analytics.com/g/collect | Stop this response from setting cookies until opt-in. |
| 2 | mismatch | FIRES_AFTER_REJECT | reject | Microsoft Clarity | https://www.clarity.ms/tag/abc at 2026-11-02T10:00:05Z after reject | Make the reject path tear down or never load this tag; re-test in a fresh profile. |
| 3 | mismatch | FIRES_BEFORE_CHOICE | baseline | Google Analytics | https://www.google-analytics.com/g/collect at 2026-11-02T10:00:05Z with the banner untouched | Hold this tag until the visitor opts in (consent-mode default denied, or load it from the consent callback). |
| 4 | mismatch | IGNORES_GPC | gpc | Meta Pixel | https://connect.facebook.net/en_US/fbevents.js at 2026-11-02T10:00:04Z with Sec-GPC: 1 | Treat Sec-GPC: 1 / navigator.globalPrivacyControl as an opt-out of sale/sharing before loading ad tags. |
| 5 | mismatch | UNDECLARED_FIELD | - | - | form 'checkout' on /checkout collects 'birthday' (date-of-birth) | Add 'date-of-birth' to the categories the notice says you collect, or stop asking for it. |
| 6 | mismatch | UNDECLARED_RECIPIENT | accept,reject | Microsoft Clarity | https://www.clarity.ms/tag/abc (session-replay) first seen 2026-11-02T10:00:07Z | Name this recipient and its purpose in the notice, or remove the tag that calls it. |
| 7 | note | DECLARED_NOT_SEEN | - | - | Klaviyo is in the notice but no capture reached klaviyo.com | Either the pages tested never load it, or the notice is stale. Test the page that uses it, or drop it from the notice. |
