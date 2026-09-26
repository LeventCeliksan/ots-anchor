from pathlib import Path

import pytest

from ots_anchor import core
from ots_anchor.cli import main

HERE = Path(__file__).parent
FILE = HERE / "hello-world.txt"
PROOF = HERE / "hello-world.txt.ots"


def test_sha256():
    assert core.sha256_file(FILE).hex() == "03ba204e50d126e4674c005e04d82e84c21366780af1f43bd54a37816b6ab340"


def test_proof_matches_file():
    assert core.load_proof(PROOF).file_digest == core.sha256_file(FILE)


def test_roundtrip(tmp_path):
    out = tmp_path / "copy.ots"
    core.save_proof(core.load_proof(PROOF), out)
    assert out.read_bytes() == PROOF.read_bytes()


def test_tampered_file_rejected(tmp_path):
    bad = tmp_path / "hello-world.txt"
    bad.write_bytes(b"Hello World?\n")
    with pytest.raises(ValueError):
        core.verify(bad, PROOF)


@pytest.mark.network
def test_verify_against_bitcoin():
    confs = core.verify(FILE, PROOF)
    assert confs and confs[0].height == 358391


@pytest.mark.network
def test_cli_verify(capsys):
    assert main(["verify", str(FILE), str(PROOF)]) == 0
    assert "358391" in capsys.readouterr().out


@pytest.mark.network
def test_upgrade_pending_proof(tmp_path):
    f, p = tmp_path / "incomplete.txt", tmp_path / "incomplete.txt.ots"
    f.write_bytes((HERE / "incomplete.txt").read_bytes())
    p.write_bytes((HERE / "incomplete.txt.ots").read_bytes())
    assert core.verify(f, p) == []
    assert core.upgrade(p) is True
    assert core.verify(f, p)[0].height == 428648
