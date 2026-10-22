// The browser code must give the same answers as the Python package.
// Run: node --test web/test   (expected.json comes from web/test/make_expected.py)
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { analyze, chi2Sf, formatG, parseCsv, zCritical } from "../causalpilot.js";

const here = new URL(".", import.meta.url);
const load = (url) => parseCsv(readFileSync(url, "utf-8"));
const example = load(new URL("../synthetic_example.csv", here));
const cases = JSON.parse(readFileSync(new URL("cases.json", here), "utf-8"));
const expected = JSON.parse(readFileSync(new URL("expected.json", here), "utf-8"));

function camel(settings) {
  const map = { min_lift: "minLift", planned_n: "plannedN" };
  return Object.fromEntries(Object.entries(settings).map(([k, v]) => [map[k] || k, v]));
}

function close(actual, wanted, path) {
  if (wanted === null || typeof wanted !== "number") {
    assert.equal(actual, wanted, path);
    return;
  }
  const tol = 1e-9 * Math.max(1, Math.abs(wanted));
  assert.ok(Math.abs(actual - wanted) <= tol, `${path}: js ${actual} vs python ${wanted}`);
}

function compareNumbers(actual, wanted, path) {
  for (const [key, value] of Object.entries(wanted)) {
    if (value !== null && typeof value === "object") compareNumbers(actual[key], value, `${path}.${key}`);
    else close(actual[key], value, `${path}.${key}`);
  }
}

for (const c of cases) {
  test(`same result as Python: ${c.name}`, () => {
    const csv = c.csv ? load(new URL(c.csv, here)) : example;
    const js = analyze(csv, camel(c.settings));
    const py = expected[c.name];
    assert.equal(js.rows, py.rows);
    compareNumbers(js.srm, py.srm, "srm");
    assert.equal(js.comparisons.length, py.comparisons.length);
    py.comparisons.forEach((pc, i) => {
      const jc = js.comparisons[i];
      assert.equal(jc.treatment, pc.treatment);
      assert.deepEqual(jc.verdict, pc.verdict);
      close(jc.min_effect, pc.min_effect, "min_effect");
      close(jc.sample_factor, pc.sample_factor, "sample_factor");
      pc.metrics.forEach((pm, j) => compareNumbers(jc.metrics[j], pm, `${pc.treatment}.${pm.metric}`));
    });
    assert.deepEqual(js.notes, py.notes);
  });
}

test("chi-square tail and normal quantile", () => {
  close(chi2Sf(3.841458820694124, 1), 0.05, "chi2 df1");
  close(chi2Sf(5.991464547107979, 2), 0.05, "chi2 df2");
  close(chi2Sf(7.814727903251178, 3), 0.05, "chi2 df3");
  close(zCritical(0.05), 1.959963984540054, "z 0.975");
});

test("number formatting follows Python's format spec", () => {
  assert.equal(formatG(0.03264, 4, true), "+0.03264");
  assert.equal(formatG(1.0, 4, true), "+1");
  assert.equal(formatG(-0.1944, 4, true), "-0.1944");
  assert.equal(formatG(9.99996, 4, true), "+10");
  assert.equal(formatG(1.2e-5, 2), "1.2e-05");
  assert.equal(formatG(0.00023, 2), "0.00023");
  assert.equal(formatG(123456, 4, true), "+1.235e+05");
});
