"""Rebuild the processed AVCAD datasets directly from the original INE XLS files.

The INE exports use merged, multi-row headers.  This module makes the cell
selection explicit, translates the Portuguese labels used in the source files,
validates the result, and writes the harmonised CSV files used by the analysis.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
TABLES_DIR = ROOT / "outputs" / "tables"
YEARS = [1989, 1999, 2009, 2019]


def _source(prefix: str) -> Path:
    exact = RAW_DIR / f"{prefix}.xls"
    if exact.exists():
        return exact
    matches = sorted(RAW_DIR.glob(f"{prefix}*.xls"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one raw XLS beginning with {prefix!r}; found {matches}")
    return matches[0]


def _read(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name="Quadro", header=None, engine="xlrd")


def _number(value: object) -> float:
    if pd.isna(value) or str(value).strip().lower() in {"", "-", "x", "..."}:
        return np.nan
    return float(value)


def _vertical_total(path: Path, value_name: str) -> pd.DataFrame:
    """Extract exports where years run down rows and the total is column 3."""
    raw = _read(path)
    year = pd.to_numeric(raw.iloc[:, 0], errors="coerce").ffill()
    mask = raw.iloc[:, 1].astype(str).str.strip().eq("Continente")
    out = pd.DataFrame(
        {
            "year": year.loc[mask].astype(int),
            "geographic_location": "Continente",
            "code": "1",
            value_name: raw.loc[mask, 3].map(_number),
        }
    )
    return out.sort_values("year", ascending=False).reset_index(drop=True)


def _horizontal_series(path: Path, translations: dict[str, str]) -> pd.DataFrame:
    """Extract exports where each year is a horizontal block of measures."""
    raw = _read(path)
    years = pd.to_numeric(raw.iloc[7, :], errors="coerce").ffill()
    records: dict[int, dict[str, object]] = {}
    for column in range(2, raw.shape[1]):
        year = years.iloc[column]
        label = raw.iloc[9, column]
        unit = raw.iloc[10, column]
        if pd.isna(year) or int(year) not in YEARS or pd.isna(label):
            continue
        label = str(label).strip()
        if label in {"", "-"} or str(unit).strip() == "-":
            continue
        if label not in translations:
            raise ValueError(f"Unmapped source label {label!r} in {path.name}")
        record = records.setdefault(
            int(year),
            {"year": int(year), "geographic_location": "Continente", "code": "1"},
        )
        record[translations[label]] = _number(raw.iloc[12, column])
    return pd.DataFrame(records.values()).sort_values("year", ascending=False).reset_index(drop=True)


def _validate(name: str, frame: pd.DataFrame, value_columns: list[str]) -> None:
    if frame["year"].tolist() != YEARS[::-1]:
        raise ValueError(f"{name}: expected years {YEARS[::-1]}, got {frame['year'].tolist()}")
    if frame["year"].duplicated().any():
        raise ValueError(f"{name}: duplicate years")
    if not frame["geographic_location"].eq("Continente").all():
        raise ValueError(f"{name}: observations outside Continente")
    missing = set(value_columns).difference(frame.columns)
    if missing:
        raise ValueError(f"{name}: missing extracted columns {sorted(missing)}")
    if frame[value_columns].notna().sum().sum() == 0:
        raise ValueError(f"{name}: all extracted values are missing")


def prepare_processed_data() -> dict[str, pd.DataFrame]:
    """Create all processed CSVs from raw INE files and return the frames."""
    temporary_labels = {
        "Total": "Total",
        "Cereais para grão": "Grain cereals",
        "Leguminosas secas para grão": "Dried pulses for grain",
        "Prados temporários": "Temporary meadows",
        "Culturas forrageiras": "Forage crops",
        "Batata": "Potatoes",
        "Beterraba sacarina": "Sugar beet",
        "Culturas industriais": "Industrial crops",
        "Culturas hortícolas": "Horticultural crops",
        "Flores e plantas ornamentais": "Flowers and ornamental plants",
        "Outras culturas temporárias": "Other temporary crops",
    }
    grassland_labels = {
        "Total": "Total",
        "<0,5 ha": "<0.5 ha",
        "0,5 - <1 ha": "0.5 - <1 ha",
        "1 - <2 ha": "1 - <2 ha",
        "2 - <5 ha": "2 - <5 ha",
        "5 - <20 ha": "5 - <20 ha",
        "20 - <50 ha": "20 - <50 ha",
        "50 - <100 ha": "50 - <100 ha",
        ">= 100 ha": ">= 100 ha",
    }
    productivity_labels = {
        "Cereais para grão": "Cereals for grain",
        "Principais leguminosas secas": "Main dried legumes",
        "Batata": "Potatoes",
        "Principais culturas para indústria": "Main crops for industry",
        "Culturas hortícolas": "Horticultural crops",
        "Principais culturas forrageiras": "Main fodder crops",
        "Principais frutos frescos": "Main fresh fruits",
        "Frutos pequenos de baga": "Small berries",
        "Principais frutos subtropicais": "Main subtropical fruits",
        "Citrinos": "Citrus fruits",
        "Principais frutos de casca rija": "Main nut fruits",
        "Vinha": "Vineyards",
        "Olival": "Olive groves",
    }

    sources = {
        "agricultural_labour_clean.csv": _source("Mão-de-obra agrícola"),
        "agricultural_holdings_area_clean.csv": _source("Superfície das explorações agrícolas"),
        "temporary_crops_holdings_clean.csv": _source("Explorações agrícolas com culturas temporárias"),
        "permanent_crops_holdings_clean.csv": _source("Explorações agrícolas com culturas permanentes"),
        "permanent_grasslands_area_clean.csv": _source("Superfície de prados e pastagens permanentes"),
        "crop_productivity_clean.csv": _source("Produtividade das principais culturas agrícolas (kg_ha) por Localização geográfica (NUTS - 2013) e Espécie; Anual"),
    }
    frames = {
        "agricultural_labour_clean.csv": _vertical_total(sources["agricultural_labour_clean.csv"], "Agricultural labour"),
        "agricultural_holdings_area_clean.csv": _vertical_total(sources["agricultural_holdings_area_clean.csv"], "Agricultural holdings area (ha)"),
        "temporary_crops_holdings_clean.csv": _horizontal_series(sources["temporary_crops_holdings_clean.csv"], temporary_labels),
        "permanent_crops_holdings_clean.csv": _vertical_total(sources["permanent_crops_holdings_clean.csv"], "Total"),
        "permanent_grasslands_area_clean.csv": _horizontal_series(sources["permanent_grasslands_area_clean.csv"], grassland_labels),
        "crop_productivity_clean.csv": _horizontal_series(sources["crop_productivity_clean.csv"], productivity_labels),
    }

    for filename, frame in frames.items():
        values = [c for c in frame.columns if c not in {"year", "geographic_location", "code"}]
        # The INE tables report whole people, holdings, hectares and kg/ha.
        # Nullable integers preserve missing cells without adding misleading .0.
        frame[values] = frame[values].round().astype("Int64")
        _validate(filename, frame, values)

    # Cross-file checks catch silent shifts in merged headers and wrong-row selection.
    if frames["agricultural_labour_clean.csv"].loc[0, "Agricultural labour"] != 596938:
        raise ValueError("Labour anchor check failed for Continente, 2019")
    productivity = frames["crop_productivity_clean.csv"].set_index("year")
    if productivity.loc[2019, "Potatoes"] != 22953 or productivity.loc[2009, "Olive groves"] != 1229:
        raise ValueError("Productivity anchor checks failed; header alignment may have changed")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    for filename, frame in frames.items():
        frame.to_csv(PROCESSED_DIR / filename, index=False)

    provenance = pd.DataFrame(
        [
            {
                "processed_file": filename,
                "raw_file": sources[filename].name,
                "sheet": "Quadro",
                "geographic_filter": "Continente (code 1)",
                "years": "1989, 1999, 2009, 2019",
                "transformation": "Explicit merged-header parsing; INE missing markers converted to NA",
            }
            for filename in frames
        ]
    )
    provenance.to_csv(TABLES_DIR / "data_provenance.csv", index=False)
    return frames


def main() -> None:
    frames = prepare_processed_data()
    for filename, frame in frames.items():
        print(f"{filename}: {len(frame)} rows, {len(frame.columns)} columns")


if __name__ == "__main__":
    main()
