# A/B test report: Hillstrom MineThatData e-mail test (2008)

64,000 rows. Control: **No E-Mail**. Primary metric: **spend**. Smallest worthwhile lift: 5% of the control mean. Alpha: 0.05. Covariates for CUPED: recency, history, mens, womens, newbie, zip_code, channel.

## Verdict

**Womens E-Mail: SHIP.** spend improves by more than the minimum worthwhile change.

- Even the low end of the 95% interval +0.1693 to +0.6799 clears the smallest change you said is worth shipping (+0.03264).

**Mens E-Mail: SHIP.** spend improves by more than the minimum worthwhile change.

- Even the low end of the 95% interval +0.4823 to +1.051 clears the smallest change you said is worth shipping (+0.03264).

## Sample ratio check

| Group | Users | Expected |
| --- | ---: | ---: |
| Womens E-Mail | 21,387 | 21,333 |
| No E-Mail | 21,306 | 21,333 |
| Mens E-Mail | 21,307 | 21,333 |

Chi-square = 0.20 on 2 df, p = 0.904: no evidence of a mismatch.

![Effects with intervals](effects.png)

## Womens E-Mail vs No E-Mail

| Metric | Control | Treatment | Difference (95% CI) | p | CUPED difference (CI) | Variance cut | Always-valid CI | Relative lift |
| --- | ---: | ---: | --- | ---: | --- | ---: | --- | ---: |
| spend | 0.6528 | 1.077 | +0.4244 [+0.169, +0.6799] | 0.00113 | +0.4246 [+0.1693, +0.6799] | 0.1% | [+0.02917, +0.82] | +65.0% [+14.9%, +115.1%] |
| visit | 10.62% | 15.14% | +4.52 pp [+3.89 pp, +5.16 pp] | 1.93e-44 | +4.54 pp [+3.91 pp, +5.17 pp] | 2.6% | [+3.57 pp, +5.51 pp] | +42.6% [+35.4%, +49.8%] |
| conversion | 0.57% | 0.88% | +0.31 pp [+0.15 pp, +0.47 pp] | 0.000156 | +0.31 pp [+0.15 pp, +0.47 pp] | 0.2% | [+0.06 pp, +0.56 pp] | +54.3% [+19.3%, +89.3%] |

Users: 21,387 treatment, 21,306 control.

## Mens E-Mail vs No E-Mail

| Metric | Control | Treatment | Difference (95% CI) | p | CUPED difference (CI) | Variance cut | Always-valid CI | Relative lift |
| --- | ---: | ---: | --- | ---: | --- | ---: | --- | ---: |
| spend | 0.6528 | 1.423 | +0.7698 [+0.4851, +1.055] | 1.16e-07 | +0.7668 [+0.4823, +1.051] | 0.1% | [+0.3262, +1.207] | +117.9% [+54.4%, +181.4%] |
| visit | 10.62% | 18.28% | +7.66 pp [+7.00 pp, +8.32 pp] | 2.74e-113 | +7.60 pp [+6.95 pp, +8.26 pp] | 2.9% | [+6.59 pp, +8.62 pp] | +72.1% [+63.8%, +80.4%] |
| conversion | 0.57% | 1.25% | +0.68 pp [+0.50 pp, +0.86 pp] | 1.47e-13 | +0.68 pp [+0.50 pp, +0.86 pp] | 0.2% | [+0.40 pp, +0.96 pp] | +118.8% [+72.2%, +165.5%] |

Users: 21,307 treatment, 21,306 control.

## How to read this

- **Difference** is treatment minus control. For 0/1 metrics it is in percentage points (pp).
- **CUPED** subtracts the part of each user's metric that the pre-experiment covariates predict. The effect estimate stays unbiased and the interval gets narrower; the variance cut column says by how much.
- **Always-valid CI** is wider on purpose: it stays correct even if you looked at the results every day. Use it (pass `--peeking`) if you did.
- The verdict uses the CUPED interval of the primary metric when covariates are given.

## Notes

- 2 treatments are compared with the same control. Each interval is a separate 95% interval; for a stricter family-wide error rate use --alpha 0.025.
- These intervals assume the sample size was fixed in advance and the results were read once. If you checked repeatedly and would have stopped on a good day, rerun with --peeking, which uses intervals that stay valid under continuous monitoring.
- CUPED is only unbiased if the covariates were measured before assignment (recency, history, mens, womens, newbie, zip_code, channel).
