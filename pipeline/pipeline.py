"""
pipeline/pipeline.py
Orchestrator sementara untuk menjalankan ingestion flow lalu cleaning flow.
"""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = Path(__file__).resolve().parent


def run_flow(relative_path: str):
    script_path = PIPELINE_DIR / relative_path
    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        check=True,
    )


def main():
    run_flow("ingestion/flow_ingestion.py")
    run_flow("cleaning/flow_cleaning.py")


if __name__ == "__main__":
    main()
