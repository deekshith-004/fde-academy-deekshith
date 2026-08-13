"""
Day 14 Exercise 1 — Build a RAG Pipeline Over an Operations Manual
Task 1: Chunk + Embed → ChromaDB
Task 2: Build retrieval chain in LangChain
Task 3: Verify citations
"""
from __future__ import annotations
import os
import chromadb
from chromadb.utils import embedding_functions
from langchain_anthropic import ChatAnthropic
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings

# ── Sample Operations Manual ──────────────────────────────────────────────────
MANUAL_TEXT = """
Section 4.2 - Pump Maintenance:
Pump 4 requires inspection every 90 days under normal operating conditions.
If ambient temperature exceeds 40C, reduce the interval to 60 days.
Vibration readings above 8mm/s require immediate inspection regardless of schedule.
Lubrication of pump bearings must be performed at each inspection.
Pump seals should be replaced every 180 days or if leakage is detected.

Section 4.5 - Conveyor Systems:
Conveyor belts should be visually inspected weekly for wear and tear.
Full belt replacement is recommended after 18 months of continuous operation
or at the first sign of fraying, whichever comes first.
Belt tension must be checked monthly and adjusted to manufacturer specifications.
Conveyor rollers should be lubricated every 30 days.
Any conveyor operating with misalignment must be stopped immediately for realignment.

Section 6.1 - Emergency Shutoff:
All emergency shutoff valves must be tested monthly.
A failed test requires the valve to be tagged out of service and replaced within 24 hours.
Emergency shutoff activation logs must be reviewed weekly by the safety officer.
Replacement valves must meet ISO 9001 certification requirements.
Post-replacement testing must be completed before returning the valve to service.

Section 7.3 - Electrical Safety:
All electrical panels must be inspected quarterly by a certified electrician.
Lock-out tag-out (LOTO) procedures must be followed before any maintenance work.
Ground fault circuit interrupters (GFCIs) must be tested monthly.
Any exposed wiring must be reported and repaired within 48 hours.
"""

# ─── TASK 1: CHUNK AND EMBED ──────────────────────────────────────────────────
print("=" * 65)
print("TASK 1 — CHUNK AND EMBED THE SOURCE DOCUMENT")
print("=" * 65)

# Chunk the manual
splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=40,
    separators=["\n\n", "\n", ". ", " "],
)
chunks = splitter.split_text(MANUAL_TEXT)

print(f"\nTotal chunks created: {len(chunks)}")
for i, chunk in enumerate(chunks):
    print(f"\nChunk {i} ({len(chunk)} chars):")
    print(chunk[:120] + "..." if len(chunk) > 120 else chunk)

# Assign section metadata by scanning chunk content
def get_section(chunk_text: str) -> str:
    if "4.2" in chunk_text or "Pump" in chunk_text:
        return "Section 4.2 - Pump Maintenance"
    elif "4.5" in chunk_text or "Conveyor" in chunk_text or "belt" in chunk_text.lower():
        return "Section 4.5 - Conveyor Systems"
    elif "6.1" in chunk_text or "Shutoff" in chunk_text or "shutoff" in chunk_text:
        return "Section 6.1 - Emergency Shutoff"
    elif "7.3" in chunk_text or "Electrical" in chunk_text or "electrical" in chunk_text:
        return "Section 7.3 - Electrical Safety"
    return "General"

# Use sentence-transformers (free, no API key needed for embeddings)
print("\nLoading embedding model (sentence-transformers)...")
embed_model = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)

# Build ChromaDB collection
chroma_client = chromadb.PersistentClient(path="./chroma_db_day14")
try:
    chroma_client.delete_collection("operations_manual")
except Exception:
    pass

vectorstore = Chroma(
    collection_name="operations_manual",
    embedding_function=embed_model,
    client=chroma_client,
)

# Add chunks with metadata
ids = [f"chunk_{i}" for i in range(len(chunks))]
metadatas = [
    {"source": "ops_manual.txt", "chunk_index": i, "section": get_section(chunk)}
    for i, chunk in enumerate(chunks)
]

vectorstore.add_texts(texts=chunks, ids=ids, metadatas=metadatas)
print(f"\n✓ Added {len(chunks)} chunks to ChromaDB collection 'operations_manual'")
print("\nChunk IDs and sections:")
for i, (cid, meta) in enumerate(zip(ids, metadatas)):
    print(f"  {cid}: {meta['section']}")

# ─── TASK 2: BUILD THE RETRIEVAL CHAIN ───────────────────────────────────────
print("\n" + "=" * 65)
print("TASK 2 — BUILD THE RETRIEVAL CHAIN")
print("=" * 65)

# Retriever: top-3 chunks
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Constraint prompt — answers ONLY from context
RAG_PROMPT = ChatPromptTemplate.from_template("""
You are a field engineering assistant for a manufacturing facility.
Answer the question using ONLY the context provided below.
If the answer is not present in the context, say explicitly:
"This information is not covered in the operations manual provided."
Do not use any outside knowledge or make assumptions.
Cite the section name when giving your answer.

Context:
{context}

Question: {question}

Answer:""")

# LLM — using Claude (no OpenAI key needed)
llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

def format_docs(docs: list) -> str:
    return "\n\n".join(d.page_content for d in docs)

# Assemble the RAG chain
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | RAG_PROMPT
    | llm
    | StrOutputParser()
)

# Test questions
questions = [
    "How often should Pump 4 be inspected?",
    "What is the belt replacement schedule for conveyors?",
    "What is the warranty period for the HVAC system?",
]

print("\nRunning 3 test questions through RAG pipeline:")
rag_answers = {}
for q in questions:
    print(f"\nQ: {q}")
    answer = rag_chain.invoke(q)
    rag_answers[q] = answer
    print(f"A: {answer}")

# ─── TASK 3: VERIFY CITATIONS ────────────────────────────────────────────────
print("\n" + "=" * 65)
print("TASK 3 — VERIFY CITATIONS")
print("=" * 65)

def answer_with_citations(question: str) -> dict:
    """Return answer + list of sections that grounded it."""
    docs = retriever.invoke(question)
    context = format_docs(docs)
    sections = list({d.metadata.get("section", "Unknown") for d in docs})
    chunk_ids = [d.metadata.get("chunk_index", "?") for d in docs]

    answer_prompt = RAG_PROMPT.format_messages(
        context=context, question=question
    )
    answer = llm.invoke(answer_prompt).content

    return {
        "question": question,
        "answer": answer,
        "grounding_sections": sections,
        "chunk_ids_used": chunk_ids,
    }

print()
for q in questions:
    result = answer_with_citations(q)
    print(f"Q: {result['question']}")
    print(f"A: {result['answer']}")
    print(f"   Grounded in: {result['grounding_sections']}")
    print(f"   Chunk IDs:   {result['chunk_ids_used']}")
    print()

print("""
EXPECTED OUTPUTS:
  Q1: 'Pump 4 should be inspected every 90 days under normal conditions,
       or every 60 days if ambient temperature exceeds 40C.'
       Grounded in: Section 4.2 - Pump Maintenance

  Q2: 'Conveyor belts should be replaced after 18 months of continuous
       operation or at the first sign of fraying, whichever comes first.'
       Grounded in: Section 4.5 - Conveyor Systems

  Q3: 'This information is not covered in the operations manual provided.'
       (No HVAC section exists — correct pipeline declines to answer)
""")l