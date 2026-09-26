"""Command-line entry point: ots-anchor stamp|upgrade|verify."""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import core


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ots-anchor", description="Timestamp files on Bitcoin with OpenTimestamps (no transaction fees).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stamp", help="create <file>.ots").add_argument("file", type=Path)
    sub.add_parser("upgrade", help="fetch Bitcoin attestation for a pending proof").add_argument("proof", type=Path)
    v = sub.add_parser("verify", help="verify a file against its proof")
    v.add_argument("file", type=Path)
    v.add_argument("proof", type=Path, nargs="?")
    a = p.parse_args(argv)

    try:
        if a.cmd == "stamp":
            print(f"Pending proof written: {core.stamp(a.file)} (Bitcoin confirmation usually takes a few hours; then run upgrade)")
        elif a.cmd == "upgrade":
            print("Upgraded." if core.upgrade(a.proof) else "Nothing to upgrade yet (still pending or already complete).")
        else:
            proof = a.proof or a.file.with_name(a.file.name + ".ots")
            confs = core.verify(a.file, proof)
            if not confs:
                print("Proof is valid for this file but not yet confirmed on Bitcoin (run upgrade later).")
                return 2
            for c in confs:
                when = datetime.fromtimestamp(c.block_time, timezone.utc).isoformat()
                print(f"Verified: existed before Bitcoin block {c.height} ({when}) {c.block_hash}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
