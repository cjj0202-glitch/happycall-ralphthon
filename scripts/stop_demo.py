"""Stop only the local demo processes recorded and verified by start_demo.py."""
import sys
import subprocess

from start_demo import locked, load_state, stop_owned


if __name__ == "__main__":
    try:
        with locked():
            stop_owned(load_state())
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
