import sys
import time
from datetime import datetime, UTC
from pathlib import Path

# Ensure project root is importable when run as a script.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import SIMULATION_INTERVAL_SECONDS
from simulator.generator import EnergyDataSimulator


def run_scheduler(num_readings: int = 10) -> None:
    """Run simulator continuously at a fixed interval."""
    simulator = EnergyDataSimulator()
    interval = max(10, SIMULATION_INTERVAL_SECONDS)

    print(f"Scheduler started. Interval: {interval} seconds")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            started = time.time()
            ts = datetime.now(UTC).isoformat()
            print(f"[{ts}] Running ingestion batch...")

            ok = simulator.ingest_batch(num_readings=num_readings)
            if ok:
                print("Batch completed successfully.\n")
            else:
                print("Batch failed. Will retry on next interval.\n")

            elapsed = time.time() - started
            sleep_for = max(0, interval - elapsed)
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        print("\nScheduler stopped by user.")
    finally:
        simulator.close()


if __name__ == "__main__":
    run_scheduler(num_readings=10)
