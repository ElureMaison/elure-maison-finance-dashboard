"""
render.py

Shared HTML rendering for both the static site generator (GitHub Pages,
auto-refreshed daily) and the local Flask app (live editing). One set of
templates so the two surfaces can't visually/logically drift apart -
mirrors the dashboard_common.py pattern from the MannaHouse project.
"""

import hashlib
import json

from finance_common import CATEGORIES, type_label

VERSE = "“Commit to the LORD whatever you do, and he will establish your plans.” — Proverbs 16:3"

SHARED_CSS = """
html, body { margin: 0; padding: 0; }
.fd-root {
  --surface-1:      #fcfcfb;
  --page:           #f9f9f7;
  --text-primary:   #0b0b0b;
  --text-secondary: #52514e;
  --text-muted:     #898781;
  --grid:           #e1e0d9;
  --baseline:       #c3c2b7;
  --border:         rgba(11,11,11,0.10);
  --series-revenue: #2a78d6;
  --series-expense: #e34948;
  --good:           #0ca30c;
  --critical:       #d03b3b;
  --seq-blue-400:   #3987e5;
  --seq-blue-600:   #184f95;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--page);
  color: var(--text-primary);
  min-height: 100vh;
  box-sizing: border-box;
}
.fd-root * { box-sizing: border-box; }
@media (prefers-color-scheme: dark) {
  .fd-root {
    --surface-1:      #1a1a19;
    --page:           #0d0d0d;
    --text-primary:   #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted:     #898781;
    --grid:           #2c2c2a;
    --baseline:       #383835;
    --border:         rgba(255,255,255,0.10);
    --series-revenue: #3987e5;
    --series-expense: #e66767;
    --good:           #0ca30c;
    --critical:       #e66767;
    --seq-blue-400:   #3987e5;
    --seq-blue-600:   #86b6ef;
  }
}
.fd-wrap { max-width: 1080px; margin: 0 auto; padding: 32px 20px 64px; }
.fd-header { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 6px; }
.fd-title { font-size: 22px; font-weight: 650; margin: 0; }
.fd-updated { font-size: 13px; color: var(--text-muted); }
.fd-verse { font-size: 12.5px; font-style: italic; color: var(--text-muted); margin-bottom: 22px; }

.fd-nav { display: flex; gap: 4px; margin-bottom: 24px; border-bottom: 1px solid var(--border); }
.fd-nav a { padding: 9px 14px; font-size: 13.5px; font-weight: 550; color: var(--text-secondary); text-decoration: none; border-bottom: 2px solid transparent; }
.fd-nav a.active { color: var(--text-primary); border-bottom-color: var(--series-revenue); }
.fd-nav a:hover { color: var(--text-primary); }

.fd-kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 28px; }
@media (max-width: 760px) { .fd-kpis { grid-template-columns: repeat(2, 1fr); } }
.fd-tile { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }
.fd-tile-label { font-size: 12.5px; color: var(--text-secondary); margin-bottom: 8px; }
.fd-tile-value { font-size: 26px; font-weight: 650; line-height: 1.1; }
.fd-tile-delta { font-size: 12.5px; margin-top: 6px; font-weight: 550; }
.fd-up { color: var(--good); }
.fd-down { color: var(--critical); }

.fd-card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 20px 20px 8px; margin-bottom: 20px; }
.fd-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; flex-wrap: wrap; gap: 8px; }
.fd-card-title { font-size: 14.5px; font-weight: 600; margin: 0; }
.fd-legend { display: flex; gap: 16px; font-size: 12.5px; color: var(--text-secondary); }
.fd-legend-item { display: flex; align-items: center; gap: 6px; }
.fd-swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.fd-toggle { font-size: 12px; color: var(--text-secondary); background: none; border: 1px solid var(--border); border-radius: 6px; padding: 4px 9px; cursor: pointer; font-family: inherit; }
.fd-toggle:hover { background: var(--page); }

.fd-tooltip { position: absolute; background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; font-size: 12px; pointer-events: none; box-shadow: 0 2px 10px rgba(0,0,0,0.12); white-space: nowrap; z-index: 5; }
.fd-tooltip-row { display: flex; gap: 8px; justify-content: space-between; }

table.fd-table { width: 100%; border-collapse: collapse; font-size: 13px; margin: 10px 0 16px; }
table.fd-table th { text-align: left; font-weight: 600; color: var(--text-secondary); font-size: 12px; padding: 6px 10px; border-bottom: 1px solid var(--grid); }
table.fd-table td { padding: 7px 10px; border-bottom: 1px solid var(--grid); font-variant-numeric: tabular-nums; }
table.fd-table td.fd-num { text-align: right; }
table.fd-table tr.fd-forecast td { color: var(--text-muted); font-style: italic; }
table.fd-table tr.fd-overdue td { color: var(--critical); }
.fd-hidden { display: none; }
.fd-cat-bar-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; }
.fd-cat-label { width: 190px; flex-shrink: 0; font-size: 12.5px; color: var(--text-secondary); }
.fd-cat-track { flex: 1; height: 18px; background: var(--page); border-radius: 4px; position: relative; }
.fd-cat-fill { height: 100%; border-radius: 4px; background: var(--seq-blue-400); }
.fd-cat-value { width: 80px; text-align: right; font-size: 12.5px; font-variant-numeric: tabular-nums; flex-shrink: 0; }

.fd-empty { color: var(--text-muted); font-size: 13px; padding: 20px 0; }
.fd-footnote { color: var(--text-muted); font-size: 12px; margin-top: 8px; }
.fd-pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; background: var(--page); color: var(--text-secondary); }
.fd-pill.fd-overdue { background: rgba(208,59,59,0.12); color: var(--critical); }
.fd-due-group { border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }
.fd-due-group-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; font-weight: 600; }
.fd-due-item { display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; color: var(--text-secondary); }
.fd-btn { font-size: 12px; padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--series-revenue); color: #fff; cursor: pointer; text-decoration: none; }
.fd-btn.fd-btn-danger { background: var(--critical); }
.fd-form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 12px; }
.fd-form-row label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-secondary); min-width: 0; }
.fd-form-row input, .fd-form-row select { padding: 8px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--page); color: var(--text-primary); font-family: inherit; font-size: 13px; width: 100%; box-sizing: border-box; }
.fd-actions-cell { display: flex; gap: 6px; }
.fd-dropzone { border: 2px dashed var(--border); border-radius: 6px; padding: 8px 10px; text-align: center; font-size: 12px; color: var(--text-secondary); cursor: pointer; min-height: 21px; display: flex; align-items: center; justify-content: center; transition: border-color 0.15s, background 0.15s; }
.fd-dropzone.fd-drag-over { border-color: var(--series-revenue); background: var(--page); color: var(--text-primary); }
.fd-dropzone.fd-has-file { border-style: solid; color: var(--text-primary); }
.fd-dropzone:focus-visible { outline: 2px solid var(--series-revenue); outline-offset: 2px; }
.fd-filter-select { padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--page); color: var(--text-primary); font-family: inherit; font-size: 12.5px; }
"""

GATE_CSS = """
#fd-gate { position: fixed; inset: 0; background: #0d0d0d; color: #fff; display: flex; align-items: center; justify-content: center; z-index: 100; font-family: system-ui, sans-serif; }
#fd-gate form { display: flex; flex-direction: column; gap: 12px; width: 260px; }
#fd-gate .fd-verse-gate { font-size: 12px; font-style: italic; color: #aaa; text-align: center; }
#fd-gate input { padding: 10px 12px; border-radius: 8px; border: 1px solid #444; background: #1a1a19; color: #fff; font-size: 14px; }
#fd-gate button { padding: 10px 12px; border-radius: 8px; border: none; background: #2a78d6; color: #fff; font-size: 14px; cursor: pointer; }
#fd-gate .fd-gate-error { color: #e66767; font-size: 12.5px; min-height: 16px; }
"""

NAV_TABS = [
    ("dashboard", "Dashboard"),
    ("monthly", "Monthly P&L"),
    ("annual", "Annual P&L"),
    ("ap", "Accounts Payable"),
]

# Wires up every .fd-dropzone on the page - drag-and-drop, click-to-browse,
# and paste (Ctrl+V) all set the same hidden file input. No-op if a page
# has no dropzone. Shared by the Add and Edit forms so both behave the same.
DROPZONE_INIT_JS = """
document.querySelectorAll(".fd-dropzone").forEach(zone => {
  const input = zone.querySelector("input[type=file]");
  const label = zone.querySelector(".fd-dropzone-label");
  const defaultLabel = label.textContent;

  function showFile(file) {
    label.textContent = file ? file.name : defaultLabel;
    zone.classList.toggle("fd-has-file", !!file);
  }

  zone.addEventListener("click", () => input.click());
  zone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("fd-drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("fd-drag-over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("fd-drag-over");
    if (e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      showFile(e.dataTransfer.files[0]);
    }
  });
  input.addEventListener("change", () => showFile(input.files[0]));
  zone.addEventListener("paste", (e) => {
    const items = (e.clipboardData || window.clipboardData).items;
    for (const item of items) {
      if (item.type.indexOf("image") !== -1) {
        const file = item.getAsFile();
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        showFile(file);
        e.preventDefault();
        break;
      }
    }
  });
});

document.querySelectorAll(".fd-toggle").forEach(btn => {
  btn.addEventListener("click", () => {
    const id = btn.getAttribute("data-toggle");
    const el = document.getElementById(id);
    const chartHost = el.previousElementSibling;
    el.classList.toggle("fd-hidden");
    chartHost.classList.toggle("fd-hidden");
    btn.textContent = el.classList.contains("fd-hidden") ? "View data" : "View chart";
  });
});
"""


def receipt_dropzone_html(name="receipt_file", note=""):
    return f"""<div class="fd-dropzone" tabindex="0">
      <input type="file" name="{name}" accept="image/*,.pdf" style="display:none;">
      <span class="fd-dropzone-label">Drop photo, click to browse, or paste</span>
    </div>{note}"""


# Shared chart/KPI JS - used by the Dashboard, Monthly P&L, and Annual P&L
# pages so they all render identically and a fix in one place fixes all
# three. Always injected via shell() (no-op if a page has no matching
# element ids). Charts take a labelFn so the same drawTrendChart/
# drawProfitChart work for month-keyed rows (Dashboard, Monthly P&L) and
# year-keyed rows (Annual P&L).
CHART_JS = """
function fmtCurrency(n, compact) {
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  if (compact && abs >= 1000000) return sign + "$" + (abs/1000000).toFixed(1) + "M";
  if (compact && abs >= 100000) return sign + "$" + (abs/1000).toFixed(0) + "K";
  return sign + "$" + abs.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
}
function fmtExpense(n, compact) {
  return `<span class="fd-down">-${fmtCurrency(Math.abs(n), compact)}</span>`;
}
function fmtProfit(n, compact) {
  if (n > 0) return `<span class="fd-up">+${fmtCurrency(n, compact)}</span>`;
  if (n < 0) return `<span class="fd-down">${fmtCurrency(n, compact)}</span>`;
  return `<span style="color:var(--text-muted);">${fmtCurrency(n, compact)}</span>`;
}
function fmtMonth(m) {
  const [y, mo] = m.split("-");
  const d = new Date(parseInt(y), parseInt(mo)-1, 1);
  return d.toLocaleDateString(undefined, {month: "short", year: "2-digit"});
}

function renderKpiTiles(hostId, tiles) {
  const host = document.getElementById(hostId);
  if (!host) return;
  let html = "";
  tiles.forEach(t => {
    const subHtml = t.sub ? `<div class="fd-tile-delta">${t.sub}</div>` : "";
    html += `<div class="fd-tile"><div class="fd-tile-label">${t.label}</div><div class="fd-tile-value">${t.value}</div>${subHtml}</div>`;
  });
  host.innerHTML = html;
}

function drawTrendChart(hostId, tableId, rows, labelFn) {
  const host = document.getElementById(hostId);
  if (!host || !rows.length) return;
  const w = Math.max(host.clientWidth || 960, 320), h = 260;
  const padL = 56, padR = 16, padT = 16, padB = 28;
  const plotW = w - padL - padR, plotH = h - padT - padB;
  const allVals = rows.flatMap(m => [m.revenue, m.expenses]);
  const maxV = Math.max(1, ...allVals);
  const niceMax = (() => {
    const magnitude = Math.pow(10, Math.floor(Math.log10(maxV || 1)));
    return Math.ceil(maxV / magnitude) * magnitude;
  })();
  const x = i => rows.length > 1 ? padL + (i / (rows.length - 1)) * plotW : padL + plotW / 2;
  const y = v => padT + plotH - (v / niceMax) * plotH;
  const ticks = 4;
  let svg = `<svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" style="overflow:visible;">`;
  for (let t = 0; t <= ticks; t++) {
    const v = niceMax * t / ticks;
    const yy = y(v);
    svg += `<line x1="${padL}" y1="${yy}" x2="${w-padR}" y2="${yy}" stroke="var(--grid)" stroke-width="1"/>`;
    svg += `<text x="${padL-8}" y="${yy+4}" text-anchor="end" font-size="11" fill="var(--text-muted)">${fmtCurrency(v, true)}</text>`;
  }
  const step = Math.ceil(rows.length / 7);
  rows.forEach((m, i) => {
    if (i % step === 0 || i === rows.length - 1) {
      svg += `<text x="${x(i)}" y="${h-8}" text-anchor="middle" font-size="11" fill="var(--text-muted)">${labelFn(m)}</text>`;
    }
  });
  function linePath(key) { return rows.map((m, i) => `${i===0?"M":"L"} ${x(i)} ${y(m[key])}`).join(" "); }
  svg += `<path d="${linePath("revenue")}" fill="none" stroke="var(--series-revenue)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
  svg += `<path d="${linePath("expenses")}" fill="none" stroke="var(--series-expense)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
  const last = rows.length - 1;
  svg += `<circle cx="${x(last)}" cy="${y(rows[last].revenue)}" r="4" fill="var(--series-revenue)" stroke="var(--surface-1)" stroke-width="2"/>`;
  svg += `<circle cx="${x(last)}" cy="${y(rows[last].expenses)}" r="4" fill="var(--series-expense)" stroke="var(--surface-1)" stroke-width="2"/>`;
  svg += `<text x="${x(last)+8}" y="${y(rows[last].revenue)+4}" font-size="11" fill="var(--series-revenue)" font-weight="600">${fmtCurrency(rows[last].revenue, true)}</text>`;
  svg += `<text x="${x(last)+8}" y="${y(rows[last].expenses)+4}" font-size="11" fill="var(--series-expense)" font-weight="600">${fmtCurrency(-rows[last].expenses, true)}</text>`;
  rows.forEach((m, i) => { svg += `<circle data-i="${i}" cx="${x(i)}" cy="${y(m.revenue)}" r="9" fill="transparent" class="fd-hit-${hostId}"/>`; });
  svg += `</svg>`;
  host.innerHTML = svg;
  const tip = document.createElement("div");
  tip.className = "fd-tooltip"; tip.style.display = "none";
  host.appendChild(tip);
  host.querySelectorAll(`.fd-hit-${hostId}`).forEach(el => {
    el.addEventListener("mouseenter", () => {
      const i = +el.getAttribute("data-i"); const m = rows[i];
      tip.innerHTML = `<div style="font-weight:600; margin-bottom:4px;">${labelFn(m)}</div>
        <div class="fd-tooltip-row"><span>Revenue</span><span>&nbsp;${fmtCurrency(m.revenue)}</span></div>
        <div class="fd-tooltip-row"><span>Expenses</span><span>&nbsp;${fmtExpense(m.expenses)}</span></div>
        <div class="fd-tooltip-row"><span>Profit</span><span>&nbsp;${fmtProfit(m.profit)}</span></div>`;
      tip.style.display = "block";
      const rect = host.getBoundingClientRect();
      tip.style.left = Math.min(x(i) + 12, rect.width - 160) + "px";
      tip.style.top = Math.max(y(m.revenue) - 60, 0) + "px";
    });
    el.addEventListener("mouseleave", () => tip.style.display = "none");
  });
  if (tableId) {
    const tableHost = document.getElementById(tableId);
    let t = `<table class="fd-table"><thead><tr><th></th><th>Revenue</th><th>Expenses</th><th>Profit</th></tr></thead><tbody>`;
    rows.forEach(m => { t += `<tr><td>${labelFn(m)}</td><td class="fd-num">${fmtCurrency(m.revenue)}</td><td class="fd-num">${fmtExpense(m.expenses)}</td><td class="fd-num">${fmtProfit(m.profit)}</td></tr>`; });
    t += `</tbody></table>`;
    tableHost.innerHTML = t;
  }
}

function drawProfitChart(hostId, tableId, rows, labelFn) {
  const host = document.getElementById(hostId);
  if (!host || !rows.length) return;
  const w = Math.max(host.clientWidth || 960, 320), h = 220;
  const padL = 56, padR = 16, padT = 16, padB = 28;
  const plotW = w - padL - padR, plotH = h - padT - padB;
  const maxAbs = Math.max(1, ...rows.map(m => Math.abs(m.profit)));
  const baseline = padT + plotH;
  const slot = plotW / rows.length;
  const bw = Math.min(24, slot - 6);
  let svg = `<svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" style="overflow:visible;">`;
  svg += `<line x1="${padL}" y1="${baseline}" x2="${w-padR}" y2="${baseline}" stroke="var(--baseline)" stroke-width="1"/>`;
  rows.forEach((m, i) => {
    const cx = padL + slot * i + slot/2;
    const barH = Math.max(Math.abs(m.profit) * (plotH / maxAbs), m.profit !== 0 ? 2 : 1);
    const yTop = baseline - barH;
    const color = m.profit > 0 ? "var(--good)" : m.profit < 0 ? "var(--critical)" : "var(--baseline)";
    svg += `<rect x="${cx - bw/2}" y="${yTop}" width="${bw}" height="${barH}" rx="3" fill="${color}"/>`;
    const step = Math.ceil(rows.length / 7);
    if (i % step === 0 || i === rows.length - 1) {
      svg += `<text x="${cx}" y="${h-8}" text-anchor="middle" font-size="11" fill="var(--text-muted)">${labelFn(m)}</text>`;
    }
    svg += `<rect data-i="${i}" x="${cx - slot/2}" y="${padT}" width="${slot}" height="${plotH}" fill="transparent" class="fd-phit-${hostId}"/>`;
  });
  svg += `</svg>`;
  host.innerHTML = svg;
  const tip = document.createElement("div");
  tip.className = "fd-tooltip"; tip.style.display = "none";
  host.appendChild(tip);
  host.querySelectorAll(`.fd-phit-${hostId}`).forEach(el => {
    el.addEventListener("mouseenter", () => {
      const i = +el.getAttribute("data-i"); const m = rows[i];
      tip.innerHTML = `<div style="font-weight:600;">${labelFn(m)}</div><div>${fmtProfit(m.profit)}</div>`;
      tip.style.display = "block";
      const rect = el.getBoundingClientRect(), hostRect = host.getBoundingClientRect();
      tip.style.left = Math.min(rect.left - hostRect.left, hostRect.width - 140) + "px";
      tip.style.top = "0px";
    });
    el.addEventListener("mouseleave", () => tip.style.display = "none");
  });
  if (tableId) {
    const tableHost = document.getElementById(tableId);
    let t = `<table class="fd-table"><thead><tr><th></th><th>Profit</th></tr></thead><tbody>`;
    rows.forEach(m => { t += `<tr><td>${labelFn(m)}</td><td class="fd-num">${fmtProfit(m.profit)}</td></tr>`; });
    t += `</tbody></table>`;
    tableHost.innerHTML = t;
  }
}
"""


def fmt_currency_py(n):
    sign = "-" if n < 0 else ""
    n = abs(n)
    return f"{sign}${n:,.2f}"


def fmt_expense_py(n):
    return f'<span class="fd-down">-{fmt_currency_py(abs(n))}</span>'


def fmt_profit_py(n):
    if n > 0:
        return f'<span class="fd-up">+{fmt_currency_py(n)}</span>'
    if n < 0:
        return f'<span class="fd-down">{fmt_currency_py(n)}</span>'
    return f'<span style="color:var(--text-muted);">{fmt_currency_py(n)}</span>'


def nav_html(active_tab, nav_urls):
    links = "".join(
        f'<a href="{nav_urls[key]}" class="{"active" if key == active_tab else ""}">{label}</a>'
        for key, label in NAV_TABS
    )
    return f'<div class="fd-nav">{links}</div>'


def shell(title, active_tab, nav_urls, body_html, data, gate_hash=None, extra_head=""):
    gate_block = ""
    gate_css = ""
    gate_unlock_js = ""
    if gate_hash:
        gate_css = GATE_CSS
        gate_block = f"""
<div id="fd-gate">
  <form id="fd-gate-form">
    <div style="font-size:15px; font-weight:600; text-align:center;">Elure Maison — Finance</div>
    <input type="password" id="fd-gate-input" placeholder="Password" autocomplete="off" autofocus>
    <button type="submit">View dashboard</button>
    <div class="fd-gate-error" id="fd-gate-error"></div>
    <div class="fd-verse-gate">{VERSE}</div>
  </form>
</div>"""
        gate_unlock_js = f"""
const GATE_HASH = "{gate_hash}";
async function sha256(text) {{
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
}}
async function unlock(pw) {{
  const hash = await sha256(pw);
  if (hash === GATE_HASH) {{
    sessionStorage.setItem("fd-unlocked", "1");
    document.getElementById("fd-gate").style.display = "none";
    document.getElementById("fd-content").style.display = "block";
    return true;
  }}
  return false;
}}
document.getElementById("fd-gate-form").addEventListener("submit", async (e) => {{
  e.preventDefault();
  const pw = document.getElementById("fd-gate-input").value;
  const ok = await unlock(pw);
  if (!ok) document.getElementById("fd-gate-error").textContent = "Wrong password.";
}});
if (sessionStorage.getItem("fd-unlocked") === "1") {{
  document.getElementById("fd-gate").style.display = "none";
  document.getElementById("fd-content").style.display = "block";
}}
"""
    content_display = 'style="display:none;"' if gate_hash else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{title}</title>
<style>
{SHARED_CSS}
{gate_css}
</style>
<script>
{CHART_JS}
</script>
{extra_head}
</head>
<body>
{gate_block}
<div class="fd-root" id="fd-content" {content_display}>
  <div class="fd-wrap">
    <div class="fd-header">
      <h1 class="fd-title">Elure Maison — Finance</h1>
      <div class="fd-updated">Last updated {data.get("generated_at_display", "")}</div>
    </div>
    <div class="fd-verse">{VERSE}</div>
    {nav_html(active_tab, nav_urls)}
    {body_html}
  </div>
</div>
<script>
{gate_unlock_js}
{DROPZONE_INIT_JS}
</script>
</body>
</html>"""


def kpi_tiles_html(data):
    months = data["monthly"]
    ytd = data["ytd"]
    total_revenue = sum(m["revenue"] for m in months)
    total_expenses = sum(m["expenses"] for m in months)
    total_orders = sum(m["orders"] for m in months)
    total_profit = total_revenue - total_expenses
    margin = (total_profit / total_revenue * 100) if total_revenue else 0.0
    span = f'{months[0]["month"]} to {months[-1]["month"]}' if months else ""
    tiles = [
        ("Revenue (Total)", fmt_currency_py(total_revenue), f'{total_orders} orders · {span}', None),
        ("Expenses (Total)", fmt_expense_py(total_expenses), span, None),
        ("Profit (Total)", fmt_profit_py(total_profit), span, None),
        ("Margin (Total)", f'{margin:.1f}%', f'YTD profit {fmt_profit_py(ytd["profit"])}', margin >= 0),
        ("Open Accounts Payable", fmt_currency_py(data.get("total_ap", 0)), f'{sum(g["count"] for g in data.get("ap_groups", []))} items', data.get("total_ap", 0) == 0),
    ]
    html = '<div class="fd-kpis">'
    for label, value, sub, up in tiles:
        cls = "fd-up" if up is True else ("fd-down" if up is False else "")
        sub_html = f'<div class="fd-tile-delta {cls}">{sub}</div>' if sub else ""
        html += f'<div class="fd-tile"><div class="fd-tile-label">{label}</div><div class="fd-tile-value">{value}</div>{sub_html}</div>'
    html += "</div>"
    return html


def dashboard_body(data, editable=False):
    kpis = kpi_tiles_html(data)
    data_json = json.dumps(data)

    add_form = ""
    if editable:
        cats_options = "".join(f'<option value="{c}">{c}</option>' for c in CATEGORIES)
        add_form = f"""
    <div class="fd-card">
      <div class="fd-card-head"><h2 class="fd-card-title">Add expense</h2></div>
      <form method="POST" action="/add" enctype="multipart/form-data" class="fd-form-row" style="align-items:end;">
        <label>Date <input type="date" name="date" required></label>
        <label>Category <select name="category">{cats_options}</select></label>
        <label>Vendor <input type="text" name="vendor"></label>
        <label>Description <input type="text" name="description"></label>
        <label>Amount <input type="number" step="0.01" name="amount" required></label>
        <label>Currency <select name="currency"><option value="USD" selected>USD</option><option value="PHP">PHP</option><option value="EUR">EUR</option></select></label>
        <label>Payment method <select name="payment_method">{{PAYMENT_METHOD_OPTIONS}}</select></label>
        <label>Or add new method <input type="text" name="new_payment_method" placeholder="e.g. Amex ...1234"></label>
        <label>Transaction # <input type="text" name="reference_number" placeholder="auto-detected from receipt if left blank"></label>
        <label>Receipt {receipt_dropzone_html()}</label>
        <label style="flex-direction:row; align-items:center; gap:6px;"><input type="checkbox" name="unpaid" value="1" onchange="document.getElementById('due-date-field').style.display=this.checked?'flex':'none'" style="width:auto;"> Unpaid</label>
        <label id="due-date-field" style="display:none;">Due date <input type="date" name="due_date"></label>
        <button type="submit" class="fd-btn">Add</button>
      </form>
    </div>"""

    actions_th = '<th></th>' if editable else ''
    return f"""
    {kpis}

    <div class="fd-card">
      <div class="fd-card-head">
        <h2 class="fd-card-title">Revenue vs. expenses — last 13 months</h2>
        <div style="display:flex; align-items:center; gap:12px;">
          <div class="fd-legend">
            <span class="fd-legend-item"><span class="fd-swatch" style="background:var(--series-revenue)"></span>Revenue</span>
            <span class="fd-legend-item"><span class="fd-swatch" style="background:var(--series-expense)"></span>Expenses</span>
          </div>
          <button class="fd-toggle" data-toggle="trend-table">View data</button>
        </div>
      </div>
      <div id="fd-trend-chart" style="position:relative;"></div>
      <div id="trend-table" class="fd-hidden"></div>
    </div>

    <div class="fd-card">
      <div class="fd-card-head">
        <h2 class="fd-card-title">Monthly profit</h2>
        <button class="fd-toggle" data-toggle="profit-table">View data</button>
      </div>
      <div id="fd-profit-chart" style="position:relative;"></div>
      <div id="profit-table" class="fd-hidden"></div>
    </div>

    <div class="fd-card">
      <div class="fd-card-head">
        <h2 class="fd-card-title" id="fd-cat-title">Expenses by category — this month</h2>
      </div>
      <div id="fd-cat-chart"></div>
    </div>

    {add_form}

    <div class="fd-card">
      <div class="fd-card-head">
        <h2 class="fd-card-title">Recent expenses</h2>
      </div>
      <table class="fd-table">
        <thead><tr><th>Date</th><th>Category</th><th>Type</th><th>Vendor</th><th>Description</th><th>Transaction #</th><th>Receipt</th><th>Amount</th>{actions_th}</tr></thead>
        <tbody id="fd-recent-body"></tbody>
      </table>
    </div>

    <div class="fd-footnote">Revenue is auto-pulled from Shopify (paid orders, net of refunds). Expenses come from the "Elure Maison - Expenses" Google Sheet.</div>

<script>
const DATA = {data_json};
const EDITABLE = {"true" if editable else "false"};

drawTrendChart("fd-trend-chart", "trend-table", DATA.monthly, m => fmtMonth(m.month));
drawProfitChart("fd-profit-chart", "profit-table", DATA.monthly, m => fmtMonth(m.month));

(function() {{
  const host = document.getElementById("fd-cat-chart");
  const titleEl = document.getElementById("fd-cat-title");
  const monthLabel = DATA.monthly.length ? fmtMonth(DATA.monthly[DATA.monthly.length-1].month) : "this month";
  titleEl.textContent = "Expenses by category — " + monthLabel;
  const cats = DATA.current_month_expense_breakdown;
  if (!cats || !cats.length) {{ host.innerHTML = `<div class="fd-empty">No expenses logged this month yet.</div>`; return; }}
  const max = Math.max(...cats.map(c => c.amount));
  let html = "";
  cats.forEach(c => {{
    const pct = (c.amount / max) * 100;
    html += `<div class="fd-cat-bar-row"><div class="fd-cat-label">${{c.category}}</div><div class="fd-cat-track"><div class="fd-cat-fill" style="width:${{pct}}%"></div></div><div class="fd-cat-value">${{fmtExpense(c.amount)}}</div></div>`;
  }});
  host.innerHTML = html;
}})();

(function() {{
  const host = document.getElementById("fd-recent-body");
  const rows = DATA.recent_expenses || [];
  if (!rows.length) {{ host.parentElement.parentElement.innerHTML = '<div class="fd-empty">No expenses logged yet.</div>'; return; }}
  let html = "";
  rows.forEach(r => {{
    const actions = EDITABLE ? `<td class="fd-actions-cell"><a class="fd-btn" href="/edit/${{r.id||''}}">Edit</a><form method="POST" action="/delete/${{r.id||''}}" style="display:inline;" onsubmit="return confirm('Delete this expense?');"><button class="fd-btn fd-btn-danger" type="submit">Del</button></form></td>` : "";
    const receipt = r.receipt_drive_link ? `<a class="fd-btn" href="${{r.receipt_drive_link}}" target="_blank" rel="noopener">Receipt</a>` : "";
    const currencySymbols = {{PHP: "₱", EUR: "€"}};
    const amountCell = (r.original_currency && r.original_currency !== "USD")
      ? `${{fmtExpense(r.amount)}}<div style="font-size:11px; color:var(--text-muted);">${{currencySymbols[r.original_currency] || r.original_currency + " "}}${{Number(r.original_amount).toLocaleString(undefined,{{minimumFractionDigits:2,maximumFractionDigits:2}})}} @ ${{r.fx_rate!=null ? r.fx_rate.toFixed(5) : "?"}}</div>`
      : fmtExpense(r.amount);
    html += `<tr><td>${{r.date}}</td><td>${{r.category}}</td><td>${{r.type_label||''}}</td><td>${{r.vendor||""}}</td><td>${{r.description||""}}</td><td>${{r.reference_number||""}}</td><td>${{receipt}}</td><td class="fd-num">${{amountCell}}</td>${{actions}}</tr>`;
  }});
  host.innerHTML = html;
}})();
</script>
"""


def monthly_body(data):
    actual_rows = data["monthly"][-6:]
    forecast_rows = data["monthly_forecast"]
    all_rows = actual_rows + forecast_rows

    trs = ""
    for i, r in enumerate(actual_rows):
        trs += f'<tr><td>{r["month"]}</td><td>Actual</td><td class="fd-num">{fmt_currency_py(r["revenue"])}</td><td class="fd-num">{fmt_expense_py(r["expenses"])}</td><td class="fd-num">{fmt_profit_py(r["profit"])}</td></tr>'
    for r in forecast_rows:
        trs += f'<tr class="fd-forecast"><td>{r["month"]}</td><td>Forecast</td><td class="fd-num">{fmt_currency_py(r["revenue"])}</td><td class="fd-num">{fmt_expense_py(r["expenses"])}</td><td class="fd-num">{fmt_profit_py(r["profit"])}</td></tr>'

    filter_options = '<option value="__all__">All actual months (total)</option>' + "".join(
        f'<option value="{i}">{r["month"]}{" (forecast)" if not r.get("actual", True) else ""}</option>'
        for i, r in enumerate(all_rows)
    )

    return f"""
    <div class="fd-kpis" id="monthly-kpis"></div>

    <div class="fd-card">
      <div class="fd-card-head">
        <h2 class="fd-card-title">Revenue vs. expenses</h2>
        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
          <select id="monthly-filter" class="fd-filter-select">{filter_options}</select>
          <button class="fd-toggle" data-toggle="monthly-trend-table">View data</button>
        </div>
      </div>
      <div id="monthly-trend-chart" style="position:relative;"></div>
      <div id="monthly-trend-table" class="fd-hidden"></div>
    </div>

    <div class="fd-card">
      <div class="fd-card-head">
        <h2 class="fd-card-title">Monthly profit</h2>
        <button class="fd-toggle" data-toggle="monthly-profit-table">View data</button>
      </div>
      <div id="monthly-profit-chart" style="position:relative;"></div>
      <div id="monthly-profit-table" class="fd-hidden"></div>
    </div>

    <div class="fd-card">
      <div class="fd-card-head"><h2 class="fd-card-title">Monthly P&L — actuals + 6-month forecast</h2></div>
      <div class="fd-footnote" style="margin-bottom:10px;">Forecast = trailing 3-month average, flat (0% assumed growth).</div>
      <table class="fd-table">
        <thead><tr><th>Month</th><th>Status</th><th>Revenue</th><th>Expenses</th><th>Profit</th></tr></thead>
        <tbody>{trs}</tbody>
      </table>
    </div>

<script>
const MONTHLY_ROWS = {json.dumps(all_rows)};
const MONTHLY_ACTUAL_COUNT = {len(actual_rows)};

drawTrendChart("monthly-trend-chart", "monthly-trend-table", MONTHLY_ROWS, m => fmtMonth(m.month));
drawProfitChart("monthly-profit-chart", "monthly-profit-table", MONTHLY_ROWS, m => fmtMonth(m.month));

function updateMonthlyKpis(selection) {{
  let rows, label;
  if (selection === "__all__") {{
    rows = MONTHLY_ROWS.slice(0, MONTHLY_ACTUAL_COUNT);
    label = rows.length ? `${{fmtMonth(rows[0].month)}} – ${{fmtMonth(rows[rows.length-1].month)}}` : "";
  }} else {{
    rows = [MONTHLY_ROWS[+selection]];
    label = rows[0].actual === false ? "Forecast" : "Actual";
  }}
  const revenue = rows.reduce((s,r) => s+r.revenue, 0);
  const expenses = rows.reduce((s,r) => s+r.expenses, 0);
  const orders = rows.reduce((s,r) => s+(r.orders||0), 0);
  const profit = revenue - expenses;
  const margin = revenue ? (profit/revenue*100) : 0;
  renderKpiTiles("monthly-kpis", [
    {{label: "Revenue", value: fmtCurrency(revenue), sub: `${{orders}} orders · ${{label}}`}},
    {{label: "Expenses", value: fmtExpense(expenses), sub: label}},
    {{label: "Profit", value: fmtProfit(profit), sub: label}},
    {{label: "Margin", value: margin.toFixed(1) + "%", sub: label}},
  ]);
}}

document.getElementById("monthly-filter").addEventListener("change", (e) => updateMonthlyKpis(e.target.value));
updateMonthlyKpis("__all__");
</script>
    """


def annual_body(data):
    rows = data["annual"]
    trs = ""
    for r in rows:
        trs += f'<tr><td>{r["year"]}</td><td>{r["label"]}</td><td class="fd-num">{fmt_currency_py(r["revenue"])}</td><td class="fd-num">{fmt_expense_py(r["expenses"])}</td><td class="fd-num">{fmt_profit_py(r["profit"])}</td></tr>'

    filter_options = '<option value="__all__">All years (total)</option>' + "".join(
        f'<option value="{i}">{r["year"]}</option>' for i, r in enumerate(rows)
    )

    return f"""
    <div class="fd-kpis" id="annual-kpis"></div>

    <div class="fd-card">
      <div class="fd-card-head">
        <h2 class="fd-card-title">Revenue vs. expenses by year</h2>
        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
          <select id="annual-filter" class="fd-filter-select">{filter_options}</select>
          <button class="fd-toggle" data-toggle="annual-trend-table">View data</button>
        </div>
      </div>
      <div id="annual-trend-chart" style="position:relative;"></div>
      <div id="annual-trend-table" class="fd-hidden"></div>
    </div>

    <div class="fd-card">
      <div class="fd-card-head">
        <h2 class="fd-card-title">Profit by year</h2>
        <button class="fd-toggle" data-toggle="annual-profit-table">View data</button>
      </div>
      <div id="annual-profit-chart" style="position:relative;"></div>
      <div id="annual-profit-table" class="fd-hidden"></div>
    </div>

    <div class="fd-card">
      <div class="fd-card-head"><h2 class="fd-card-title">Annual P&L</h2></div>
      <table class="fd-table">
        <thead><tr><th>Year</th><th>Status</th><th>Revenue</th><th>Expenses</th><th>Profit</th></tr></thead>
        <tbody>{trs}</tbody>
      </table>
    </div>

<script>
const ANNUAL_ROWS = {json.dumps(rows)};

drawTrendChart("annual-trend-chart", "annual-trend-table", ANNUAL_ROWS, r => String(r.year));
drawProfitChart("annual-profit-chart", "annual-profit-table", ANNUAL_ROWS, r => String(r.year));

function updateAnnualKpis(selection) {{
  let rows, label;
  if (selection === "__all__") {{
    rows = ANNUAL_ROWS;
    label = rows.length ? `${{rows[0].year}} – ${{rows[rows.length-1].year}}` : "";
  }} else {{
    rows = [ANNUAL_ROWS[+selection]];
    label = rows[0].label;
  }}
  const revenue = rows.reduce((s,r) => s+r.revenue, 0);
  const expenses = rows.reduce((s,r) => s+r.expenses, 0);
  const profit = revenue - expenses;
  const margin = revenue ? (profit/revenue*100) : 0;
  renderKpiTiles("annual-kpis", [
    {{label: "Revenue", value: fmtCurrency(revenue), sub: label}},
    {{label: "Expenses", value: fmtExpense(expenses), sub: label}},
    {{label: "Profit", value: fmtProfit(profit), sub: label}},
    {{label: "Margin", value: margin.toFixed(1) + "%", sub: label}},
  ]);
}}

document.getElementById("annual-filter").addEventListener("change", (e) => updateAnnualKpis(e.target.value));
updateAnnualKpis("__all__");
</script>
    """


def ap_body(data, editable=False):
    groups = data.get("ap_groups", [])
    total = data.get("total_ap", 0)
    if not groups:
        body = '<div class="fd-empty">No open Accounts Payable — nothing marked Unpaid in the expenses sheet.</div>'
    else:
        body = ""
        for g in groups:
            due_label = g["due_date"] or "No due date"
            pill = '<span class="fd-pill fd-overdue">Overdue</span>' if g["overdue"] else '<span class="fd-pill">Upcoming</span>'
            items_html = ""
            for item in g["items"]:
                mark_paid = f'<form method="POST" action="/mark_paid/{item.get("id","")}" style="display:inline;"><button class="fd-btn" type="submit">Mark paid</button></form>' if editable else ""
                items_html += f'<div class="fd-due-item"><span>{item.get("category","")} — {item.get("vendor") or item.get("description") or ""}</span><span>{fmt_currency_py(item["amount"])} {mark_paid}</span></div>'
            body += f"""<div class="fd-due-group">
              <div class="fd-due-group-head"><span>{due_label} {pill}</span><span>{fmt_currency_py(g["total"])} — {g["count"]} item{"s" if g["count"] != 1 else ""}</span></div>
              {items_html}
            </div>"""
    return f"""
    <div class="fd-card">
      <div class="fd-card-head"><h2 class="fd-card-title">Payment reminders — by due date</h2></div>
      <div class="fd-footnote" style="margin-bottom:10px;">Total open Accounts Payable: {fmt_currency_py(total)}</div>
      {body}
    </div>
    """
