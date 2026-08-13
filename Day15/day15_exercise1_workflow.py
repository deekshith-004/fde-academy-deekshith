"""
Day 15 Exercise 1 — Build a 3-Step AI Workflow: Classify → Extract → Summarize
Uses Anthropic Claude (ANTHROPIC_API_KEY required)
"""
from __future__ import annotations
from typing import TypedDict
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

# ── WHERE API KEY IS USED ─────────────────────────────────────────────────────
# Claude is used as the LLM for ALL three chains:
#   1. classify_chain  → decides URGENT or ROUTINED
#   2. extract_chain   → pulls account/ticket ID from urgent complaints
#   3. summarize_chain → writes one-line summary for routine complaints
# Every chain invokes Claude via the Anthropic API.
# ─────────────────────────────────────────────────────────────────────────────

model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

# ── Test complaints ───────────────────────────────────────────────────────────
TEST_COMPLAINTS = [
    "Account #48213 - My internet has been down for 6 hours and I work "
    "from home. This is costing me money. Fix this NOW.",

    "Ticket #9042 - Billing seems slightly higher this month than usual, "
    "could someone check when convenient? No rush.",

    "Account #77410 - Complete outage across my whole building, multiple "
    "neighbors affected, please escalate immediately.",

    "Just wanted to say the new app update looks nice. Ticket #201.",
]

# ─── TASK 1: BUILD 3 INDEPENDENT CHAINS ──────────────────────────────────────
print("=" * 65)
print("TASK 1 — BUILD 3 INDEPENDENT CHAINS")
print("=" * 65)

# Chain 1: Classify
classify_prompt = ChatPromptTemplate.from_template("""
You are a telecom customer complaint classifier.
Classify the complaint below as exactly one of:
  URGENT   — service outage, immediate financial loss, safety issue,
              or customer explicitly demands immediate action
  ROUTINE  — billing queries, general feedback, non-urgent requests,
              positive comments

Return ONLY the single word URGENT or ROUTINE. No other text.

Complaint: {complaint}
""")
classify_chain = classify_prompt | model | StrOutputParser()

# Chain 2: Extract account/ticket ID
extract_prompt = ChatPromptTemplate.from_template("""
Extract the account or ticket ID from the complaint below.
Look for patterns like 'Account #12345', 'Ticket #9042', 'Ref: TCK-001'.
Return ONLY the ID (e.g. '#48213' or 'TCK-9042'). 
If no ID is present, return 'NOT_FOUND'. No other text.

Complaint: {complaint}
""")
extract_chain = extract_prompt | model | StrOutputParser()

# Chain 3: Summarize
summarize_prompt = ChatPromptTemplate.from_template("""
Write a single sentence summary of this customer complaint suitable
for a support agent's queue. Be factual and neutral. Max 20 words.

Complaint: {complaint}
""")
summarize_chain = summarize_prompt | model | StrOutputParser()

# Test each chain individually
print("\nTesting classify_chain:")
for i, c in enumerate(TEST_COMPLAINTS, 1):
    result = classify_chain.invoke({"complaint": c})
    print(f"  Complaint {i}: {result}")

print("\nTesting extract_chain (on urgents 1 & 3):")
for i in [0, 2]:
    result = extract_chain.invoke({"complaint": TEST_COMPLAINTS[i]})
    print(f"  Complaint {i+1}: {result}")

print("\nTesting summarize_chain (on routines 2 & 4):")
for i in [1, 3]:
    result = summarize_chain.invoke({"complaint": TEST_COMPLAINTS[i]})
    print(f"  Complaint {i+1}: {result}")

# ─── TASK 2: COMPOSE THE LANGGRAPH WORKFLOW ───────────────────────────────────
print("\n" + "=" * 65)
print("TASK 2 — COMPOSE THE LANGGRAPH WORKFLOW")
print("=" * 65)

class ComplaintState(TypedDict):
    complaint: str
    classification: str
    account_id: str
    summary: str

def classify_node(state: ComplaintState) -> ComplaintState:
    """Node 1: Classify complaint as URGENT or ROUTINE."""
    classification = classify_chain.invoke({"complaint": state["complaint"]})
    return {**state, "classification": classification.strip().upper()}

def extract_node(state: ComplaintState) -> ComplaintState:
    """Node 2: Extract account/ticket ID (URGENT path only)."""
    account_id = extract_chain.invoke({"complaint": state["complaint"]})
    return {**state, "account_id": account_id.strip()}

def summarize_node(state: ComplaintState) -> ComplaintState:
    """Node 3: One-line summary (ROUTINE path only)."""
    summary = summarize_chain.invoke({"complaint": state["complaint"]})
    return {**state, "summary": summary.strip()}

def route_after_classify(state: ComplaintState) -> str:
    """Router: send URGENT to extract, ROUTINE to summarize."""
    if "URGENT" in state.get("classification", ""):
        return "extract"
    return "summarize"

# Build the graph
graph = StateGraph(ComplaintState)
graph.add_node("classify", classify_node)
graph.add_node("extract", extract_node)
graph.add_node("summarize", summarize_node)

graph.set_entry_point("classify")
graph.add_conditional_edges(
    "classify",
    route_after_classify,
    {"extract": "extract", "summarize": "summarize"},
)
graph.add_edge("extract", END)
graph.add_edge("summarize", END)

app = graph.compile()
print("✓ LangGraph workflow compiled successfully")

# ─── TASK 3: RUN ALL 4 COMPLAINTS ────────────────────────────────────────────
print("\n" + "=" * 65)
print("TASK 3 — RUN AND TRACE ALL 4 COMPLAINTS")
print("=" * 65)

initial_state: ComplaintState = {
    "complaint": "", "classification": "",
    "account_id": "", "summary": ""
}

for i, complaint in enumerate(TEST_COMPLAINTS, 1):
    print(f"\nComplaint {i}: {complaint[:60]}...")
    state = {**initial_state, "complaint": complaint}
    result = app.invoke(state)
    print(f"  classification: {result['classification']}")
    print(f"  account_id:     {result['account_id'] or '(not extracted)'}")
    print(f"  summary:        {result['summary'] or '(not generated)'}")

print("""
EXPECTED:
  Complaint 1 → URGENT  | account_id: #48213  | summary: (empty)
  Complaint 2 → ROUTINE | account_id: (empty) | summary: one-line summary
  Complaint 3 → URGENT  | account_id: #77410  | summary: (empty)
  Complaint 4 → ROUTINE | account_id: (empty) | summary: one-line summary
""")