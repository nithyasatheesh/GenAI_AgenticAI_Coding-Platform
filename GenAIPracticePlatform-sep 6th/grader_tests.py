"""Internal tests for grader.py (RAG lab). Run:  python grader_tests.py

Covers the 8 cases the rubric must handle:
 1 correct        -> full marks
 2 missing one    -> lose exactly that criterion
 3 wrong param    -> lose only the param criterion
 4 op never called-> lose that criterion
 5 hardcoded out  -> lose LLM-generation criteria
 6 imports only   -> near zero
 7 partial        -> partial
 8 fully wrong    -> zero
"""
from __future__ import annotations

import sys

import grader

MODE = "mock"

# ---- reference (correct) task solutions ---------------------------------- #
S1 = '''\
from langchain_community.document_loaders import PyPDFLoader
loader = PyPDFLoader(SAMPLE_PDF)
documents = loader.load()
print("Number of pages:", len(documents))
print(documents[0].metadata)
'''
S2 = '''\
from langchain_text_splitters import RecursiveCharacterTextSplitter
chunk_size = 1000
chunk_overlap = 200
splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
chunks = splitter.split_documents(documents)
print("Number of chunks:", len(chunks))
'''
S3 = '''\
embeddings = get_embeddings(MODE)
vectorstore = make_vectorstore(chunks, embeddings)
query = "How many casual leave days are provided each year?"
results = vectorstore.similarity_search(query, k=3)
for d in results:
    print(d.page_content[:120])
'''
S4 = '''\
from langchain_core.prompts import ChatPromptTemplate
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
llm = get_chat_model(MODE)
prompt = ChatPromptTemplate.from_template(
    """Answer using ONLY the context. If not present, reply exactly:
"I could not find the answer in the provided document."
Context:
{context}
Question:
{question}
Answer:""")
question = "What is the standard notice period for regular full-time employees?"
docs = retriever.invoke(question)
context = "\\n\\n".join(d.page_content for d in docs)
resp = llm.invoke(prompt.format_messages(context=context, question=question))
print("Answer:", resp.content)
'''
S5 = '''\
def answer(question):
    docs = retriever.invoke(question)
    context = "\\n\\n".join(d.page_content for d in docs)
    resp = llm.invoke(prompt.format_messages(context=context, question=question))
    return resp.content, sorted({d.metadata.get("page", "?") for d in docs})

while True:
    q = input("Q> ").strip()
    if q.lower() == "exit":
        break
    print(answer(q))
'''
SOLU = {1: S1, 2: S2, 3: S3, 4: S4, 5: S5}


def grade(task_id: int, codes_by_task: dict[int, str]) -> dict:
    ordered = [codes_by_task[i] for i in range(1, task_id + 1)]
    src = grader.assemble_source(ordered, MODE)
    return grader.grade_task(task_id, codes_by_task[task_id], lab_id="01-rag",
                             accumulated_source=src, mode=MODE)


def show(tag, r):
    print(f"  [{tag}] {r['score']}/{r['max_score']}  "
          + " ".join(f"{c['name']}={'Y' if c['passed'] else 'n'}" for c in r["criteria"]))


PASS = FAIL = 0


def expect(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {msg}")
    else:
        FAIL += 1
        print(f"  FAIL {msg}")


def crit(r, name):
    return next(c for c in r["criteria"] if c["name"] == name)


# ======================================================================= #
print("\n# 1. completely correct solution -> full marks on every task")
for tid in range(1, 6):
    r = grade(tid, dict(SOLU))
    show(f"T{tid}", r)
    expect(r["score"] == r["max_score"], f"T{tid} correct == {r['max_score']}/{r['max_score']}")

print("\n# 2. missing ONE requirement -> lose exactly that criterion")
# T2 without printing the count
codes = dict(SOLU); codes[2] = S2.replace('print("Number of chunks:", len(chunks))', 'x = len(chunks)')
r = grade(2, codes); show("T2 no-print", r)
expect(not crit(r, "chunk_count_reported")["passed"], "T2 loses chunk_count_reported")
expect(crit(r, "chunk_size_1000")["passed"] and crit(r, "documents_split")["passed"],
       "T2 keeps the other criteria")
expect(r["score"] == r["max_score"] - 4, f"T2 score == {r['max_score']-4} (lost 4)")

print("\n# 3. wrong parameter (chunk_size=500) -> lose only chunk_size_1000")
codes = dict(SOLU); codes[2] = S2.replace("chunk_size = 1000", "chunk_size = 500")
r = grade(2, codes); show("T2 size=500", r)
expect(not crit(r, "chunk_size_1000")["passed"], "T2 chunk_size_1000 fails for 500")
expect(crit(r, "chunk_overlap_200")["passed"], "T2 chunk_overlap_200 still passes")
expect(r["score"] == r["max_score"] - 4, "T2 loses only the 4 chunk_size marks")

print("\n# 4. required op never called (splitter created, never used) -> lose split")
codes = dict(SOLU)
codes[2] = ('from langchain_text_splitters import RecursiveCharacterTextSplitter\n'
            'chunk_size = 1000\nchunk_overlap = 200\n'
            'splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)\n'
            'chunks = []\nprint(len(chunks))\n')
r = grade(2, codes); show("T2 no-split", r)
expect(not crit(r, "documents_split")["passed"], "T2 documents_split fails (never called)")
expect(crit(r, "splitter_created")["passed"], "T2 splitter_created still passes")

print("\n# 5. hardcoded / fake output -> lose LLM-generation criteria")
codes = dict(SOLU)
codes[4] = (S4.replace('resp = llm.invoke(prompt.format_messages(context=context, question=question))',
                       'resp = type("R", (), {"content": "60 calendar days"})()')
              .replace('print("Answer:", resp.content)', 'print("Answer:", resp.content)'))
# simpler hardcode: answer is a plain string
codes[4] = '''\
from langchain_core.prompts import ChatPromptTemplate
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
llm = get_chat_model(MODE)
prompt = ChatPromptTemplate.from_template("Context: {context}\\nQuestion: {question}")
question = "notice period?"
docs = retriever.invoke(question)
answer = "The notice period is 60 calendar days."
print("Answer:", answer)
'''
r = grade(4, codes); show("T4 hardcoded", r)
expect(not crit(r, "answer_generated_by_llm")["passed"], "T4 answer_generated_by_llm fails (hardcoded)")
expect(not crit(r, "context_passed_to_llm")["passed"], "T4 context_passed_to_llm fails")
expect(not crit(r, "prompt_is_grounded")["passed"], "T4 prompt_is_grounded fails (no refusal line)")
expect(not crit(r, "context_built_from_docs")["passed"], "T4 context_built_from_docs fails")
expect(crit(r, "retriever_created")["passed"], "T4 retriever_created still passes (scaffolding is real)")
# a hardcoded answer can only earn the retrieval scaffolding (13), never the 12 answer marks
expect(r["score"] <= 13, f"T4 hardcoded capped at scaffolding ({r['score']}/{r['max_score']})")
expect(all(c["earned"] == 0 for c in r["criteria"]
           if c["name"] in {"prompt_is_grounded", "context_built_from_docs",
                            "context_passed_to_llm", "answer_generated_by_llm"}),
       "T4 hardcoded earns 0 on all four answer/context criteria")

print("\n# 6. imports only -> near zero")
codes = dict(SOLU); codes[1] = "from langchain_community.document_loaders import PyPDFLoader\n"
r = grade(1, codes); show("T1 import-only", r)
expect(crit(r, "loader_imported")["passed"], "T1 loader_imported passes")
expect(not crit(r, "loader_called_with_pdf_path")["passed"], "T1 loader_called fails")
expect(not crit(r, "documents_actually_loaded")["passed"], "T1 documents_actually_loaded fails")
expect(r["score"] == 1, f"T1 import-only == 1/{r['max_score']}")

print("\n# 7. partial implementation -> partial marks (Test 3 behaviour preserved)")
codes = dict(SOLU)
codes[3] = ('embeddings = get_embeddings(MODE)\n'
            'vectorstore = make_vectorstore(chunks, embeddings)\n'
            '# no similarity search\n')
r = grade(3, codes); show("T3 partial", r)
expect(0 < r["score"] < r["max_score"], f"T3 partial is between 0 and {r['max_score']} (got {r['score']})")
expect(crit(r, "embeddings_created")["passed"] and crit(r, "vectorstore_created")["passed"],
       "T3 keeps embeddings + vectorstore marks")
expect(not crit(r, "similarity_search_k3")["passed"] and not crit(r, "top3_results_obtained")["passed"],
       "T3 loses the search criteria")

print("\n# 8. completely wrong implementation -> zero")
codes = dict(SOLU); codes[2] = 'x = 1 + 1\nprint("hello world")\ny = [1, 2, 3]\n'
r = grade(2, codes); show("T2 unrelated", r)
expect(r["score"] == 0, f"T2 unrelated == 0/{r['max_score']} (got {r['score']})")

print("\n# 8b. wrong loader for T1 -> not full marks")
codes = dict(SOLU)
codes[1] = ('from langchain_community.document_loaders import TextLoader\n'
            'loader = TextLoader(SAMPLE_PDF)\ndocuments = loader.load()\nprint(len(documents))\n')
r = grade(1, codes); show("T1 TextLoader", r)
expect(not crit(r, "loader_imported")["passed"], "T1 wrong loader: loader_imported fails")
expect(r["score"] < r["max_score"], "T1 wrong loader != full marks")

print(f"\n{'='*50}\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
