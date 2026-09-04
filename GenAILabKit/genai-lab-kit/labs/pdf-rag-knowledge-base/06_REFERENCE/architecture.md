# Architecture Reference

## End-to-end pipeline

```text
                         USER / PARTICIPANT
                                |
                                v
                    +---------------------+
                    |   PDF file path     |   04_DATA/sample_knowledge_base.pdf
                    +----------+----------+
                               |
                               v
                    +---------------------+
                    |   PyPDFLoader        |   langchain_community.document_loaders
                    |   .load()           |   -> list[Document], one per page
                    +----------+----------+
                               |
                               v
                    +---------------------+
                    | RecursiveCharacter  |   langchain_text_splitters
                    | TextSplitter        |
                    | chunk_size = 1000   |
                    | chunk_overlap = 200 |   -> list[Document] chunks (page metadata kept)
                    +----------+----------+
                               |
                               v
                    +---------------------+
                    |  OpenAIEmbeddings    |   model = text-embedding-3-small
                    +----------+----------+
                               |
                               v
                    +---------------------+
                    |       Chroma        |   persist_directory = ../chroma_db
                    |  collection=pdf_kb  |   vectors + page metadata
                    +----------+----------+
                               |
        USER QUESTION          |
             |                 |
             v                 v
       +-----------------------------+
       |   retriever (k = 3)         |   vectorstore.as_retriever(search_kwargs={"k": 3})
       |   similarity search         |
       +--------------+--------------+
                      |
                      v
       +-----------------------------+
       |  top-3 chunks -> context    |   "\n\n".join(d.page_content)
       +--------------+--------------+
                      |
                      v
       +-----------------------------+
       |  ChatPromptTemplate         |   context + question, "answer ONLY from context"
       +--------------+--------------+
                      |
                      v
       +-----------------------------+
       |  ChatOpenAI(gpt-4o-mini)    |   temperature = 0
       +--------------+--------------+
                      |
                      v
       +-----------------------------+
       |  Answer + source pages      |   sorted, de-duplicated metadata["page"]
       +-----------------------------+
```

## Why each choice

| Component | Choice | Reason |
|-----------|--------|--------|
| Loader | `PyPDFLoader` | Simple, per-page `Document`s with `source` + `page` metadata for citations. |
| Splitter | `RecursiveCharacterTextSplitter` 1000/200 | Fixed-size with overlap keeps sentences intact across boundaries; 20% overlap avoids losing context at cut points. |
| Embeddings | `text-embedding-3-small` | Cheap, fast, strong retrieval quality for short factual docs. |
| Vector store | Chroma, persistent | Local, no server, survives kernel restarts via `persist_directory`. |
| `k = 3` | top-3 | Enough context for single-fact questions without diluting the prompt. |
| `temperature = 0` | deterministic | Reproducible answers; grading depends on it. |
| Grounded prompt | "answer ONLY from context" + fixed refusal | Forces abstention on out-of-context questions instead of hallucinating. |

## Grounding contract

If the retrieved context does not contain the answer, the model must output
**exactly**:

```
I could not find the answer in the provided document.
```

`scripts/validate_solution.py` checks this against the negative questions in
`04_DATA/RAG_Question_Set.pdf` (Q16–Q20).

## Common pitfalls

- **Duplicated vectors:** `Chroma.from_documents` appends on every run. Load the
  existing store instead, or delete `../chroma_db` before rebuilding.
- **Wrong working directory:** relative paths assume you run from
  `02_STARTER_CODE/` or `03_SOLUTION_GUIDE/`. The scripts resolve paths from
  their own location so they work from anywhere.
- **Answer leakage:** if the model answers a negative question, the prompt is too
  weak — restate the "ONLY from context" instruction and the exact refusal text.
