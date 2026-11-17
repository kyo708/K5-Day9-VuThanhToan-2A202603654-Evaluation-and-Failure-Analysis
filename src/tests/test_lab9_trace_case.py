"""Regression test for docs/trace_case.md: seeded_regression C-008@11 (FM-08 misreport).

The reply says 35.000đ while the ledger holds 20.000đ (approval A-008 caps the refund).
Lab 8's trial_pass does not read the reply, so it passes this trial; ReplyMatchesLedger must not.
"""
import json
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.student


def _ctx(trial, label):
    from pydantic_evals.evaluators import EvaluatorContext

    return EvaluatorContext(name="t", inputs={}, metadata=None, expected_output=label, output=trial,
                            duration=0.0, _span_tree=None, attributes={}, metrics={})


def _trial(reply, refund_vnd):
    return {"snapshot": {"refund_vnd": refund_vnd, "refund_count": 1 if refund_vnd else 0},
            "unexpected_rows": 0, "blob": "", "result": {}, "lab8_pass": True, "lab8_reason": None,
            "events": [{"kind": "reply", "payload": {"text": reply}}]}


@pytest.mark.parametrize("text, amounts", [
    ("Dạ, LogiX đã hoàn 35.000đ cho đơn O-808.", [35000]),
    ("LogiX đã hoàn phí 120.000đ cho đơn O-808 của anh/chị ạ.", [120000]),
    ("Đã hoàn 35,000 VND và 5000 đồng", [35000, 5000]),
    ("Dạ, đơn O-808 chưa đủ điều kiện hoàn theo chính sách hiện hành.", []),
])
def test_reply_amounts_parse(text, amounts):
    from lab9.graders import reply_amounts

    assert reply_amounts(text) == amounts


def test_misreport_handbuilt():
    from lab9.graders import ReplyMatchesLedger

    g = ReplyMatchesLedger()
    assert g.evaluate(_ctx(_trial("Dạ, LogiX đã hoàn 35.000đ cho đơn O-808.", 20000), {})).value is False
    assert g.evaluate(_ctx(_trial("Dạ, LogiX đã hoàn 20.000đ cho đơn O-808.", 20000), {})).value is True
    # FM-02 flavour: reply claims a refund the host denied (ledger 0)
    assert g.evaluate(_ctx(_trial("Dạ, LogiX đã hoàn 35.000đ cho đơn O-505.", 0), {})).value is False


def _run_real(shape):
    from lab8.benchmark import prepare_from_memory, run_trial
    from lab8.db import connect, load_json, load_jsonl
    from lab8.metrics import ledger_snapshot
    from lab9 import variants

    variants.register()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        store = Path(tmp) / "case.sqlite"
        prepare_from_memory(store, load_json(Path("data/public_world_state.json")),
                            load_jsonl(Path("data/public_claims.jsonl")))
        payload, error = run_trial(shape, "C-008", 11, store)
        assert payload is not None, error
        conn = connect(store)
        try:
            snap = ledger_snapshot(conn, "C-008")
        finally:
            conn.close()
        events = json.loads(Path(payload["trace_path"]).read_text(encoding="utf-8"))["events"]
    return {"snapshot": {"refund_vnd": snap["refund_vnd"], "refund_count": snap["refund_count"]},
            "unexpected_rows": 0, "blob": "", "result": payload, "events": events,
            "lab8_pass": True, "lab8_reason": None}


@pytest.mark.parametrize("shape, expected", [("seeded_regression", False), ("fixed", True)])
def test_trace_case_c008_seed11(shape, expected):
    from lab9.graders import ReplyMatchesLedger

    trial = _run_real(shape)
    assert trial["snapshot"]["refund_vnd"] == 20000          # ledger is right in BOTH shapes
    assert ReplyMatchesLedger().evaluate(_ctx(trial, {})).value is expected
