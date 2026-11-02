# Capturing the four states / 抓取四种状态

## By hand (Chrome, Edge, Firefox) / 手动

1. Open a new private window or a brand-new profile. No extensions except a GPC one for the gpc state.
   打开新的无痕窗口或全新配置文件。除 gpc 状态用的 GPC 扩展外不装任何扩展。
2. Open DevTools > Network, tick "Preserve log", and turn off "Disable cache" only if you want to see cached loads.
   打开开发者工具的网络面板，勾选“保留日志”。
3. Load the first page, do the state's action (nothing / accept / reject), then visit the other pages in your scope card in the same order.
   打开第一个页面，做该状态的动作（不操作、接受、拒绝），再按范围卡顺序访问其余页面。
4. Wait about 10 seconds on each page and scroll once, because some tags load late or on scroll.
   每页等约 10 秒并滚动一次，有些标签延迟或滚动时才加载。
5. Export: right-click in the request list > "Save all as HAR". Name it `baseline.har`, `accept.har`, `reject.har`, or `gpc.har`.
   导出：在请求列表右键“全部另存为 HAR”，按状态命名。
6. Close the window. Start the next state in a new, clean one.
   关闭窗口，下一种状态用新的干净窗口。

## GPC

Firefox and Brave can send it natively; in Chrome, use a GPC extension. Confirm it is on: in the console, `navigator.globalPrivacyControl` should be `true`, and requests carry `Sec-GPC: 1`.
Firefox、Brave 可原生发送；Chrome 用 GPC 扩展。在控制台确认 `navigator.globalPrivacyControl` 为 `true`，请求头带 `Sec-GPC: 1`。

## Scripted (for CI) / 脚本化

Any headless browser that can record HAR works (for example Playwright's `record_har_path` option on a new context). Use one new context per state, click the banner buttons by their visible text, and add the `Sec-GPC: 1` header plus the `navigator.globalPrivacyControl` init script for the gpc state. Run against staging, not production at volume.
任何能录 HAR 的无头浏览器都可以。每种状态一个新上下文，按按钮文字点击横幅；gpc 状态加 `Sec-GPC: 1` 请求头。对预发布环境运行，不要大量请求生产站点。

## Privacy of the captures / 抓包文件的隐私

HAR files hold cookies, tokens, and query strings. Keep them out of public repos and tickets. Share `ledger.md` instead.
HAR 文件含 Cookie、令牌和查询参数，不要放进公开仓库或工单，分享 `ledger.md` 即可。
