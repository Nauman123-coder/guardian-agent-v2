from __future__ import annotations
import json, os, re, time, uuid
from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import AgentState
from app.agent.prompts import ANALYZER_SYSTEM_PROMPT, INVESTIGATOR_SYSTEM_PROMPT, MITIGATOR_SYSTEM_PROMPT
from app.tools.threat_intel import bulk_investigate
from app.tools.sys_actions import execute_action, send_alert


def _now(): return datetime.now(timezone.utc).isoformat()


def _build_llm():
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=2048, temperature=0)
    elif os.getenv("GROQ_API_KEY"):
        from langchain_groq import ChatGroq
        return ChatGroq(model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), max_tokens=2048, temperature=0)
    elif os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o", max_tokens=2048, temperature=0)
    raise EnvironmentError("No LLM API key found. Set GROQ_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY.")


def _parse(text):
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return {}


def _emit(state, event_type, data):
    return [{"type": event_type, "timestamp": _now(), "incident_id": state.get("incident_id", ""), **data}]


def _persist(state):
    try:
        from app.memory.store import save_incident
        save_incident(dict(state))
    except Exception as e:
        print(f"  ⚠️  Persist error: {e}")


def _base(state):
    """Echo all identity fields so LangGraph keeps them across every node."""
    return {
        "incident_id":      state.get("incident_id", ""),
        "log_source":       state.get("log_source", "unknown"),
        "raw_log":          state.get("raw_log", ""),
        "started_at":       state.get("started_at", _now()),
        "completed_at":     state.get("completed_at", ""),
        "approval_token":   state.get("approval_token", ""),
        "approval_decision":state.get("approval_decision", "pending"),
        "mitigation_plan":  state.get("mitigation_plan", ""),
        "executed_actions": state.get("executed_actions", []),
        "investigation_results": state.get("investigation_results", []),
        "found_indicators": state.get("found_indicators", []),
        "risk_score":       state.get("risk_score", 0),
        "requires_approval":state.get("requires_approval", False),
    }


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def analyzer_node(state):
    iid = state.get("incident_id", "?")
    print(f"\n🔍 [ANALYZER] incident={iid[:8]}")
    llm = _build_llm()
    response = llm.invoke([
        SystemMessage(content=ANALYZER_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze this security log:\n\n{state['raw_log']}"),
    ])
    parsed = _parse(response.content)
    risk_score = int(parsed.get("risk_score", 0))
    found_indicators = parsed.get("found_indicators", [])
    threat_summary = parsed.get("threat_summary", "No summary provided.")
    print(f"  📊 Risk Score: {risk_score}/10  |  Indicators: {found_indicators}")

    update = {
        **_base(state),
        "messages": [AIMessage(content=f"**Analysis** (Risk: {risk_score}/10)\n\n{threat_summary}")],
        "risk_score": risk_score,
        "found_indicators": found_indicators,
        "current_node": "analyzer",
        "status": "analyzing",
        "stream_events": _emit(state, "analyzer_complete", {
            "risk_score": risk_score,
            "found_indicators": found_indicators,
            "threat_summary": threat_summary,
        }),
    }
    _persist({**state, **update})
    return update


def investigator_node(state):
    iid = state.get("incident_id", "?")
    print(f"\n🕵️  [INVESTIGATOR] incident={iid[:8]}")
    llm = _build_llm()
    indicators = state.get("found_indicators", [])
    ti_results = bulk_investigate(indicators) if indicators else []

    for r in ti_results:
        print(f"  {'🔴 MALICIOUS' if r.get('is_malicious') else '🟢 Clean'} | {r.get('indicator','?')}")

    if indicators and ti_results:
        response = llm.invoke([
            SystemMessage(content=INVESTIGATOR_SYSTEM_PROMPT),
            HumanMessage(content=f"Original risk: {state['risk_score']}/10\nIndicators: {indicators}\nTI:\n{json.dumps(ti_results, indent=2)}"),
        ])
        parsed = _parse(response.content)
        updated_score = int(parsed.get("updated_risk_score", state["risk_score"]))
        threat_context = parsed.get("threat_context", "")
        confidence = parsed.get("confidence", "MEDIUM")
    else:
        updated_score = state["risk_score"]
        threat_context = "No indicators to investigate."
        confidence = "LOW"

    update = {
        **_base(state),
        "messages": [AIMessage(content=f"**TI Complete** Risk: {updated_score}/10 ({confidence})\n\n{threat_context}")],
        "risk_score": updated_score,
        "investigation_results": ti_results,
        "current_node": "investigator",
        "stream_events": _emit(state, "investigator_complete", {
            "updated_risk_score": updated_score,
            "confidence": confidence,
            "ti_results": ti_results,
        }),
    }
    _persist({**state, **update})
    return update


def mitigator_node(state):
    iid = state.get("incident_id", "?")
    print(f"\n🛡️  [MITIGATOR] incident={iid[:8]}")
    llm = _build_llm()
    response = llm.invoke([
        SystemMessage(content=MITIGATOR_SYSTEM_PROMPT),
        HumanMessage(content=f"Risk: {state['risk_score']}/10\nIndicators: {state['found_indicators']}\nTI: {json.dumps(state.get('investigation_results',[]))}\nLog:\n{state['raw_log']}"),
    ])
    parsed = _parse(response.content)
    mitigation_plan = parsed.get("mitigation_plan", "No plan generated.")
    actions = parsed.get("actions", [])
    requires_approval = state["risk_score"] > 7
    approval_token = str(uuid.uuid4()) if requires_approval else ""
    full_plan = f"{mitigation_plan}\n\n__ACTIONS__\n{json.dumps(actions)}"
    status = "awaiting_approval" if requires_approval else "executing"
    print(f"  🔐 Requires approval: {requires_approval}  |  Actions: {len(actions)}")

    update = {
        **_base(state),
        "messages": [AIMessage(content=f"**Mitigation Plan**\n\n{mitigation_plan}")],
        "mitigation_plan": full_plan,
        "requires_approval": requires_approval,
        "approval_token": approval_token,
        "approval_decision": "pending" if requires_approval else "auto_approved",
        "current_node": "mitigator",
        "status": status,
        "stream_events": _emit(state, "mitigator_complete", {
            "mitigation_plan": mitigation_plan,
            "actions": actions,
            "requires_approval": requires_approval,
            "approval_token": approval_token,
        }),
    }
    _persist({**state, **update})
    return update


def _poll_for_web_approval(incident_id, timeout=3600):
    from app.memory.store import get_incident
    deadline = time.time() + timeout
    while time.time() < deadline:
        inc = get_incident(incident_id)
        if inc:
            decision = inc.get("approval_decision", "pending")
            if decision == "approved": return True
            if decision == "denied": return False
        time.sleep(2)
    print("  ⏰ Approval timeout — defaulting to DENIED")
    return False


def human_approval_node(state):
    iid = state.get("incident_id", "?")
    print(f"\n⚠️  [HITL] Waiting for approval — incident={iid[:8]}")

    if os.getenv("GUARDIAN_AUTO_APPROVE", "").lower() in ("true", "1", "yes"):
        approved = True
        print("  ✅ AUTO-APPROVED")
    elif os.getenv("GUARDIAN_MODE", "cli") == "web":
        approved = _poll_for_web_approval(iid)
    else:
        plan_text = state.get("mitigation_plan", "")
        display_plan = plan_text.split("__ACTIONS__\n")[0] if "__ACTIONS__" in plan_text else plan_text
        actions = json.loads(plan_text.split("__ACTIONS__\n")[1]) if "__ACTIONS__" in plan_text else []
        print("=" * 60)
        print(f"Risk: {state['risk_score']}/10 | Indicators: {state['found_indicators']}")
        print(f"\nPlan:\n{display_plan}")
        for i, a in enumerate(actions, 1):
            print(f"  {i}. [{a.get('urgency')}] {a.get('action_type')} → {a.get('target')}")
        print("=" * 60)
        while True:
            ans = input("  Approve? [yes/no/abort]: ").strip().lower()
            if ans in ("yes", "y"): approved = True; break
            elif ans in ("no", "n"): approved = False; break
            elif ans in ("abort", "a"): raise SystemExit("Aborted.")

    update = {
        **_base(state),
        "messages": [HumanMessage(content="APPROVED" if approved else "DENIED")],
        "requires_approval": not approved,
        "approval_decision": "approved" if approved else "denied",
        "current_node": "human_approval",
        "stream_events": _emit(state, "approval_decision", {"approved": approved}),
    }
    _persist({**state, **update})
    return update


def executor_node(state):
    iid = state.get("incident_id", "?")
    print(f"\n⚡ [EXECUTOR] incident={iid[:8]}")
    plan_text = state.get("mitigation_plan", "")
    actions = json.loads(plan_text.split("__ACTIONS__\n")[1]) if "__ACTIONS__" in plan_text else []

    if state.get("requires_approval", False):
        send_alert.invoke({"severity": "HIGH", "title": "Threat — manual review required",
                           "description": plan_text[:500], "indicators": state.get("found_indicators", [])})
        update = {
            **_base(state),
            "messages": [AIMessage(content="Actions blocked by operator.")],
            "executed_actions": ["alert_only (denied)"],
            "current_node": "executor", "status": "complete", "completed_at": _now(),
            "stream_events": _emit(state, "executor_complete", {"executed_actions": ["alert_only (denied)"]}),
        }
        _persist({**state, **update})
        return update

    executed = []
    for action in actions:
        atype = action.get("action_type", "")
        target = action.get("target", "")
        just = action.get("justification", "")
        if not atype or not target: continue
        print(f"  ▶️  {atype} → {target}")
        if atype == "block_ip":        result = execute_action("block_ip", ip_address=target, reason=just)
        elif atype == "block_hash":    result = execute_action("block_hash", file_hash=target, threat_name=just)
        elif atype == "disable_user":  result = execute_action("disable_user", username=target, reason=just)
        elif atype == "isolate_host":  result = execute_action("isolate_host", hostname=target, reason=just)
        else:                          result = send_alert.invoke({"severity": "HIGH", "title": f"Guardian: {atype}", "description": just, "indicators": [target]})
        executed.append(f"{atype}:{target} → {result.get('status','?')}")

    send_alert.invoke({"severity": "HIGH" if state["risk_score"] >= 7 else "MEDIUM",
                       "title": f"Incident Complete (Risk: {state['risk_score']}/10)",
                       "description": f"Executed {len(executed)} actions.",
                       "indicators": state.get("found_indicators", [])})

    update = {
        **_base(state),
        "messages": [AIMessage(content=f"Executed: {executed}")],
        "executed_actions": executed,
        "current_node": "executor", "status": "complete", "completed_at": _now(),
        "stream_events": _emit(state, "executor_complete", {"executed_actions": executed}),
    }
    _persist({**state, **update})
    return update


def report_node(state):
    iid = state.get("incident_id", "?")
    plan_text = state.get("mitigation_plan", "")
    display_plan = plan_text.split("__ACTIONS__\n")[0] if "__ACTIONS__" in plan_text else plan_text
    report = (f"\n{'='*70}\n  GUARDIAN — INCIDENT {iid}\n{'='*70}\n"
              f"  Risk   : {state.get('risk_score',0)}/10\n"
              f"  IOCs   : {state.get('found_indicators',[])}\n"
              f"\n--- PLAN ---\n{display_plan}\n\n--- ACTIONS ---\n")
    for a in state.get("executed_actions", []):
        report += f"  ✓ {a}\n"
    report += f"{'='*70}"
    print(report)

    update = {
        **_base(state),
        "messages": [AIMessage(content=report)],
        "current_node": "report", "status": "complete", "completed_at": _now(),
        "stream_events": _emit(state, "incident_complete", {"report": report}),
    }
    _persist({**state, **update})
    return update


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def route_after_mitigator(state) -> Literal["human_approval", "executor"]:
    return "human_approval" if state.get("requires_approval") else "executor"

def route_after_approval(state) -> Literal["executor"]:
    return "executor"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(checkpointer=None):
    builder = StateGraph(AgentState)
    builder.add_node("analyzer", analyzer_node)
    builder.add_node("investigator", investigator_node)
    builder.add_node("mitigator", mitigator_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("executor", executor_node)
    builder.add_node("report", report_node)
    builder.set_entry_point("analyzer")
    builder.add_edge("analyzer", "investigator")
    builder.add_edge("investigator", "mitigator")
    builder.add_conditional_edges("mitigator", route_after_mitigator,
        {"human_approval": "human_approval", "executor": "executor"})
    builder.add_conditional_edges("human_approval", route_after_approval,
        {"executor": "executor"})
    builder.add_edge("executor", "report")
    builder.add_edge("report", END)
    return builder.compile(checkpointer=checkpointer or MemorySaver())