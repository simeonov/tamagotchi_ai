# training/load_data.py
import json
import os
import sys
import pandas as pd  # For easier data inspection
from typing import List, Dict

# Add project root to a Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure logging is configured if this script is run directly
try:
    from app.core.logging_config import setup_logging

    setup_logging(log_level_str="DEBUG")  # Use DEBUG to see more details if needed
except ModuleNotFoundError:
    import logging

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.info("Fallback basic logging initialized for load_data.py.")

import structlog

log = structlog.get_logger(__name__)


def load_jsonl_data(file_path: str) -> List[Dict]:
    """Loads data from a JSON Lines file."""
    data = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    log.error("Error decoding JSON line", line=line, error=str(e))
                    continue
        log.info("Successfully loaded data.", file_path=file_path, num_records=len(data))
    except FileNotFoundError:
        log.error("Data file not found.", file_path=file_path)
    except Exception as e:
        log.error("An error occurred while loading data.", file_path=file_path, error=str(e))
    return data


if __name__ == "__main__":
    # Find the most recent simulation data file in data/raw
    # This is a simple way, for robust pipelines use DVC to get data paths
    data_raw_path = os.path.join(PROJECT_ROOT, "data", "raw")
    latest_file = None
    latest_time = 0

    if os.path.exists(data_raw_path):
        for filename in os.listdir(data_raw_path):
            if filename.startswith("sim_") and filename.endswith(".jsonl"):
                file_path = os.path.join(data_raw_path, filename)
                file_mod_time = os.path.getmtime(file_path)
                if file_mod_time > latest_time:
                    latest_time = file_mod_time
                    latest_file = file_path

    if latest_file:
        log.info(f"Loading latest simulation data file: {latest_file}")
        simulation_data = load_jsonl_data(latest_file)

        if simulation_data:
            log.info(f"Loaded {len(simulation_data)} records.")

            # Example: Print the first 3 records to inspect
            for i, record in enumerate(simulation_data[:3]):
                log.info(f"Record {i}: {record}")

            # Example: Convert to Pandas DataFrame for easier inspection
            df = pd.DataFrame(simulation_data)
            log.info("DataFrame head:\n", data_head=df.head().to_string())
            log.info("DataFrame info:\n")
            df.info(verbose=True)  # Using info() directly prints to console

            # Inspect the structure of 'state' and 'next_state'
            if not df.empty:
                log.info("Structure of a 'state' object:", state_example=df['state'].iloc)
                log.info("Structure of a 'next_state' object:", next_state_example=df['next_state'].iloc)
        else:
            log.warn("No data loaded.")
    else:
        log.error("No simulation data files found in data/raw. Please run simulation/simulator.py first.")