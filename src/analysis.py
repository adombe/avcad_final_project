"""Reproducible analysis for the AVCAD final project.

The script starts from the processed INE extracts committed to the repository,
creates a harmonised national time series, performs descriptive and cautious
inferential analyses, and writes all report tables and figures under outputs/.
"""

# prompt: Complete the AVCAD project with a reproducible national temporal
# analysis, descriptive statistics, cautious inference for four census years,
# publication-ready figures, and auditable output tables. Do not claim regional
# effects because the processed extracts contain only mainland totals.
# Modifications: variable names, hypotheses, plots, statistical caveats, and
# paths were adapted to the six INE-derived CSV files in this repository.

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "outputs" / "figures"
TABLES_DIR = ROOT / "outputs" / "tables"

YEARS = [1989, 1999, 2009, 2019]
COLORS = {
    "labour": "#1F4E79",
    "area": "#548235",
    "temporary": "#C55A11",
    "permanent": "#7030A0",
    "grasslands": "#7F6000",
}


def read_processed() -> dict[str, pd.DataFrame]:
    files = {
        "labour": "agricultural_labour_clean.csv",
        "area": "agricultural_holdings_area_clean.csv",
        "temporary": "temporary_crops_holdings_clean.csv",
        "permanent": "permanent_crops_holdings_clean.csv",
        "grasslands": "permanent_grasslands_area_clean.csv",
        "productivity": "crop_productivity_clean.csv",
    }
    frames = {name: pd.read_csv(DATA_DIR / filename) for name, filename in files.items()}
    for name, frame in frames.items():
        required = {"year", "geographic_location", "code"}
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{name} is missing required columns: {sorted(missing)}")
        if frame["year"].duplicated().any():
            raise ValueError(f"{name} contains duplicate years")
        if set(frame["year"]) != set(YEARS):
            raise ValueError(f"{name} does not contain exactly {YEARS}")
        if not frame["geographic_location"].eq("Continente").all():
            raise ValueError(f"{name} contains observations outside mainland Portugal")
    return frames


def build_core_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    extracts = [
        frames["labour"][["year", "Agricultural labour"]].rename(
            columns={"Agricultural labour": "agricultural_labour_people"}
        ),
        frames["area"][["year", "Agricultural holdings area (ha)"]].rename(
            columns={"Agricultural holdings area (ha)": "agricultural_area_ha"}
        ),
        frames["temporary"][["year", "Total"]].rename(
            columns={"Total": "temporary_crop_holdings"}
        ),
        frames["permanent"][["year", "Total"]].rename(
            columns={"Total": "permanent_crop_holdings"}
        ),
        frames["grasslands"][["year", "Total", ">= 100 ha"]].rename(
            columns={
                "Total": "permanent_grasslands_ha",
                ">= 100 ha": "grasslands_ge_100ha",
            }
        ),
    ]
    core = extracts[0]
    for extract in extracts[1:]:
        core = core.merge(extract, on="year", validate="one_to_one")
    core = core.sort_values("year").reset_index(drop=True)
    core["agricultural_area_per_worker_ha"] = (
        core["agricultural_area_ha"] / core["agricultural_labour_people"]
    )
    core["grasslands_ge_100ha_share"] = (
        core["grasslands_ge_100ha"] / core["permanent_grasslands_ha"]
    )
    return core


def percent_change_table(core: pd.DataFrame) -> pd.DataFrame:
    labels = {
        "agricultural_labour_people": "Agricultural labour",
        "agricultural_area_ha": "Agricultural area",
        "temporary_crop_holdings": "Holdings with temporary crops",
        "permanent_crop_holdings": "Holdings with permanent crops",
        "permanent_grasslands_ha": "Permanent grasslands and pastures",
        "agricultural_area_per_worker_ha": "Agricultural area per worker",
        "grasslands_ge_100ha_share": "Share of grasslands in >=100 ha class",
    }
    rows = []
    first = core.set_index("year").loc[1989]
    last = core.set_index("year").loc[2019]
    for variable, label in labels.items():
        start = float(first[variable])
        end = float(last[variable])
        rows.append(
            {
                "indicator": label,
                "value_1989": start,
                "value_2019": end,
                "absolute_change": end - start,
                "percent_change": 100 * (end / start - 1),
            }
        )
    return pd.DataFrame(rows)


def trend_tests(core: pd.DataFrame) -> pd.DataFrame:
    variables = {
        "agricultural_labour_people": "Agricultural labour",
        "agricultural_area_ha": "Agricultural area",
        "temporary_crop_holdings": "Holdings with temporary crops",
        "permanent_crop_holdings": "Holdings with permanent crops",
        "permanent_grasslands_ha": "Permanent grasslands and pastures",
        "agricultural_area_per_worker_ha": "Agricultural area per worker",
    }
    x = core["year"].to_numpy(dtype=float)
    rows = []
    for variable, label in variables.items():
        y = core[variable].to_numpy(dtype=float)
        fit = stats.linregress(x, y)
        critical_t = stats.t.ppf(0.975, df=len(x) - 2)
        slope_decade = fit.slope * 10
        margin_decade = critical_t * fit.stderr * 10
        spearman = stats.spearmanr(x, y)
        rows.append(
            {
                "indicator": label,
                "n": len(x),
                "ols_slope_per_decade": slope_decade,
                "slope_ci95_low": slope_decade - margin_decade,
                "slope_ci95_high": slope_decade + margin_decade,
                "pearson_r": fit.rvalue,
                "ols_p_value": fit.pvalue,
                "r_squared": fit.rvalue**2,
                "spearman_rho": spearman.statistic,
                "spearman_p_value": spearman.pvalue,
            }
        )
    return pd.DataFrame(rows)


def productivity_changes(productivity: pd.DataFrame) -> pd.DataFrame:
    id_columns = {"year", "geographic_location", "code"}
    crop_columns = [column for column in productivity.columns if column not in id_columns]
    indexed = productivity.set_index("year").sort_index()
    rows = []
    for crop in crop_columns:
        start = indexed.at[1989, crop]
        end = indexed.at[2019, crop]
        if pd.notna(start) and pd.notna(end) and start != 0:
            rows.append(
                {
                    "crop_group": crop,
                    "productivity_1989_kg_ha": float(start),
                    "productivity_2019_kg_ha": float(end),
                    "percent_change": 100 * (float(end) / float(start) - 1),
                }
            )
    return pd.DataFrame(rows).sort_values("percent_change", ascending=False)


def hypothesis_table(changes: pd.DataFrame, trends: pd.DataFrame) -> pd.DataFrame:
    change = changes.set_index("indicator")["percent_change"]
    pvalue = trends.set_index("indicator")["ols_p_value"]
    return pd.DataFrame(
        [
            {
                "hypothesis": "H1",
                "assessment": "Supported descriptively and by a negative linear trend",
                "evidence": f"Labour changed {change['Agricultural labour']:.1f}% (OLS p={pvalue['Agricultural labour']:.3f}).",
            },
            {
                "hypothesis": "H2",
                "assessment": "Partially supported",
                "evidence": f"Total area changed only {change['Agricultural area']:.1f}%, but land-use composition changed strongly.",
            },
            {
                "hypothesis": "H3",
                "assessment": "Supported descriptively",
                "evidence": f"Temporary-crop holdings changed {change['Holdings with temporary crops']:.1f}% versus {change['Holdings with permanent crops']:.1f}% for permanent crops.",
            },
            {
                "hypothesis": "H4",
                "assessment": "Supported descriptively",
                "evidence": f"Permanent grasslands changed {change['Permanent grasslands and pastures']:.1f}%, with increasing weight in the >=100 ha class.",
            },
            {
                "hypothesis": "H5",
                "assessment": "Supported descriptively",
                "evidence": "Productivity changes differ substantially among crop groups; missing observations limit formal comparison.",
            },
        ]
    )


def save_figure(fig: plt.Figure, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def create_figures(
    core: pd.DataFrame,
    productivity_change: pd.DataFrame,
) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
        }
    )

    indexed_variables = {
        "agricultural_labour_people": ("Agricultural labour", COLORS["labour"]),
        "agricultural_area_ha": ("Agricultural area", COLORS["area"]),
        "temporary_crop_holdings": ("Temporary-crop holdings", COLORS["temporary"]),
        "permanent_crop_holdings": ("Permanent-crop holdings", COLORS["permanent"]),
        "permanent_grasslands_ha": ("Permanent grasslands", COLORS["grasslands"]),
    }
    fig, axis = plt.subplots(figsize=(9, 5.3))
    for variable, (label, color) in indexed_variables.items():
        values = 100 * core[variable] / core.loc[core["year"].eq(1989), variable].iloc[0]
        axis.plot(core["year"], values, marker="o", linewidth=2.2, label=label, color=color)
    axis.axhline(100, color="#777777", linewidth=0.8, linestyle="--")
    axis.set_title("Structural change in mainland Portuguese agriculture (1989=100)")
    axis.set_xlabel("Census year")
    axis.set_ylabel("Index (1989=100)")
    axis.set_xticks(YEARS)
    axis.grid(alpha=0.25)
    axis.legend(frameon=False, ncol=2)
    save_figure(fig, "indexed_structural_change.png")

    fig, axis = plt.subplots(figsize=(7.5, 4.6))
    axis.plot(
        core["year"],
        core["agricultural_area_per_worker_ha"],
        marker="o",
        linewidth=2.4,
        color=COLORS["labour"],
    )
    axis.set_title("Agricultural area per agricultural worker")
    axis.set_xlabel("Census year")
    axis.set_ylabel("Hectares per worker")
    axis.set_xticks(YEARS)
    axis.grid(alpha=0.25)
    save_figure(fig, "area_per_worker.png")

    fig, axis = plt.subplots(figsize=(7.8, 4.8))
    axis.plot(core["year"], core["temporary_crop_holdings"], marker="o", linewidth=2.2, label="Temporary crops", color=COLORS["temporary"])
    axis.plot(core["year"], core["permanent_crop_holdings"], marker="o", linewidth=2.2, label="Permanent crops", color=COLORS["permanent"])
    axis.set_title("Holdings reporting temporary and permanent crops")
    axis.set_xlabel("Census year")
    axis.set_ylabel("Number of holdings")
    axis.set_xticks(YEARS)
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    save_figure(fig, "crop_holdings.png")

    fig, left = plt.subplots(figsize=(7.8, 4.8))
    left.plot(core["year"], core["permanent_grasslands_ha"] / 1_000_000, marker="o", linewidth=2.2, color=COLORS["grasslands"])
    left.set_xlabel("Census year")
    left.set_ylabel("Permanent grasslands (million ha)", color=COLORS["grasslands"])
    left.tick_params(axis="y", labelcolor=COLORS["grasslands"])
    left.set_xticks(YEARS)
    right = left.twinx()
    right.plot(core["year"], 100 * core["grasslands_ge_100ha_share"], marker="s", linewidth=2.0, color="#4472C4")
    right.set_ylabel("Share in >=100 ha class (%)", color="#4472C4")
    right.tick_params(axis="y", labelcolor="#4472C4")
    left.set_title("Expansion and concentration of permanent grasslands")
    left.grid(alpha=0.22)
    save_figure(fig, "grasslands_change.png")

    fig, axis = plt.subplots(figsize=(8.3, 5.3))
    plot_data = productivity_change.sort_values("percent_change")
    colors = ["#A61C00" if value < 0 else "#548235" for value in plot_data["percent_change"]]
    axis.barh(plot_data["crop_group"], plot_data["percent_change"], color=colors)
    axis.axvline(0, color="#555555", linewidth=0.8)
    axis.set_title("Change in crop productivity, 1989-2019")
    axis.set_xlabel("Change (%)")
    axis.grid(axis="x", alpha=0.22)
    save_figure(fig, "productivity_change.png")


def run_analysis() -> dict[str, pd.DataFrame]:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    frames = read_processed()
    core = build_core_table(frames)
    changes = percent_change_table(core)
    trends = trend_tests(core)
    productivity_change = productivity_changes(frames["productivity"])
    hypotheses = hypothesis_table(changes, trends)

    outputs = {
        "core_summary": core,
        "percent_change": changes,
        "trend_tests": trends,
        "productivity_change": productivity_change,
        "hypothesis_assessment": hypotheses,
    }
    for name, table in outputs.items():
        table.to_csv(TABLES_DIR / f"{name}.csv", index=False)
    create_figures(core, productivity_change)
    return outputs


def main() -> None:
    outputs = run_analysis()
    print("Core time series")
    print(outputs["core_summary"].to_string(index=False))
    print("\nChanges, 1989-2019")
    print(outputs["percent_change"][["indicator", "percent_change"]].to_string(index=False))
    print("\nTrend tests (interpret cautiously: n=4)")
    print(outputs["trend_tests"][["indicator", "ols_slope_per_decade", "ols_p_value", "r_squared"]].to_string(index=False))


if __name__ == "__main__":
    main()
