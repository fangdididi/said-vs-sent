import json, os, subprocess, sys, tempfile, unittest
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import gapcheck as g


def entry(url, cookies=(), t="2026-01-01T00:00:00Z", resp_cookies=()):
    return {"startedDateTime": t, "request": {"url": url},
            "response": {"headers": [{"name": "Set-Cookie", "value": c + "=v"} for c in cookies],
                          "cookies": [{"name": c} for c in resp_cookies]}}


def write_har(d, name, entries):
    with open(os.path.join(d, name + ".har"), "w") as fh:
        json.dump({"log": {"entries": entries}}, fh)


NOTICE = {
    "site": "a.test", "first_party": ["cdn.a.test"],
    "recipients": [
        {"name": "GA", "domains": ["google-analytics.com"], "purpose": "analytics"},
        {"name": "Meta", "domains": ["connect.facebook.net"], "purpose": "advertising"},
        {"name": "Fonts", "domains": ["fonts.gstatic.com"], "purpose": "fonts", "needs_consent": False},
    ],
    "consent_claims": {"blocks_before_consent": True, "honors_reject": True, "honors_gpc": True},
    "data_categories": ["contact"],
}


def run(captures, notice=NOTICE, forms=None):
    n = g.Notice(notice)
    return g.analyse(n, captures, forms)


def codes(findings, level=None):
    return [f["code"] for f in findings if level is None or f["level"] == level]


def recs(*urls):
    return [{"url": u, "host": g.host_of(u), "time": "t", "set_cookies": []} for u in urls]


class Matching(unittest.TestCase):
    def test_suffix_match(self):
        self.assertTrue(g.matches("www.google-analytics.com", "google-analytics.com"))
        self.assertTrue(g.matches("google-analytics.com", ".google-analytics.com"))

    def test_no_partial_label_match(self):
        self.assertFalse(g.matches("evilgoogle-analytics.com", "google-analytics.com"))

    def test_vendor_longest_wins(self):
        self.assertEqual(g.vendor_for("analytics.google.com")[0], "Google Analytics")
        self.assertEqual(g.vendor_for("px.ads.linkedin.com")[1], "advertising")

    def test_unknown_vendor(self):
        self.assertIsNone(g.vendor_for("example.org"))

    def test_strip_query(self):
        self.assertEqual(g.strip_query("https://x.test/p?id=1&cid=secret"), "https://x.test/p")

    def test_host_of_bad(self):
        self.assertEqual(g.host_of("not a url"), "")

    def test_first_party_includes_site(self):
        n = g.Notice(NOTICE)
        self.assertTrue(n.is_first_party("www.a.test"))
        self.assertTrue(n.is_first_party("cdn.a.test"))
        self.assertFalse(n.is_first_party("a.test.evil.com"))


class Har(unittest.TestCase):
    def test_load_skips_data_urls_and_reads_cookies(self):
        with tempfile.TemporaryDirectory() as d:
            write_har(d, "baseline", [entry("data:image/png;base64,xx"), entry("https://x.test/", ["sid"], resp_cookies=["sid", "b"])])
            rows = g.load_har(os.path.join(d, "baseline.har"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["set_cookies"], ["sid", "b"])

    def test_empty_har(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "x.har"), "w") as fh:
                json.dump({}, fh)
            self.assertEqual(g.load_har(os.path.join(d, "x.har")), [])


class Rules(unittest.TestCase):
    def test_clean_site(self):
        f = run({"baseline": recs("https://a.test/", "https://fonts.gstatic.com/f"),
                 "reject": recs("https://a.test/")})
        self.assertEqual(codes(f, "mismatch"), [])

    def test_undeclared_recipient(self):
        f = run({"baseline": recs("https://a.test/"), "accept": recs("https://www.clarity.ms/t"), "reject": []})
        self.assertIn("UNDECLARED_RECIPIENT", codes(f, "mismatch"))

    def test_undeclared_lists_states(self):
        f = run({"baseline": recs("https://x.unknown.test/a"), "reject": recs("https://x.unknown.test/a")})
        row = [r for r in f if r["code"] == "UNDECLARED_RECIPIENT"][0]
        self.assertEqual(row["state"], "baseline,reject")

    def test_fires_before_choice(self):
        f = run({"baseline": recs("https://www.google-analytics.com/g"), "reject": []})
        self.assertIn("FIRES_BEFORE_CHOICE", codes(f, "mismatch"))

    def test_before_choice_is_check_when_notice_admits_it(self):
        n = dict(NOTICE, consent_claims={"blocks_before_consent": False, "honors_reject": True})
        f = run({"baseline": recs("https://www.google-analytics.com/g"), "reject": []}, n)
        self.assertIn("FIRES_BEFORE_CHOICE", codes(f, "check"))

    def test_fonts_not_consent_gated(self):
        f = run({"baseline": recs("https://fonts.gstatic.com/x"), "reject": recs("https://fonts.gstatic.com/x")})
        self.assertNotIn("FIRES_BEFORE_CHOICE", codes(f))
        self.assertNotIn("FIRES_AFTER_REJECT", codes(f))

    def test_needs_consent_override_true(self):
        n = dict(NOTICE, recipients=NOTICE["recipients"] + [{"name": "CDN", "domains": ["cdn.jsdelivr.net"], "needs_consent": True}])
        f = run({"baseline": recs("https://cdn.jsdelivr.net/x"), "reject": []}, n)
        self.assertIn("FIRES_BEFORE_CHOICE", codes(f))

    def test_unknown_declared_uses_purpose(self):
        n = dict(NOTICE, recipients=NOTICE["recipients"] + [{"name": "AdCo", "domains": ["adco.test"], "purpose": "advertising"}])
        f = run({"baseline": recs("https://px.adco.test/p"), "reject": []}, n)
        self.assertIn("FIRES_BEFORE_CHOICE", codes(f))

    def test_fires_after_reject(self):
        f = run({"baseline": [], "reject": recs("https://connect.facebook.net/x")})
        self.assertIn("FIRES_AFTER_REJECT", codes(f, "mismatch"))

    def test_accept_traffic_is_fine(self):
        f = run({"baseline": [], "accept": recs("https://connect.facebook.net/x", "https://www.google-analytics.com/g"), "reject": []})
        self.assertEqual(codes(f, "mismatch"), [])

    def test_ignores_gpc(self):
        f = run({"baseline": [], "reject": [], "gpc": recs("https://connect.facebook.net/x")})
        self.assertIn("IGNORES_GPC", codes(f, "mismatch"))

    def test_gpc_analytics_not_flagged(self):
        f = run({"baseline": [], "reject": [], "gpc": recs("https://www.google-analytics.com/g")})
        self.assertNotIn("IGNORES_GPC", codes(f))

    def test_gpc_check_when_no_claim(self):
        n = dict(NOTICE, consent_claims={})
        f = run({"baseline": [], "reject": [], "gpc": recs("https://connect.facebook.net/x")}, n)
        self.assertIn("IGNORES_GPC", codes(f, "check"))

    def test_gpc_undeclared_ad_vendor(self):
        f = run({"baseline": [], "reject": [], "gpc": recs("https://bat.bing.com/x")})
        self.assertIn("IGNORES_GPC", codes(f))

    def test_cookie_before_choice(self):
        cap = recs("https://www.google-analytics.com/g")
        cap[0]["set_cookies"] = ["_ga"]
        f = run({"baseline": cap, "reject": []})
        row = [r for r in f if r["code"] == "COOKIE_BEFORE_CHOICE"][0]
        self.assertIn("_ga", row["evidence"])

    def test_first_party_cookie_ignored(self):
        cap = recs("https://a.test/")
        cap[0]["set_cookies"] = ["session"]
        f = run({"baseline": cap, "reject": []})
        self.assertNotIn("COOKIE_BEFORE_CHOICE", codes(f))

    def test_declared_not_seen(self):
        f = run({"baseline": recs("https://www.google-analytics.com/g"), "reject": []})
        self.assertEqual(codes(f, "note").count("DECLARED_NOT_SEEN"), 2)

    def test_undeclared_field(self):
        forms = [{"name": "signup", "page": "/", "fields": [{"name": "email", "category": "contact"}, {"name": "id", "category": "government-id"}]}]
        f = run({"baseline": [], "reject": []}, forms=forms)
        rows = [r for r in f if r["code"] == "UNDECLARED_FIELD"]
        self.assertEqual(len(rows), 1)
        self.assertIn("government-id", rows[0]["evidence"])

    def test_missing_captures_noted(self):
        f = run({})
        self.assertEqual(codes(f).count("MISSING_CAPTURE"), 2)

    def test_order_mismatch_first(self):
        f = run({"baseline": recs("https://www.google-analytics.com/g")})
        levels = [r["level"] for r in f]
        self.assertEqual(levels, sorted(levels, key=lambda x: {"mismatch": 0, "check": 1, "note": 2}[x]))

    def test_query_never_in_evidence(self):
        f = run({"baseline": recs("https://www.google-analytics.com/g?cid=12345&uid=me@x.test"), "reject": []})
        self.assertFalse(any("cid=" in r["evidence"] for r in f))


class Render(unittest.TestCase):
    def test_render_counts_and_escape(self):
        n = g.Notice(NOTICE)
        caps = {"baseline": recs("https://www.google-analytics.com/a|b")}
        md = g.render(n, caps, g.analyse(n, caps))
        self.assertIn("mismatch", md)
        self.assertIn("not a legal opinion", md)
        self.assertIn("\\|", md)

    def test_render_empty(self):
        n = g.Notice(NOTICE)
        md = g.render(n, {}, [])
        self.assertIn("nothing to report", md)


class Cli(unittest.TestCase):
    def test_demo_end_to_end(self):
        root = os.path.join(HERE, "..")
        with tempfile.TemporaryDirectory() as out:
            r = subprocess.run([sys.executable, os.path.join(root, "scripts", "gapcheck.py"),
                                "--notice", os.path.join(root, "examples/demo/notice.json"),
                                "--captures", os.path.join(root, "examples/demo/captures"),
                                "--forms", os.path.join(root, "examples/demo/forms.json"),
                                "--out", out, "--fail-on-mismatch"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            data = json.load(open(os.path.join(out, "ledger.json")))
            got = {f["code"] for f in data["findings"]}
            for c in ("UNDECLARED_RECIPIENT", "FIRES_BEFORE_CHOICE", "FIRES_AFTER_REJECT", "IGNORES_GPC", "COOKIE_BEFORE_CHOICE", "UNDECLARED_FIELD", "DECLARED_NOT_SEEN"):
                self.assertIn(c, got)

    def test_exit_zero_without_flag(self):
        with tempfile.TemporaryDirectory() as d:
            write_har(d, "baseline", [entry("https://a.test/")])
            write_har(d, "reject", [entry("https://a.test/")])
            np = os.path.join(d, "n.json")
            json.dump(NOTICE, open(np, "w"))
            self.assertEqual(g.main(["--notice", np, "--captures", d, "--out", d, "--fail-on-mismatch"]), 0)


if __name__ == "__main__":
    unittest.main()
