"""
Data Insights Website
---------------------
A FastAPI backend that accepts a CSV (or Excel) upload, analyzes it with
pandas, and returns summary statistics, correlations, and plain-English
insights. A minimal HTML/JS frontend (templates/index.html) calls this API.

Run with:
    pip install -r requirements.txt
    uvicorn main:app --reload
Then open http://localhost:8000 in your browser.
"""

import io
import json

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI(title="Data Insights App")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file_to_df(filename: str, content: bytes) -> pd.DataFrame:
    """Load an uploaded CSV or Excel file into a pandas DataFrame."""
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    elif filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a .csv or .xlsx file.",
        )


def safe_json(obj):
    """Convert numpy/pandas types into plain JSON-safe Python types."""
    return json.loads(json.dumps(obj, default=str))


def analyze_dataframe(df: pd.DataFrame) -> dict:
    n_rows, n_cols = df.shape

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    categorical_cols = [c for c in df.columns if c not in numeric_cols]

    # --- Basic overview ---
    overview = {
        "rows": int(n_rows),
        "columns": int(n_cols),
        "column_names": df.columns.tolist(),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
    }

    # --- Missing values ---
    missing = df.isnull().sum()
    missing_pct = (missing / n_rows * 100).round(2)
    missing_report = [
        {"column": col, "missing_count": int(missing[col]), "missing_pct": float(missing_pct[col])}
        for col in df.columns
        if missing[col] > 0
    ]

    # --- Numeric summary stats ---
    numeric_summary = {}
    if numeric_cols:
        desc = df[numeric_cols].describe().T
        for col in numeric_cols:
            numeric_summary[col] = {
                "mean": round(float(desc.loc[col, "mean"]), 3),
                "median": round(float(df[col].median()), 3),
                "std": round(float(desc.loc[col, "std"]), 3) if not pd.isna(desc.loc[col, "std"]) else None,
                "min": round(float(desc.loc[col, "min"]), 3),
                "max": round(float(desc.loc[col, "max"]), 3),
            }

    # --- Categorical summary (top categories) ---
    categorical_summary = {}
    for col in categorical_cols:
        top_vals = df[col].value_counts().head(5)
        categorical_summary[col] = [
            {"value": str(idx), "count": int(cnt)} for idx, cnt in top_vals.items()
        ]

    # --- Correlations (strongest pairs) ---
    strong_correlations = []
    if len(numeric_cols) >= 2:
        corr_matrix = df[numeric_cols].corr()
        seen = set()
        for col_a in numeric_cols:
            for col_b in numeric_cols:
                if col_a == col_b:
                    continue
                pair = tuple(sorted([col_a, col_b]))
                if pair in seen:
                    continue
                seen.add(pair)
                val = corr_matrix.loc[col_a, col_b]
                if pd.isna(val):
                    continue
                if abs(val) >= 0.5:
                    strong_correlations.append(
                        {"column_a": col_a, "column_b": col_b, "correlation": round(float(val), 3)}
                    )
        strong_correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        strong_correlations = strong_correlations[:8]

    # --- Chart data: histogram-ready bins for up to 4 numeric columns ---
    charts = {}
    for col in numeric_cols[:4]:
        series = df[col].dropna()
        if series.empty:
            continue
        counts, bin_edges = np.histogram(series, bins=10)
        labels = [f"{round(bin_edges[i], 1)}–{round(bin_edges[i+1], 1)}" for i in range(len(bin_edges) - 1)]
        charts[col] = {"labels": labels, "counts": counts.tolist()}

    # For a categorical column (first one), give bar chart data too
    bar_chart = None
    if categorical_cols:
        col = categorical_cols[0]
        top = df[col].value_counts().head(8)
        bar_chart = {
            "column": col,
            "labels": [str(x) for x in top.index.tolist()],
            "counts": top.values.tolist(),
        }

    # --- Plain-English insights ---
    insights = []
    insights.append(f"The dataset has {n_rows} rows and {n_cols} columns.")

    if missing_report:
        worst = max(missing_report, key=lambda x: x["missing_pct"])
        insights.append(
            f"{len(missing_report)} column(s) have missing values — "
            f"'{worst['column']}' is the most affected at {worst['missing_pct']}% missing."
        )
    else:
        insights.append("No missing values were found — the dataset is complete.")

    for col, stats in numeric_summary.items():
        if stats["std"] is not None and stats["mean"] != 0:
            cv = abs(stats["std"] / stats["mean"])
            if cv > 1:
                insights.append(
                    f"'{col}' shows high variability (values range widely from {stats['min']} to {stats['max']})."
                )

    if strong_correlations:
        top_corr = strong_correlations[0]
        direction = "positive" if top_corr["correlation"] > 0 else "negative"
        insights.append(
            f"Strongest relationship: '{top_corr['column_a']}' and '{top_corr['column_b']}' have a "
            f"{direction} correlation of {top_corr['correlation']}."
        )
    elif len(numeric_cols) >= 2:
        insights.append("No strong correlations (|r| ≥ 0.5) were found between numeric columns.")

    if categorical_summary:
        for col, vals in categorical_summary.items():
            if vals:
                insights.append(
                    f"Most common value in '{col}' is '{vals[0]['value']}' ({vals[0]['count']} occurrences)."
                )
            break  # just highlight the first categorical column to keep it concise

    return safe_json({
        "overview": overview,
        "missing_report": missing_report,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "strong_correlations": strong_correlations,
        "charts": charts,
        "bar_chart": bar_chart,
        "insights": insights,
    })


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    df = read_file_to_df(file.filename, content)
    if df.empty:
        raise HTTPException(status_code=400, detail="No data found in the file.")
    result = analyze_dataframe(df)
    result["preview"] = safe_json(df.head(10).to_dict(orient="records"))
    return result
