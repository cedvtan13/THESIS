#!/usr/bin/env python3
"""
verify_literature_dataset.py -- Benchmark thesis yield and growth models against
the public WUR 3rd Autonomous Greenhouse Challenge Lettuce Dataset.

Literature & Dataset Sources:
  - Lin, Z., Fu, R., Ren, G., Zhong, R., Ying, Y., & Lin, T. (2022).
    "Automatic monitoring of lettuce fresh weight by multi-modal fusion based deep learning."
    Frontiers in Plant Science, 13, 980581. (DOI: 10.3389/fpls.2022.980581)
  - Dataset: Wageningen University & Research (2021), 3rd Autonomous Greenhouse Challenge:
    Online Challenge Lettuce Images (4TU.ResearchData DOI: 10.4121/15023088),
    mirrored with binary masks and GroundTruth_All_388_Images.csv at
    QianGong1990/Varietal-Classification-and-Morphological-Traits-Prediction-of-Lettuce-Cultivar-.
  - Secondary comparison: Kim et al. (2024), Frontiers in Plant Science, 15, 1365266.

No scipy dependency; pure numpy + pandas + PIL + matplotlib so it runs cleanly in all environments.
"""

from concurrent.futures import ThreadPoolExecutor
import io
import os
import ssl
import urllib.request

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

REPO_RAW_BASE = (
    "https://raw.githubusercontent.com/QianGong1990/"
    "Varietal-Classification-and-Morphological-Traits-Prediction-of-Lettuce-Cultivar-/main/dataset/"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
THESIS_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(THESIS_ROOT, "DATA", "literature_verification")
ARTIFACT_DIR = "/Users/moapilaw/.gemini/antigravity/brain/9bca437a-e7c5-493a-9dee-847723fb9bed"

DATASET_CSV = os.path.join(OUT_DIR, "wur_agc3_lettuce_gpr_dataset.csv")
YIELD_METRICS_CSV = os.path.join(OUT_DIR, "yield_verification_metrics.csv")
GROWTH_METRICS_CSV = os.path.join(OUT_DIR, "growth_verification_metrics.csv")
FIG_OUT_PATH = os.path.join(OUT_DIR, "literature_model_verification.png")
FIG_ARTIFACT_PATH = os.path.join(ARTIFACT_DIR, "literature_model_verification.png")

CULTIVARS = ["Aphylion", "Lugano", "Salanova", "Satine"]
CULTIVAR_COLORS = {
    "Aphylion": "#1F77B4",
    "Lugano": "#2CA02C",
    "Salanova": "#FF7F0E",
    "Satine": "#9467BD",
}


def assign_week(img_id: int) -> int:
    """Map chronological sampling Image_id blocks to greenhouse weeks 1..7."""
    if img_id <= 19:
        return 1
    if img_id <= 67:
        return 2
    if img_id <= 131:
        return 3
    if img_id <= 194:
        return 4
    if img_id <= 240:
        return 5
    if img_id <= 284:
        return 6
    return 7


def fetch_bytes(url: str, ctx: ssl.SSLContext) -> bytes:
    """Download URL payload with timeout and status check."""
    with urllib.request.urlopen(url, context=ctx, timeout=30) as resp:
        if getattr(resp, "status", 200) != 200:
            raise RuntimeError(f"HTTP {resp.status} fetching {url}")
        return resp.read()


def compute_mask_gpr(fname: str, ctx: ssl.SSLContext) -> tuple[int, float, float]:
    """Download binary canopy mask and compute foreground pixels and GPR (%)."""
    data = fetch_bytes(REPO_RAW_BASE + "binary_masks/" + fname, ctx)
    arr = np.asarray(Image.open(io.BytesIO(data)).convert("L")) > 127
    green_px = int(arr.sum())
    gpr_1080 = 100.0 * green_px / (1080 * 1080)
    gpr_full = 100.0 * green_px / (1920 * 1080)
    return green_px, gpr_1080, gpr_full


def load_or_fetch_dataset() -> pd.DataFrame:
    """Load cached 388-plant CSV or build it from remote ground truth and binary masks."""
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(DATASET_CSV):
        df = pd.read_csv(DATASET_CSV)
        if len(df) == 388 and "gpr_1080_pct" in df.columns:
            print(f"Loaded cached dataset ({len(df)} rows) from {DATASET_CSV}")
            return df

    print("Downloading GroundTruth_All_388_Images.csv, split CSV, and 388 binary canopy masks...")
    ctx = ssl._create_unverified_context()
    gt_text = fetch_bytes(REPO_RAW_BASE + "GroundTruth_All_388_Images.csv", ctx).decode("utf-8")
    sp_text = fetch_bytes(REPO_RAW_BASE + "split/dataset_split.csv", ctx).decode("utf-8")

    df = pd.read_csv(io.StringIO(gt_text))
    df_sp = pd.read_csv(io.StringIO(sp_text))
    df = df.merge(df_sp[["id", "split"]], left_on="Image_id", right_on="id", how="left")
    if "id" in df.columns:
        df = df.drop(columns=["id"])

    with ThreadPoolExecutor(max_workers=24) as pool:
        mask_stats = list(pool.map(lambda fn: compute_mask_gpr(fn, ctx), df["RGB_Image"]))

    df["green_px"] = [r[0] for r in mask_stats]
    df["gpr_1080_pct"] = [round(r[1], 6) for r in mask_stats]
    df["gpr_full_pct"] = [round(r[2], 6) for r in mask_stats]
    df["week"] = df["Image_id"].apply(assign_week)
    df["day"] = df["week"] * 7

    df.to_csv(DATASET_CSV, index=False)
    print(f"Saved {len(df)} rows to {DATASET_CSV}")
    return df


def build_design_matrix(sub: pd.DataFrame, model_key: str) -> np.ndarray:
    """Construct OLS design matrix matching thesis analyze_yield.py reduced terms."""
    G = sub["gpr_1080_pct"].to_numpy(dtype=float)
    D = sub["day"].to_numpy(dtype=float)
    ones = np.ones_like(G)
    if model_key == "Y1_Linear_GPR":
        return np.column_stack([ones, G])
    if model_key == "Y2_Quadratic_GPR":
        return np.column_stack([ones, G, G ** 2])
    if model_key == "Y3_Thesis_Poly_D_GPR":
        return np.column_stack([ones, D, G, G ** 2])
    raise ValueError(f"Unknown model_key: {model_key}")


def calc_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float]:
    """Return R^2, MAE, RMSE."""
    err = y_true - y_pred
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1.0 - float(np.sum(err ** 2)) / ss_tot if ss_tot > 0 else float("nan")
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    return r2, mae, rmse


def evaluate_yield_models(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Fit Y1, Y2, Y3 via OLS, score full-fit, exact LOOCV, and 70/15/15 test split."""
    model_specs = [
        ("Y1_Linear_GPR", "Y = b0 + b1*GPR"),
        ("Y2_Quadratic_GPR", "Y = b0 + b1*GPR + b2*GPR^2"),
        ("Y3_Thesis_Poly_D_GPR", "Y = b0 + b1*D + b2*GPR + b4*GPR^2"),
    ]
    cohorts = [(c, df[df["Variety"] == c].copy()) for c in CULTIVARS] + [("ALL", df.copy())]

    records = []
    loocv_preds_y3 = {}
    y2_fits = {}

    for cohort_name, sub in cohorts:
        y = sub["FreshWeightShoot_g"].to_numpy(dtype=float)
        is_train = sub["split"].isin(["train", "valid"]).to_numpy()
        is_test = (sub["split"] == "test").to_numpy()

        for model_key, formula in model_specs:
            X = build_design_matrix(sub, model_key)
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            yhat_fit = X @ beta
            r2_fit, mae_fit, rmse_fit = calc_metrics(y, yhat_fit)

            # Exact LOOCV predictions via individual hold-out refits
            yhat_loo = np.zeros_like(y)
            n = len(y)
            mask = np.ones(n, dtype=bool)
            for i in range(n):
                mask[i] = False
                b_i, *_ = np.linalg.lstsq(X[mask], y[mask], rcond=None)
                yhat_loo[i] = float(X[i] @ b_i)
                mask[i] = True
            r2_loo, mae_loo, rmse_loo = calc_metrics(y, yhat_loo)

            # Fixed 85/15 (train+valid vs test) split evaluation
            b_sp, *_ = np.linalg.lstsq(X[is_train], y[is_train], rcond=None)
            yhat_test = X[is_test] @ b_sp
            r2_test, mae_test, rmse_test = calc_metrics(y[is_test], yhat_test)

            records.append(
                {
                    "cohort": cohort_name,
                    "n_total": len(sub),
                    "n_test": int(is_test.sum()),
                    "model": model_key,
                    "formula": formula,
                    "fit_r2": round(r2_fit, 4),
                    "fit_mae_g": round(mae_fit, 2),
                    "fit_rmse_g": round(rmse_fit, 2),
                    "loocv_r2": round(r2_loo, 4),
                    "loocv_mae_g": round(mae_loo, 2),
                    "loocv_rmse_g": round(rmse_loo, 2),
                    "test_split_r2": round(r2_test, 4),
                    "test_split_mae_g": round(mae_test, 2),
                    "test_split_rmse_g": round(rmse_test, 2),
                }
            )

            if model_key == "Y3_Thesis_Poly_D_GPR" and cohort_name in CULTIVARS:
                loocv_preds_y3[cohort_name] = {
                    "y_true": y,
                    "y_loo": yhat_loo,
                    "loocv_r2": r2_loo,
                    "loocv_mae": mae_loo,
                }
            if model_key == "Y2_Quadratic_GPR" and cohort_name in CULTIVARS:
                y2_fits[cohort_name] = {
                    "gpr": sub["gpr_1080_pct"].to_numpy(dtype=float),
                    "y_true": y,
                    "beta": beta,
                }

    metrics_df = pd.DataFrame(records)
    metrics_df.to_csv(YIELD_METRICS_CSV, index=False)
    print("\n=== VERIFICATION 1: YIELD REGRESSION (LOOCV & TEST SPLIT) ===")
    print(metrics_df.to_string(index=False))
    return metrics_df, {"loocv_y3": loocv_preds_y3, "y2_fits": y2_fits}


def fit_logistic_numpy(t_tr: np.ndarray, y_tr: np.ndarray) -> tuple[float, float, float]:
    """Fit M1 Logistic curve K / (1 + exp(-r*(t - t0))) using coarse-to-fine grid search."""
    Ks = np.linspace(max(y_tr[-1], 5.0), 40.0, 120)
    rs = np.linspace(0.02, 0.30, 120)
    t0s = np.linspace(15.0, 55.0, 120)

    best_loss = float("inf")
    best_p = (20.0, 0.1, 30.0)
    R, T0 = np.meshgrid(rs, t0s, indexing="ij")
    for K in Ks:
        P = K / (1.0 + np.exp(-R[..., None] * (t_tr[None, None, :] - T0[..., None])))
        loss = np.sum((P - y_tr[None, None, :]) ** 2, axis=-1)
        idx = np.unravel_index(np.argmin(loss), loss.shape)
        if loss[idx] < best_loss:
            best_loss = float(loss[idx])
            best_p = (float(K), float(rs[idx[0]]), float(t0s[idx[1]]))

    # Local refinement around best parameters
    for step_scale in (0.15, 0.04):
        k0, r0, t00 = best_p
        Ks_f = np.linspace(max(y_tr[-1], k0 * (1 - step_scale)), k0 * (1 + step_scale), 45)
        rs_f = np.linspace(max(0.005, r0 * (1 - step_scale)), r0 * (1 + step_scale), 45)
        t0s_f = np.linspace(max(5.0, t00 * (1 - step_scale)), t00 * (1 + step_scale), 45)
        R_f, T0_f = np.meshgrid(rs_f, t0s_f, indexing="ij")
        for K in Ks_f:
            P = K / (1.0 + np.exp(-R_f[..., None] * (t_tr[None, None, :] - T0_f[..., None])))
            loss = np.sum((P - y_tr[None, None, :]) ** 2, axis=-1)
            idx = np.unravel_index(np.argmin(loss), loss.shape)
            if loss[idx] < best_loss:
                best_loss = float(loss[idx])
                best_p = (float(K), float(rs_f[idx[0]]), float(t0s_f[idx[1]]))
    return best_p


def fit_gompertz_numpy(t_tr: np.ndarray, y_tr: np.ndarray) -> tuple[float, float, float]:
    """Fit M2 Gompertz curve K * exp(-b * exp(-r*t)) using coarse-to-fine grid search."""
    Ks = np.linspace(max(y_tr[-1], 5.0), 45.0, 120)
    bs = np.linspace(1.0, 25.0, 120)
    rs = np.linspace(0.015, 0.20, 120)

    best_loss = float("inf")
    best_p = (20.0, 5.0, 0.06)
    B, R = np.meshgrid(bs, rs, indexing="ij")
    for K in Ks:
        P = K * np.exp(-B[..., None] * np.exp(-R[..., None] * t_tr[None, None, :]))
        loss = np.sum((P - y_tr[None, None, :]) ** 2, axis=-1)
        idx = np.unravel_index(np.argmin(loss), loss.shape)
        if loss[idx] < best_loss:
            best_loss = float(loss[idx])
            best_p = (float(K), float(bs[idx[0]]), float(rs[idx[1]]))

    for step_scale in (0.15, 0.04):
        k0, b0, r0 = best_p
        Ks_f = np.linspace(max(y_tr[-1], k0 * (1 - step_scale)), k0 * (1 + step_scale), 45)
        bs_f = np.linspace(max(0.2, b0 * (1 - step_scale)), b0 * (1 + step_scale), 45)
        rs_f = np.linspace(max(0.005, r0 * (1 - step_scale)), r0 * (1 + step_scale), 45)
        B_f, R_f = np.meshgrid(bs_f, rs_f, indexing="ij")
        for K in Ks_f:
            P = K * np.exp(-B_f[..., None] * np.exp(-R_f[..., None] * t_tr[None, None, :]))
            loss = np.sum((P - y_tr[None, None, :]) ** 2, axis=-1)
            idx = np.unravel_index(np.argmin(loss), loss.shape)
            if loss[idx] < best_loss:
                best_loss = float(loss[idx])
                best_p = (float(K), float(bs_f[idx[0]]), float(rs_f[idx[1]]))
    return best_p


def evaluate_growth_models(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Fit M1/M2/M3 on Days 7..35 and evaluate forecast skill vs Persistence B1 on Days 42..49."""
    weekly = df.groupby(["day", "Variety"])["gpr_1080_pct"].mean().unstack()
    t_all = weekly.index.to_numpy(dtype=float)
    t_tr, t_te = t_all[:5], t_all[5:]

    records = []
    curve_data = {}

    for var in CULTIVARS:
        y_all = weekly[var].to_numpy(dtype=float)
        y_tr, y_te = y_all[:5], y_all[5:]

        # B1: Persistence (last training observation)
        pred_b1 = np.full_like(y_te, y_tr[-1])
        mae_b1 = float(np.mean(np.abs(y_te - pred_b1)))
        rmse_b1 = float(np.sqrt(np.mean((y_te - pred_b1) ** 2)))

        # M1: Logistic
        k1, r1, t01 = fit_logistic_numpy(t_tr, y_tr)
        pred_m1 = k1 / (1.0 + np.exp(-r1 * (t_te - t01)))
        mae_m1 = float(np.mean(np.abs(y_te - pred_m1)))
        rmse_m1 = float(np.sqrt(np.mean((y_te - pred_m1) ** 2)))
        skill_m1 = 1.0 - mae_m1 / mae_b1

        # M2: Gompertz
        k2, b2, r2 = fit_gompertz_numpy(t_tr, y_tr)
        pred_m2 = k2 * np.exp(-b2 * np.exp(-r2 * t_te))
        mae_m2 = float(np.mean(np.abs(y_te - pred_m2)))
        rmse_m2 = float(np.sqrt(np.mean((y_te - pred_m2) ** 2)))
        skill_m2 = 1.0 - mae_m2 / mae_b1

        # M3: Linear
        X_tr = np.column_stack([np.ones_like(t_tr), t_tr])
        X_te = np.column_stack([np.ones_like(t_te), t_te])
        beta_lin = np.linalg.lstsq(X_tr, y_tr, rcond=None)[0]
        pred_m3 = X_te @ beta_lin
        mae_m3 = float(np.mean(np.abs(y_te - pred_m3)))
        rmse_m3 = float(np.sqrt(np.mean((y_te - pred_m3) ** 2)))
        skill_m3 = 1.0 - mae_m3 / mae_b1

        model_rows = [
            ("B1_Persistence", mae_b1, rmse_b1, 0.0, f"last={y_tr[-1]:.2f}%"),
            ("M1_Logistic", mae_m1, rmse_m1, skill_m1, f"K={k1:.2f}%, r={r1:.3f}, t0={t01:.1f}d"),
            ("M2_Gompertz", mae_m2, rmse_m2, skill_m2, f"K={k2:.2f}%, b={b2:.2f}, r={r2:.3f}"),
            ("M3_Linear", mae_m3, rmse_m3, skill_m3, f"a={beta_lin[0]:.2f}, c={beta_lin[1]:.3f}"),
        ]
        for mname, mae, rmse, skill, params in model_rows:
            records.append(
                {
                    "cultivar": var,
                    "model": mname,
                    "mae_pp": round(mae, 3),
                    "rmse_pp": round(rmse, 3),
                    "skill_vs_b1": round(skill, 3),
                    "params": params,
                }
            )

        curve_data[var] = {
            "t_all": t_all,
            "y_all": y_all,
            "t_tr": t_tr,
            "y_tr": y_tr,
            "t_te": t_te,
            "y_te": y_te,
            "m1_params": (k1, r1, t01),
            "skill_m1": skill_m1,
        }

    growth_df = pd.DataFrame(records)
    growth_df.to_csv(GROWTH_METRICS_CSV, index=False)
    print("\n=== VERIFICATION 2: PRE-HARVEST CANOPY GROWTH MODEL (FIT D7..35, TEST D42..49) ===")
    print(growth_df.to_string(index=False))
    return growth_df, curve_data


def make_verification_plot(
    metrics_df: pd.DataFrame, yield_artifacts: dict, curve_data: dict
) -> None:
    """Create 4-panel verification plot comparing thesis equations with literature benchmarks."""
    fig, axes = plt.subplots(2, 2, figsize=(15.0, 11.6), dpi=300)
    plt.subplots_adjust(hspace=0.33, wspace=0.22)

    # --- Panel A: Fresh Weight vs GPR (%) + Quadratic Curves ---
    ax_a = axes[0, 0]
    y2_fits = yield_artifacts["y2_fits"]
    for var in CULTIVARS:
        color = CULTIVAR_COLORS[var]
        info = y2_fits[var]
        gpr, y_true, beta = info["gpr"], info["y_true"], info["beta"]
        ax_a.scatter(gpr, y_true, color=color, alpha=0.65, s=26, edgecolors="white", linewidths=0.4, label=var)
        xs = np.linspace(float(gpr.min()), float(gpr.max()), 100)
        ys = beta[0] + beta[1] * xs + beta[2] * (xs ** 2)
        ax_a.plot(xs, ys, color=color, linewidth=2.2)

    ax_a.set_title("A. Fresh Weight vs. Top-View GPR (WUR 3rd AGC, N = 388)", fontsize=12, fontweight="bold")
    ax_a.set_xlabel("Green Pixel Ratio, GPR (% of 1080x1080 crop)", fontsize=10.5, fontweight="bold")
    ax_a.set_ylabel("Measured Fresh Weight (g)", fontsize=10.5, fontweight="bold")
    ax_a.grid(True, linestyle=":", alpha=0.55)
    ax_a.legend(loc="upper left", frameon=True, fontsize=9.5)

    # --- Panel B: LOOCV Predicted vs Measured (Thesis Polynomial: D + GPR + GPR^2) ---
    ax_b = axes[0, 1]
    loocv_y3 = yield_artifacts["loocv_y3"]
    max_val = 480.0
    ax_b.plot([0, max_val], [0, max_val], "k--", linewidth=1.4, alpha=0.75, label="1:1 Ideal Line")
    for var in CULTIVARS:
        color = CULTIVAR_COLORS[var]
        d = loocv_y3[var]
        ax_b.scatter(
            d["y_true"],
            d["y_loo"],
            color=color,
            alpha=0.65,
            s=26,
            edgecolors="white",
            linewidths=0.4,
            label=f"{var} (LOOCV R²={d['loocv_r2']:.3f}, MAE={d['loocv_mae']:.1f}g)",
        )
    ax_b.set_title("B. LOOCV Predicted vs. Measured (D + GPR + GPR²)", fontsize=12, fontweight="bold")
    ax_b.set_xlabel("Measured Fresh Weight (g)", fontsize=10.5, fontweight="bold")
    ax_b.set_ylabel("LOOCV Predicted Fresh Weight (g)", fontsize=10.5, fontweight="bold")
    ax_b.set_xlim(-10, max_val)
    ax_b.set_ylim(-10, max_val)
    ax_b.grid(True, linestyle=":", alpha=0.55)
    ax_b.legend(loc="upper left", frameon=True, fontsize=8.8)

    # --- Panel C: Pre-Harvest Canopy Growth Forecast (M1 Logistic vs B1 Persistence) ---
    ax_c = axes[1, 0]
    t_dense = np.linspace(7.0, 49.0, 150)
    ax_c.axvspan(35.0, 50.0, color="#ECEFF1", alpha=0.7, label="Out-of-sample test (D42–D49)")
    ax_c.axvline(35.0, color="#546E7A", linestyle="--", linewidth=1.2)

    for var in CULTIVARS:
        color = CULTIVAR_COLORS[var]
        cd = curve_data[var]
        k1, r1, t01 = cd["m1_params"]
        y_curve = k1 / (1.0 + np.exp(-r1 * (t_dense - t01)))
        ax_c.plot(t_dense, y_curve, color=color, linewidth=2.0)
        ax_c.scatter(cd["t_tr"], cd["y_tr"], color=color, marker="o", s=38, zorder=4)
        ax_c.scatter(
            cd["t_te"],
            cd["y_te"],
            color=color,
            marker="s",
            s=46,
            edgecolors="black",
            linewidths=0.7,
            zorder=5,
            label=f"{var}: Logistic skill {cd['skill_m1']:+.3f}",
        )
        # B1 Persistence horizontal dashed line across test horizon
        ax_c.hlines(cd["y_tr"][-1], xmin=35.0, xmax=49.0, colors=color, linestyles=":", linewidth=1.5, alpha=0.85)

    ax_c.set_title("C. Pre-Harvest Canopy Growth Model (M1 Logistic vs. B1 Persistence)", fontsize=12, fontweight="bold")
    ax_c.set_xlabel("Growth Day (Weekly Sampling Blocks, D7 to D49)", fontsize=10.5, fontweight="bold")
    ax_c.set_ylabel("Mean Cultivar GPR (%)", fontsize=10.5, fontweight="bold")
    ax_c.set_xticks([7, 14, 21, 28, 35, 42, 49])
    ax_c.set_xticklabels(["D7", "D14", "D21", "D28", "D35", "D42", "D49"])
    ax_c.grid(True, linestyle=":", alpha=0.55)
    ax_c.legend(loc="upper left", frameon=True, fontsize=8.5)

    # --- Panel D: R^2 Benchmark vs Published Literature ---
    ax_d = axes[1, 1]
    y1_all = float(metrics_df[(metrics_df["cohort"] == "ALL") & (metrics_df["model"] == "Y1_Linear_GPR")]["loocv_r2"].iloc[0])
    y3_all = float(metrics_df[(metrics_df["cohort"] == "ALL") & (metrics_df["model"] == "Y3_Thesis_Poly_D_GPR")]["loocv_r2"].iloc[0])
    y1_cult = float(
        metrics_df[(metrics_df["cohort"].isin(CULTIVARS)) & (metrics_df["model"] == "Y1_Linear_GPR")]["loocv_r2"].mean()
    )
    y3_cult = float(
        metrics_df[(metrics_df["cohort"].isin(CULTIVARS)) & (metrics_df["model"] == "Y3_Thesis_Poly_D_GPR")]["loocv_r2"].mean()
    )

    labels = [
        "Kim et al. (2024)\nLinear Area",
        "Kim et al. (2024)\nCubic Area",
        "Thesis Linear\n(Pooled N=388)",
        "Thesis Poly\n(Pooled N=388)",
        "Thesis Linear\n(Mean/Cultivar)",
        "Thesis Poly\n(Mean/Cultivar)",
        "Lin et al. (2022)\nRGB-D Deep CNN",
    ]
    r2_vals = [0.770, 0.830, y1_all, y3_all, y1_cult, y3_cult, 0.938]
    bar_colors = ["#95A5A6", "#7F8C8D", "#5DADE2", "#2E86C1", "#58D68D", "#1E8449", "#AF7AC5"]

    bars = ax_d.bar(range(len(labels)), r2_vals, color=bar_colors, width=0.62, edgecolor="#2C3E50", linewidth=0.6)
    for bar, val in zip(bars, r2_vals):
        ax_d.text(
            bar.get_x() + bar.get_width() / 2.0,
            val + 0.012,
            f"{val:.3f}",
            ha="center",
            va="bottom",
            fontsize=9.0,
            fontweight="bold",
        )

    ax_d.set_title("D. Model Performance Comparison (R² Benchmark)", fontsize=12, fontweight="bold")
    ax_d.set_ylabel("Coefficient of Determination (R²)", fontsize=10.5, fontweight="bold")
    ax_d.set_ylim(0.65, 1.02)
    ax_d.set_xticks(range(len(labels)))
    ax_d.set_xticklabels(labels, fontsize=8.0, rotation=28, ha="right", rotation_mode="anchor")
    ax_d.grid(True, axis="y", linestyle=":", alpha=0.55)

    fig.suptitle(
        "External Literature Dataset Verification: Thesis Yield & Growth Models on WUR 3rd AGC Lettuce (Lin et al., 2022)",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    plt.savefig(FIG_OUT_PATH, dpi=300, bbox_inches="tight")
    if os.path.isdir(ARTIFACT_DIR):
        plt.savefig(FIG_ARTIFACT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved verification figure to:\n  {FIG_OUT_PATH}\n  {FIG_ARTIFACT_PATH}")


def main() -> None:
    df = load_or_fetch_dataset()
    metrics_df, yield_artifacts = evaluate_yield_models(df)
    _, curve_data = evaluate_growth_models(df)
    make_verification_plot(metrics_df, yield_artifacts, curve_data)


if __name__ == "__main__":
    main()
