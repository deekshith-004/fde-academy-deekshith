"""
Day 13 Exercise 2 — Build a Prompt Template Library
3 enterprise use cases: executive summary, work order classifier,
banking compliance QA
"""

from __future__ import annotations
import anthropic
import json

client = anthropic.Anthropic()

# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE 1 — Executive Summary Generator (provided worked example)
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATE_1 = {
    "name": "executive_summary_generator",
    "pattern": "Role prompting + constraint prompting",
    "system": (
        "You are an operations analyst preparing a brief for a "
        "time-constrained executive. Write exactly 3 sentences: "
        "one on overall performance, one on the single biggest risk, "
        "one on a recommended next action. No jargon, no bullet points."
    ),
    "user": "Dashboard data: {dashboard_metrics}",
    "parameters": {"dashboard_metrics": "raw KPI figures as text or JSON"},
    "known_limitation": "Struggles if more than 8 metrics are provided at once.",
}

# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE 2 — Work Order Priority Classifier
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATE_2 = {
    "name": "work_order_priority_classifier",
    "pattern": "Role prompting + structured output + few-shot",
    "system": (
        "You are a maintenance operations manager at an industrial facility. "
        "Your job is to classify incoming work orders so the right team is "
        "dispatched with the right urgency. A wrong CRITICAL classification "
        "wastes emergency resources; a missed CRITICAL classification risks "
        "injury or production shutdown.\n\n"
        "Classify each work order as LOW, MEDIUM, HIGH, or CRITICAL.\n\n"
        "Classification rules:\n"
        "  LOW      — routine maintenance, no operational impact\n"
        "  MEDIUM   — needs attention within 48 hours, minor impact\n"
        "  HIGH     — needs attention within 4 hours, significant impact\n"
        "  CRITICAL — immediate action required, safety risk or line down\n\n"
        "Examples:\n"
        "Work order: 'Replace worn drive belt on packaging line 2, machine "
        "still operational but belt showing fraying.'\n"
        '{"priority": "HIGH", "reason": "Fraying belt poses imminent '
        'failure risk that would stop the packaging line.", '
        '"dispatch_team": "mechanical"}\n\n'
        "Work order: 'Monthly lubrication of conveyor bearings — Line 4.'\n"
        '{"priority": "LOW", "reason": "Scheduled preventive maintenance '
        'with no current issue reported.", '
        '"dispatch_team": "maintenance"}\n\n'
        "Return ONLY valid JSON with no other text:\n"
        '{"priority": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL", '
        '"reason": "one sentence", '
        '"dispatch_team": "mechanical" | "electrical" | '
        '"safety" | "maintenance"}'
    ),
    "user": "Work order: {work_order_text}",
    "parameters": {
        "work_order_text": "free-text work order description from the client system"
    },
    "known_limitation": (
        "May over-classify ambiguous notes as HIGH when safety keywords "
        "appear in routine context. Human review recommended for all CRITICAL "
        "classifications before dispatching emergency team."
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE 3 — Banking Compliance Policy QA (Banking & Financial Services)
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATE_3 = {
    "name": "compliance_policy_qa",
    "pattern": "Role prompting + RAG grounding + structured output + constraint",
    "system": (
        "You are a compliance officer assistant at a regulated Indian bank. "
        "Your role is to answer employee questions about internal compliance "
        "policy using ONLY the policy excerpts provided in the user message. "
        "Do not use general knowledge or training data to supplement your answer — "
        "if the provided excerpts do not contain sufficient information to answer "
        "the question, say so explicitly.\n\n"
        "Return ONLY valid JSON with no other text:\n"
        "{\n"
        '  "answer": "direct answer in plain English, 2-3 sentences max",\n'
        '  "confidence": "high" | "medium" | "low",\n'
        '  "source_clause": "document name and clause number if identifiable, '
        'else null",\n'
        '  "requires_legal_review": true | false\n'
        "}\n\n"
        "Set requires_legal_review to true if the question involves a regulatory "
        "filing, penalty risk, or interpretation of an RBI circular."
    ),
    "user": (
        "Policy excerpts:\n{policy_excerpts}\n\nEmployee question: {employee_question}"
    ),
    "parameters": {
        "policy_excerpts": (
            "relevant sections retrieved from the policy corpus via RAG — "
            "passed as plain text with document name and clause number as header"
        ),
        "employee_question": "natural-language question from a bank employee",
    },
    "known_limitation": (
        "Answers are only as good as the retrieved excerpts — "
        "if the RAG retrieval misses the relevant clause, the model will "
        "correctly say it cannot answer, but the employee may incorrectly "
        "assume the policy does not address their question. "
        "Retrieval quality must be validated separately."
    ),
}

ALL_TEMPLATES = [TEMPLATE_1, TEMPLATE_2, TEMPLATE_3]


def call_template(template: dict, **kwargs) -> str:
    """Fill template parameters and call Claude."""
    user_msg = template["user"]
    for key, val in kwargs.items():
        user_msg = user_msg.replace("{" + key + "}", str(val))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        temperature=0,
        system=template["system"],
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text.strip()


# ── Test all 3 templates ──────────────────────────────────────────────────────
print("=" * 70)
print("DAY 13 EXERCISE 2 — PROMPT TEMPLATE LIBRARY")
print("=" * 70)

# Template 1 test
print("\n" + "─" * 70)
print("TEMPLATE 1: executive_summary_generator")
print("─" * 70)
metrics = (
    "On-time delivery rate: 76% (target 90%). "
    "Average freight cost: ₹271 (up 8% vs last month). "
    "Delayed shipments: 23% of total. "
    "Top delayed carrier: FEDEX (32% delay rate). "
    "High-cost outliers flagged: 11 shipments."
)
result1 = call_template(TEMPLATE_1, dashboard_metrics=metrics)
print(f"Input metrics: {metrics[:80]}...")
print(f"\nOutput:\n{result1}")

# Template 2 tests
print("\n" + "─" * 70)
print("TEMPLATE 2: work_order_priority_classifier")
print("─" * 70)
test_orders = [
    "Emergency shutoff valve on Tank 3 failed during safety test this morning. "
    "Line supervisor on site.",
    "Quarterly inspection of fire suppression system in Warehouse B — "
    "all checks passed, logging for records.",
]
for order in test_orders:
    result = call_template(TEMPLATE_2, work_order_text=order)
    print(f"\nWork order: {order[:70]}...")
    try:
        parsed = json.loads(result)
        print(
            f"Priority: {parsed['priority']} | "
            f"Team: {parsed['dispatch_team']}\n"
            f"Reason: {parsed['reason']}"
        )
    except json.JSONDecodeError:
        print(f"Raw output: {result}")

# Template 3 tests
print("\n" + "─" * 70)
print("TEMPLATE 3: compliance_policy_qa")
print("─" * 70)
policy_excerpt = (
    "[RBI Circular RBI/2024-25/47, Clause 3.2] "
    "All wire transfers exceeding ₹50 lakh to a first-time beneficiary "
    "must be reviewed by a relationship manager before release. "
    "The review must be completed within 2 business hours of initiation."
)
question = (
    "Can I approve a ₹60 lakh wire transfer to a new vendor if my manager is on leave?"
)
result3 = call_template(
    TEMPLATE_3, policy_excerpts=policy_excerpt, employee_question=question
)
print(f"\nPolicy excerpt: {policy_excerpt[:80]}...")
print(f"Question: {question}")
try:
    parsed = json.loads(result3)
    print(f"\nAnswer: {parsed['answer']}")
    print(f"Confidence: {parsed['confidence']}")
    print(f"Source: {parsed['source_clause']}")
    print(f"Requires legal review: {parsed['requires_legal_review']}")
except json.JSONDecodeError:
    print(f"Raw output: {result3}")

# ── Print full template library documentation ─────────────────────────────────
print("\n" + "=" * 70)
print("FULL TEMPLATE LIBRARY DOCUMENTATION")
print("=" * 70)
for t in ALL_TEMPLATES:
    print(f"\nTEMPLATE NAME: {t['name']}")
    print(f"PATTERN USED:  {t['pattern']}")
    print(f"PARAMETERS:    {list(t['parameters'].keys())}")
    print(f"KNOWN LIMITATION: {t['known_limitation']}")
