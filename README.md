# Evidence Search

A local document-retrieval engine that returns **ranked excerpts with exact file-and-line citations**. It combines BM25 and word/bigram TF-IDF rankings using reciprocal rank fusion.

This is the retrieval component of a potential RAG system. It has **no LLM, embeddings or generated answers**. Keeping source text visible makes ranking errors and unsupported questions easier to inspect.

[![CI](https://github.com/ayanirfan099/evidence-search/actions/workflows/tests.yml/badge.svg)](https://github.com/ayanirfan099/evidence-search/actions/workflows/tests.yml)


## Executed example

For `python app.py search --query "What should I do after receiving HTTP 429?"`, the bundled fictional corpus returns `api-limits.md:L4-L7`, including: “Requests above the limit receive HTTP 429. Respect the Retry-After response header.”

See the [actual JSON transcript](docs/query-example.json). The four-line citation can be checked directly against `data/docs/api-limits.md`; it is source retrieval, not a generated answer.

## How it works

1. Read UTF-8 `.md` and `.txt` documents (maximum 1 MiB each; external/symlinked files are rejected).
2. Create four-line windows with one-line overlap, retaining original line coordinates.
3. Compute BM25 term statistics and a TF-IDF matrix.
4. Fuse the two rankings; identical excerpt text is deduplicated by content hash.
5. Return source excerpts and line citations. Unknown terms and stopword-only queries return no matches.

The index is rebuilt in memory at startup. It is suitable for a small corpus, not a multi-million-document search service.

## Try it

```sh
python app.py search --query "What should I do after receiving HTTP 429?"
python app.py search --docs path/to/docs --query "refund policy" --top-k 5
python app.py serve --port 8002
```

Send `POST http://127.0.0.1:8002/predict` with `Content-Type: application/json`:

```json
{"query":"Where can I download invoices?","top_k":3}
```

Every result contains `source`, `start_line`, `end_line`, `citation`, `excerpt`, the fused `score`, and component scores. Scores express ranking, not certainty. A lexical match does **not** mean a document answers the question; read the excerpt before using it.

## Evaluation and data

`data/docs/` contains eight fictional AcmeDesk help documents written for this project. They are not real business, legal or security policies. `data/queries.json` contains 12 manually authored query/source judgments.

The committed report records **Hit@3 = 1.0 and MRR@3 = 1.0** over those 12 queries and 32 chunks. This is an intentionally small smoke benchmark, not proof of general search quality. It measures whether the expected document was retrieved, not answer correctness or citation completeness.

The tests verify exact excerpt/line correspondence, no-match handling, deterministic ranking, invalid queries and corpus constraints.

## Files

- `engine.py`: chunking, indexing, BM25, TF-IDF, rank fusion and evaluation.
- `app.py`: search CLI and API integration.
- `api.py`: bounded local JSON server.
- `data/docs/`: fictional corpus.
- `data/queries.json`: query/source relevance judgments.
- `reports/evaluation.json`: retrieval results.

## Known limitations and next milestones

English lexical matching misses synonyms, paraphrases and cross-language matches. Fixed line windows can split a paragraph. Overlapping excerpts may still cover the same source passage. Citations refer to the indexed snapshot, so rebuild after editing files. A local user can search every file in the supplied corpus; there are no per-document permissions.

Next steps: add held-out human relevance judgments, reciprocal-rank ablations, embedding retrieval, a reranker, persistent incremental indexing and document-level access checks. If adding an LLM, test unsupported questions and citation fidelity separately rather than treating retrieval metrics as answer accuracy.

Reference: [scikit-learn text feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction).

## Quick start

Tested with Python 3.12. Use a separate virtual environment for each project:

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python app.py evaluate
```

The dependencies are pinned to the versions tested for this project, not advertised as the newest versions. After the first dependency installation, the bundled examples run offline. No paid API keys or external model downloads are needed.

The lightweight HTTP server is for local demonstrations. It binds to localhost, accepts JSON only, limits request size and does not log request bodies. Authentication, production serving, rate limiting and operational monitoring must be added before public deployment. The included GitHub Actions workflow runs tests and evaluation when pushed to a repository; check the linked Actions badge for current remote status.
