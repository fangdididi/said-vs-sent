# said-vs-sent（说的 vs 发的）

[English](README.md) | **简体中文**

一个检查网站有没有兑现自己隐私承诺的智能体技能。它把隐私声明、Cookie 横幅和表单**说的**，与浏览器在四种同意状态下实际**发出去的**放在一起对照，写出一份带日期的差异账本：每条不一致都附证据和修复建议。

## 为什么需要它

隐私声明可以写得很用心，却和它描述的网站对不上。标签管理器里加载着没人记得加过的脚本；“全部拒绝”按钮保存了选择，会话录屏脚本却还在跑；结算表单开始要求填生日，声明里却从没提过。光看文字发现不了这些，手动翻 HAR 文件又太慢。

said-vs-sent 让这种对照可以重复进行：

- 网站**说的**：声明点名的服务商、关于同意的承诺、收集的数据类别；
- 网站**发的**：横幅未操作、全部接受、全部拒绝、开启全球隐私控制（GPC）这四种状态下，分别访问了哪些主机、写入了哪些 Cookie；
- **账本**：每条不一致一行，写明是谁、何时、哪个 URL（已去掉查询参数）、哪个状态、怎么修。

它不判断是否合法，只拿网站自己的话来检验网站，所以哪个国家都适用。如果你指定了某部法律或指引，智能体会在报告里把相关行对应过去，并引用原文和日期。

## 功能

- **四状态抓包方案**（baseline、accept、reject、gpc）：每种状态用干净的配置文件，提供手动和脚本化两种录制方式。
- **主张文件**：从声明整理而来，每个点名的接收方都附一句原文短引用，每一行都能追溯到它所检验的那句话。
- **`gapcheck.py`**：只用 Python 标准库，离线运行，读取 HAR 文件，报告 8 类行：未声明接收方、选择前触发、选择前写 Cookie、拒绝后仍触发、无视 GPC、表单字段未声明、已声明未出现、缺少抓包。
- **三个级别**：*mismatch*（违背了明说的承诺）、*check*（声明没表态，交给人判断）、*note*（仅提示）。
- **内置服务商对照表**：涵盖常见的统计、广告、会话录屏、客服、字体、CDN、同意管理工具主机，声明里可以逐个覆盖。
- **证据安全**：自动去掉查询参数，避免标识符泄露进报告。
- **CI 模式**：加 `--fail-on-mismatch`，只要有不一致就以退出码 1 结束。
- **修复前后对比**：用新抓包重跑，证明修好并关闭对应行。

## 安装

把整个文件夹复制到你的智能体读取技能的位置。

| 智能体 | 放置位置 |
|---|---|
| Claude Code | `~/.claude/skills/said-vs-sent/`（个人）或 `.claude/skills/said-vs-sent/`（项目） |
| Codex CLI | `~/.codex/skills/said-vs-sent/`，或在 `AGENTS.md` 里引用 `SKILL.md` |
| Cursor | `.cursor/skills/said-vs-sent/`，或让项目规则指向 `SKILL.md` |
| 其他智能体 | 把 `SKILL.md`（或 `SKILL.zh-CN.md`）作为指令加载，并让它能调用 `scripts/gapcheck.py` |

```bash
git clone https://github.com/fangdididi/said-vs-sent.git ~/.claude/skills/said-vs-sent
```

脚本只需要 Python 3.8 及以上，不依赖其他库。

## 使用

直接用大白话告诉智能体，比如：

- “我网店的 Cookie 横幅，在用户点之前到底有没有拦住东西？”
- “拿我们的隐私政策对照首页、商品页和结算页实际加载的内容。”
- “我们换了标签管理器容器，帮我确认拒绝和 GPC 还管用。”

智能体会先写范围卡，把声明整理成 `notice.json`，告诉你怎么抓包（或者用它能控制的浏览器自己抓），然后运行：

```bash
python3 scripts/gapcheck.py --notice notice.json --captures captures/ --forms forms.json --out report/
```

## 示例

`examples/demo/` 里虚构的茶叶网店声称“只有您同意后才启用统计”“我们尊重全球隐私控制”：

```bash
python3 examples/demo/make_demo.py
python3 scripts/gapcheck.py --notice examples/demo/notice.json --captures examples/demo/captures \
  --forms examples/demo/forms.json --out examples/demo/output
```

结果是 7 行，其中 6 条不一致：
1. 页面未操作时 Google Analytics 就写入了 `_ga`；
2. 点拒绝后 Microsoft Clarity 仍在加载；
3. 横幅未操作时 Google Analytics 就请求了 `/g/collect`；
4. 开启 GPC 后 Meta Pixel 仍然加载；
5. 结算页收集“生日”，但声明里没有出生日期这类数据；
6. 声明没有提到 Microsoft Clarity（会话录屏）；
7. （提示）声明点名了 Klaviyo，但测过的页面都没访问它。

带修复建议的完整表格见 `examples/demo/output/ledger.md`。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

## 文件结构

```
said-vs-sent/
├── SKILL.md                    # 技能说明（英文）
├── SKILL.zh-CN.md              # 技能说明（中文）
├── README.md / README.zh-CN.md
├── scripts/gapcheck.py         # 声明与 HAR 对照，输出 ledger.md 和 ledger.json
├── references/
│   ├── notice-format.md        # notice.json 与 forms.json 格式
│   └── capture-guide.md        # 四种状态的手动和脚本化录制方法
├── examples/demo/              # 虚构网店：声明、表单、HAR 生成器、示例输出
├── tests/test_gapcheck.py      # 34 个单元测试和端到端测试
└── LICENSE
```

## 局限

这是对文档和实际流量的事实对照，不是法律意见。结果只覆盖你抓过的页面、状态、地区和日期。原始 HAR 文件含 Cookie 和令牌，请勿外传。

## 许可证

MIT © fangdididi
