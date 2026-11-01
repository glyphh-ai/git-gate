"""git_gate through rrotor.testing: the glyphh CLI answered by FakeCli, no network."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from rrotor import CliResult
from rrotor.testing import FakeCli, Harness

HERE = Path(__file__).resolve().parent.parent
CASE = {"move": {"intent": {"action": "merge_pr", "asked": "asked_task"}, "repo": {"ci": "pass", "pr": "open"}}}


def program() -> ModuleType:
    spec = importlib.util.spec_from_file_location("git_gate_program", HERE / "program.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def harness(tmp_path: Path, answer) -> Harness:
    return Harness(program(), tmp_path, clis={"glyphh": FakeCli(answer)})


def decided(outcome: str, ask: bool = False) -> str:
    return json.dumps({
        "outcome": outcome, "ask": ask, "probabilities": {outcome: 0.8}, "version": 2,
        "receipts": [{"id": "a", "outcome": outcome, "sim": 0.9, "hash": "h"}],
    })


def test_check_answers_ada_outcome_and_its_receipts(tmp_path):
    h = harness(tmp_path, decided("ask_chris"))
    r = h.call("check", {"case": CASE})
    assert r.status == "done" and r.data["outcome"] == "ask_chris" and r.data["receipts"][0]["id"] == "a"
    [(name, args, _)] = h.cli_calls
    assert name == "glyphh" and args[:2] == ["decide", "git-moves"] and json.loads(args[2]) == CASE


def test_when_ada_says_ask_it_is_chris_call(tmp_path):
    r = harness(tmp_path, decided("proceed", ask=True)).call("check", {"case": CASE})
    assert (r.data["outcome"], r.data["ada_outcome"], r.data["ask"]) == ("ask_chris", "proceed", True)


def test_record_teaches_it(tmp_path):
    h = harness(tmp_path, json.dumps({"id": "x", "precedents": 28}))
    r = h.call("record", {"case": CASE, "outcome": "proceed"})
    assert r.status == "done" and r.data["recorded"] is True
    assert h.cli_calls[0][1][-2:] == ["--outcome", "proceed"]


def test_glyphh_failing_is_a_failed_result(tmp_path):
    r = harness(tmp_path, CliResult(1, "", "not signed in")).call("check", {"case": CASE})
    assert (r.status, r.step) == ("failed", "glyphh") and "not signed in" in r.data["reason"]
