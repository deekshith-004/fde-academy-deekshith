"""
Day 15 Exercise 2 — Add a Human Approval Step to a Work Order Workflow
Uses Anthropic Claude (ANTHROPIC_API_KEY required)
WHERE: Claude generates the proposed_work_order text in propose_work_order_node
WHY: The AI drafts a structured work order from the complaint context —
     this is the step a supervisor reviews before dispatch.
"""
from __future__ import annotations
from typing import TypedDict
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

# Reuse chains from Exercise 1
classify_prompt = ChatPromptTemplate.from_template("""
Classify the complaint below as exactly URGENT or ROUTINE.
Return ONLY the single word. No other text.
Complaint: {complaint}
""")
classify_chain = classify_prompt | model | StrOutputParser()

extract_prompt = ChatPromptTemplate.from_template("""
Extract the account or ticket ID from the complaint.
Return ONLY the ID. If not present return 'NOT_FOUND'. No other text.
Complaint: {complaint}
""")
extract_chain = extract_prompt | model | StrOutputParser()

summarize_prompt = ChatPromptTemplate.from_template("""
Write a single sentence summary (max 20 words) for a support agent's queue.
Complaint: {complaint}
""")
summarize_chain = summarize_prompt | model | StrOutputParser()

# ── TASK 1: EXTENDED STATE + WORK ORDER NODE ──────────────────────────────────
print("=" * 65)
print("TASK 1 — EXTENDED STATE AND WORK ORDER NODE")
print("=" * 65)

class ComplaintState(TypedDict):
    complaint: str
    classification: str
    account_id: str
    summary: str
    proposed_work_order: str   # NEW
    status: str                # NEW

work_order_prompt = ChatPromptTemplate.from_template("""
You are a field operations coordinator at a telecom company.
Draft a brief work order (2-3 sentences) for a field technician based on:
- Account ID: {account_id}
- Customer complaint: {complaint}
- Priority: URGENT

Include: what needs to happen, for which account, at what priority.
Be specific and action-oriented. No more than 3 sentences.
""")
work_order_chain = work_order_prompt | model | StrOutputParser()

def classify_node(state: ComplaintState) -> ComplaintState:
    classification = classify_chain.invoke({"complaint": state["complaint"]})
    return {**state, "classification": classification.strip().upper()}

def extract_node(state: ComplaintState) -> ComplaintState:
    account_id = extract_chain.invoke({"complaint": state["complaint"]})
    return {**state, "account_id": account_id.strip()}

def summarize_node(state: ComplaintState) -> ComplaintState:
    summary = summarize_chain.invoke({"complaint": state["complaint"]})
    return {**state, "summary": summary.strip()}

def propose_work_order_node(state: ComplaintState) -> ComplaintState:
    """Generate AI-drafted work order and set status to pending_approval."""
    work_order = work_order_chain.invoke({
        "account_id": state.get("account_id", "UNKNOWN"),
        "complaint": state["complaint"],
    })
    return {
        **state,
        "proposed_work_order": work_order.strip(),
        "status": "pending_approval",
    }

def dispatch_node(state: ComplaintState) -> ComplaintState:
    """Only reached after human approval — sets status to dispatched."""
    print(f"\n  ✓ DISPATCHING work order for account {state.get('account_id')}")
    print(f"  Work order: {state.get('proposed_work_order')[:100]}...")
    return {**state, "status": "dispatched"}

def route_after_classify(state: ComplaintState) -> str:
    if "URGENT" in state.get("classification", ""):
        return "extract"
    return "summarize"

# ─── TASK 2: WIRE THE INTERRUPT ───────────────────────────────────────────────
print("\n" + "=" * 65)
print("TASK 2 — WIRE THE INTERRUPT")
print("=" * 65)

graph = StateGraph(ComplaintState)
graph.add_node("classify", classify_node)
graph.add_node("extract", extract_node)
graph.add_node("summarize", summarize_node)
graph.add_node("propose_work_order", propose_work_order_node)
graph.add_node("dispatch", dispatch_node)

graph.set_entry_point("classify")
graph.add_conditional_edges(
    "classify",
    route_after_classify,
    {"extract": "extract", "summarize": "summarize"},
)
graph.add_edge("extract", "propose_work_order")
graph.add_edge("propose_work_order", "dispatch")
graph.add_edge("dispatch", END)
graph.add_edge("summarize", END)

# Compile WITH checkpointer and interrupt BEFORE dispatch
checkpointer = MemorySaver()
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["dispatch"],   # ← PAUSES here for human review
)
print("✓ Graph compiled with MemorySaver checkpointer")
print("✓ interrupt_before=['dispatch'] — graph pauses before dispatching")

# Run with urgent complaint
URGENT_COMPLAINT = (
    "Account #48213 - My internet has been down for 6 hours and I work "
    "from home. This is costing me money. Fix this NOW."
)
config = {"configurable": {"thread_id": "complaint-001"}}

initial_state: ComplaintState = {
    "complaint": URGENT_COMPLAINT,
    "classification": "", "account_id": "",
    "summary": "", "proposed_work_order": "", "status": "",
}

print(f"\nRunning urgent complaint through graph...")
print(f"Complaint: {URGENT_COMPLAINT[:60]}...")

# First invoke — will PAUSE before dispatch
result = app.invoke(initial_state, config=config)

print(f"\nAfter first invoke (paused before dispatch):")
print(f"  classification:       {result['classification']}")
print(f"  account_id:           {result['account_id']}")
print(f"  status:               {result['status']}")
print(f"  proposed_work_order:  {result['proposed_work_order'][:150]}...")

# ─── TASK 3: SIMULATE APPROVAL AND RESUME ────────────────────────────────────
print("\n" + "=" * 65)
print("TASK 3 — SIMULATE HUMAN APPROVAL AND RESUME")
print("=" * 65)

# Simulate supervisor reviewing
current_state = app.get_state(config)
print("\n--- SUPERVISOR REVIEW ---")
print(f"Proposed Work Order:\n{current_state.values['proposed_work_order']}")
print(f"\nStatus: {current_state.values['status']}")

# Simulate approval decision
supervisor_decision = input("\nApprove this work order? (yes/no): ").strip().lower()

if supervisor_decision == "yes":
    print("\nSupervisor APPROVED. Resuming graph...")
    # Resume by invoking with None — continues from checkpoint
    final_result = app.invoke(None, config=config)
    print(f"\nFinal state:")
    print(f"  status:     {final_result['status']}")
    print(f"  account_id: {final_result['account_id']}")
    assert final_result["status"] == "dispatched", "Expected status=dispatched"
    print("\n✓ Work order successfully dispatched!")
else:
    print("\nSupervisor REJECTED. Work order NOT dispatched.")
    print("(In a full implementation, rejection would route back for revision)")

print("""
EXPECTED BEHAVIOUR:
  First invoke()  → status = 'pending_approval', proposed_work_order populated
  Graph PAUSES    → supervisor sees work order for review
  Resume (None)   → status = 'dispatched', dispatch_node executes
""")