# ots-anchor

Timestamp any file on Bitcoin **with no transaction fees** using [OpenTimestamps](https://opentimestamps.org), and verify proofs against **real Bitcoin block headers** (via a public Esplora API — no local node needed).

This is a small, standalone version of the proof-of-existence approach I use in production at [Sealify](https://sealify.io), where 1,600+ registrations are anchored on Bitcoin mainnet.

## How it works
1. **stamp** — the file's SHA-256 is sent to several public OpenTimestamps calendars (the file itself never leaves your machine). A pending `.ots` proof is written.
2. The calendars aggregate thousands of hashes into one Merkle tree and commit its root in a single Bitcoin transaction — so each file costs nothing.
3. **upgrade** — after a few hours, fetch the completed path from your hash to the Bitcoin block.
4. **verify** — recompute the file hash, replay the proof, and check the result equals the Merkle root of the actual Bitcoin block.

## Install
```bash
pip install git+https://github.com/LeventCeliksan/ots-anchor
```

## Usage
```bash
ots-anchor stamp contract.pdf            # -> contract.pdf.ots (pending)
ots-anchor upgrade contract.pdf.ots      # a few hours later
ots-anchor verify contract.pdf           # uses contract.pdf.ots
# Verified: existed before Bitcoin block 358391 (2015-05-28T15:41:18+00:00) 0000...2319
```
Exit codes: `0` verified, `2` valid but not yet confirmed on Bitcoin, `1` error or mismatch.

Python API:
```python
from pathlib import Path
from ots_anchor import core
core.verify(Path("hello-world.txt"), Path("hello-world.txt.ots"))
```

## Tests
```bash
pip install -e . pytest
pytest                 # includes live checks against Bitcoin block data
pytest -m "not network"  # offline only
```
The test fixtures are the official examples from the OpenTimestamps client repository: a confirmed proof (block 358391) and a pending one that the test upgrades and verifies (block 428648).

## License
MIT
