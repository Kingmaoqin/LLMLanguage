#!/usr/bin/env python3
"""R8 Full-Episode: mixed-effects SENSITIVITY models (spec 12.2 / 12.3).

SENSITIVITY ONLY. The pre-registered primary inference is the paired task-cluster
bootstrap + clustered permutation test in analyze_full_episode.py. These models
must never replace it; they only check that the primary conclusion is not an
artifact of the paired/nonparametric approach.

  P1 (reward, binary)  : mixed-effects logistic
                         reward ~ condition + model + domain + task_type + (1|task)
  P2 (tool calls, count): count model (negative-binomial-style via Poisson/NB GLM
                         with task random intercept approximated by a mixed LM on
                         the log scale; NB mixed models are not available in
                         statsmodels, so the fallback is documented honestly).

Output: results/r8_full_episode/analysis/mixed_effects_sensitivity.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import warnings

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
warnings.filterwarnings("ignore")


def load(metrics: pathlib.Path) -> pd.DataFrame:
    rows = [json.loads(l) for l in metrics.read_text().splitlines() if l.strip()]
    df = pd.DataFrame(rows)
    df["task"] = df["domain"].astype(str) + "::" + df["task_id"].astype(str)
    df["reward_bin"] = (df["official_reward"] == 1.0).astype(int)
    # C1 is the reference level (the matched neutral control)
    df["condition"] = pd.Categorical(df["condition"],
                                     categories=["C1", "C0", "C2", "C3", "C4"])
    for c in ("model", "domain", "task_type"):
        df[c] = df[c].astype("category")
    # drop rows with missing modelling fields UP FRONT so patsy cannot silently drop
    need = ["reward_bin", "total_agent_tool_calls", "condition", "model", "domain",
            "task_type", "task"]
    df = df.dropna(subset=need).reset_index(drop=True)
    df["task_code"] = df["task"].astype("category").cat.codes   # int groups for clustering
    return df


def fit_p1_logit(df: pd.DataFrame) -> dict:
    """Mixed-effects logistic for reward (spec 12.2). Uses statsmodels BinomialBayesMixedGLM
    (variational) since MixedLM does not support binomial; falls back to a cluster-robust
    GLM if it does not converge."""
    import statsmodels.formula.api as smf
    import statsmodels.api as sm
    formula = "reward_bin ~ condition + model + domain + task_type"
    out = {"model": "mixed-effects logistic (task random intercept)", "formula": formula}
    try:
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
        md = BinomialBayesMixedGLM.from_formula(formula, {"task": "0 + C(task_code)"}, df)
        res = md.fit_vb(verbose=False)
        params = dict(zip(res.model.exog_names, res.fe_mean))
        sds = dict(zip(res.model.exog_names, res.fe_sd))
        out["fixed_effects"] = {
            k: {"coef_logodds": float(params[k]), "sd": float(sds[k]),
                "z": float(params[k] / sds[k]) if sds[k] else None}
            for k in params if k.startswith("condition")}
        out["method"] = "BinomialBayesMixedGLM.fit_vb (variational)"
    except Exception as exc:  # noqa: BLE001 - documented fallback, not silent
        glm = smf.glm(formula, data=df, family=sm.families.Binomial()).fit(
            cov_type="cluster", cov_kwds={"groups": df["task_code"].to_numpy()})
        out["fixed_effects"] = {
            k: {"coef_logodds": float(glm.params[k]), "se": float(glm.bse[k]),
                "p": float(glm.pvalues[k])}
            for k in glm.params.index if k.startswith("condition")}
        out["method"] = "cluster-robust GLM fallback (task clusters)"
        out["fallback_reason"] = repr(exc)[:200]
    return out


def fit_p2_count(df: pd.DataFrame) -> dict:
    """Count model for tool calls (spec 12.3). statsmodels has no NB mixed model, so we
    report (a) NB GLM with task-cluster-robust SEs and (b) a Gaussian MixedLM on the raw
    count with a task random intercept. Both are SENSITIVITY only; the honest limitation
    is stated in the output."""
    import statsmodels.formula.api as smf
    import statsmodels.api as sm
    formula = "total_agent_tool_calls ~ condition + model + domain + task_type"
    out = {"model": "count sensitivity for tool calls", "formula": formula}
    # (a) Negative-binomial GLM, cluster-robust by task
    try:
        # dispersion MUST be estimated (statsmodels' GLM default alpha=1.0 is an
        # ASSERTED dispersion and yields optimistic p-values). Use the discrete NB
        # MLE, which estimates alpha, with task-cluster-robust SEs.
        import statsmodels.discrete.discrete_model as dm
        import patsy
        y, X = patsy.dmatrices(formula, df, return_type="dataframe")
        nb = dm.NegativeBinomial(y, X).fit(
            disp=0, cov_type="cluster", cov_kwds={"groups": df["task_code"].to_numpy()})
        out["nb_alpha_estimated"] = float(nb.params.get("alpha", float("nan")))
        out["negbin_glm_cluster_robust"] = {
            k: {"coef_log": float(nb.params[k]), "se": float(nb.bse[k]),
                "p": float(nb.pvalues[k]),
                "irr": float(np.exp(nb.params[k]))}          # incidence-rate ratio
            for k in nb.params.index if k.startswith("condition")}
    except Exception as exc:  # noqa: BLE001
        out["negbin_glm_cluster_robust"] = {"error": repr(exc)[:200]}
    # (b) MixedLM with task random intercept (Gaussian approximation)
    try:
        mlm = smf.mixedlm(formula, data=df, groups=df["task_code"].to_numpy()).fit()
        out["mixedlm_task_random_intercept"] = {
            k: {"coef_calls": float(mlm.params[k]), "se": float(mlm.bse[k]),
                "p": float(mlm.pvalues[k])}
            for k in mlm.params.index if k.startswith("condition")}
    except Exception as exc:  # noqa: BLE001
        out["mixedlm_task_random_intercept"] = {"error": repr(exc)[:200]}
    out["limitation"] = ("statsmodels provides no negative-binomial MIXED model; the NB fit "
                         "uses task-cluster-robust SEs and the mixed model uses a Gaussian "
                         "approximation. Both are SENSITIVITY ONLY and do not replace the "
                         "pre-registered paired bootstrap/permutation primary.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/metrics/episode_metrics.jsonl")
    ap.add_argument("--out", type=pathlib.Path,
                    default=ROOT / "results/r8_full_episode/analysis/mixed_effects_sensitivity.json")
    args = ap.parse_args()
    df = load(args.metrics)
    res = {
        "n_episodes": int(len(df)), "n_tasks": int(df["task"].nunique()),
        "reference_condition": "C1 (matched adaptive neutral)",
        "role": "SENSITIVITY ONLY — does NOT replace the paired cluster-bootstrap / "
                "clustered-permutation primary (spec 12.2/12.3).",
        "P1_reward": fit_p1_logit(df),
        "P2_tool_calls": fit_p2_count(df),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    print(json.dumps({"P1": res["P1_reward"].get("fixed_effects"),
                      "P2_negbin": res["P2_tool_calls"].get("negbin_glm_cluster_robust")},
                     indent=1, ensure_ascii=False, default=str))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
