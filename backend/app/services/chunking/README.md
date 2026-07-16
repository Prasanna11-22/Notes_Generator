# Semantic Chunking & Metadata Enrichment Module

This module is responsible for converting processed document texts (from Phase 4) into high-quality semantic chunks enriched with curriculum context. The output is structured to be consumed directly by downstream embedding models for vector search.

---

## 1. Pipeline Architecture

```
                       Cleaned Text
                            ↓
                    [Block Protector]  ──► Locates code blocks, tables, lists,
                            ↓              math formulas, and algorithms to preserve.
                  [Semantic Chunker]   ──► Splits text at sentence boundaries (spaCy/NLTK)
                            ↓              while keeping protected blocks atomic.
               [Chunk Quality Validator] ──► Rejects empty, too short, too long,
                            ↓              or high symbol-density noise segments.
                 [Metadata Enricher]   ──► Matches content to course Units & Topics
                            ↓              and aligns outcomes (CO, Bloom, Knowledge).
                 [Chunk Deduplicator]  ──► Computes SHA-256 and Jaccard token similarity
                            ↓              to prevent duplicate rows.
               Persist Chunk & Mapping
```

---

## 2. Chunking Strategies

The pipeline implements the **Strategy Pattern** under the `BaseChunker` interface:
1. **SpaCy Chunker (`SpaCyChunker`)**: Uses spaCy's sentence segmentation. If statistical model weights are not loaded, it falls back to a blank model with a lightweight sentencizer component.
2. **NLTK Chunker (`NLTKChunker`)**: Uses NLTK's sentence tokenizer (`sent_tokenize`) as a fast alternative.
3. **Regex Chunker (`RegexChunker`)**: Splitting based on paragraphs (`\n\n`) as a lightweight fallback.

### Block Preservation
All chunkers utilize the `BlockProtector` to ensure the following educational content is **never split in half**:
- **Markdown Tables**: Lines containing `|` formatting.
- **Lists**: Contiguous ordered or unordered lines.
- **Math Formulas**: LaTeX equations enclosed in `$$` or `\[ ... \]`.
- **Algorithms**: Pseudocode segments starting with `Algorithm:` or `Procedure:`.
- **Code Blocks**: Fenced triple-backtick markdown blocks.

---

## 3. Database Normalization (Deduplication)

To prevent text duplicates from bloating the database, the database structure is split:
- **`chunks`**: Stores unique text content, calculated SHA-256 hashes, character counts, word counts, and estimated reading times.
- **`chunk_mappings`**: Connects a unique chunk to a specific resource, course, unit, topic, course outcome, page numbers, and index. 

If the exact text hash already exists, or if a near-duplicate Jaccard token similarity score exceeds the threshold (default: `0.95`), the text content is not duplicated. Instead, a new mapping reference is created to point to the existing chunk.

---

## 4. How to Configure

Settings in `app/core/config.py`:
```env
CHUNK_STRATEGY=spacy             # spacy | nltk | regex
CHUNK_SIZE=1000                  # Character count target per chunk
CHUNK_OVERLAP=200                # Overlapping characters between adjacent chunks
MIN_CHUNK_CHAR_LENGTH=100        # Minimum length to accept
MAX_CHUNK_CHAR_LENGTH=4000       # Maximum length to accept
SPACY_MODEL=en_core_web_sm       # spaCy pipeline model
NEAR_DUPLICATE_SIMILARITY_THRESHOLD=0.95
```

---

## 5. Fail-Fast NLP Startup Verification

To ensure self-contained container deployments:
- No downloads are attempted at runtime.
- On startup, the application verifies that the required spaCy model and NLTK resource packages (`punkt` or `punkt_tab`) exist.
- If missing, the app fails fast with a critical `RuntimeError` at startup, ensuring setup issues are caught immediately.
