# Agricultural Restructuring in Mainland Portugal (1989-2019)

Final project for Analysis and Visualisation of Complex Agro-Environmental
Data, Master's in Green Data Science, Instituto Superior de Agronomia,
Universidade de Lisboa (2025/2026).

The project tells a national temporal story from official Statistics Portugal
(INE) data. The complete pipeline begins with the original `.xls` exports and
examines agricultural labour, total agricultural area, holdings
reporting temporary and permanent crops, permanent grasslands, and crop
productivity at four Agricultural Census reference years.

## Research question

How did the structure of agriculture in mainland Portugal change between 1989
and 2019?

The processed extracts contain mainland totals only. The final analysis is
therefore temporal rather than regional and does not claim to identify regional
effects.

## Main findings

Between 1989 and 2019:

- agricultural labour decreased 58.8%;
- total agricultural area decreased only 3.3%;
- agricultural area per worker increased 134.9%;
- holdings reporting temporary crops decreased 72.1%;
- holdings reporting permanent crops decreased 54.7%;
- permanent grasslands and pastures increased 165.5%.

The combined evidence is consistent with agricultural restructuring toward
less labour-intensive land management, not uniform disappearance of agriculture.

## Repository structure

```text
data/raw/                  Original INE .xls files
data/processed/            Harmonised mainland extracts
notebooks/01_data_loading_and_audit.ipynb
                           Initial extraction/audit notebook
notebooks/02_full_analysis.ipynb
                           Reproducible EDA and inference
src/analysis.py            Authoritative analysis pipeline
src/prepare_data.py        Raw XLS extraction, cleaning and validation
outputs/figures/           Report-ready visualisations
outputs/tables/            Descriptive and inferential results
report/Report_AVCAD_fernanda.md
                           Visual, reproducible final-report draft
```

The Word-report drafts are retained for provenance and remain outside the new
commit. The Markdown report is the authoritative content draft and can be moved
into the team's preferred Word template after final editorial review.

## Reproduce the analysis

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python src/analysis.py
```

`src/analysis.py` first runs `src/prepare_data.py`, so the CSVs, audit table,
analysis tables and figures are all rebuilt from the original INE files. The
preparation step resolves merged headers and preserves missing values; this also
prevents values from shifting into the wrong productivity columns.

The notebook `02_full_analysis.ipynb` contains an Open in Colab badge and runs
the same pipeline.

## Statistical interpretation

OLS and Spearman trend statistics are included because inferential analysis is
required by the project brief. Each census series has only four observations,
so p-values and confidence intervals must be interpreted cautiously. They do not
establish causality. Productivity comparisons are descriptive where missing
values prevent a complete four-year series.

## Data notes

- Crop-holding indicators count holdings reporting a crop group and are not
  mutually exclusive.
- The project does not estimate average crop-specific holding size because the
  available data do not contain the required crop-area numerator.
- Long INE filenames may require `git config --global core.longpaths true` on
  Windows.
- `outputs/tables/data_provenance.csv` records the raw source, worksheet,
  geographic filter, years and transformation used for each processed file.

## Team

- Andrea Dombe - 27119
- Dandara França - 27916
- Fernanda Chácara - 26298

## Sources

- Statistics Portugal (INE), Agricultural Census and agricultural statistics.
- Eurostat agriculture statistics for contextual interpretation.
