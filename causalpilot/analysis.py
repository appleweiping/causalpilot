"""Load an experiment export and run every check on it."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import stats
from .decide import decide

_TRUE = {"true", "yes", "y", "t", "1"}
_FALSE = {"false", "no", "n", "f", "0"}


@dataclass
class Settings:
    group: str
    control: str
    metrics: list[str]
    treatments: list[str] | None = None
    covariates: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    split: str | None = None
    alpha: float = 0.05
    min_lift: float = 0.01
    peeking: bool = False
    planned_n: int | None = None
    srm_alpha: float = 0.001
    max_extend: float = 4.0


def parse_split(text: str | None, groups: list[str]) -> dict[str, float] | None:
    """Parse "control=50,treatment=50" or "50:50".

    Positional parts follow `groups`: the control first, then the other groups in
    the order they first appear in the file.
    """
    if not text:
        return None
    if "=" in text:
        out = {}
        for part in text.split(","):
            name, _, value = part.partition("=")
            out[name.strip()] = float(value)
        return out
    values = [float(v) for v in text.replace("/", ":").split(":")]
    if len(values) != len(groups):
        raise ValueError(f"--split has {len(values)} parts but there are {len(groups)} groups: {groups}")
    return dict(zip(groups, values))


def _to_number(series: pd.Series, name: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(float)
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    lowered = series.astype(str).str.strip().str.lower()
    if lowered.dropna().isin(_TRUE | _FALSE | {"nan", ""}).all():
        return lowered.map(lambda v: 1.0 if v in _TRUE else (0.0 if v in _FALSE else np.nan))
    converted = pd.to_numeric(series, errors="coerce")
    bad = int(converted.isna().sum() - series.isna().sum())
    if bad:
        raise ValueError(f"column '{name}' has {bad} values that are not numbers")
    return converted.astype(float)


def _covariate_matrix(frame: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, list[str], int]:
    """Numeric covariates as-is, text covariates one-hot encoded (first level dropped).

    Missing values are filled with the column mean; the count is returned so the
    report can mention it.
    """
    parts, names, filled = [], [], 0
    for column in columns:
        series = frame[column]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            values = series.astype(float)
            filled += int(values.isna().sum())
            parts.append(values.fillna(values.mean()).to_numpy()[:, None])
            names.append(column)
        else:
            levels = sorted(series.dropna().astype(str).unique())
            for level in levels[1:]:
                parts.append((series.astype(str) == level).to_numpy(dtype=float)[:, None])
                names.append(f"{column}={level}")
    if not parts:
        return np.empty((len(frame), 0)), [], 0
    return np.hstack(parts), names, filled


def _is_binary(values: np.ndarray) -> bool:
    return bool(np.isin(values, (0.0, 1.0)).all())


def analyze_frame(frame: pd.DataFrame, settings: Settings) -> dict:
    """Analyze a data frame with one row per user (or per randomization unit)."""
    missing = [
        c
        for c in [settings.group, *settings.metrics, *settings.covariates, *settings.guardrails]
        if c not in frame.columns
    ]
    if missing:
        raise ValueError(f"missing column(s) {missing}; the file has {list(frame.columns)}")
    if not settings.metrics:
        raise ValueError("give at least one --metric")

    frame = frame.copy()
    groups_raw = frame[settings.group]
    dropped_no_group = int(groups_raw.isna().sum())
    frame = frame[groups_raw.notna()]
    frame[settings.group] = frame[settings.group].astype(str).str.strip()
    groups = list(dict.fromkeys(frame[settings.group]))
    if settings.control not in groups:
        raise ValueError(f"control group '{settings.control}' not found; groups are {groups}")
    treatments = settings.treatments or [g for g in groups if g != settings.control]
    unknown = [t for t in treatments if t not in groups]
    if unknown:
        raise ValueError(f"treatment group(s) {unknown} not found; groups are {groups}")
    if not treatments:
        raise ValueError("found only the control group in the file")

    # Sample ratio test across every group in the file, not just the ones compared.
    counts = frame[settings.group].value_counts()
    observed = {g: int(counts[g]) for g in groups}
    ordered = [settings.control] + [g for g in groups if g != settings.control]
    split = parse_split(settings.split, ordered) or {g: 1.0 for g in groups}
    if set(split) != set(groups):
        raise ValueError(f"--split must cover every group in the file: {groups}")
    srm = stats.sample_ratio_test(observed, split)

    numeric = {m: _to_number(frame[m], m) for m in dict.fromkeys(settings.metrics + settings.guardrails)}
    x_all, covariate_names, filled = _covariate_matrix(frame, settings.covariates)
    arm = frame[settings.group].to_numpy()
    control_mask = arm == settings.control

    notes: list[str] = []
    if filled:
        notes.append(f"{filled} missing covariate values were filled with the column mean.")
    if dropped_no_group:
        notes.append(f"{dropped_no_group} rows without a group were dropped.")

    comparisons = []
    for treatment in treatments:
        treat_mask = arm == treatment
        results = {}
        for metric, values in numeric.items():
            valid = values.notna().to_numpy()
            y = values.to_numpy()
            y_t, y_c = y[treat_mask & valid], y[control_mask & valid]
            n = int(y_t.size + y_c.size)
            binary = _is_binary(np.concatenate([y_t, y_c]))
            raw = stats.difference_in_means(y_t, y_c, settings.alpha)
            row = {
                "metric": metric,
                "binary": binary,
                "n_treatment": int(y_t.size),
                "n_control": int(y_c.size),
                "dropped_missing": int((~valid & (treat_mask | control_mask)).sum()),
                "mean_treatment": float(y_t.mean()),
                "mean_control": float(y_c.mean()),
                "raw": raw.as_dict(),
                "relative": stats.relative_lift(y_t, y_c, settings.alpha),
                "cuped": None,
            }
            chosen = raw
            if covariate_names:
                adjusted = stats.cuped(
                    y_t, y_c, x_all[treat_mask & valid], x_all[control_mask & valid], settings.alpha
                )
                row["cuped"] = {
                    **adjusted.estimate.as_dict(),
                    "theta": dict(zip(covariate_names, adjusted.theta)),
                    "variance_reduction": adjusted.variance_reduction,
                }
                chosen = adjusted.estimate
            low, high = stats.always_valid_interval(chosen, n, settings.alpha, settings.planned_n)
            row["always_valid"] = {"ci_low": low, "ci_high": high}
            row["used"] = "cuped" if covariate_names else "raw"
            if binary and min(y_t.sum(), y_c.sum(), (1 - y_t).sum(), (1 - y_c).sum()) < 10:
                notes.append(
                    f"{metric} ({treatment}): fewer than 10 events in an arm; the normal "
                    "approximation behind the intervals is shaky."
                )
            results[metric] = row

        primary = results[settings.metrics[0]]
        chosen = primary["cuped"] or primary["raw"]
        if settings.peeking:
            low, high = primary["always_valid"]["ci_low"], primary["always_valid"]["ci_high"]
            interval_name = f"always-valid {100 * (1 - settings.alpha):.0f}% interval"
        else:
            low, high = chosen["ci_low"], chosen["ci_high"]
            interval_name = f"{100 * (1 - settings.alpha):.0f}% interval"
        min_effect = abs(settings.min_lift * primary["mean_control"])
        factor = stats.sample_size_factor(chosen["se"], min_effect, settings.alpha)
        n_primary = primary["n_treatment"] + primary["n_control"]
        still_running = bool(settings.planned_n and n_primary < settings.planned_n)
        harmed = []
        for guardrail in settings.guardrails:
            g_row = results[guardrail]
            g_est = g_row["cuped"] or g_row["raw"]
            g_high = g_row["always_valid"]["ci_high"] if settings.peeking else g_est["ci_high"]
            if g_high < 0:
                harmed.append(guardrail)
        verdict = decide(
            metric=primary["metric"],
            effect=chosen["effect"],
            ci_low=low,
            ci_high=high,
            min_effect=min_effect,
            srm_p=srm.p_value,
            srm_alpha=settings.srm_alpha,
            sample_factor=factor,
            # Before the planned sample is reached an inconclusive result means "keep going".
            max_extend=float("inf") if still_running else settings.max_extend,
            harmed_guardrails=tuple(harmed),
            interval_name=interval_name,
            unit="%" if primary["binary"] else "",
        )
        comparisons.append(
            {
                "treatment": treatment,
                "metrics": list(results.values()),
                "min_effect": min_effect,
                "sample_factor": factor if np.isfinite(factor) else None,
                "verdict": verdict.as_dict(),
            }
        )

    if len(treatments) > 1:
        notes.append(
            f"{len(treatments)} treatments are compared with the same control. Each interval is "
            f"a separate {100 * (1 - settings.alpha):.0f}% interval; for a stricter family-wide "
            f"error rate use --alpha {settings.alpha / len(treatments):.3g}."
        )
    if not settings.peeking:
        notes.append(
            "These intervals assume the sample size was fixed in advance and the results were "
            "read once. If you checked repeatedly and would have stopped on a good day, rerun "
            "with --peeking, which uses intervals that stay valid under continuous monitoring."
        )
    if settings.covariates:
        notes.append(
            "CUPED is only unbiased if the covariates were measured before assignment "
            f"({', '.join(settings.covariates)})."
        )

    return {
        "settings": {
            "group": settings.group,
            "control": settings.control,
            "treatments": treatments,
            "metrics": settings.metrics,
            "primary_metric": settings.metrics[0],
            "covariates": settings.covariates,
            "covariate_columns": covariate_names,
            "guardrails": settings.guardrails,
            "alpha": settings.alpha,
            "min_lift": settings.min_lift,
            "peeking": settings.peeking,
            "planned_n": settings.planned_n,
            "split": split,
        },
        "rows": int(len(frame)),
        "srm": srm.as_dict(),
        "comparisons": comparisons,
        "notes": notes,
    }


def analyze_csv(path: str | Path, settings: Settings) -> dict:
    frame = pd.read_csv(path)
    result = analyze_frame(frame, settings)
    result["source"] = Path(path).name
    return result
