import csv
import json
from pathlib import Path
import pyarrow.parquet as pq
import orjson


from src.common.config import settings
from src.common.logger import logger


def inspect_taxi_parquet(taxi_path: Path) -> None:
    taxi_files = sorted(taxi_path.glob("*.parquet"))
    if not taxi_files:
        logger.warning("No NYC Taxi parquet files found.")
        return

    sample_file = taxi_files[0]
    logger.info(f"=== NYC TAXI SCHEMA ({sample_file.name}) ===")
    parquet_file = pq.ParquetFile(sample_file)
    print(f"Total Rows: {parquet_file.metadata.num_rows:,}")
    print(parquet_file.schema_arrow)

    # Read just the first 3 rows from the first row group
    first_batch = next(parquet_file.iter_batches(batch_size=3))
    print("Sample Rows:", first_batch.to_pylist(), "\n")

def inspect_openaq_jsonl(openaq_path: Path) -> None:
    aq_files = sorted(openaq_path.glob("*.jsonl"))
    if not aq_files:
        logger.warning("No OpenAQ jsonl files found.")
        return

    sample_file = aq_files[0]
    logger.info(f"=== OPENAQ JSONL SAMPLE ({sample_file.name}) ===")
    with open(sample_file, "rb") as f:
        for i in range(2):
            line = f.readline()
            if not line:
                break
            record = orjson.loads(line)
            print(f"Record {i + 1}:", json.dumps(record, indent=2))
    print()

def inspect_macro_files(worldbank_path: Path, ecb_path: Path) -> None:
    ecb_fx_dir = ecb_path
    worldbank_dir = worldbank_path

    # 1. Inspect World Bank JSON
    wb_files = sorted(worldbank_dir.glob("worldbank_*.json"))
    if wb_files:
        logger.info(f"=== WORLD BANK GDP SAMPLE ({wb_files[0].name}) ===")
        with open(wb_files[0], "rb") as f:
            payload = orjson.loads(f.read())
            records = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
            print(f"Total Records: {len(records)}")
            if records:
                print("Sample Record:", json.dumps(records[0], indent=2), "\n")

    # 2. Inspect ECB FX CSV
    ecb_files = sorted(ecb_fx_dir.glob("ecb_*.csv"))
    if ecb_files:
        logger.info(f"=== ECB FX CSV SAMPLE ({ecb_files[0].name}) ===")
        with open(ecb_files[0], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            print("Columns:", reader.fieldnames)
            for i in range(2):
                row = next(reader, None)
                if row:
                    print(f"Row {i + 1} (Key Fields): TIME_PERIOD={row.get('TIME_PERIOD')}, OBS_VALUE={row.get('OBS_VALUE')}, CURRENCY={row.get('CURRENCY')}")
        print()

if __name__ == "__main__":
    taxi_bronze_dir = Path(settings.NYC_TAXI_RAW_TARGET_DIR)
    openaq_bronze_dir = Path(settings.OPENAQ_RAW_TARGET_DIR)
    worldbank_bronze_dir = Path(settings.WORLDBANK_RAW_TARGET_DIR)
    ecb_fx_bronze_dir = Path(settings.ECB_FX_RAW_TARGET_DIR)
    
    inspect_taxi_parquet(taxi_bronze_dir)
    inspect_openaq_jsonl(openaq_bronze_dir)
    inspect_macro_files(worldbank_bronze_dir, ecb_fx_bronze_dir)