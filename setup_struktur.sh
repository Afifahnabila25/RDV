#!/bin/bash
mkdir -p dashboard/pages
mkdir -p pipeline/ingestion
mkdir -p pipeline/cleaning
mkdir -p pipeline/modelling
mkdir -p analysis
mkdir -p data/raw/yellow
mkdir -p data/raw/green
mkdir -p data/raw/external
mkdir -p data/clean
mkdir -p data/final
mkdir -p docs

touch dashboard/app.py
touch dashboard/pages/overview.py
touch dashboard/pages/revenue_region.py
touch dashboard/pages/time_external.py
touch pipeline/ingestion/download_tlc.py
touch pipeline/ingestion/fetch_external.py
touch pipeline/ingestion/flow_ingestion.py
touch pipeline/ingestion/verify_download.py
touch pipeline/cleaning/clean_tlc.py
touch pipeline/cleaning/clean_external.py
touch pipeline/modelling/build_warehouse.py
touch analysis/run_analysis.py
touch docs/DECISIONS.md
touch prefect.yaml

cat >> .gitignore << 'EOF'

# Data folders
data/raw/
data/clean/
data/final/

# Python
__pycache__/
*.py[cod]
venv/
.env
EOF

echo "✅ Selesai! Struktur folder:"
find . -not -path './.git/*' | sort | sed 's|[^/]*/|  |g'
