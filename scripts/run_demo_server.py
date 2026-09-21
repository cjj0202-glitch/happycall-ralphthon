"""Run the synthetic demo API on loopback only (uv run python scripts/run_demo_server.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="127.0.0.1", port=8100, access_log=False, log_level="warning")
