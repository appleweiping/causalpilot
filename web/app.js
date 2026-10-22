import { analyze, parseCsv } from "./causalpilot.js";

const $ = (id) => document.getElementById(id);
let data = null;
let sourceName = "";

const LABEL = { ship: "SHIP", hold: "HOLD", extend: "EXTEND" };

function esc(text) {
  return String(text).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
}

// The analysis text mentions command-line flags; say the same thing in terms of this page.
function forPage(text) {
  return text
    .replace(/rerun with --peeking/g, 'tick "I looked at the results more than once"')
    .replace(/use --alpha ([0-9.e-]+)/g, "set alpha to $1")
    .replace(/beyond the --max-extend limit/g, "more than 4x, so waiting is not realistic");
}

function guessGroup(header, columns) {
  for (const name of ["arm", "group", "variant", "variation", "bucket", "treatment", "experiment_group", "segment"]) {
    const hit = header.find((h) => h.toLowerCase() === name);
    if (hit) return hit;
  }
  return header.find((h) => {
    const distinct = new Set(columns[h]).size;
    return distinct >= 2 && distinct <= 6 && columns[h].some((v) => Number.isNaN(Number(v)));
  }) || header[0];
}

function isNumeric(values) {
  return values.slice(0, 2000).every((v) => v === "" || Number.isFinite(Number(v)) || /^(true|false|yes|no)$/i.test(v));
}

function fillSelect(select, options, chosen) {
  select.innerHTML = options.map((o) => `<option${o === chosen ? " selected" : ""}>${esc(o)}</option>`).join("");
}

function checkboxes(container, names, checked = []) {
  container.innerHTML = names.length
    ? names.map((n) => `<label><input type="checkbox" value="${esc(n)}"${checked.includes(n) ? " checked" : ""}>${esc(n)}</label>`).join("")
    : '<span class="hint">none available</span>';
}

function ticked(container) {
  return [...container.querySelectorAll("input:checked")].map((i) => i.value);
}

function refreshControls() {
  const group = $("group").value;
  const arms = [...new Set(data.columns[group].filter((v) => v !== ""))];
  const control = arms.find((a) => /^(control|ctrl|a|baseline|no e-mail|0|false)$/i.test(a)) || arms[0];
  fillSelect($("control"), arms, control);
  const others = data.header.filter((h) => h !== group);
  const numeric = others.filter((h) => isNumeric(data.columns[h]));
  const prior = numeric.find((h) => /^(converted|conversion|revenue|spend|clicked|purchase)/i.test(h)) || numeric[0];
  fillSelect($("metric"), numeric, prior);
  refreshLists();
}

function refreshLists() {
  const group = $("group").value;
  const metric = $("metric").value;
  const others = data.header.filter((h) => h !== group && h !== metric);
  const numeric = others.filter((h) => isNumeric(data.columns[h]));
  const keepMetrics = ticked($("metrics"));
  const keepCov = ticked($("covariates"));
  const idLike = (h) => /(^id$|_id$|^day$|^date$)/i.test(h);
  checkboxes($("metrics"), numeric.filter((h) => !idLike(h)), keepMetrics);
  const guessCov = others.filter((h) => /^(prior|pre_|history|past|baseline|segment|country|platform|channel|recency)/i.test(h));
  checkboxes($("covariates"), others.filter((h) => !idLike(h)), keepCov.length ? keepCov : guessCov);
}

function load(text, name) {
  try {
    data = parseCsv(text);
  } catch (e) {
    $("file-info").textContent = `Could not read the file: ${e.message}`;
    return;
  }
  sourceName = name;
  $("file-info").textContent = `${name}: ${data.rows.toLocaleString()} rows, columns ${data.header.join(", ")}`;
  fillSelect($("group"), data.header, guessGroup(data.header, data.columns));
  refreshControls();
  if (name === "synthetic_example.csv") {
    for (const box of $("metrics").querySelectorAll("input")) box.checked = box.value === "revenue";
    for (const box of $("covariates").querySelectorAll("input")) box.checked = ["prior_orders", "segment"].includes(box.value);
    $("min-lift").value = 5;
  }
  $("setup").hidden = false;
  $("results").hidden = true;
}

function fmtValue(x, binary) {
  return binary ? `${(x * 100).toFixed(2)}%` : x.toPrecision(4);
}
function fmtDiff(x, binary) {
  return binary ? `${x >= 0 ? "+" : ""}${(x * 100).toFixed(2)} pp` : `${x >= 0 ? "+" : ""}${x.toPrecision(4)}`;
}
function fmtCi(lo, hi, binary) {
  return `[${fmtDiff(lo, binary)}, ${fmtDiff(hi, binary)}]`;
}
function fmtP(p) {
  return p < 1e-4 ? p.toExponential(1) : p.toPrecision(2);
}

function chart(result) {
  const rows = [];
  for (const c of result.comparisons) {
    for (const m of c.metrics) {
      if (m.mean_control === 0) continue;
      const est = m.cuped || m.raw;
      const b = m.mean_control;
      rows.push({
        label: `${m.metric} · ${c.treatment}`,
        eff: est.effect / b, lo: est.ci_low / b, hi: est.ci_high / b,
        alo: m.always_valid.ci_low / b, ahi: m.always_valid.ci_high / b, call: c.verdict.call,
      });
    }
  }
  if (!rows.length) return "";
  const minLift = result.settings.minLift;
  const xs = rows.flatMap((r) => [r.alo, r.ahi]).concat([minLift, -minLift, 0]);
  let lo = Math.min(...xs), hi = Math.max(...xs);
  const pad = (hi - lo) * 0.06 || 0.01;
  lo -= pad; hi += pad;
  const W = 640, left = 170, right = 20, rowH = 30, top = 10, H = top + rows.length * rowH + 34;
  const x = (v) => left + ((v - lo) / (hi - lo)) * (W - left - right);
  const step = niceStep((hi - lo) * 100);
  let ticks = "";
  for (let t = Math.ceil((lo * 100) / step) * step; t <= hi * 100; t += step) {
    ticks += `<line class="grid-line" x1="${x(t / 100)}" x2="${x(t / 100)}" y1="${top}" y2="${H - 30}"/>` +
      `<text x="${x(t / 100)}" y="${H - 16}" text-anchor="middle">${+t.toFixed(6)}%</text>`;
  }
  const bars = rows.map((r, i) => {
    const y = top + i * rowH + rowH / 2;
    return `<text x="${left - 8}" y="${y + 4}" text-anchor="end">${esc(r.label)}</text>` +
      `<line x1="${x(r.alo)}" x2="${x(r.ahi)}" y1="${y}" y2="${y}" stroke="var(--grey)" stroke-width="7"/>` +
      `<line x1="${x(r.lo)}" x2="${x(r.hi)}" y1="${y}" y2="${y}" stroke="var(--${r.call})" stroke-width="2.5"/>` +
      `<circle cx="${x(r.eff)}" cy="${y}" r="4.5" fill="var(--${r.call})"/>`;
  }).join("");
  const bars0 = `<line class="axis" x1="${x(0)}" x2="${x(0)}" y1="${top}" y2="${H - 30}"/>` +
    [minLift, -minLift].map((v) => `<line class="axis" stroke-dasharray="2 3" x1="${x(v)}" x2="${x(v)}" y1="${top}" y2="${H - 30}"/>`).join("");
  return `<h3>Lift relative to the control mean</h3>
    <p class="hint">Coloured: ${result.settings.covariates.length ? "CUPED-adjusted" : "unadjusted"} interval (colour = verdict).
    Grey: always-valid interval. Dotted: smallest worthwhile lift.</p>
    <svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Effects with intervals">${ticks}${bars0}${bars}
    <text x="${(left + W - right) / 2}" y="${H - 2}" text-anchor="middle">lift (%)</text></svg>`;
}

function niceStep(range) {
  const raw = range / 6;
  const mag = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw);
}

function render(result, scroll = true) {
  const s = result.settings;
  const srm = result.srm;
  const srmOk = srm.p_value >= 0.001;
  let html = `<div class="card"><h2>Verdict</h2>`;
  for (const c of result.comparisons) {
    const v = c.verdict;
    html += `<div class="verdict ${v.call}"><span class="badge">${LABEL[v.call]}</span> · ${esc(c.treatment)} vs ${esc(s.control)}:
      ${esc(v.headline)}<ul>${v.reasons.map((r) => `<li>${esc(forPage(r))}</li>`).join("")}</ul></div>`;
  }
  html += `<h3>Sample ratio check</h3><p>${Object.entries(srm.observed).map(([g, n]) => `${esc(g)}: ${n.toLocaleString()} (expected ${Math.round(srm.expected[g]).toLocaleString()})`).join(" · ")}<br>
    Chi-square ${srm.chi_square.toFixed(2)} on ${srm.df} df, p = ${fmtP(srm.p_value)}:
    ${srmOk ? "no evidence of a mismatch." : "<b>mismatch: fix assignment or logging before reading the results.</b>"}</p>`;
  html += chart(result);
  for (const c of result.comparisons) {
    const hasCuped = c.metrics.some((m) => m.cuped);
    html += `<h3>${esc(c.treatment)} vs ${esc(s.control)}</h3><div class="table-wrap"><table><thead><tr>
      <th>Metric</th><th>Control</th><th>Treatment</th><th>Difference [${(100 * (1 - s.alpha)).toFixed(0)}% CI]</th><th>p</th>
      ${hasCuped ? "<th>CUPED difference</th><th>Variance cut</th>" : ""}<th>Always-valid CI</th><th>Relative lift</th></tr></thead><tbody>`;
    for (const m of c.metrics) {
      const b = m.binary;
      html += `<tr><td>${esc(m.metric)}</td><td>${fmtValue(m.mean_control, b)}</td><td>${fmtValue(m.mean_treatment, b)}</td>
        <td>${fmtDiff(m.raw.effect, b)} ${fmtCi(m.raw.ci_low, m.raw.ci_high, b)}</td><td>${fmtP(m.raw.p_value)}</td>
        ${hasCuped ? `<td>${fmtDiff(m.cuped.effect, b)} ${fmtCi(m.cuped.ci_low, m.cuped.ci_high, b)}</td><td>${(m.cuped.variance_reduction * 100).toFixed(1)}%</td>` : ""}
        <td>${fmtCi(m.always_valid.ci_low, m.always_valid.ci_high, b)}</td>
        <td>${m.relative ? `${(m.relative.lift * 100).toFixed(1)}%` : "n/a"}</td></tr>`;
    }
    html += `</tbody></table></div><p class="hint">${c.metrics[0].n_treatment.toLocaleString()} treatment users, ${c.metrics[0].n_control.toLocaleString()} control users.</p>`;
  }
  if (result.notes.length) html += `<h3>Notes</h3><ul>${result.notes.map((n) => `<li>${esc(forPage(n))}</li>`).join("")}</ul>`;
  html += `</div>`;
  $("results").innerHTML = html;
  $("results").hidden = false;
  if (scroll) $("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function run(scroll = true) {
  $("error").textContent = "";
  const metric = $("metric").value;
  const settings = {
    group: $("group").value,
    control: $("control").value,
    metrics: [metric, ...ticked($("metrics")).filter((m) => m !== metric)],
    covariates: ticked($("covariates")).filter((c) => c !== metric),
    minLift: Number($("min-lift").value) / 100,
    alpha: Number($("alpha").value),
    peeking: $("peeking").checked,
    plannedN: Number($("planned").value) || null,
  };
  try {
    const result = analyze(data, settings);
    result.source = sourceName;
    render(result, scroll);
  } catch (e) {
    $("error").textContent = e.message;
  }
}

$("file").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (f) f.text().then((t) => load(t, f.name));
});
const drop = $("drop");
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  drop.classList.remove("over");
  const f = e.dataTransfer.files[0];
  if (f) f.text().then((t) => load(t, f.name));
});
function loadExample() {
  return fetch("synthetic_example.csv").then((r) => r.text()).then((t) => load(t, "synthetic_example.csv"));
}
$("example").addEventListener("click", loadExample);
$("group").addEventListener("change", refreshControls);
$("metric").addEventListener("change", refreshLists);
$("run").addEventListener("click", () => run());

// index.html#example opens the page with the example already analyzed.
if (location.hash === "#example") loadExample().then(() => run(false));
