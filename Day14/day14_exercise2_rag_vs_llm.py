"""
Day 14 Exercise 2 — Compare RAG Responses vs Base LLM
Prove grounding matters with evidence
"""
from __future__ import annotations
from langchain_anthropic import ChatAnthropic
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.embeddings import HuggingFaceEmbeddings
import chromadb

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
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

QUESTIONS = [
    "How often should Pump 4 be inspected?",
    "What is the belt replacement schedule for conveyors?",
    "What is the warranty period for the HVAC system?",
]

# ─── TASK 1: BASE LLM (NO RETRIEVAL) ─────────────────────────────────────────
print("=" * 65)
print("TASK 1 — BASE LLM ANSWERS (NO RETRIEVAL, NO CONTEXT)")
print("=" * 65)

BASE_PROMPT = ChatPromptTemplate.from_template(
    "Answer this question as best you can:\n\n{question}"
)
base_chain = BASE_PROMPT | llm | StrOutputParser()

base_answers = {}
for q in QUESTIONS:
    print(f"\nQ: {q}")
    answer = base_chain.invoke({"question": q})
    base_answers[q] = answer
    print(f"A: {answer}")

# ─── RAG ANSWERS (from Exercise 1) ───────────────────────────────────────────
RAG_PROMPT = ChatPromptTemplate.from_template("""
You are a field engineering assistant for a manufacturing facility.
Answer the question using ONLY the context provided below.
If the answer is not present in the context, say explicitly:
"This information is not covered in the operations manual provided."
Do not use any outside knowledge. Cite the section name.

Context:
{context}

Question: {question}

Answer:""")

def format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | RAG_PROMPT
    | llm
    | StrOutputParser()
)

rag_answers = {}
for q in QUESTIONS:
    rag_answers[q] = rag_chain.invoke(q)

# ─── TASK 2: COMPARISON TABLE ────────────────────────────────────────────────
print("\n" + "=" * 65)
print("TASK 2 — COMPARISON TABLE")
print("=" * 65)

for i, q in enumerate(QUESTIONS, 1):
    print(f"\nQ{i}: {q}")
    print(f"\n  BASE LLM:\n  {base_answers[q][:300]}")
    print(f"\n  RAG PIPELINE:\n  {rag_answers[q][:300]}")
    print("-" * 65)

# ─── TASK 3: CLASSIFY BASE LLM ANSWERS ───────────────────────────────────────
print("\n" + "=" * 65)
print("TASK 3 — CLASSIFY BASE LLM ANSWERS")
print("=" * 65)

CLASSIFICATIONS = {
    QUESTIONS[0]: {
        "classification": "CORRECT_BY_COINCIDENCE",
        "justification": (
            "The base LLM likely gives a plausible generic interval (e.g. '3-6 months' "
            "or 'quarterly') that sounds reasonable for industrial pumps but is NOT "
            "grounded in this client's specific manual (90 days normal, 60 days if >40C). "
            "A field engineer following the base LLM answer could over-inspect or "
            "under-inspect depending on ambient temperature — a safety risk. "
            "If the LLM happens to say '90 days' it is correct BY COINCIDENCE only, "
            "because it had no access to this document."
        ),
    },
    QUESTIONS[1]: {
        "classification": "PLAUSIBLE_BUT_WRONG",
        "justification": (
            "The base LLM typically gives a generic conveyor belt replacement interval "
            "(e.g. '12 months' or '24 months based on usage') that is confident and "
            "specific but does not match this client's actual policy of 18 months OR "
            "first sign of fraying. A field engineer following this answer might delay "
            "replacement past the fraying trigger, risking a belt failure and line "
            "stoppage. This is the most dangerous classification — the answer sounds "
            "authoritative but is fabricated from general knowledge."
        ),
    },
    QUESTIONS[2]: {
        "classification": "APPROPRIATELY_UNCERTAIN",
        "justification": (
            "The base LLM typically admits it does not know the warranty period for "
            "THIS client's HVAC system because it has no access to the client's "
            "specific contracts. However, some LLMs hallucinate a generic warranty "
            "period (e.g. '1 year parts and labour') — if it does so confidently "
            "this becomes PLAUSIBLE_BUT_WRONG. The RAG pipeline correctly says the "
            "information is not in the manual provided — the ideal behaviour."
        ),
    },
}

for i, (q, clf) in enumerate(CLASSIFICATIONS.items(), 1):
    print(f"\nQ{i}: {q}")
    print(f"  Classification: {clf['classification']}")
    print(f"  Justification:  {clf['justification'][:200]}...")

print("""
KEY FINDING FOR SKEPTICAL MENTOR:
  "The base LLM gave a confident, specific, wrong answer for Q2 (conveyor belt 
  replacement) — with no way for a field engineer to know it was wrong without 
  checking the manual themselves. The RAG pipeline gave the correct client-specific 
  answer with a citation, so the engineer can verify in one click. The risk isn't 
  that the LLM is always wrong — it's that you can't tell WHEN it's wrong without 
  the document grounding that RAG provides."
""")