"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

from typing import Any

from lab8.compensation import quote
from lab8.config_loader import as_of
from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.trace import Trace
from lab8.tools import get_claim_view, tool_cost


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        budget = Budget()
        run_id = make_run_id("single", claim_id, seed)
        trace = Trace(run_id)

        budget.add_tool(tool_cost())
        claim = get_claim_view(conn, claim_id)
        trace.add(
            "claim",
            {
                "found": claim["found"],
                "claim_id": claim_id,
                "order_id": claim.get("order_id"),
            },
        )
        if not claim["found"]:
            trace.add("error", {"reason": "unknown_claim"})
            return finish(
                conn,
                shape="single",
                claim_id=claim_id,
                seed=seed,
                status="failed",
                proposal_amount=0,
                budget=budget,
                trace=trace,
                error_reason="unknown_claim",
            )

        if not claim.get("order_id"):
            trace.add("decision", {"status": "needs_info", "reason": "missing_order_id"})
            return finish(
                conn,
                shape="single",
                claim_id=claim_id,
                seed=seed,
                status="needs_info",
                proposal_amount=0,
                budget=budget,
                trace=trace,
                error_reason="missing_order_id",
            )

        observation_claim = {
            "claim_id": claim_id,
            "order_id": claim["order_id"],
            "principal_id": claim["principal_id"],
        }
        order_view: dict[str, Any] = {}
        policy_view: dict[str, Any] = {}
        refund_history: dict[str, Any] = {}

        def decide(observation: dict[str, Any]) -> dict[str, Any]:
            nonlocal order_view, policy_view, refund_history
            last_tool = observation.get("last_tool")
            complete(
                budget,
                seed=seed,
                purpose="single_decide",
                prompt=f"last_tool={last_tool or 'start'}",
            )
            if last_tool == "lookup_order":
                order_view = observation["last_result"]
                trace.add("react_result", {"tool": last_tool, "result": safe_dump(order_view)})
                if not order_view.get("visible"):
                    return {
                        "final": {
                            "status": "escalated",
                            "reason": order_view.get("reason", "order_not_visible"),
                        }
                    }
            elif last_tool == "lookup_policy":
                policy_view = observation["last_result"]
                trace.add(
                    "react_result",
                    {"tool": last_tool, "result": safe_dump(policy_view)},
                )
            elif last_tool == "lookup_refund_history":
                refund_history = observation["last_result"]
                trace.add(
                    "react_result",
                    {"tool": last_tool, "result": safe_dump(refund_history)},
                )
                return {"final": {"status": "ready"}}

            if last_tool is None:
                action = {
                    "tool": "lookup_order",
                    "args": {
                        "order_id": observation_claim["order_id"],
                        "principal_id": observation_claim["principal_id"],
                    },
                }
            elif last_tool == "lookup_order":
                action = {"tool": "lookup_policy", "args": {}}
            elif last_tool == "lookup_policy":
                action = {
                    "tool": "lookup_refund_history",
                    "args": {
                        "order_id": observation_claim["order_id"],
                        "principal_id": observation_claim["principal_id"],
                    },
                }
            else:
                return {"final": {"status": "failed", "reason": "unexpected_react_state"}}
            trace.add("react_action", {"tool": action["tool"]})
            return action

        react_result = run_react(
            conn,
            budget,
            observation={"claim": observation_claim},
            decide=decide,
            max_steps=8,
        )
        final = react_result["final"]
        if final.get("status") == "escalated":
            trace.add("decision", {"status": "escalated", "reason": final.get("reason")})
            return finish(
                conn,
                shape="single",
                claim_id=claim_id,
                seed=seed,
                status="escalated",
                proposal_amount=0,
                budget=budget,
                trace=trace,
                error_reason=final.get("reason"),
            )
        if react_result["stopped"] != "final" or final.get("status") != "ready":
            reason = final.get("error_reason") or final.get("reason") or "step_cap"
            trace.add("decision", {"status": "failed", "reason": reason})
            return finish(
                conn,
                shape="single",
                claim_id=claim_id,
                seed=seed,
                status="failed",
                proposal_amount=0,
                budget=budget,
                trace=trace,
                error_reason=reason,
            )

        order = order_view["order"]
        quote_result = quote(order, policy_view.get("policies", []), as_of=as_of())
        quote_payload = {
            "amount_vnd": quote_result.amount_vnd,
            "reason": quote_result.reason,
            "clause_ids": quote_result.clause_ids,
            "parts": quote_result.parts,
            "refund_history": refund_history,
        }
        trace.add("quote", safe_dump(quote_payload))
        proposal = int(quote_result.amount_vnd)
        if proposal <= 0:
            trace.add("decision", {"status": "denied", "reason": quote_result.reason})
            return finish(
                conn,
                shape="single",
                claim_id=claim_id,
                seed=seed,
                status="denied",
                proposal_amount=0,
                budget=budget,
                trace=trace,
                error_reason=quote_result.reason,
            )

        try:
            outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
        except InjectedCrash:
            trace.add("crash", {"at": crash_at})
            trace.write()
            raise

        if not outcome["ok"]:
            status = "failed" if outcome["conflict"] else "denied"
            trace.add("decision", {"status": status, "reason": outcome["reason"]})
            return finish(
                conn,
                shape="single",
                claim_id=claim_id,
                seed=seed,
                status=status,
                proposal_amount=proposal,
                budget=budget,
                trace=trace,
                error_reason=outcome["reason"],
            )

        trace.add("decision", {"status": "resolved"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="resolved",
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=None,
        )
    finally:
        conn.close()
