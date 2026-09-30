#!/usr/bin/env python3
"""高性价比升学指南 · 静态站生成器.

用法:
    python3 build.py

读取 entries/*.md（YAML frontmatter + "- 字段：" 正文），生成根目录 index.html。
增删改条目后重新运行本脚本即可，无需其他依赖（纯标准库）。
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRIES_DIR = ROOT / "entries"
OUT = ROOT / "index.html"

SITE_TITLE = "高性价比升学指南"
SITE_SUB = "花掉什么、换回什么、证据有多硬 —— 每个升学、留学与移民决策都算一笔账"

RATIO_ORDER = {"极高": 0, "高": 1, "一般": 2}

# 编号前缀 → 板块：一站三库，导航按板块分区
SEC_MAP = {"LS": "升学", "LX": "留学", "YM": "移民"}
SEC_ORDER = ["升学", "留学", "移民"]
SEC_PREFIX = {"升学": "LS", "留学": "LX", "移民": "YM"}


def sec_of(entry: dict) -> str:
    no = entry.get("编号", "")
    for p, s in SEC_MAP.items():
        if no.startswith(p + "-") or no == p:
            return s
    return "升学"


def parse_entry(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta: dict = {}
    body = text
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
        body = m.group(2).strip()
    fields: dict = {}
    order: list = []
    for line in body.splitlines():
        fm = re.match(r"^-\s*([^：:]+)[：:]\s*(.*)$", line)
        if fm:
            k = fm.group(1).strip()
            fields[k] = fm.group(2).strip()
            order.append(k)
        elif order:
            fields[order[-1]] += "\n" + line
    meta["_fields"] = fields
    meta["_order"] = order
    return meta


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def nl2br(s: str) -> str:
    return esc(s).replace("\n", "<br>")


def main() -> None:
    entries = [parse_entry(p) for p in sorted(ENTRIES_DIR.glob("*.md"))]
    entries.sort(key=lambda e: (RATIO_ORDER.get(e.get("性价比", ""), 9), e.get("编号", "")))

    cats = sorted({e.get("分类", "") for e in entries if e.get("分类")})
    evs = sorted({e.get("证据等级", "") for e in entries if e.get("证据等级")},
                 key=lambda x: ({"A": 0, "B": 1, "C": 2}.get(x[0], 9), x))
    ratios = [r for r in ("极高", "高", "一般") if any(e.get("性价比") == r for e in entries)]
    latest = max((e.get("日期", "") for e in entries), default="")

    AUD_ORDER = ["初中", "高中", "大学", "通用"]
    auds = [a for a in AUD_ORDER if any(e.get("人群") == a for e in entries)]

    cards = []
    for e in entries:
        f = e["_fields"]
        search_text = " ".join([e.get("编号", ""), e.get("标题", ""), e.get("分类", ""),
                                f.get("成本", ""), f.get("说人话", ""), f.get("收益", ""),
                                f.get("备注", "")])
        ratio = e.get("性价比", "")
        badge_ratio = f'<span class="badge ratio-{esc(ratio)}">性价比·{esc(ratio)}</span>' if ratio else ""
        detail_rows = []
        for k in e["_order"]:
            if k in ("成本", "说人话", "性价比"):
                continue
            if k == "附件":
                parts = [p.strip() for p in f[k].split("|", 1)]
                label = parts[1] if len(parts) > 1 else "附件下载"
                detail_rows.append(
                    f'<div class="row"><div class="label">附件下载</div>'
                    f'<div class="val"><a href="{esc(parts[0])}">{esc(label)}</a></div></div>')
                continue
            label = {"收益": "算账明细", "证据等级": "证据有多硬",
                     "来源": "原始来源", "备注": "适用人群与提醒",
                     "国家/项目": "国家 / 项目", "政策时效": "政策时效"}.get(k, k)
            detail_rows.append(
                f'<div class="row"><div class="label">{esc(label)}</div>'
                f'<div class="val">{nl2br(f[k])}</div></div>')
        sec = sec_of(e)
        country = f'<span class="badge country">{esc(e.get("国家/项目", ""))}</span>' \
            if e.get("国家/项目") else ""
        cards.append(f"""
<article class="card" id="{esc(e.get('编号', ''))}" data-ratio="{esc(ratio)}" data-cat="{esc(e.get('分类', ''))}"
         data-ev="{esc(e.get('证据等级', ''))}" data-aud="{esc(e.get('人群', ''))}" data-sec="{sec}" data-text="{esc(search_text.lower())}">
  <div class="badges">{badge_ratio}<span class="badge sec">板块·{sec}</span>{country}<span class="badge">{esc(e.get('分类', ''))}</span>
  <span class="badge aud">人群·{esc(e.get('人群', ''))}</span>
  <span class="badge ev">证据 {esc(e.get('证据等级', ''))}</span></div>
  <h2><span class="no">{esc(e.get('编号', ''))}</span> {esc(e.get('标题', ''))}</h2>
  <p class="cost">💰 {esc(f.get('成本', ''))}</p>
  <p class="plain">{esc(f.get('说人话', ''))}</p>
  <details><summary>展开看完整算账</summary>
    <div class="detail">{''.join(detail_rows)}</div>
  </details>
  <p class="foot">数据截至：{esc(e.get('数据截至', ''))} ｜ 条目日期：{esc(e.get('日期', ''))}</p>
</article>""")

    opt_cats = "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in cats)
    opt_evs = "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in evs)
    opt_auds = "".join(f'<option value="{esc(a)}">{esc(a)}</option>' for a in auds)
    ratio_btns = '<button data-r="" class="on">全部</button>' + "".join(
        f'<button data-r="{r}">{r}</button>' for r in ratios)
    sec_btns = '<button data-s="" class="on">全部</button>' + "".join(
        f'<button data-s="{s}">{s}</button>' for s in SEC_ORDER)
    sec_counts = {s: sum(1 for e in entries if sec_of(e) == s) for s in SEC_ORDER}
    stats_line = (f"共 {len(entries)} 条 · " +
                  " · ".join(f"{s} {sec_counts[s]} 条" for s in SEC_ORDER) +
                  f" · 最后更新 {esc(latest)} · 每条标明证据等级，查不到就写查不到")

    toc_secs = []
    for s in SEC_ORDER:
        sec_entries = [e for e in entries if sec_of(e) == s]
        if not sec_entries:
            continue
        groups = []
        for a in auds:
            items = [e for e in sec_entries if e.get("人群") == a]
            if not items:
                continue
            lis = "".join(
                f'<li><a href="#{esc(e.get("编号", ""))}"><span class="no">{esc(e.get("编号", ""))}</span> '
                f'{esc(e.get("标题", ""))}</a></li>' for e in items)
            groups.append(
                f'<div class="toc-group"><h3><a href="?sec={esc(s)}&aud={esc(a)}" class="toc-aud">{esc(a)}</a>'
                f'<span class="cnt">{len(items)} 条</span></h3><ul>{lis}</ul></div>')
        toc_secs.append(
            f'<div class="toc-sec"><h2 class="toc-sec-h"><a href="?sec={esc(s)}">{s}</a>'
            f'<span class="cnt">{len(sec_entries)} 条</span></h2>{"".join(groups)}</div>')
    toc = "".join(toc_secs)

    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SITE_TITLE} · {SITE_SUB}</title>
<meta name="description" content="{SITE_TITLE}：{SITE_SUB}。共 {len(entries)} 条，每条写明成本、收益、证据等级。">
<style>
:root{{--bg:#faf8f3;--card:#fff;--ink:#222;--mut:#888;--line:#e8e2d6;--acc:#b7792b}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.7}}
.wrap{{max-width:860px;margin:0 auto;padding:20px 16px 60px}}
header{{text-align:center;padding:28px 0 10px}}
header h1{{margin:0;font-size:30px;letter-spacing:2px}}
header p{{color:var(--mut);margin:8px 0 0}}
.stats{{text-align:center;color:var(--mut);font-size:14px;margin-bottom:18px}}
.toolbar{{position:sticky;top:0;background:var(--bg);padding:10px 0;z-index:5;border-bottom:1px solid var(--line)}}
.toolbar .row{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}}
.toolbar button,.toolbar select,.toolbar input{{font-size:14px;padding:7px 12px;border:1px solid var(--line);
 border-radius:20px;background:#fff;color:var(--ink)}}
.toolbar button.on{{background:var(--ink);color:#fff;border-color:var(--ink)}}
.toolbar input[type=search]{{flex:1;min-width:160px;border-radius:8px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;
 padding:18px;margin:16px 0}}
.badges{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}}
.badge{{font-size:12px;padding:3px 10px;border-radius:12px;background:#f0ece1;color:#666}}
.badge.ratio-极高{{background:#1a7f4b;color:#fff}}
.badge.ratio-高{{background:#e8f3ec;color:#1a7f4b}}
.badge.ratio-一般{{background:#f0ece1;color:#666}}
.badge.ev{{background:#e8effa;color:#2b5cb7}}
.card h2{{margin:6px 0 10px;font-size:19px;line-height:1.5}}
.card h2 .no{{color:var(--acc);font-size:14px;margin-right:6px}}
.cost{{font-size:14px;color:#555;margin:6px 0}}
.plain{{font-size:16px;margin:10px 0;padding:10px 12px;background:#fdf6e3;
 border-left:3px solid var(--acc);border-radius:0 8px 8px 0}}
details{{margin-top:8px}}
summary{{cursor:pointer;color:var(--acc);font-size:14px}}
.detail .row{{display:flex;gap:10px;margin:10px 0;font-size:14px}}
.detail .label{{flex:0 0 88px;color:var(--mut)}}
.detail .val{{flex:1}}
.foot{{font-size:12px;color:var(--mut);margin-top:12px}}
.empty{{text-align:center;color:var(--mut);padding:40px 0;display:none}}
footer{{text-align:center;color:var(--mut);font-size:13px;margin-top:36px;line-height:2}}
footer a{{color:var(--acc)}}
.method{{background:#fff;border:1px dashed var(--line);border-radius:12px;
 padding:16px;margin:24px 0;font-size:14px;color:#555}}
.method b{{color:var(--ink)}}
.toc{{background:#fff;border:1px solid var(--line);border-radius:12px;
 padding:16px 18px;margin:24px 0}}
.toc h2{{margin:0 0 10px;font-size:17px}}
.toc-group{{margin-bottom:12px}}
.toc-group h3{{margin:10px 0 6px;font-size:15px}}
.toc-group h3 .cnt{{color:var(--mut);font-size:12px;margin-left:8px;font-weight:normal}}
.toc-aud{{color:var(--ink);text-decoration:none;border-bottom:2px solid var(--acc)}}
.toc ul{{margin:4px 0;padding-left:4px;list-style:none}}
.toc li{{margin:5px 0;font-size:14px}}
.toc li a{{color:#444;text-decoration:none}}
.toc li a:hover{{color:var(--acc)}}
.toc li .no{{color:var(--acc);font-size:12px;margin-right:6px}}
.badge.aud{{background:#eef3e6;color:#5a7a2b}}
.badge.sec{{background:#f3e8f5;color:#7a2b8f}}
.badge.country{{background:#e6f0f5;color:#2b6f8f}}
.toc-sec{{margin-bottom:18px}}
.toc-sec-h{{margin:14px 0 6px;font-size:16px}}
.toc-sec-h a{{color:var(--ink);text-decoration:none;border-bottom:2px solid var(--acc)}}
.toc-sec-h .cnt{{color:var(--mut);font-size:12px;margin-left:8px;font-weight:normal}}
</style>
</head>
<body>
<div class="wrap">
<header><h1>{SITE_TITLE}</h1><p>{SITE_SUB}</p></header>
<p class="stats">{stats_line}</p>
<div class="toolbar">
  <div class="row" id="secRow">{sec_btns}</div>
  <div class="row" id="ratioRow">{ratio_btns}</div>
  <div class="row">
    <select id="audSel"><option value="">全部人群</option>{opt_auds}</select>
    <select id="catSel"><option value="">全部分类</option>{opt_cats}</select>
    <select id="evSel"><option value="">全部证据等级</option>{opt_evs}</select>
    <input type="search" id="q" placeholder="搜索：如 复读 / 马来亚 / 选科">
  </div>
</div>
<div class="toc" id="toc"><h2>📖 目录 · 按板块找条目</h2>{toc}</div>
<div class="method"><b>怎么读这本指南：</b>每条只回答两件事 ——
<b>花掉什么</b>（钱 / 时间 / 精力）、<b>换回什么</b>（分数与录取 / 时间 / 金钱 / 选择权）。
证据分三级：<b>A</b> = 官方数据或大样本实证，<b>B</b> = 机构数据或单年数据，<b>C</b> = 从业经验。
<b>性价比是判断不是证据</b>，只算 C 级。政策、分数线带截至日期，请以官方最新公布为准。</div>
<main id="list">{''.join(cards)}</main>
<p class="empty" id="empty">没有符合条件的条目，换个筛选试试。</p>
<footer>《{SITE_TITLE}》 · 内容持续更新中<br>
方法论致敬 <a href="https://eternity4719.github.io/HowToLiveBetter/">《高性价比人生指南》</a>（Unlicense 公有领域）</footer>
</div>
<script>
const params = new URLSearchParams(location.search);
const cards = [...document.querySelectorAll('.card')];
const state = {{ratio: params.get('ratio') || '', cat: params.get('cat') || '',
                ev: params.get('ev') || '', aud: params.get('aud') || '',
                sec: params.get('sec') || '',
                q: (params.get('q') || '').toLowerCase()}};
const SEC_PREFIX = {{"升学": "LS", "留学": "LX", "移民": "YM"}};

document.querySelectorAll('#secRow button').forEach(b => {{
  if (b.dataset.s === state.sec) {{
    document.querySelector('#secRow .on').classList.remove('on');
    b.classList.add('on');
  }}
  b.onclick = () => {{ state.sec = b.dataset.s; sync(); }};
}});
document.querySelectorAll('#ratioRow button').forEach(b => {{
  if (b.dataset.r === state.ratio) {{
    document.querySelector('#ratioRow .on').classList.remove('on');
    b.classList.add('on');
  }}
  b.onclick = () => {{ state.ratio = b.dataset.r; sync(); }};
}});
const catSel = document.getElementById('catSel'), evSel = document.getElementById('evSel'),
      audSel = document.getElementById('audSel'), qInput = document.getElementById('q');
catSel.value = state.cat; evSel.value = state.ev; audSel.value = state.aud;
qInput.value = params.get('q') || '';
catSel.onchange = () => {{ state.cat = catSel.value; sync(); }};
evSel.onchange = () => {{ state.ev = evSel.value; sync(); }};
audSel.onchange = () => {{ state.aud = audSel.value; sync(); }};
let t; qInput.oninput = () => {{ clearTimeout(t);
  t = setTimeout(() => {{ state.q = qInput.value.toLowerCase(); sync(); }}, 200); }};

function sync() {{
  const p = new URLSearchParams();
  if (state.sec) p.set('sec', state.sec);
  if (state.ratio) p.set('ratio', state.ratio);
  if (state.cat) p.set('cat', state.cat);
  if (state.ev) p.set('ev', state.ev);
  if (state.aud) p.set('aud', state.aud);
  if (state.q) p.set('q', state.q);
  history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
  let n = 0;
  cards.forEach(c => {{
    const ok = (!state.sec || c.dataset.sec === state.sec)
      && (!state.ratio || c.dataset.ratio === state.ratio)
      && (!state.cat || c.dataset.cat === state.cat)
      && (!state.ev || c.dataset.ev === state.ev)
      && (!state.aud || c.dataset.aud === state.aud)
      && (!state.q || c.dataset.text.includes(state.q));
    c.style.display = ok ? '' : 'none';
    if (ok) n++;
  }});
  const emptyEl = document.getElementById('empty');
  emptyEl.style.display = n ? 'none' : '';
  if (!n && state.sec && SEC_PREFIX[state.sec]) {{
    emptyEl.textContent = '「' + state.sec + '」板块暂无条目 —— 在对话里说一句「新增一条 ' +
      SEC_PREFIX[state.sec] + '」即可入库。';
  }} else if (!n) {{
    emptyEl.textContent = '没有符合条件的条目，换个筛选试试。';
  }}
  document.getElementById('toc').style.display =
    (state.sec || state.ratio || state.cat || state.ev || state.aud || state.q) ? 'none' : '';
  document.querySelectorAll('#secRow button').forEach(b =>
    b.classList.toggle('on', b.dataset.s === state.sec));
  document.querySelectorAll('#ratioRow button').forEach(b =>
    b.classList.toggle('on', b.dataset.r === state.ratio));
}}
sync();
</script>
</body>
</html>"""
    OUT.write_text(page, encoding="utf-8")
    print(f"built {OUT} with {len(entries)} entries")


if __name__ == "__main__":
    main()
