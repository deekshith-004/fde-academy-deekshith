"""
Day 15 Exercise 3 — Implement Retry Logic and Fallback Prompts
Uses Anthropic Claude (ANTHROPIC_API_KEY required)
WHERE: Claude is called in extract_chain (primary) and fallback_extract_chain
WHY:  The primary prompt extracts IDs from clean text.
      The fallback prompt uses stricter instructions when the primary fails.
      Claude is called up to 3 times per complaint via retry logic.
"""
from __future__ import annotations
import time
import re
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

# Original extract chain from Exercise 1
extract_prompt = ChatPromptTemplate.from_template("""
Extract the account or ticket ID from the complaint below.
Look for patterns like 'Account #12345', 'Ticket #9042', 'Ref: TCK-001'.
Return ONLY the ID. If no ID is present, return 'NOT_FOUND'. No other text.

Complaint: {complaint}
""")
extract_chain = extract_prompt | model | StrOutputParser()

# ─── TASK 1: MESSY TEST INPUTS ───────────────────────────────────────────────
print("=" * 65)
print("TASK 1 — MESSY COMPLAINTS (ORIGINAL CHAIN BASELINE)")
print("=" * 65)

MESSY_COMPLAINTS = [
    # No clean format — just a reference to 'acct'
    "my service acct is acting up again this is like the third time",
    # Non-standard format: TCK- prefix with dash
    "Ref: TCK-9042-B / urgent pls advise re: outage",
    # ID buried in noise, informal writing
    "hey its me again acct 77410 still broken since yesterday morning",
    # No ID at all — tests NOT_FOUND path
    "your service is terrible and I want to cancel everything immediately",
]

print("\nRunning ORIGINAL extract_chain on messy complaints:")
original_results = []
for i, complaint in enumerate(MESSY_COMPLAINTS, 1):
    result = extract_chain.invoke({"complaint": complaint})
    original_results.append(result.strip())
    print(f"  Complaint {i}: '{result.strip()}'  ← {'OK' if result.strip() != 'NOT_FOUND' and len(result.strip()) > 2 else 'FAILED/NOT_FOUND'}")
    print(f"             Input: {complaint[:60]}...")


# ─── TASK 2: RETRY WRAPPER WITH VALIDATION ───────────────────────────────────
print("\n" + "=" * 65)
print("TASK 2 — RETRY WRAPPER WITH VALIDATION")
print("=" * 65)

def is_valid_id(extracted_text: str) -> bool:
    """
    Returns True only if extracted_text looks like a real ID.
    Rules:
    - Must contain at least 3 consecutive digits, OR
    - Must match pattern like TCK-NNNN or similar reference code
    - Must NOT be 'NOT_FOUND' or empty
    - Must be reasonably short (< 30 chars) — long text = hallucination
    """
    text = extracted_text.strip()
    if not text or text.upper() == "NOT_FOUND":
        return False
    if len(text) > 30:
        return False
    # Must contain digits or a known reference prefix
    has_digits = bool(re.search(r'\d{3,}', text))
    has_ref_prefix = bool(re.search(r'(TCK|ACT|REF|TKT|ACCT)[-#]?\w+', text, re.IGNORECASE))
    return has_digits or has_ref_prefix

def extract_with_retry(complaint: str, max_attempts: int = 3) -> str | None:
    """
    Retry extraction up to max_attempts times with exponential backoff.
    Returns the extracted ID if valid, None if all attempts fail.
    """
    for attempt in range(1, max_attempts + 1):
        result = extract_chain.invoke({"complaint": complaint})
        result = result.strip()

        if is_valid_id(result):
            if attempt > 1:
                print(f"    → Succeeded on attempt {attempt}")
            return result
        else:
            if attempt < max_attempts:
                wait = 2 ** attempt
                print(f"    → Attempt {attempt} returned '{result}' (invalid). "
                      f"Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"    → Attempt {attempt} returned '{result}' (invalid). "
                      f"All attempts exhausted.")
    return None   # Signal: no valid extraction found

print("\nRunning retry wrapper on messy complaints:")
retry_results = []
for i, complaint in enumerate(MESSY_COMPLAINTS, 1):
    print(f"\n  Complaint {i}: {complaint[:55]}...")
    result = extract_with_retry(complaint, max_attempts=3)
    retry_results.append(result)
    print(f"    Result: {result}")


# ─── TASK 3: FALLBACK PROMPT ─────────────────────────────────────────────────
print("\n" + "=" * 65)
print("TASK 3 — FALLBACK PROMPT + BEFORE/AFTER COMPARISON")
print("=" * 65)

# Stricter fallback prompt — more explicit pattern guidance
fallback_extract_prompt = ChatPromptTemplate.from_template("""
You are an ID extraction specialist. Find the customer account or ticket
reference number in the complaint text below.

Search specifically for these patterns (in order of priority):
  1. 'Account #' followed by digits      e.g. Account #48213 → #48213
  2. 'acct' followed by digits           e.g. acct 77410 → #77410
  3. 'Ticket #' followed by digits       e.g. Ticket #9042 → #9042
  4. 'Ref:' followed by alphanumeric     e.g. Ref: TCK-9042-B → TCK-9042-B
  5. 'TCK-' or 'TKT-' prefix patterns   e.g. TCK-9042 → TCK-9042

Rules:
  - Return EXACTLY the ID with its prefix (e.g. '#48213' or 'TCK-9042-B')
  - If you find nothing matching the patterns above, return exactly: NOT_FOUND
  - Return ONLY the ID or NOT_FOUND — absolutely no other text

Complaint: {complaint}
""")
fallback_extract_chain = fallback_extract_prompt | model | StrOutputParser()

def extract_with_retry_and_fallback(
    complaint: str, max_attempts: int = 3
) -> str:
    """
    Primary: retry up to max_attempts with validation.
    Fallback: stricter prompt if primary exhausted.
    Returns ID string or 'NOT_FOUND'.
    """
    # Primary path
    result = extract_with_retry(complaint, max_attempts)

    if result is not None:
        return result

    # Fallback path
    print(f"    → Primary exhausted. Trying fallback prompt...")
    fallback_result = fallback_extract_chain.invoke({"complaint": complaint})
    fallback_result = fallback_result.strip()
    print(f"    → Fallback returned: '{fallback_result}'")

    # Validate fallback result too
    if is_valid_id(fallback_result):
        return fallback_result
    return "NOT_FOUND"

print("\nRunning retry + fallback on messy complaints:")
final_results = []
for i, complaint in enumerate(MESSY_COMPLAINTS, 1):
    print(f"\n  Complaint {i}: {complaint[:55]}...")
    result = extract_with_retry_and_fallback(complaint, max_attempts=3)
    final_results.append(result)

# ── BEFORE / AFTER TABLE ─────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("BEFORE vs AFTER COMPARISON")
print("=" * 65)

print(f"\n{'Complaint':<45} {'Original':>12} {'Retry+Fallback':>16}")
print("-" * 75)
for i, (complaint, orig, final) in enumerate(
    zip(MESSY_COMPLAINTS, original_results, final_results), 1
):
    orig_ok = "✓" if is_valid_id(orig) else "✗"
    final_ok = "✓" if is_valid_id(final) or final == "NOT_FOUND" else "✗"
    print(
        f"Complaint {i}: {complaint[:38]:<38} "
        f"{orig_ok} {orig[:8]:>10}  "
        f"{final_ok} {final[:12]:>14}"
    )

print("""
KEY IMPROVEMENTS:
  Complaint 1: No ID format → original may return garbage; fallback returns NOT_FOUND
  Complaint 2: TCK- prefix → retry validates digit pattern; fallback catches Ref: pattern
  Complaint 3: 'acct 77410' → fallback explicitly looks for 'acct' pattern
  Complaint 4: No ID → both return NOT_FOUND (correct — no hallucination)
""")