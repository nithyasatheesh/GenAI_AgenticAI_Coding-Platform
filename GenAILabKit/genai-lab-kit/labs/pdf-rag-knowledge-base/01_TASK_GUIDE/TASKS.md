# Task Guide — PDF Knowledge Base RAG System

Work these in order inside `02_STARTER_CODE/participant_notebook.ipynb`.
Required settings (do not change): **chunk_size=1000, chunk_overlap=200, k=3,
model=gpt-4o-mini, temperature=0**.

---

## Task 0 — Environment preflight

Run the first code cell. It confirms packages, the `OPENAI_API_KEY`, and the data
file are all present. Do not continue until it prints **"Preflight passed"**.

---

## Task 1 — Load the PDF

**Goal:** Load `../04_DATA/sample_knowledge_base.pdf` with LangChain's PDF loader.

**Do:**
1. Import the loader.
2. Create it with the PDF path.
3. `.load()` the documents.
4. Print page count, page 1 text, page 1 metadata.

**Hints:**
1. `from langchain_community.document_loaders import ...`
2. The class name starts with `PyPDF`.
3. `.load()` returns a list of `Document` objects, one per page.

**Expected:** page count prints; page 1 shows readable handbook text; metadata is a
dict with `source` and `page`.

---

## Task 2 — Chunk the document

**Goal:** Split the pages into overlapping fixed-size chunks.

**Do:**
1. `from langchain_text_splitters import RecursiveCharacterTextSplitter`
2. Create it with `chunk_size=1000, chunk_overlap=200`.
3. `split_documents(documents)` → `chunks`.
4. Print `len(chunks)` and the first 2 chunks (content + metadata).

**Mini experiment:** try `500 / 100`, compare the chunk count, then restore `1000 / 200`.

**Expected:** more chunks than pages; each chunk keeps its page metadata.

---

## Task 3 — Embeddings + ChromaDB

**Goal:** Embed chunks and store them in a persistent vector database.

**Do:**
1. Import `OpenAIEmbeddings` (`langchain_openai`) and `Chroma` (`langchain_chroma`).
2. `embeddings = OpenAIEmbeddings(model="text-embedding-3-small")`
3. Build the store from `chunks`, `persist_directory="../chroma_db"`,
   `collection_name="pdf_kb"`.
4. `vectorstore.similarity_search("How many casual leave days are provided each year?", k=3)`
   and print the results.

**Hint — re-runs:** `Chroma.from_documents` **adds** chunks every time. If you
re-run Task 3, delete `../chroma_db` first, or load the existing store with
`Chroma(persist_directory=..., embedding_function=..., collection_name=...)`.

**Expected:** 3 chunks returned, all clearly about leave / casual leave.

---

## Task 4 — Grounded RAG QA

**Goal:** Turn retrieval + GPT-4o-mini into grounded answers.

**Do:**
1. Import `ChatOpenAI`, `ChatPromptTemplate`.
2. `retriever = vectorstore.as_retriever(search_kwargs={"k": 3})`
3. `llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)`
4. Write a prompt with `{context}` and `{question}` that says: answer **only** from
   the context; if not present, reply exactly
   `I could not find the answer in the provided document.`
5. For a question: retrieve → `context = "\n\n".join(page_content)` → `format_messages`
   → `llm.invoke`.
6. Print the answer and `sorted({d.metadata.get("page", "?") for d in docs})`.

**Test all three:**
- Grounded: *"What is the standard notice period for regular full-time employees?"* → **60 calendar days** + pages.
- Reasoning: *"What class of air travel is standard for domestic business trips?"* → **Economy class**.
- Negative: *"Who is the current Prime Minister of India?"* → the refusal sentence.

---

## Task 5 — Interactive application

**Goal:** Combine everything into `02_STARTER_CODE/rag_app.py`.

**The app must:**
1. Load PDF → chunk → embed → Chroma (load the store if it already exists).
2. Build a `k=3` retriever and the grounded GPT-4o-mini chain.
3. Loop: read a question, print a grounded answer + de-duplicated source pages.
4. Exit on `exit`.

**Run:**
```bash
cd 02_STARTER_CODE
python rag_app.py
```

**Validate** with questions from `04_DATA/RAG_Question_Set.pdf`: at least one
grounded, one reasoning, one negative.

---

## Final checklist

- [ ] Task 0 preflight passed
- [ ] PDF loads, page count shown
- [ ] Chunks at 1000 / 200
- [ ] `text-embedding-3-small` used
- [ ] Chroma persisted at `../chroma_db` (collection `pdf_kb`)
- [ ] Similarity search returns relevant chunks
- [ ] `gpt-4o-mini`, `temperature=0`
- [ ] Answers use only retrieved context
- [ ] Source pages displayed, de-duplicated
- [ ] Negative question → exact refusal sentence
- [ ] `rag_app.py` runs interactively
- [ ] `python scripts/validate_solution.py` passes
