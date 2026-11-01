"""git_gate: before Claude makes a git move, the git-moves Ada model says what Chris would do in that repo state, from
his own past rulings (fetch first, check his unpushed branches, branch before committing, nothing merges without his
go, stop when blocked...). The same state always gets the same answer. It asks through rrotor's built-in glyphh CLI,
signed in once with an API key; `record` adds what Chris decided, so the next answer stands on it."""

from __future__ import annotations

import json
from typing import Any

from rrotor import CliError, Ctx, Result

MODEL = "git-moves"


def _glyphh(ctx: Ctx, args: list[str]) -> dict[str, Any] | Result:
    try:
        got = ctx.cli("glyphh", args)
    except CliError as err:
        return Result.failed("glyphh", f"{err.code}: {err.message}")
    if got.exit_code != 0:
        return Result.failed("glyphh", (got.stderr or got.stdout).strip()[:500] or f"glyphh exited {got.exit_code}")
    try:
        return json.loads(got.stdout)
    except ValueError:
        return Result.failed("glyphh", f"glyphh answered no JSON: {got.stdout.strip()[:300]}")


def check(ctx: Ctx, inputs: dict[str, Any]) -> Result:
    answer = _glyphh(ctx, ["decide", MODEL, json.dumps(inputs["case"])])
    if isinstance(answer, Result):
        return answer
    # Ada's own "ask a person" (nothing close enough is known, or it is unsure) is Chris's call too.
    outcome = "ask_chris" if answer.get("ask") else answer["outcome"]
    receipts = [{"id": r["id"], "outcome": r["outcome"], "sim": r["sim"]} for r in answer.get("receipts", [])[:3]]
    ctx.log("checked", outcome=outcome, ada=answer["outcome"], ask=bool(answer.get("ask")))
    return Result.done({
        "outcome": outcome,
        "ada_outcome": answer["outcome"],
        "ask": bool(answer.get("ask")),
        "probabilities": answer.get("probabilities", {}),
        "receipts": receipts,
        "version": answer.get("version"),
    })


def record(ctx: Ctx, inputs: dict[str, Any]) -> Result:
    answer = _glyphh(ctx, ["record", MODEL, json.dumps(inputs["case"]), "--outcome", inputs["outcome"]])
    if isinstance(answer, Result):
        return answer
    ctx.log("recorded", outcome=inputs["outcome"])
    return Result.done({"recorded": True, "outcome": inputs["outcome"], "answer": answer})
