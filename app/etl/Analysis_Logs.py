
import polars as pl
import gzip
import json
import time
import os
import logging
import pyarrow as pa
import pyarrow.parquet as pq

# rute: /app/data/local/sample.log.gz
file_path = "/app/data/local/sample.log.gz"
output_path = "/app/data/export/processed_log_data.parquet"

def detect_columns(file_path, sample_size=100):
    columns = set()
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                record = json.loads(line)
                columns.update(record.keys())
            except Exception:
                continue
            if i >= sample_size:
                break
    return list(columns)


def process_log_file(file_path, output_path):
    detected_columns = detect_columns(file_path)
    chunk_size = 500000  # Number of lines to process at a time
    start_time = time.time()  
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Starting log file processing...")

    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            records = []
            chunk_idx = 0
            for line in f:
                try:
                    record = json.loads(line)
                    if record.get('status_code', 0) >= 500:
                        # Clean and parse fields
                        full_record = {col: record.get(col, None) for col in detected_columns}
                        records.append(full_record)
                except json.JSONDecodeError as e:
                    logging.error(f"JSON decode error: {e}")
                    continue

                if len(records) >= chunk_size:
                    df = pl.DataFrame(records)    
                    df = df.with_columns(pl.col('timestamp').str.strptime(pl.Datetime, format="%Y-%m-%dT%H:%M:%SZ", strict=False))
                    df = df.group_by([pl.col('timestamp').dt.truncate("1h"), 'endpoint']).agg(
                        pl.len().alias('count'),
                        pl.mean('size_bytes').alias('avg_size_bytes'),
                        pl.mean('response_time_ms').alias('avg_response_time_ms')
                        ## This depends, what status codes you want to calculate 
                    )
                    chunk_output_path = f"{output_path.rstrip('.parquet')}_chunk{chunk_idx}.parquet"
                    df.write_parquet(chunk_output_path, compression="snappy")
                    chunk_idx += 1
                    records = []

            # Process remaining records
            if records:
                df = pl.DataFrame(records)        
                df = df.with_columns(pl.col('timestamp').str.strptime(pl.Datetime, format="%Y-%m-%dT%H:%M:%SZ", strict=False))
                df = df.group_by([pl.col('timestamp').dt.truncate("1h"), 'endpoint']).agg(
                    pl.len().alias('count'),
                    pl.mean('size_bytes').alias('avg_size_bytes'),
                    pl.mean('response_time_ms').alias('avg_response_time_ms')
                    ## This depends, what status codes you want to calculate 
                )
                chunk_output_path = f"{output_path.rstrip('.parquet')}_chunk{chunk_idx}.parquet"
                df.write_parquet(chunk_output_path, compression="snappy")

        logging.info(f"Processing completed in {time.time() - start_time:.2f} seconds.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

process_log_file(file_path, output_path)