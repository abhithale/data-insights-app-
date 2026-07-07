# Data Insights App

A website where you upload a CSV or Excel file and instantly get:
- Dataset overview (rows, columns, types)
- Summary statistics (mean, median, std, min, max) for numeric columns
- Missing data report
- Correlation detection between numeric columns
- Auto-generated histograms and bar charts
- Plain-English insights ("Strongest relationship: X and Y have a positive correlation of 0.98")
- A preview table of your data

## Tech Stack
- **Backend**: FastAPI (Python)
- **Data analysis**: pandas + numpy
- **Frontend**: Plain HTML/CSS/JS (no framework), Chart.js for graphs
- Everything is served from the same backend — no separate frontend server needed.

## Setup 

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

3. Open your browser to:
   ```
   http://localhost:8000
   ```

4. Upload `sample_data.csv` (included) to see it in action, or upload your own `.csv` / `.xlsx` file.

## Project Structure
```
data-insights-app/
├── main.py              # FastAPI backend + analysis logic
├── templates/
│   └── index.html       # Frontend page (upload UI + charts)
├── static/               # (reserved for future CSS/JS/images)
├── sample_data.csv       # Example dataset to try immediately
├── requirements.txt
└── README.md
```

## How it works

1. You upload a file through the browser.
2. The browser sends it to `POST /api/analyze`.
3. The backend loads it into a pandas DataFrame and computes:
   - Descriptive statistics for every numeric column
   - Top categories for every categorical column
   - Correlation coefficients between numeric column pairs (flags |r| ≥ 0.5)
   - Missing-value counts and percentages
   - Histogram bins for charting
4. The backend also generates a few plain-English insight sentences based on the above.
5. The frontend renders all of this as cards, tables, and Chart.js graphs.

## Extending it

Some ideas if you want to build this out further:
- **Add authentication** so users can save past analyses (e.g. with a database like SQLite/Postgres + a users table).
- **Persist uploads** — currently files are analyzed in-memory and not saved to disk.
- **Add more analysis** — outlier detection, time-series trends (if there's a date column), or clustering.
- **Export insights** — add a `/api/export` endpoint that generates a PDF or Word report of the findings (this pairs well with report-generation libraries).
- **Support JSON input** or database connections (e.g., paste a Postgres connection string) instead of just file upload.

## Notes on customizing the analysis

All the analysis logic lives in one function: `analyze_dataframe()` in `main.py`. If you want to change what counts as a "strong correlation," add new insight rules, or analyze specific columns differently, that's the only place you need to edit.
