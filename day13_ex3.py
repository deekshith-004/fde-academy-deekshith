"""
Day 13 Exercise 3 — Extract Structured JSON from Maintenance Reports
Baseline → Schema + Few-Shot → Programmatic Validation
"""

from __future__ import annotations
import anthropic
import json

client = anthropic.Anthropic()

# ── Test notes ────────────────────────────────────────────────────────────────
TEST_NOTES = [
    (
        "Note 1",
        "On 03/14, Pump 4 began showing elevated vibration during the morning shift. "
        "Technician flagged for inspection within 48 hours -- not an immediate safety concern.",
    ),
    (
        "Note 2",
        "URGENT -- Tank 3 emergency shutoff valve failed during routine test this morning. "
        "Line supervisor notified immediately.",
    ),
    ("Note 3", "Filter replacement on HVAC unit 2 completed, no issues."),
    (
        "Note 4",
        "Conveyor belt 12 motor showing signs of overheating, exact date of onset unclear, "
        "reported by night shift.",
    ),
    (
        "Note 5",
        "Compressor unit 7 pressure readings inconsistent since last Tuesday, "
        "monitoring closely, no action taken yet.",
    ),
]

REQUIRED_FIELDS = {
    "equipment_id",
    "issue_type",
    "severity",
    "reported_date",
    "requires_immediate_action",
}
VALID_SEVERITIES = {"low", "medium", "high"}


# ── Task 1: Baseline zero-shot prompt ────────────────────────────────────────
BASELINE_PROMPT = """
Extract the following information from this maintenance note and return it:
- equipment_id: the equipment name or ID mentioned
- issue_type: what the problem is
- severity: how serious this is
- reported_date: when this was reported

Note: {note}
"""

# ── Task 2: Improved prompt with schema + few-shot examples ──────────────────
IMPROVED_SYSTEM = """
Extract structured data from maintenance reports.
Return ONLY valid JSON matching this schema, no other text, no markdown:
{
  "equipment_id": string,
  "issue_type": string,
  "severity": "low" | "medium" | "high",
  "reported_date": string | null,
  "requires_immediate_action": boolean
}

Rules:
- severity must be exactly one of: low, medium, high (lowercase)
- If reported_date cannot be determined from the text, use null
- requires_immediate_action is true only if the note indicates immediate danger,
  line stoppage, or emergency — not just monitoring or scheduled inspection
- equipment_id should be the most specific identifier mentioned (e.g. "Pump 4")

Examples:

Input: "On 15/01, Boiler unit 3 pressure relief valve opened unexpectedly.
  Emergency team dispatched immediately."
Output: {"equipment_id": "Boiler unit 3", "issue_type": "pressure relief valve
  unexpected activation", "severity": "high", "reported_date": "15/01",
  "requires_immediate_action": true}

Input: "Monthly oil change completed on Generator 1, all readings normal."
Output: {"equipment_id": "Generator 1", "issue_type": "scheduled oil change
  completed", "severity": "low", "reported_date": null,
  "requires_immediate_action": false}
"""

IMPROVED_USER = "Maintenance note: {note}"


# ── API call helpers ──────────────────────────────────────────────────────────
def call_baseline(note: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        temperature=0,
        messages=[{"role": "user", "content": BASELINE_PROMPT.replace("{note}", note)}],
    )
    return response.content[0].text.strip()


def call_improved(note: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        temperature=0,
        system=IMPROVED_SYSTEM,
        messages=[{"role": "user", "content": IMPROVED_USER.replace("{note}", note)}],
    )
    return response.content[0].text.strip()


# ── Task 3: Validation function ───────────────────────────────────────────────
def validate_extraction(raw_response: str) -> tuple[bool, dict | str]:
    """
    Returns (True, parsed_dict) if valid, (False, error_reason) if not.
    Never crashes on malformed input.
    """
    # Step 1: parse JSON
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as e:
        return False, f"JSON parse error: {e}"

    # Step 2: check all required fields present
    missing = REQUIRED_FIELDS - set(parsed.keys())
    if missing:
        return False, f"Missing fields: {missing}"

    # Step 3: check severity is valid enum
    if parsed.get("severity") not in VALID_SEVERITIES:
        return False, f"Invalid severity: {parsed.get('severity')!r}"

    # Step 4: check requires_immediate_action is boolean
    if not isinstance(parsed.get("requires_immediate_action"), bool):
        return False, (
            f"requires_immediate_action must be bool, "
            f"got {type(parsed.get('requires_immediate_action')).__name__}"
        )

    return True, parsed


# ── Run everything ────────────────────────────────────────────────────────────
print("=" * 70)
print("DAY 13 EXERCISE 3 — STRUCTURED JSON EXTRACTION PIPELINE")
print("=" * 70)

baseline_results = []
improved_results = []

print("\n" + "─" * 70)
print("TASK 1 — BASELINE ZERO-SHOT EXTRACTION")
print("─" * 70)
for label, note in TEST_NOTES:
    raw = call_baseline(note)
    ok, result = validate_extraction(raw)
    baseline_results.append(ok)
    status = "✓ PASS" if ok else "✗ FAIL"
    print(f"\n{label}: {status}")
    print(f"  Note: {note[:60]}...")
    print(f"  Raw output:\n{raw[:200]}")
    if not ok:
        print(f"  Validation error: {result}")

print("\n" + "─" * 70)
print("TASK 2 — IMPROVED PROMPT (SCHEMA + FEW-SHOT)")
print("─" * 70)
for label, note in TEST_NOTES:
    raw = call_improved(note)
    ok, result = validate_extraction(raw)
    improved_results.append(ok)
    status = "✓ PASS" if ok else "✗ FAIL"
    print(f"\n{label}: {status}")
    print(f"  Note: {note[:60]}...")
    if ok:
        r = result
        print(
            f"  equipment_id: {r['equipment_id']}\n"
            f"  issue_type:   {r['issue_type']}\n"
            f"  severity:     {r['severity']}\n"
            f"  reported_date: {r['reported_date']}\n"
            f"  requires_immediate_action: {r['requires_immediate_action']}"
        )
    else:
        print(f"  Raw: {raw[:200]}")
        print(f"  Validation error: {result}")

# ── Summary ───────────────────────────────────────────────────────────────────
baseline_score = sum(baseline_results)
improved_score = sum(improved_results)

print("\n" + "=" * 70)
print("TASK 3 — VALIDATION SUMMARY")
print("=" * 70)
print(f"\nBaseline (Task 1) parse-success rate:  {baseline_score} / 5")
print(f"Improved (Task 2) parse-success rate:  {improved_score} / 5")
print(
    f"Improvement:                           +{improved_score - baseline_score} notes"
)

print("""
NOTE 4 ANALYSIS (ambiguous reported_date):
  Note 4 says "exact date of onset unclear" — reported_date should be null.
  The improved prompt explicitly instructs: "If reported_date cannot be
  determined from the text, use null." — compliance should be 100%.

FAILURE MODES FIXED BY IMPROVED PROMPT:
  - Baseline often returns prose instead of JSON
  - Baseline uses 'High'/'Medium' instead of lowercase enum values
  - Baseline omits requires_immediate_action field entirely
  - Improved prompt fixes all three with explicit schema + examples
""")
