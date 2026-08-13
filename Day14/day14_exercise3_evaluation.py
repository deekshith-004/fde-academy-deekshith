"""
Day 14 Exercise 3 — Evaluate Retrieval Quality with Precision & Recall
Task 1: Build test set with known-good chunk IDs
Task 2: Compute precision & recall
Task 3: Diagnose and tune
"""
from __future__ import annotations
import chromadb
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# ── Reconnect to Exercise 1 vector store ──────────────────────────────────────
embed_model = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)
chroma_client = chromadb.PersistentClient(path="./chroma_db_day14")
vectorstore = Chroma(
    collection_name="operations_manual",
    embedding_function=embed_model,
    client=chroma_client,
)

# ─── TASK 1: BUILD TEST SET ───────────────────────────────────────────────────
print("=" * 65)
print("TASK 1 — INSPECT COLLECTION AND BUILD TEST SET")
print("=" * 65)

# Inspect what's stored
collection = chroma_client.get_collection("operations_manual")
stored = collection.get()
print(f"\nTotal chunks in collection: {len(stored['ids'])}")
print("\nStored chunk IDs and content preview:")
for cid, doc, meta in zip(stored['ids'], stored['documents'], stored['metadatas']):
    print(f"  {cid} [{meta.get('section','?')}]: {doc[:80]}...")

# Build test set — questions with known-correct chunk IDs
# (verified by reading stored documents above)
TEST_SET = [
    {
        "question": "How often should Pump 4 be inspected?",
        "relevant_chunk_ids": {"chunk_0"},
        "expected_section": "Section 4.2 - Pump Maintenance",
    },
    {
        "question": "What vibration reading triggers an immediate pump inspection?",
        "relevant_chunk_ids": {"chunk_0"},
        "expected_section": "Section 4.2 - Pump Maintenance",
    },
    {
        "question": "How often are conveyor belts visually inspected?",
        "relevant_chunk_ids": {"chunk_1"},
        "expected_section": "Section 4.5 - Conveyor Systems",
    },
    {
        "question": "What happens if an emergency shutoff valve fails its monthly test?",
        "relevant_chunk_ids": {"chunk_2"},
        "expected_section": "Section 6.1 - Emergency Shutoff",
    },
    {
        "question": "How often must electrical panels be inspected?",
        "relevant_chunk_ids": {"chunk_3"},
        "expected_section": "Section 7.3 - Electrical Safety",
    },
]

print(f"\nTest set: {len(TEST_SET)} questions")
for i, t in enumerate(TEST_SET, 1):
    print(f"  Q{i}: {t['question']}")
    print(f"       Expected chunks: {t['relevant_chunk_ids']}")


# ─── TASK 2: COMPUTE PRECISION & RECALL ──────────────────────────────────────
print("\n" + "=" * 65)
print("TASK 2 — COMPUTE PRECISION & RECALL (k=3)")
print("=" * 65)

def evaluate_retrieval(test_set: list, vs: Chroma, k: int = 3) -> list:
    results = []
    retriever = vs.as_retriever(search_kwargs={"k": k})

    for item in test_set:
        docs = retriever.invoke(item["question"])

        # Get retrieved chunk IDs from metadata
        retrieved_ids = set()
        for doc in docs:
            # chunk_index stored as int in metadata
            idx = doc.metadata.get("chunk_index")
            if idx is not None:
                retrieved_ids.add(f"chunk_{idx}")

        relevant_ids = item["relevant_chunk_ids"]
        true_positives = relevant_ids & retrieved_ids

        precision = len(true_positives) / len(retrieved_ids) if retrieved_ids else 0.0
        recall = len(true_positives) / len(relevant_ids) if relevant_ids else 0.0

        results.append({
            "question": item["question"][:50] + "...",
            "relevant": relevant_ids,
            "retrieved": retrieved_ids,
            "true_positives": true_positives,
            "precision": round(precision, 2),
            "recall": round(recall, 2),
        })
    return results


results_k3 = evaluate_retrieval(TEST_SET, vectorstore, k=3)

print(f"\nResults at k=3:")
print(f"{'Question':<52} {'Prec':>6} {'Recall':>7}")
print("-" * 68)
for r in results_k3:
    tp_str = str(r["true_positives"]) if r["true_positives"] else "none"
    print(f"{r['question']:<52} {r['precision']:>6.2f} {r['recall']:>7.2f}")
    print(f"  Retrieved: {r['retrieved']} | TP: {tp_str}")

avg_p_k3 = sum(r["precision"] for r in results_k3) / len(results_k3)
avg_r_k3 = sum(r["recall"] for r in results_k3) / len(results_k3)
print(f"\nAverage precision: {avg_p_k3:.2f}")
print(f"Average recall:    {avg_r_k3:.2f}")


# ─── TASK 3: DIAGNOSE AND TUNE ───────────────────────────────────────────────
print("\n" + "=" * 65)
print("TASK 3 — DIAGNOSE AND TUNE")
print("=" * 65)

print(f"""
BEFORE TUNING (k=3):
  Average precision: {avg_p_k3:.2f}
  Average recall:    {avg_r_k3:.2f}

DIAGNOSIS:
  If recall < precision: retriever is missing relevant chunks entirely.
  Cause: k too small, chunks too small (answer split across chunk boundary),
         or embedding model not capturing domain vocabulary well.
  Fix: increase k from 3 to 5.

  If precision < recall: retriever is returning too many irrelevant chunks.
  Cause: chunks too large (containing multiple topics), k too high.
  Fix: decrease chunk_size or increase similarity threshold.
""")

# Apply tuning: increase k from 3 to 5
results_k5 = evaluate_retrieval(TEST_SET, vectorstore, k=5)

print("CHANGE APPLIED: Increased k from 3 to 5")
print(f"\nResults at k=5:")
print(f"{'Question':<52} {'Prec':>6} {'Recall':>7}")
print("-" * 68)
for r in results_k5:
    print(f"{r['question']:<52} {r['precision']:>6.2f} {r['recall']:>7.2f}")

avg_p_k5 = sum(r["precision"] for r in results_k5) / len(results_k5)
avg_r_k5 = sum(r["recall"] for r in results_k5) / len(results_k5)

print(f"""
AFTER TUNING (k=5):
  Average precision: {avg_p_k5:.2f}
  Average recall:    {avg_r_k5:.2f}

BEFORE vs AFTER:
  Precision: {avg_p_k3:.2f} → {avg_p_k5:.2f}  ({"improved" if avg_p_k5 > avg_p_k3 else "decreased" if avg_p_k5 < avg_p_k3 else "unchanged"})
  Recall:    {avg_r_k3:.2f} → {avg_r_k5:.2f}  ({"improved" if avg_r_k5 > avg_r_k3 else "decreased" if avg_r_k5 < avg_r_k3 else "unchanged"})

TRADEOFF NOTE:
  Increasing k from 3 to 5 typically improves recall (fewer missed relevant chunks)
  but may decrease precision (more irrelevant chunks included in context).
  It also increases token cost per query by ~67% and adds slight latency.
  For a manufacturing safety manual, higher recall is preferred — missing a
  critical safety instruction is more dangerous than including a slightly
  irrelevant one.
""")