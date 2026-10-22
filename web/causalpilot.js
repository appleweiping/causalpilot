// Browser port of the causalpilot Python package (stats.py, decide.py, analysis.py).
// Kept deliberately line-for-line close to the Python so that web/test/parity.test.mjs
// can check both give the same numbers on the same file.

// ---------- numerics ----------

function erfc(x) {
  // Series for small |x|, Lentz continued fraction for the tail; ~1e-15 relative accuracy.
  if (x < 0) return 2 - erfc(-x);
  if (x < 2.5) {
    let sum = x, term = x, n = 0;
    const x2 = x * x;
    do {
      n += 1;
      term *= -x2 / n;
      const add = term / (2 * n + 1);
      sum += add;
      if (Math.abs(add) < 1e-17 * Math.abs(sum)) break;
    } while (n < 200);
    return 1 - (2 / Math.sqrt(Math.PI)) * sum;
  }
  // erfc(x) = exp(-x^2)/sqrt(pi) * 1/(x + 1/2/(x + 1/(x + 3/2/(x + ...))))
  const tiny = 1e-300;
  let f = x, c = x, d = 0;
  for (let i = 1; i < 300; i++) {
    const a = i / 2;
    d = x + a * d;
    d = Math.abs(d) < tiny ? tiny : d;
    c = x + a / c;
    c = Math.abs(c) < tiny ? tiny : c;
    d = 1 / d;
    const delta = c * d;
    f *= delta;
    if (Math.abs(delta - 1) < 1e-16) break;
  }
  return Math.exp(-x * x) / Math.sqrt(Math.PI) / f;
}

function normCdf(z) {
  return 0.5 * erfc(-z / Math.SQRT2);
}

function normPpf(p) {
  // Acklam's rational approximation, then two Newton steps on the exact CDF.
  const a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.38357751867269e2, -3.066479806614716e1, 2.506628277459239];
  const b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1];
  const c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996, 3.754408661907416];
  let x;
  if (p < 0.02425) {
    const q = Math.sqrt(-2 * Math.log(p));
    x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  } else if (p > 1 - 0.02425) {
    const q = Math.sqrt(-2 * Math.log(1 - p));
    x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  } else {
    const q = p - 0.5, r = q * q;
    x = ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  }
  for (let i = 0; i < 2; i++) {
    const err = normCdf(x) - p;
    x -= err * Math.sqrt(2 * Math.PI) * Math.exp((x * x) / 2);
  }
  return x;
}

export function zCritical(alpha) {
  return normPpf(1 - alpha / 2);
}

function twoSidedP(z) {
  return erfc(Math.abs(z) / Math.SQRT2);
}

export function chi2Sf(x, df) {
  if (x <= 0) return 1;
  const half = x / 2;
  if (df % 2 === 0) {
    let term = 1, total = 1;
    for (let k = 1; k < df / 2; k++) {
      term *= half / k;
      total += term;
    }
    return Math.min(1, Math.exp(-half) * total);
  }
  let q = erfc(Math.sqrt(half));
  let term = (Math.sqrt(half) * Math.exp(-half)) / (Math.sqrt(Math.PI) / 2);
  let nu = 1;
  while (nu < df) {
    q += term;
    nu += 2;
    term *= half / (nu / 2);
  }
  return Math.min(1, q);
}

function mean(v) {
  let s = 0;
  for (let i = 0; i < v.length; i++) s += v[i];
  return s / v.length;
}

function variance(v) {
  const m = mean(v);
  let s = 0;
  for (let i = 0; i < v.length; i++) s += (v[i] - m) ** 2;
  return s / (v.length - 1);
}

// ---------- stats ----------

export function sampleRatioTest(observed, expectedShare) {
  const groups = Object.keys(observed);
  const totalShare = groups.reduce((s, g) => s + expectedShare[g], 0);
  const n = groups.reduce((s, g) => s + observed[g], 0);
  const expected = {};
  let chi = 0;
  for (const g of groups) {
    expected[g] = (n * expectedShare[g]) / totalShare;
    chi += (observed[g] - expected[g]) ** 2 / expected[g];
  }
  const df = groups.length - 1;
  return { observed: { ...observed }, expected, chi_square: chi, df, p_value: chi2Sf(chi, df) };
}

function estimate(effect, se, alpha) {
  const z = zCritical(alpha);
  const p = se > 0 ? twoSidedP(effect / se) : effect === 0 ? 1 : 0;
  return { effect, se, ci_low: effect - z * se, ci_high: effect + z * se, p_value: p };
}

export function differenceInMeans(yT, yC, alpha = 0.05) {
  if (yT.length < 2 || yC.length < 2) throw new Error("each arm needs at least two rows");
  const effect = mean(yT) - mean(yC);
  const se = Math.sqrt(variance(yT) / yT.length + variance(yC) / yC.length);
  return estimate(effect, se, alpha);
}

function solve(A, b) {
  // Gaussian elimination with partial pivoting; a column with no pivot gets coefficient 0,
  // which gives the same fitted values as a least-squares solver on collinear inputs.
  const n = b.length;
  const M = A.map((row, i) => [...row, b[i]]);
  const pivotCol = new Array(n).fill(-1);
  let r = 0;
  for (let col = 0; col < n && r < n; col++) {
    let best = r;
    for (let i = r + 1; i < n; i++) if (Math.abs(M[i][col]) > Math.abs(M[best][col])) best = i;
    const scale = Math.max(1, ...M.map((row) => Math.abs(row[col])));
    if (Math.abs(M[best][col]) < 1e-12 * scale) continue;
    [M[r], M[best]] = [M[best], M[r]];
    for (let i = 0; i < n; i++) {
      if (i === r) continue;
      const f = M[i][col] / M[r][col];
      if (f === 0) continue;
      for (let j = col; j <= n; j++) M[i][j] -= f * M[r][j];
    }
    pivotCol[r] = col;
    r++;
  }
  const x = new Array(n).fill(0);
  for (let i = 0; i < r; i++) x[pivotCol[i]] = M[i][n] / M[i][pivotCol[i]];
  return x;
}

export function cuped(yT, yC, xT, xC, alpha = 0.05) {
  // xT, xC: arrays of rows (each row an array of covariates)
  const y = [...yT, ...yC];
  const x = [...xT, ...xC];
  const n = y.length;
  const k = x[0].length;
  const means = new Array(k).fill(0);
  for (const row of x) for (let j = 0; j < k; j++) means[j] += row[j] / n;
  const keep = [];
  for (let j = 0; j < k; j++) {
    let s = 0;
    for (const row of x) s += (row[j] - means[j]) ** 2;
    if (Math.sqrt(s / n) > 0) keep.push(j);
  }
  if (!keep.length) throw new Error("covariates are constant; CUPED has nothing to adjust with");
  const m = keep.length;
  const yBar = mean(y);
  const XtX = Array.from({ length: m }, () => new Array(m).fill(0));
  const Xty = new Array(m).fill(0);
  const xc = new Float64Array(m);
  for (let i = 0; i < n; i++) {
    for (let a = 0; a < m; a++) xc[a] = x[i][keep[a]] - means[keep[a]];
    const yc = y[i] - yBar;
    for (let a = 0; a < m; a++) {
      Xty[a] += xc[a] * yc;
      for (let b = a; b < m; b++) XtX[a][b] += xc[a] * xc[b];
    }
  }
  for (let a = 0; a < m; a++) for (let b = 0; b < a; b++) XtX[a][b] = XtX[b][a];
  const thetaKept = solve(XtX, Xty);
  const adjusted = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    let fit = 0;
    for (let a = 0; a < m; a++) fit += (x[i][keep[a]] - means[keep[a]]) * thetaKept[a];
    adjusted[i] = y[i] - fit;
  }
  const est = differenceInMeans(adjusted.subarray(0, yT.length), adjusted.subarray(yT.length), alpha);
  const varY = variance(y);
  const theta = new Array(k).fill(0);
  keep.forEach((j, a) => (theta[j] = thetaKept[a]));
  return { estimate: est, theta, variance_reduction: varY > 0 ? 1 - variance(adjusted) / varY : 0 };
}

export function alwaysValidInterval(est, n, alpha = 0.05, plannedN = null) {
  const logTerm = -2 * Math.log(alpha);
  const rho2 = (logTerm + Math.log(logTerm + 1)) / (plannedN || n);
  const sigma = est.se * Math.sqrt(n);
  const radius = sigma * Math.sqrt(((2 * (n * rho2 + 1)) / (n * n * rho2)) * Math.log(Math.sqrt(n * rho2 + 1) / alpha));
  return [est.effect - radius, est.effect + radius];
}

export function relativeLift(yT, yC, alpha = 0.05) {
  const mT = mean(yT), mC = mean(yC);
  if (mC === 0) return null;
  const vT = variance(yT) / yT.length, vC = variance(yC) / yC.length;
  const lift = mT / mC - 1;
  const se = Math.sqrt(vT / mC ** 2 + (mT ** 2 * vC) / mC ** 4);
  const z = zCritical(alpha);
  return { lift, ci_low: lift - z * se, ci_high: lift + z * se };
}

export function sampleSizeFactor(se, minEffect, alpha = 0.05, power = 0.8) {
  if (minEffect <= 0) return Infinity;
  const target = minEffect / (zCritical(alpha) + normPpf(power));
  return (se / target) ** 2;
}

// ---------- formatting (mimics Python's format spec for the verdict text) ----------

export function formatG(x, p, sign = false) {
  const s = sign && x >= 0 ? "+" : "";
  if (x === 0) return s + "0";
  if (!Number.isFinite(x)) return s + String(x);
  const [mant, expStr] = Math.abs(x).toExponential(p - 1).split("e");
  const exp = Number(expStr);
  const neg = x < 0 ? "-" : s;
  if (exp >= -4 && exp < p) {
    let fixed = Math.abs(x).toFixed(Math.max(p - 1 - exp, 0));
    if (fixed.includes(".")) fixed = fixed.replace(/0+$/, "").replace(/\.$/, "");
    return neg + fixed;
  }
  let m = mant.includes(".") ? mant.replace(/0+$/, "").replace(/\.$/, "") : mant;
  const e = Math.abs(exp) < 10 ? "0" + Math.abs(exp) : String(Math.abs(exp));
  return `${neg}${m}e${exp < 0 ? "-" : "+"}${e}`;
}

function fmt(value, unit) {
  if (unit === "%") return `${value * 100 >= 0 ? "+" : ""}${(value * 100).toFixed(2)} pp`;
  return formatG(value, 4, true);
}

// ---------- decide ----------

export function decide({
  metric, effect, ciLow, ciHigh, minEffect, srmP, srmAlpha = 0.001, sampleFactor = null,
  maxExtend = 4, harmedGuardrails = [], intervalName = "95% interval", unit = "",
}) {
  const span = `${intervalName} ${fmt(ciLow, unit)} to ${fmt(ciHigh, unit)}`;
  const bar = `the smallest change you said is worth shipping (${fmt(minEffect, unit)})`;
  const v = (call, headline, reasons = []) => ({ call, headline, reasons });

  if (srmP < srmAlpha) {
    return v("hold", "Do not trust this result yet: the groups are not the size the design says.", [
      `Sample ratio test p = ${formatG(srmP, 2)} (threshold ${srmAlpha}). Some users were lost, duplicated or assigned unevenly, and that usually biases the effect.`,
      "Check assignment and logging (bots, redirects, crashes in one arm, filters applied after assignment) before reading any metric.",
    ]);
  }
  if (harmedGuardrails.length) {
    // Each entry: { metric, ciLow, ciHigh, lowerIsBetter, unit } for a guardrail that clearly moved the wrong way.
    const names = harmedGuardrails.map((g) => g.metric).join(", ");
    const reasons = harmedGuardrails.map((g) => {
      const gSpan = `${intervalName} ${fmt(g.ciLow, g.unit)} to ${fmt(g.ciHigh, g.unit)}`;
      return g.lowerIsBetter
        ? `${g.metric} went up, and lower is better: the ${gSpan} lies entirely above zero.`
        : `${g.metric} went down, and higher is better: the ${gSpan} lies entirely below zero.`;
    });
    return v("hold", `The change clearly hurts a guardrail metric (${names}).`, reasons);
  }
  if (ciHigh < 0) return v("hold", `The treatment makes ${metric} worse.`, [`The whole ${span} is below zero.`]);
  if (ciLow > 0) {
    if (minEffect > 0 && ciHigh < minEffect) {
      return v("hold", `The effect on ${metric} is real but too small to matter.`, [
        `The ${span} excludes zero but stays under ${bar}.`,
        "Ship anyway only if the change costs nothing to keep.",
      ]);
    }
    if (ciLow >= minEffect) {
      return v("ship", `${metric} improves by more than the minimum worthwhile change.`, [`Even the low end of the ${span} clears ${bar}.`]);
    }
    return v("ship", `${metric} improves, though the size is uncertain.`, [
      `The ${span} excludes zero; the point estimate is ${fmt(effect, unit)}.`,
      `The low end is below ${bar}, so a repeat with more traffic would pin the size down.`,
    ]);
  }
  if (minEffect > 0 && ciLow > -minEffect && ciHigh < minEffect) {
    return v("hold", `No meaningful effect on ${metric}.`, [`The ${span} contains zero and rules out changes as large as ${bar}.`]);
  }
  if (sampleFactor !== null && sampleFactor <= maxExtend) {
    const more = Math.max(sampleFactor - 1, 0);
    return v("extend", `Not enough data yet to tell whether ${metric} moves.`, [
      `The ${span} contains zero but is too wide to rule out ${bar}.`,
      `Detecting that change with 80% power needs about ${sampleFactor.toFixed(1)}x the current sample (${more.toFixed(1)}x more users per arm).`,
      "Decide the new end date now and look once at the end, or rerun with --peeking if you will keep checking.",
    ]);
  }
  const reasons = [`The ${span} contains zero and is too wide to rule out ${bar}.`];
  if (sampleFactor !== null) {
    reasons.push(`Detecting that change with 80% power would need about ${sampleFactor.toFixed(0)}x the current sample, which is beyond the --max-extend limit.`);
  }
  return v("hold", `The test cannot detect a worthwhile effect on ${metric} at this traffic.`, reasons);
}

// ---------- CSV + analysis ----------

export function parseCsv(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else quoted = false;
      } else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field); field = "";
      if (row.length > 1 || row[0] !== "") rows.push(row);
      row = [];
    } else field += ch;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  const header = rows.shift().map((h) => h.trim());
  const columns = {};
  header.forEach((h, j) => (columns[h] = rows.map((r) => (r[j] ?? "").trim())));
  return { header, columns, rows: rows.length };
}

const TRUE = new Set(["true", "yes", "y", "t", "1"]);
const FALSE = new Set(["false", "no", "n", "f", "0"]);
// The strings pandas.read_csv treats as missing by default (case-sensitive, like pandas).
const MISSING = new Set(["", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan", "1.#IND", "1.#QNAN", "<NA>", "N/A", "NA", "NULL", "NaN", "None", "n/a", "nan", "null"]);
const isMissing = (s) => MISSING.has(s);

function isNumericColumn(values) {
  return values.every((s) => isMissing(s) || Number.isFinite(Number(s)));
}

function toNumber(values, name) {
  if (isNumericColumn(values)) return values.map((s) => (isMissing(s) ? NaN : Number(s)));
  const lowered = values.map((s) => s.toLowerCase());
  if (lowered.every((s) => isMissing(s) || TRUE.has(s) || FALSE.has(s))) {
    return lowered.map((s) => (TRUE.has(s) ? 1 : FALSE.has(s) ? 0 : NaN));
  }
  const bad = values.filter((s) => !isMissing(s) && !Number.isFinite(Number(s))).length;
  throw new Error(`column '${name}' has ${bad} values that are not numbers`);
}

function covariateMatrix(columns, names, rowIndex) {
  const parts = [], labels = [];
  let filled = 0;
  for (const name of names) {
    const values = rowIndex.map((i) => columns[name][i]);
    if (isNumericColumn(values)) {
      const nums = values.map((s) => (isMissing(s) ? NaN : Number(s)));
      const present = nums.filter((v) => !Number.isNaN(v));
      const m = present.reduce((a, b) => a + b, 0) / present.length;
      filled += nums.length - present.length;
      parts.push(nums.map((v) => (Number.isNaN(v) ? m : v)));
      labels.push(name);
    } else {
      const levels = [...new Set(values.filter((s) => !isMissing(s)))].sort();
      for (const level of levels.slice(1)) {
        parts.push(values.map((s) => (s === level ? 1 : 0)));
        labels.push(`${name}=${level}`);
      }
    }
  }
  const matrix = rowIndex.map((_, r) => parts.map((p) => p[r]));
  return { matrix, labels, filled };
}

export function parseSplit(text, groups) {
  if (!text) return null;
  if (text.includes("=")) {
    const out = {};
    for (const part of text.split(",")) {
      const [name, value] = part.split("=");
      out[name.trim()] = Number(value);
    }
    return out;
  }
  const values = text.replace(/\//g, ":").split(":").map(Number);
  if (values.length !== groups.length) throw new Error(`--split has ${values.length} parts but there are ${groups.length} groups`);
  return Object.fromEntries(groups.map((g, i) => [g, values[i]]));
}

// "refunded:lower" -> ["refunded", true]: lower is better, so a clear rise blocks a ship.
// No suffix (or ":higher") means higher is better, so a clear drop does.
export function parseGuardrail(spec) {
  const at = spec.lastIndexOf(":");
  const direction = at >= 0 ? spec.slice(at + 1).trim().toLowerCase() : "";
  if (direction === "lower" || direction === "higher") return [spec.slice(0, at).trim(), direction === "lower"];
  return [spec.trim(), false];
}

export function analyze(data, s) {
  const settings = {
    treatments: null, covariates: [], guardrails: [], split: null, alpha: 0.05, minLift: 0.01,
    peeking: false, plannedN: null, srmAlpha: 0.001, maxExtend: 4, ...s,
  };
  const guardrails = new Map(settings.guardrails.map(parseGuardrail));
  const { columns } = data;
  const needed = [settings.group, ...settings.metrics, ...settings.covariates, ...guardrails.keys()];
  const missingCols = needed.filter((c) => !(c in columns));
  if (missingCols.length) throw new Error(`missing column(s) ${missingCols.join(", ")}`);

  const rowIndex = [];
  let droppedNoGroup = 0;
  columns[settings.group].forEach((g, i) => (isMissing(g) ? droppedNoGroup++ : rowIndex.push(i)));
  const arm = rowIndex.map((i) => columns[settings.group][i]);
  const groups = [...new Set(arm)];
  if (!groups.includes(settings.control)) throw new Error(`control group '${settings.control}' not found; groups are ${groups.join(", ")}`);
  const treatments = settings.treatments || groups.filter((g) => g !== settings.control);
  if (!treatments.length) throw new Error("found only the control group in the file");

  const observed = {};
  for (const g of groups) observed[g] = 0;
  for (const a of arm) observed[a]++;
  const ordered = [settings.control, ...groups.filter((g) => g !== settings.control)];
  const split = parseSplit(settings.split, ordered) || Object.fromEntries(groups.map((g) => [g, 1]));
  const srm = sampleRatioTest(observed, split);

  const metricNames = [...new Set([...settings.metrics, ...guardrails.keys()])];
  const numeric = {};
  for (const m of metricNames) numeric[m] = toNumber(rowIndex.map((i) => columns[m][i]), m);
  const cov = covariateMatrix(columns, settings.covariates, rowIndex);

  const notes = [];
  if (cov.filled) notes.push(`${cov.filled} missing covariate values were filled with the column mean.`);
  if (droppedNoGroup) notes.push(`${droppedNoGroup} rows without a group were dropped.`);

  const comparisons = [];
  for (const treatment of treatments) {
    const results = {};
    for (const metric of metricNames) {
      const yT = [], yC = [], xT = [], xC = [];
      let dropped = 0;
      numeric[metric].forEach((v, r) => {
        const inT = arm[r] === treatment, inC = arm[r] === settings.control;
        if (!inT && !inC) return;
        if (Number.isNaN(v)) { dropped++; return; }
        (inT ? yT : yC).push(v);
        if (cov.labels.length) (inT ? xT : xC).push(cov.matrix[r]);
      });
      const n = yT.length + yC.length;
      const binary = [...yT, ...yC].every((v) => v === 0 || v === 1);
      const raw = differenceInMeans(yT, yC, settings.alpha);
      const row = {
        metric, binary, n_treatment: yT.length, n_control: yC.length, dropped_missing: dropped,
        mean_treatment: mean(yT), mean_control: mean(yC), raw,
        relative: relativeLift(yT, yC, settings.alpha), cuped: null,
      };
      let chosen = raw;
      if (cov.labels.length) {
        const adj = cuped(yT, yC, xT, xC, settings.alpha);
        row.cuped = { ...adj.estimate, theta: Object.fromEntries(cov.labels.map((l, j) => [l, adj.theta[j]])), variance_reduction: adj.variance_reduction };
        chosen = adj.estimate;
      }
      const [lo, hi] = alwaysValidInterval(chosen, n, settings.alpha, settings.plannedN);
      row.always_valid = { ci_low: lo, ci_high: hi };
      row.used = cov.labels.length ? "cuped" : "raw";
      if (binary) {
        const sT = yT.reduce((a, b) => a + b, 0), sC = yC.reduce((a, b) => a + b, 0);
        if (Math.min(sT, sC, yT.length - sT, yC.length - sC) < 10) {
          notes.push(`${metric} (${treatment}): fewer than 10 events in an arm; the normal approximation behind the intervals is shaky.`);
        }
      }
      results[metric] = row;
    }
    const primary = results[settings.metrics[0]];
    const chosen = primary.cuped || primary.raw;
    const level = `${(100 * (1 - settings.alpha)).toFixed(0)}%`;
    let lo = chosen.ci_low, hi = chosen.ci_high, intervalName = `${level} interval`;
    if (settings.peeking) {
      lo = primary.always_valid.ci_low; hi = primary.always_valid.ci_high;
      intervalName = `always-valid ${level} interval`;
    }
    const minEffect = Math.abs(settings.minLift * primary.mean_control);
    const factor = sampleSizeFactor(chosen.se, minEffect, settings.alpha);
    const nPrimary = primary.n_treatment + primary.n_control;
    const stillRunning = Boolean(settings.plannedN && nPrimary < settings.plannedN);
    const harmed = [];
    for (const [g, lowerIsBetter] of guardrails) {
      const r = results[g];
      const e = settings.peeking ? r.always_valid : r.cuped || r.raw;
      if (lowerIsBetter ? e.ci_low > 0 : e.ci_high < 0) {
        harmed.push({ metric: g, ciLow: e.ci_low, ciHigh: e.ci_high, lowerIsBetter, unit: r.binary ? "%" : "" });
      }
    }
    const verdict = decide({
      metric: primary.metric, effect: chosen.effect, ciLow: lo, ciHigh: hi, minEffect, srmP: srm.p_value,
      srmAlpha: settings.srmAlpha, sampleFactor: factor, maxExtend: stillRunning ? Infinity : settings.maxExtend,
      harmedGuardrails: harmed, intervalName, unit: primary.binary ? "%" : "",
    });
    comparisons.push({ treatment, metrics: Object.values(results), min_effect: minEffect, sample_factor: Number.isFinite(factor) ? factor : null, verdict });
  }
  const level = `${(100 * (1 - settings.alpha)).toFixed(0)}%`;
  if (treatments.length > 1) {
    notes.push(
      `${treatments.length} treatments are compared with the same control. Each interval is a separate ${level} interval; ` +
        `for a stricter family-wide error rate use --alpha ${formatG(settings.alpha / treatments.length, 3)}.`,
    );
  }
  if (guardrails.size) {
    const rules = [...guardrails].map(([name, lower]) =>
      lower ? `${name} must not go up (lower is better)` : `${name} must not go down (higher is better)`);
    notes.push(`Guardrails, where a clear move the wrong way blocks a ship: ${rules.join("; ")}.`);
  }
  if (!settings.peeking) {
    notes.push(
      "These intervals assume the sample size was fixed in advance and the results were read once. If you checked " +
        "repeatedly and would have stopped on a good day, rerun with --peeking, which uses intervals that stay valid " +
        "under continuous monitoring.",
    );
  }
  if (settings.covariates.length) {
    notes.push(`CUPED is only unbiased if the covariates were measured before assignment (${settings.covariates.join(", ")}).`);
  }
  return {
    settings: {
      ...settings, treatments, covariate_columns: cov.labels, split,
      guardrails: [...guardrails].map(([metric, lower]) => ({ metric, lower_is_better: lower })),
    },
    rows: rowIndex.length, srm, comparisons, notes,
  };
}
