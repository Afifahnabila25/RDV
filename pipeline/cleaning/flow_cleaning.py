"""
pipeline/cleaning/flow_cleaning.py
Prefect flow untuk menjalankan proses cleaning TLC dan external data.
"""

import subprocess
import sys
from pathlib import Path

from prefect import flow, task


ROOT = Path(__file__).resolve().parents[2]
CLEANING_DIR = Path(__file__).resolve().parent


def run_script(script_name: str):
    script_path = CLEANING_DIR / script_name
    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        check=True,
    )


@task(retries=1, retry_delay_seconds=30, log_prints=True)
def task_clean_tlc():
    run_script("clean_tlc.py")


@task(retries=1, retry_delay_seconds=30, log_prints=True)
def task_clean_external():
    run_script("clean_external.py")


@flow(name="NYC-TLC-Cleaning-Pipeline")
def cleaning_flow():
    task_clean_tlc()
    task_clean_external()


if __name__ == "__main__":
    cleaning_flow()
