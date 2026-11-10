/* Trend charts. Reads data/records.json, the same file as the main dashboard.
   Every chart is drawn as plain SVG: thin lines, ringed dots, labels on the lead series. */
(async function () {
  const NS = "http://www.w3.org/2000/svg";
  const svgEl = (tag, attrs = {}, text) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) k === "text" ? (n.textContent = v) : n.setAttribute(k, v);
    kids.forEach((k) => k && n.append(k));
    return n;
  };
  const tip = document.getElementById("tip");
  const hover = (node, html) => {
    node.addEventListener("mousemove", (e) => {
      tip.innerHTML = html; tip.hidden = false;
      tip.style.left = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8) + "px";
      tip.style.top = Math.max(8, e.clientY - tip.offsetHeight - 12) + "px";
    });
    node.addEventListener("mouseleave", () => (tip.hidden = true));
  };

  let data;
  try { data = await (await fetch("data/records.json", { cache: "no-cache" })).json(); }
  catch (e) { document.getElementById("lede").textContent = "The data file could not be loaded."; return; }
  const { meta, records } = data;

  // Colours in a fixed order; a series keeps its colour in every chart.
  const C = ["#5f9a85", "#d9785a", "#5b7fb5", "#c9a13b", "#8a6fb0", "#6b6a65", "#b9cfc7", "#c9645f"];
  const MUTED = "#d3d1c7";

  // ---- time buckets -------------------------------------------------------
  const y0 = +meta.window_start.slice(0, 4), y1 = +meta.window_end.slice(0, 4);
  const years = []; for (let y = y0; y <= y1; y++) years.push(String(y));
  const halves = years.flatMap((y) => [y + " H1", y + " H2"]);
  const yearOf = (r) => r.date.slice(0, 4);
  const halfOf = (r) => r.date.slice(0, 4) + (+r.date.slice(5, 7) <= 6 ? " H1" : " H2");
  const endLabel = new Date(meta.window_end).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  const partialNote = `${y1} runs to ${endLabel} only, so its last point is incomplete.`;
  const reviewedFrom = meta.reviewed_from ? meta.reviewed_from.slice(0, 4) : null;

  const countBy = (rows, keyFn, bucketFn, buckets) => {
    const out = {};
    rows.forEach((r) => { const k = keyFn(r), b = buckets.indexOf(bucketFn(r)); if (b < 0) return; (out[k] ??= buckets.map(() => 0))[b]++; });
    return out;
  };
  const sum = (a) => a.reduce((x, y) => x + y, 0);

  // ---- generic line chart -------------------------------------------------
  function lineChart({ title, sub, x, series, yLabel, caption, labelSeries = 0, pct = false, markFrom }) {
    const W = 1000, H = 560, m = { l: 78, r: 34, t: 26, b: 70 };
    const max = Math.max(1, ...series.flatMap((s) => s.values));
    const step = pct ? 20 : [1, 2, 5, 10, 20, 25, 50, 100, 200].find((s) => max / s <= 6) || 500;
    const top = pct ? 100 : Math.ceil(max / step) * step;
    const X = (i) => m.l + 30 + (i * (W - m.l - m.r - 60)) / Math.max(1, x.length - 1);
    const Y = (v) => H - m.b - (v / top) * (H - m.t - m.b);
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": title });
    for (let v = 0; v <= top; v += step) {
      if (v) svg.append(svgEl("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: "var(--grid)", "stroke-width": 1.2 }));
      svg.append(svgEl("text", { x: m.l - 14, y: Y(v) + 5, "text-anchor": "end" }, v + (pct ? "%" : "")));
    }
    svg.append(svgEl("line", { x1: m.l, x2: m.l, y1: m.t, y2: H - m.b, stroke: "var(--axis)", "stroke-width": 1.3 }));
    svg.append(svgEl("line", { x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b, stroke: "var(--axis)", "stroke-width": 1.3 }));
    const every = x.length > 7 ? 2 : 1;
    x.forEach((lab, i) => { if (i % every === 0) svg.append(svgEl("text", { x: X(i), y: H - m.b + 26, "text-anchor": "middle" }, lab)); });
    svg.append(svgEl("text", { x: 22, y: (H - m.b + m.t) / 2, "text-anchor": "middle", transform: `rotate(-90 22 ${(H - m.b + m.t) / 2})`, fill: "var(--ink)" }, yLabel));
    if (markFrom !== undefined && markFrom > 0) {
      const xm = (X(markFrom - 1) + X(markFrom)) / 2;
      svg.append(svgEl("line", { x1: xm, x2: xm, y1: m.t, y2: H - m.b, stroke: "#8b8a84", "stroke-dasharray": "6 5", "stroke-width": 1.2 }));
      svg.append(svgEl("text", { x: xm + 8, y: m.t + 12, "font-size": 12.5 }, "hand-reviewed from here"));
      svg.append(svgEl("text", { x: xm - 8, y: m.t + 12, "text-anchor": "end", "font-size": 12.5 }, "rule output only"));
    }
    // muted series first so the coloured ones sit on top
    [...series].sort((a, b) => (a.color === MUTED ? -1 : 1) - (b.color === MUTED ? -1 : 1)).forEach((s) => {
      const pts = s.values.map((v, i) => [X(i), Y(v)]);
      const last = pts.length - 1;
      svg.append(svgEl("polyline", { points: pts.slice(0, last).map((p) => p.join(",")).join(" "), fill: "none", stroke: s.color, "stroke-width": 2.6, "stroke-linejoin": "round" }));
      svg.append(svgEl("line", { x1: pts[last - 1][0], y1: pts[last - 1][1], x2: pts[last][0], y2: pts[last][1], stroke: s.color, "stroke-width": 2.6, "stroke-dasharray": "5 5" }));
      pts.forEach(([px, py], i) => {
        const c = svgEl("circle", { cx: px, cy: py, r: s.color === MUTED ? 5 : 8, fill: s.color, stroke: "#141413", "stroke-width": s.color === MUTED ? 0.8 : 1.3 });
        hover(c, `<b>${s.name}</b><br>${x[i]}: ${s.values[i]}${pct ? "%" : ""}`);
        svg.append(c);
      });
    });
    const lead = series[labelSeries];
    lead.values.forEach((v, i) => svg.append(svgEl("text", { x: X(i), y: Y(v) - 16, "text-anchor": "middle", class: "pt-label" }, v + (pct ? "%" : ""))));
    const legend = el("div", { class: "legend" });
    series.forEach((s) => legend.append(el("span", {}, el("i", { style: `background:${s.color}` }), document.createTextNode(s.name))));
    return el("figure", {}, el("h2", { text: title }), el("p", { class: "sub", text: sub }), legend, svg, el("figcaption", { text: caption }));
  }

  // ---- header -------------------------------------------------------------
  const byYear = years.map((y) => records.filter((r) => yearOf(r) === y).length);
  document.getElementById("lede").textContent =
    `${records.length} recorded steps by ${meta.states.length} state governments. ${byYear[0]} in ${years[0]}, ${byYear[years.length - 2]} in ${years[years.length - 2]}, ` +
    `and ${byYear[years.length - 1]} so far in ${y1}.`;
  document.getElementById("caveat").textContent =
    "Read these as reported activity, not a census. Counts come from English news headlines. Older years are thinner partly because less was happening and partly because news search indexes keep less of the past. " +
    (reviewedFrom ? `Records from ${reviewedFrom} onward were hand-checked; earlier years are the pipeline's rule output, which in the checked period was right about four times in five. ` : "") + partialNote;

  const charts = document.getElementById("charts");
  const markYear = reviewedFrom ? years.indexOf(reviewedFrom) : undefined;
  const markHalf = reviewedFrom ? halves.indexOf(reviewedFrom + " H1") : undefined;

  // 1. All states together, by half-year
  const total = halves.map((h) => records.filter((r) => halfOf(r) === h).length);
  charts.append(lineChart({
    title: "State AI policy activity by half-year", sub: "Recorded steps across all tracked states", x: halves, yLabel: "Records",
    series: [{ name: "All tracked states", color: C[0], values: total }], markFrom: markHalf,
    caption: "Each point is the number of distinct events first reported in that half-year. " + partialNote,
  }));

  // 2. Leading states by year
  const perState = countBy(records, (r) => r.state, yearOf, years);
  const ranked = meta.states.slice().sort((a, b) => sum(perState[b] || []) - sum(perState[a] || []));
  const lead = ranked.slice(0, 5);
  const rest = years.map((_, i) => Math.round(sum(ranked.slice(5).map((s) => (perState[s] || years.map(() => 0))[i])) / Math.max(1, ranked.length - 5)));
  charts.append(lineChart({
    title: "Leading states by year", sub: "Five most active states against the average of the rest", x: years, yLabel: "Records per year",
    series: [...lead.map((s, i) => ({ name: s, color: C[i], values: perState[s] || years.map(() => 0) })), { name: "Average of other states", color: MUTED, values: rest }],
    markFrom: markYear, caption: "Numbers are printed for the most active state. " + partialNote,
  }));

  // 3. Kind of step by year
  const CATS = ["Government deployment", "Skilling and education", "Institutions and bodies", "Infrastructure and investment",
    "Partnerships and MoUs", "Policy and strategy", "Funding and budget", "Regulation and ethics"];
  const perCat = countBy(records, (r) => r.category, yearOf, years);
  charts.append(lineChart({
    title: "Category of policy, by year", sub: "Records in each category", x: years, yLabel: "Records per year",
    series: CATS.map((c, i) => ({ name: c, color: C[i], values: perCat[c] || years.map(() => 0) })), markFrom: markYear,
    caption: "Government deployment is also the default category, so it holds some records that belong elsewhere. " + partialNote,
  }));

  // 4. Stage share by year
  const STAGES = ["announced", "signed", "approved", "launched"];
  const perStage = countBy(records.filter((r) => STAGES.includes(r.stage)), (r) => r.stage, yearOf, years);
  const stageTotals = years.map((_, i) => sum(STAGES.map((s) => (perStage[s] || [])[i] || 0)));
  charts.append(lineChart({
    title: "From announcement to launch", sub: "Share of each year's records at each stage", x: years, yLabel: "Share of records", pct: true,
    series: STAGES.map((s, i) => ({ name: s[0].toUpperCase() + s.slice(1), color: C[i], values: years.map((_, k) => stageTotals[k] ? Math.round(100 * ((perStage[s] || [])[k] || 0) / stageTotals[k]) : 0) })),
    markFrom: markYear, caption: "Stage is read from the headline verb. An announcement is a stated plan; a launch is something switched on. Years with few records swing widely.",
  }));

  // 5. Sector by year
  const perSector = countBy(records, (r) => r.sector, yearOf, years);
  const topSectors = Object.keys(perSector).filter((s) => s !== "Cross-sector").sort((a, b) => sum(perSector[b]) - sum(perSector[a])).slice(0, 6);
  charts.append(lineChart({
    title: "Which part of government, by year", sub: "Six sectors with the most records", x: years, yLabel: "Records per year",
    series: topSectors.map((s, i) => ({ name: s, color: C[i], values: perSector[s] })), markFrom: markYear, caption: partialNote,
  }));

  // 6. Small multiples: every state on the same scale
  const perStateHalf = countBy(records, (r) => r.state, halfOf, halves);
  const peak = Math.max(1, ...Object.values(perStateHalf).flat());
  const grid = el("div", { class: "multiples" });
  ranked.forEach((st) => {
    const v = perStateHalf[st] || halves.map(() => 0);
    const W = 240, H = 96, X = (i) => 6 + (i * (W - 12)) / (halves.length - 1), Y = (n) => H - 18 - (n / peak) * (H - 30);
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${st}: records per half-year` });
    svg.append(svgEl("line", { x1: 0, x2: W, y1: H - 18, y2: H - 18, stroke: "var(--axis)", "stroke-width": 1 }));
    svg.append(svgEl("polyline", { points: v.map((n, i) => `${X(i)},${Y(n)}`).join(" "), fill: "none", stroke: C[0], "stroke-width": 2 }));
    v.forEach((n, i) => { const c = svgEl("circle", { cx: X(i), cy: Y(n), r: 3.6, fill: C[0], stroke: "#141413", "stroke-width": 0.8 }); hover(c, `<b>${st}</b><br>${halves[i]}: ${n}`); svg.append(c); });
    svg.append(svgEl("text", { x: 6, y: H - 3, "font-size": 11 }, years[0]));
    svg.append(svgEl("text", { x: W - 6, y: H - 3, "font-size": 11, "text-anchor": "end" }, years[years.length - 1]));
    grid.append(el("div", {}, el("h3", {}, document.createTextNode(st), el("span", { text: sum(v) + " records" })), svg));
  });
  charts.append(el("figure", {}, el("h2", { text: "Every state on one scale" }), el("p", { class: "sub", text: "Records per half-year, same vertical scale for all" }), grid,
    el("figcaption", { text: "States are ordered by total records. A shared scale shows how far apart the most and least reported states are." })));

  // 7. Table of state metrics
  const first = (rows, test) => { const r = rows.filter(test).sort((a, b) => a.date.localeCompare(b.date))[0]; return r ? r.date.slice(0, 7) : "none found"; };
  const table = el("table");
  table.append(el("tr", {}, ...["State", ...years, "Total", "Launched share", "Reported by 2+ outlets", "First policy step", "First deployment"].map((h) => el("th", { text: h }))));
  ranked.forEach((st) => {
    const rows = records.filter((r) => r.state === st), v = perState[st] || years.map(() => 0);
    const pctOf = (test) => rows.length ? Math.round(100 * rows.filter(test).length / rows.length) + "%" : "";
    table.append(el("tr", {}, el("td", { text: st }), ...v.map((n) => el("td", { text: n })), el("td", { text: rows.length }),
      el("td", { text: pctOf((r) => r.stage === "launched") }), el("td", { text: pctOf((r) => +r.n_outlets > 1) }),
      el("td", { text: first(rows, (r) => r.category === "Policy and strategy") }), el("td", { text: first(rows, (r) => r.category === "Government deployment") })));
  });
  charts.append(el("figure", {}, el("h2", { text: "State by state" }), el("p", { class: "sub", text: "Records per year and four simple measures" }),
    el("div", { class: "scroll" }, table),
    el("figcaption", { text: "First policy step and first deployment are the earliest records of that category inside the window, not the true first in the state's history. " + partialNote })));
})();
