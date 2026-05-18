# Prefect membungkus semua proses ingestion menjadi sebuah "flow" yang bisa dimonitor, dijadwalkan, dan punya retry otomatis jika gagal.
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent)) 

from prefect import flow, task
from download_tlc import download_parquet, MONTHS
from fetch_external import fetch_weather, fetch_holidays

# @task = satu unit pekerjaan, bisa retry jika gagal
@task(retries=3, retry_delay_seconds=60, log_prints=True)
def task_download_tlc(taxi_type, year, month):
    download_parquet(taxi_type, year, month)

@task(retries=2, retry_delay_seconds=30, log_prints=True)
def task_fetch_weather():
    fetch_weather()

@task(retries=2, retry_delay_seconds=30, log_prints=True)
def task_fetch_holidays():
    fetch_holidays()

# @flow = kumpulan semua task menjadi satu pipeline
@flow(name='NYC-TLC-Ingestion-Pipeline')
def ingestion_flow():
    for year, months in MONTHS.items():
        for month in months:
            for taxi in ['yellow', 'green']:
                task_download_tlc(taxi, year, month)
    task_fetch_weather()
    task_fetch_holidays()

if __name__ == '__main__':
    ingestion_flow()