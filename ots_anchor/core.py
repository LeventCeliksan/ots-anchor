"""Stamp, upgrade and verify OpenTimestamps proofs, checking Bitcoin block headers via a public Esplora API."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import requests
from opentimestamps.calendar import RemoteCalendar
from opentimestamps.core.notary import BitcoinBlockHeaderAttestation, PendingAttestation
from opentimestamps.core.op import OpSHA256
from opentimestamps.core.serialize import StreamDeserializationContext, StreamSerializationContext
from opentimestamps.core.timestamp import DetachedTimestampFile, Timestamp

DEFAULT_CALENDARS = (
    "https://a.pool.opentimestamps.org",
    "https://b.pool.opentimestamps.org",
    "https://a.pool.eternitywall.com",
)
DEFAULT_ESPLORA = "https://blockstream.info/api"


@dataclass
class Confirmation:
    height: int
    block_hash: str
    block_time: int


def sha256_file(path: Path) -> bytes:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.digest()


def load_proof(path: Path) -> DetachedTimestampFile:
    with open(path, "rb") as f:
        return DetachedTimestampFile.deserialize(StreamDeserializationContext(f))


def save_proof(proof: DetachedTimestampFile, path: Path) -> None:
    with open(path, "wb") as f:
        proof.serialize(StreamSerializationContext(f))


def stamp(path: Path, calendars=DEFAULT_CALENDARS, timeout: float = 10) -> Path:
    """Submit the file's SHA-256 to the calendars and write <file>.ots (pending until Bitcoin confirms)."""
    proof = DetachedTimestampFile(OpSHA256(), Timestamp(sha256_file(path)))
    submitted = 0
    for url in calendars:
        try:
            proof.timestamp.merge(RemoteCalendar(url).submit(proof.timestamp.msg, timeout=timeout))
            submitted += 1
        except Exception:
            continue
    if not submitted:
        raise RuntimeError("no calendar accepted the submission")
    out = path.with_name(path.name + ".ots")
    save_proof(proof, out)
    return out


def upgrade(proof_path: Path, timeout: float = 10) -> bool:
    """Ask each pending calendar for the completed Bitcoin attestation. Returns True if the proof changed."""
    proof = load_proof(proof_path)
    changed = False
    for msg, att in list(proof.timestamp.all_attestations()):
        if not isinstance(att, PendingAttestation):
            continue
        sub = _find(proof.timestamp, msg)
        try:
            sub.merge(RemoteCalendar(att.uri).get_timestamp(msg, timeout=timeout))
            changed = True
        except Exception:
            continue
    if changed:
        save_proof(proof, proof_path)
    return changed


def _find(ts: Timestamp, msg: bytes) -> Timestamp:
    if ts.msg == msg:
        return ts
    for child in ts.ops.values():
        found = _find(child, msg)
        if found is not None:
            return found
    return None


def verify(path: Path, proof_path: Path, esplora: str = DEFAULT_ESPLORA, timeout: float = 15) -> list[Confirmation]:
    """Check the file matches the proof and every Bitcoin attestation matches the real block's merkle root."""
    proof = load_proof(proof_path)
    if sha256_file(path) != proof.file_digest:
        raise ValueError("file does not match the proof (SHA-256 differs)")
    confirmations = []
    for msg, att in proof.timestamp.all_attestations():
        if not isinstance(att, BitcoinBlockHeaderAttestation):
            continue
        block_hash = _get(f"{esplora}/block-height/{att.height}", timeout).text.strip()
        block = _get(f"{esplora}/block/{block_hash}", timeout).json()
        if msg[::-1].hex() != block["merkle_root"]:
            raise ValueError(f"attestation does not match merkle root of block {att.height}")
        confirmations.append(Confirmation(att.height, block_hash, block["timestamp"]))
    return sorted(confirmations, key=lambda c: c.height)


def _get(url: str, timeout: float) -> requests.Response:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r
