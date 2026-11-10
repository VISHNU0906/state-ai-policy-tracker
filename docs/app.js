/* Dashboard logic. Reads data/records.json, which the pipeline writes, and
   nothing else. No build step and no libraries. */
(async function () {
  const $ = (id) => document.getElementById(id);
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined && v !== false) n.setAttribute(k, v);
    }
    for (const kid of kids) if (kid) n.append(kid);
    return n;
  };

  let data;
  try {
    data = await (await fetch("data/records.json", { cache: "no-cache" })).json();
  } catch (err) {
    $("lede").textContent = "The data file could not be loaded. If you opened this page from disk, serve the docs folder over HTTP instead (python -m http.server).";
    return;
  }
  const { meta, records } = data;

  // Fixed orders. A category keeps its colour whatever the filters are.
  const CATEGORIES = [
    "Policy and strategy", "Regulation and ethics", "Institutions and bodies", "Funding and budget",
    "Infrastructure and investment", "Partnerships and MoUs", "Skilling and education", "Government deployment",
  ];
  const catColor = (c) => `var(--c${CATEGORIES.indexOf(c) + 1})`;
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const LEVEL_LABEL = { state: "State government", local: "District or city body", judiciary: "High Court" };

  const months = [];
  {
    let [y, m] = meta.window_start.split("-").map(Number);
    const [ey, em] = meta.window_end.split("-").map(Number);
    while (y < ey || (y === ey && m <= em)) {
      months.push(`${y}-${String(m).padStart(2, "0")}`);
      if (++m > 12) { m = 1; y++; }
    }
  }
  const fmtMonth = (ym) => `${MONTHS[+ym.slice(5) - 1]} ${ym.slice(0, 4)}`;
  const fmtDate = (r) => {
    const [y, m, d] = r.date.split("-").map(Number);
    if (r.date_precision === "day") return `${d} ${MONTHS[m - 1]} ${y}`;
    if (r.date_precision === "month") return `${MONTHS[m - 1]} ${y}`;
    return r.date_precision === "year" ? String(y) : "Date unknown";
  };

  const f = { state: "", category: "", sector: "", level: "", q: "", month: "" };
  let shown = 30;

  const matches = (r, skip) =>
    (skip === "state" || !f.state || r.state === f.state) &&
    (skip === "category" || !f.category || r.category === f.category) &&
    (skip === "sector" || !f.sector || r.sector === f.sector) &&
    (!f.level || r.gov_level === f.level) &&
    (skip === "month" || !f.month || r.date.startsWith(f.month)) &&
    (!f.q || (r.title + " " + r.summary + " " + r.source_name).toLowerCase().includes(f.q));

  const count = (rows, key) => rows.reduce((acc, r) => (acc[key(r)] = (acc[key(r)] || 0) + 1, acc), {});

  // ---- tooltip -------------------------------------------------------------
  const tip = $("tip");
  const showTip = (ev, html) => {
    tip.innerHTML = html;
    tip.hidden = false;
    const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
    const rect = ev.type === "focus" ? ev.target.getBoundingClientRect() : null;
    const x = rect ? rect.left + rect.width / 2 : ev.clientX;
    const y = rect ? rect.top : ev.clientY;
    tip.style.left = Math.max(8, Math.min(x + pad, innerWidth - w - 8)) + "px";
    tip.style.top = (y - h - pad < 8 ? y + pad + 8 : y - h - pad) + "px";
  };
  const hideTip = () => { tip.hidden = true; };
  const withTip = (node, html) => {
    node.addEventListener("mousemove", (e) => showTip(e, html()));
    node.addEventListener("focus", (e) => showTip(e, html()));
    node.addEventListener("mouseleave", hideTip);
    node.addEventListener("blur", hideTip);
    return node;
  };
  const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;

  // ---- filter controls -------------------------------------------------------
  const fill = (sel, values, label = (v) => v) =>
    values.forEach((v) => sel.append(el("option", { value: v, text: label(v) })));
  fill($("f-state"), meta.states.slice().sort());
  fill($("f-category"), CATEGORIES);
  fill($("f-sector"), Object.keys(count(records, (r) => r.sector)).sort());
  fill($("f-level"), Object.keys(LEVEL_LABEL).filter((l) => records.some((r) => r.gov_level === l)), (l) => LEVEL_LABEL[l]);
  const bind = (id, key, ev = "change") => $(id).addEventListener(ev, (e) => {
    f[key] = key === "q" ? e.target.value.trim().toLowerCase() : e.target.value;
    shown = 30; render();
  });
  bind("f-state", "state"); bind("f-category", "category"); bind("f-sector", "sector"); bind("f-level", "level");
  bind("f-q", "q", "input");
  $("reset").addEventListener("click", () => {
    Object.keys(f).forEach((k) => (f[k] = ""));
    ["f-state", "f-category", "f-sector", "f-level", "f-q"].forEach((id) => ($(id).value = ""));
    shown = 30; render();
  });
  $("more").addEventListener("click", () => { shown += 30; render(); });
  const set = (key, value) => {
    f[key] = f[key] === value ? "" : value;
    const sel = { state: "f-state", category: "f-category", sector: "f-sector" }[key];
    if (sel) $(sel).value = f[key];
    shown = 30; render();
  };

  // ---- masthead ----------------------------------------------------------------
  const outlets = new Set(records.flatMap((r) => [r.source_name, ...r.other_outlets.split("; ")].filter(Boolean)));
  $("lede").innerHTML =
    `<b>${records.length} recorded steps</b> by ${meta.states.length} state governments between ` +
    `${fmtMonth(meta.window_start.slice(0, 7))} and ${fmtMonth(meta.window_end.slice(0, 7))}: policies, new bodies, ` +
    `agreements, deployments, budgets and rules. Collected from ${outlets.size} news outlets, with repeat coverage ` +
    `of the same announcement merged into one record.`;

  // ---- state by month grid ------------------------------------------------------
  const STEPS = 6;
  function renderGrid() {
    // The grid ignores the state and month filters so it always shows the whole picture;
    // the selected state and month are highlighted instead.
    const base = records.filter((r) => matches({ ...r, state: f.state || r.state }, "month"));
    const byCell = count(base, (r) => r.state + "|" + r.date.slice(0, 7));
    const byState = count(base, (r) => r.state);
    const max = Math.max(1, ...Object.values(byCell));
    const order = meta.states.slice().sort((a, b) => (byState[b] || 0) - (byState[a] || 0) || a.localeCompare(b));
    const grid = $("grid");
    grid.style.gridTemplateColumns = `max-content repeat(${months.length}, minmax(24px, 1fr)) max-content`;
    grid.replaceChildren(el("span"));
    months.forEach((ym) => {
      const jan = ym.endsWith("-01"), show = jan || +ym.slice(5) % 3 === 1;
      grid.append(el("span", { class: "colhead" + (jan ? " yearmark" : ""),
        text: jan ? "Jan " + ym.slice(2, 4) : show ? MONTHS[+ym.slice(5) - 1] : "" }));
    });
    grid.append(el("span"));
    for (const st of order) {
      grid.append(el("button", { class: "rowhead", type: "button", "aria-pressed": String(f.state === st),
        text: st, onclick: () => set("state", st) }));
      for (const ym of months) {
        const n = byCell[st + "|" + ym] || 0;
        const q = n === 0 ? 0 : Math.max(1, Math.ceil((n / max) * STEPS));
        const on = f.month === ym && (!f.state || f.state === st);
        const dim = (f.month && f.month !== ym) || (f.state && f.state !== st);
        const cell = el("button", {
          class: "cell" + (on ? " on" : "") + (dim ? " dim" : ""), type: "button", "data-n": n,
          style: `background:var(--s${q});color:var(--t${q})`, tabindex: n ? 0 : -1,
          "aria-label": `${st}, ${fmtMonth(ym)}: ${plural(n, "record")}`, text: n || "",
          onclick: () => { if (!n) return; const same = f.month === ym && f.state === st;
            f.month = same ? "" : ym; f.state = same ? "" : st; $("f-state").value = f.state; shown = 30; render();
            if (!same) $("h-list").scrollIntoView({ behavior: "smooth", block: "start" }); },
        });
        grid.append(withTip(cell, () => `<b>${st}</b>, ${fmtMonth(ym)}<br>${plural(n, "record")}`));
      }
      grid.append(el("span", { class: "rowtotal", text: byState[st] || 0 }));
    }
    const scale = $("scale");
    scale.replaceChildren(el("span", { text: "Fewer" }));
    for (let q = 0; q <= STEPS; q++) scale.append(el("i", { style: `background:var(--s${q})` }));
    scale.append(el("span", { text: `More (up to ${max} in a month)` }));
  }

  // ---- category stacked bars -----------------------------------------------------
  function renderBars() {
    const base = records.filter((r) => matches(r, "category"));
    const totals = count(base, (r) => r.category);
    const legend = $("legend");
    legend.replaceChildren();
    for (const c of CATEGORIES) {
      legend.append(el("button", { type: "button", "aria-pressed": String(f.category === c), onclick: () => set("category", c) },
        el("span", { class: "dot", style: `background:${catColor(c)}` }), el("span", { text: c }),
        el("span", { class: "n", text: totals[c] || 0 })));
    }
    const byState = {};
    base.forEach((r) => ((byState[r.state] ??= {})[r.category] = (byState[r.state][r.category] || 0) + 1));
    const sum = (o) => Object.values(o || {}).reduce((a, b) => a + b, 0);
    const states = meta.states.filter((s) => !f.state || s === f.state).sort((a, b) => sum(byState[b]) - sum(byState[a]));
    const max = Math.max(1, ...states.map((s) => sum(byState[s])));
    const bars = $("bars");
    bars.replaceChildren();
    for (const st of states) {
      const total = sum(byState[st]);
      const track = el("div", { class: "track", style: `width:${(total / max) * 100}%` });
      for (const c of CATEGORIES) {
        const n = (byState[st] || {})[c] || 0;
        if (!n) continue;
        const seg = el("button", { class: "seg" + (f.category && f.category !== c ? " dim" : ""), type: "button",
          style: `flex:${n} 0 0;background:${catColor(c)}`, "aria-label": `${st}, ${c}: ${n}`,
          onclick: () => set("category", c) });
        track.append(withTip(seg, () => `<b>${st}</b><br>${c}: ${n} of ${total}`));
      }
      bars.append(el("span", { text: st }), el("div", {}, track), el("span", { class: "tot", text: total }));
    }
  }

  // ---- sector bars ------------------------------------------------------------------
  function renderSectors() {
    const base = records.filter((r) => matches(r, "sector"));
    const totals = Object.entries(count(base, (r) => r.sector)).sort((a, b) => b[1] - a[1]);
    const max = Math.max(1, ...totals.map((t) => t[1]));
    const box = $("sectors");
    box.replaceChildren();
    for (const [name, n] of totals) {
      const fillEl = el("div", { class: "fill", style: `width:${(n / max) * 100}%;opacity:${f.sector && f.sector !== name ? 0.3 : 1}` });
      box.append(
        el("button", { class: "name", type: "button", "aria-pressed": String(f.sector === name), text: name, onclick: () => set("sector", name) }),
        withTip(el("div", {}, fillEl), () => `<b>${name}</b><br>${plural(n, "record")}`),
        el("span", { class: "tot", text: n }));
    }
  }

  // ---- record list ---------------------------------------------------------------------
  function renderList() {
    const rows = records.filter((r) => matches(r));
    $("list-count").textContent = rows.length === records.length
      ? `All ${rows.length} records, newest first.`
      : `${plural(rows.length, "record")} of ${records.length} match, newest first.`;
    const list = $("list");
    list.replaceChildren();
    if (!rows.length) {
      list.append(el("li", { class: "empty", text: "No records match these filters. Clear a filter to widen the search." }));
    }
    for (const r of rows.slice(0, shown)) {
      const others = r.other_outlets ? r.other_outlets.split("; ") : [];
      const meta_ = el("p", { class: "meta" },
        el("span", { class: "cat" }, el("span", { class: "dot", style: `background:${catColor(r.category)}` }), el("span", { text: r.category })),
        el("span", { text: r.sector }),
        r.gov_level !== "state" ? el("span", { text: LEVEL_LABEL[r.gov_level] }) : null,
        el("span", { text: r.source_name }),
        others.length ? withTip(el("span", { class: "others", tabindex: 0, text: `also reported by ${plural(others.length, "outlet")}` }),
          () => others.slice(0, 12).join(", ") + (others.length > 12 ? ` and ${others.length - 12} more` : "")) : null);
      list.append(el("li", { class: "rec" },
        el("div", { class: "when" }, el("span", { class: "st", text: r.state }), el("span", { text: fmtDate(r) }),
          r.date_precision !== "day" ? el("span", { class: "approx", text: "approximate date" }) : null),
        el("div", {},
          el("h4", {}, el("a", { href: r.source_url, target: "_blank", rel: "noopener", text: r.title })),
          r.summary && r.summary !== r.title ? el("p", { class: "sum", text: r.summary }) : null,
          meta_)));
    }
    $("more").hidden = rows.length <= shown;
    $("more").textContent = `Show more records (${Math.max(0, rows.length - shown)} left)`;
  }

  function renderActive() {
    const parts = [];
    if (f.state) parts.push(f.state);
    if (f.month) parts.push(fmtMonth(f.month));
    if (f.category) parts.push(f.category);
    if (f.sector) parts.push(f.sector);
    if (f.level) parts.push(LEVEL_LABEL[f.level]);
    if (f.q) parts.push(`text contains "${f.q}"`);
    $("active").textContent = parts.length ? "Showing: " + parts.join(", ") : "";
    $("reset").hidden = !parts.length;
  }

  // ---- method section ----------------------------------------------------------------------
  {
    const fu = meta.funnel || {};
    const steps = [
      [fu.raw_items, "news items collected"],
      [fu.passed_relevance, "passed the relevance rules"],
      [fu.events_after_dedupe, "distinct events after merging repeat coverage"],
      [fu.final_records, "records after review"],
    ];
    steps.filter((s) => s[0] !== undefined).forEach(([n, label]) =>
      $("funnel").append(el("li", {}, el("b", { text: Number(n).toLocaleString("en-IN") }), el("span", { text: label }))));
    const names = { google_news_rss: "Google News RSS", gdelt: "GDELT", bing_news_rss: "Bing News RSS",
      gnews_io: "GNews.io", newsapi_org: "NewsAPI.org", newsdata_io: "NewsData.io" };
    const src = Object.keys(meta.hits_per_source || {}).map((k) => names[k] || k);
    if (src.length) $("sources-line").textContent = "Sources: " + src.join(", ") + ". Article pages are read locally to get the publisher link and summary.";
  }

  function render() { renderActive(); renderGrid(); renderBars(); renderSectors(); renderList(); }
  render();
})();
