from causalpilot.decide import EXTEND, HOLD, SHIP, decide

BASE = dict(metric="conversion", min_effect=0.01, srm_p=0.5, sample_factor=2.0)


def call(**kw):
    return decide(**{**BASE, **kw}).call


def test_srm_blocks_everything():
    v = decide(**{**BASE, "srm_p": 1e-6}, effect=0.05, ci_low=0.04, ci_high=0.06)
    assert v.call == HOLD
    assert "not the size the design says" in v.headline


def test_guardrail_harm_blocks_a_win():
    assert call(effect=0.05, ci_low=0.04, ci_high=0.06, harmed_guardrails=("refunds",)) == HOLD


def test_clear_win_ships():
    assert call(effect=0.05, ci_low=0.02, ci_high=0.08) == SHIP


def test_positive_but_size_uncertain_ships():
    v = decide(**BASE, effect=0.012, ci_low=0.002, ci_high=0.022)
    assert v.call == SHIP
    assert "uncertain" in v.headline


def test_real_but_too_small_holds():
    assert call(effect=0.004, ci_low=0.002, ci_high=0.006) == HOLD


def test_harm_holds():
    assert call(effect=-0.03, ci_low=-0.05, ci_high=-0.01) == HOLD


def test_tight_null_holds():
    v = decide(**BASE, effect=0.001, ci_low=-0.004, ci_high=0.006)
    assert v.call == HOLD
    assert "no meaningful effect" in v.headline.lower()


def test_wide_null_extends_when_reachable():
    v = decide(**BASE, effect=0.005, ci_low=-0.01, ci_high=0.02)
    assert v.call == EXTEND
    assert "2.0x" in v.reasons[1]


def test_wide_null_holds_when_out_of_reach():
    assert call(effect=0.005, ci_low=-0.01, ci_high=0.02, sample_factor=30.0) == HOLD
