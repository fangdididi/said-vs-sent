# notice.json format / notice.json 格式

```json
{
  "site": "shop.example.test",
  "notice_url": "https://shop.example.test/privacy",
  "as_of": "2026-11-02",
  "first_party": ["shop.example.test", "static.example.test"],
  "recipients": [
    {
      "name": "Google Analytics",
      "domains": ["google-analytics.com", "googletagmanager.com"],
      "purpose": "analytics",
      "quote": "We use Google Analytics after you agree, to count visits."
    },
    {
      "name": "Payment provider",
      "domains": ["js.stripe.com"],
      "purpose": "payments",
      "needs_consent": false,
      "quote": "Card payments are processed by Stripe."
    }
  ],
  "consent_claims": {
    "blocks_before_consent": true,
    "honors_reject": true,
    "honors_gpc": true
  },
  "data_categories": ["contact", "order", "payment", "device"]
}
```

| key / 键 | meaning / 含义 |
|---|---|
| `site` | main host; always counted as first party / 主域名，总算作第一方 |
| `first_party` | other hosts you run (CDN, API) / 你自己运营的其他主机 |
| `recipients[].domains` | suffix-matched: `google-analytics.com` also matches `www.google-analytics.com` / 后缀匹配 |
| `recipients[].purpose` | analytics, advertising, session-replay, social, tag-manager, fonts, cdn, payments, support-chat, error-tracking, consent-tool, or your own word / 用途 |
| `recipients[].needs_consent` | optional override; otherwise known vendors use the built-in map and unknown ones use `purpose` / 可选覆盖 |
| `recipients[].quote` | the notice's own words that name this recipient; required for the report / 声明原文短引用 |
| `consent_claims.*` | include a key only if the notice or banner actually says it; missing means "check", not "mismatch" / 原文明说才填 |
| `data_categories` | compared against `forms.json` field categories / 与表单字段类别比对 |

Categories that normally wait for consent: analytics, advertising, session-replay, social.
默认需要同意的类别：analytics、advertising、session-replay、social。

## forms.json

```json
[
  {"name": "checkout", "page": "/checkout", "fields": [
    {"name": "email", "category": "contact"},
    {"name": "birthday", "category": "date-of-birth"}
  ]}
]
```
Use the same category words as `data_categories`. / 类别用词要与 `data_categories` 一致。
