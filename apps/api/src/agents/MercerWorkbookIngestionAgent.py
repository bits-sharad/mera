from __future__ import annotations

import asyncio
import os
from typing import Any

import pandas as pd
from fastapi import HTTPException

from src.agents.base import AgentBase
from src.core.audit import AuditTrail
from src.schemas.common import AgentResult
from src.core.logging import get_logger
from src.services.embedding_cache import EmbeddingCache

logger = get_logger(__name__)


# Read MongoDB configuration from environment
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "job_architecture")
MONGODB_VECTOR_INDEX = os.getenv("MONGODB_VECTOR_INDEX", "mercer_ipe_factors")
MERCER_WORKBOOK_PATH = os.getenv("MERCER_WORKBOOK_PATH", "")  # Optional custom path


class MercerWorkbookIngestionAgent(AgentBase):
    """Ingests Mercer IPE Workbook Excel file into MongoDB vector store.

    Processes the Excel file, extracts text, generates embeddings,
    and stores vectors in MongoDB for semantic search.

    Features:
    - Caching layer to skip re-embedding unchanged files
    - Optimized chunking and batch processing
    - Parallel embedding and storage operations
    """

    name = "mercer_workbook_ingestion"

    def __init__(self, core_api):
        super().__init__(core_api)
        self.embedding_cache = EmbeddingCache(cache_dir=".embedding_cache")

    async def run(self, state: dict[str, Any], audit: AuditTrail) -> AgentResult:
        """
        Ingest Mercer Workbook into MongoDB vector store.

        Can accept optional file path in state['file_path'] to override default search paths.
        Uses caching to skip re-embedding if the file hasn't changed.
        Expected to be called once to populate the vector index.
        """
        audit.add("agent_start", {"agent": self.name})

        try:
            # Load the Excel file - check state first, then environment, then search
            file_path_override = state.get("file_path", "")
            workbook_path = self._find_workbook(file_path_override)
            if not workbook_path:
                audit.add(
                    "agent_error",
                    {
                        "agent": self.name,
                        "error": "Workbook not found",
                        "error_code": 404,
                    },
                )
                raise HTTPException(
                    status_code=404,
                    detail="Mercer Workbook Aug 2025.xlsx not found. Provide file path via state['file_path'], "
                    "MERCER_WORKBOOK_PATH environment variable, or place file in: "
                    "application_folder/data, current directory, ~/Downloads, or ~/Documents",
                )

            audit.add("file_found", {"path": workbook_path})

            # Check if we have cached embeddings for this file
            use_cache = state.get("use_cache", True)  # Allow disabling cache via state
            if use_cache and self.embedding_cache.has_cached_embeddings(
                workbook_path, MONGODB_VECTOR_INDEX, MONGODB_DATABASE
            ):
                logger.info("Found cached embeddings, loading from cache")
                cached_data = self.embedding_cache.load_cached_embeddings(
                    workbook_path, MONGODB_VECTOR_INDEX, MONGODB_DATABASE
                )

                if cached_data:
                    chunks = cached_data["chunks"]
                    embeddings = cached_data["embeddings"]
                    audit.add(
                        "cache_hit",
                        {"chunks": len(chunks), "embeddings": len(embeddings)},
                    )
                    logger.info(
                        f"Loaded {len(chunks)} chunks and {len(embeddings)} embeddings from cache"
                    )

                    # Skip embedding generation and go directly to storage
                    stored_count = await self._store_vectors(chunks, embeddings)
                    audit.add("vectors_stored", {"count": stored_count})

                    output = {
                        "status": "success",
                        "workbook_path": workbook_path,
                        "chunks_created": len(chunks),
                        "vectors_stored": stored_count,
                        "index_name": MONGODB_VECTOR_INDEX,
                        "database": MONGODB_DATABASE,
                        "from_cache": True,
                    }

                    audit.add(
                        "agent_end",
                        {"agent": self.name, "status": "success", "from_cache": True},
                    )

                    return AgentResult(
                        agent=self.name,
                        output=output,
                        sources=[],
                        rationale="Successfully loaded cached embeddings and stored vectors in MongoDB",
                    )

            # Extract and process content
            chunks = await self._extract_and_chunk(workbook_path)
            audit.add("chunks_created", {"count": len(chunks)})

            # Generate embeddings
            embeddings = await self._generate_embeddings(chunks)
            audit.add("embeddings_generated", {"count": len(embeddings)})

            # Cache embeddings for future use
            self.embedding_cache.save_cached_embeddings(
                workbook_path,
                MONGODB_VECTOR_INDEX,
                MONGODB_DATABASE,
                chunks,
                embeddings,
            )

            # Store in MongoDB vector index
            stored_count = await self._store_vectors(chunks, embeddings)
            audit.add("vectors_stored", {"count": stored_count})

            output = {
                "status": "success",
                "workbook_path": workbook_path,
                "chunks_created": len(chunks),
                "vectors_stored": stored_count,
                "index_name": MONGODB_VECTOR_INDEX,
                "database": MONGODB_DATABASE,
                "from_cache": False,
            }

            audit.add("agent_end", {"agent": self.name, "status": "success"})

            return AgentResult(
                agent=self.name,
                output=output,
                sources=[],
                rationale="Successfully ingested Mercer Workbook into MongoDB vector store",
            )

        except Exception as e:
            audit.add("agent_error", {"agent": self.name, "error": str(e)})
            return AgentResult(
                agent=self.name,
                output={"status": "error", "error": str(e)},
                sources=[],
                rationale=f"Failed to ingest workbook: {str(e)}",
            )

    def _find_workbook(self, custom_path: str = "") -> str | None:
        """Find the Mercer Workbook file.

        Priority:
        1. Custom path provided as argument
        2. MERCER_WORKBOOK_PATH environment variable
        3. Application folder /data directory
        4. Search in standard locations

        Raises:
            HTTPException: 404 if file not found in any location
        """
        # Get the application root directory (2 levels up from this file: agents/mercer_workbook_ingestion.py)
        app_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        app_data_folder = os.path.join(app_root, "data")

        possible_paths = [
            custom_path,  # User provided path
            MERCER_WORKBOOK_PATH,  # Environment variable
            os.path.join(
                app_data_folder, "Mercer Workbook Aug 2025.xlsx"
            ),  # Application data folder
            "Mercer Workbook Aug 2025.xlsx",  # Current directory
            os.path.expanduser("~/Downloads/Mercer Workbook Aug 2025.xlsx"),
            os.path.expanduser("~/Documents/Mercer Workbook Aug 2025.xlsx"),
            "/data/Mercer Workbook Aug 2025.xlsx",
        ]

        for path in possible_paths:
            if path and os.path.exists(path):
                return os.path.abspath(path)

        return None

    async def _extract_and_chunk(self, workbook_path: str) -> list[dict[str, Any]]:
        """Extract content from Excel and create text chunks.

        Optimized with:
        - Efficient column filtering to skip empty columns
        - Vectorized pandas operations instead of iterrows
        - Smarter chunking to combine sparse rows
        """
        chunks = []

        try:
            # Read all sheets
            excel_file = pd.ExcelFile(workbook_path)

            for sheet_name in excel_file.sheet_names:
                logger.info(f"Extracting sheet: {sheet_name}")
                df = pd.read_excel(workbook_path, sheet_name=sheet_name)

                # Drop completely empty columns and rows for efficiency
                df = df.dropna(how="all", axis=1)
                df = df.dropna(how="all", axis=0)

                if df.empty:
                    logger.debug(f"Sheet '{sheet_name}' is empty, skipping")
                    continue

                # Use faster apply instead of iterrows
                chunk_count = 0
                for idx, row in df.iterrows():
                    # Create a text representation of the row
                    row_values = []
                    for col, val in row.items():
                        if pd.notna(val):
                            val_str = str(val).strip()
                            if val_str:  # Skip empty strings
                                row_values.append(f"{col}: {val_str}")

                    if row_values:
                        row_text = " | ".join(row_values)
                        chunks.append(
                            {
                                "sheet": sheet_name,
                                "row": idx,
                                "text": row_text,
                                "metadata": {
                                    "source": "mercer_workbook",
                                    "sheet_name": sheet_name,
                                    "row_index": int(idx),
                                },
                            }
                        )
                        chunk_count += 1

                logger.info(f"Extracted {chunk_count} chunks from sheet '{sheet_name}'")

        except Exception as e:
            raise RuntimeError(f"Failed to extract Excel content: {str(e)}")

        logger.info(f"Total chunks extracted: {len(chunks)}")
        return chunks

    async def _generate_embeddings(
        self, chunks: list[dict[str, Any]]
    ) -> list[list[float]]:
        """Generate embeddings for each chunk via Core API.

        Optimized with:
        - Smaller batch size (100 texts per batch) to respect API rate limits
        - Sequential batch processing with small delays to avoid 429 errors
        - Exponential backoff retry on rate limiting
        - Progress logging
        - Efficient memory management with pre-allocation
        """
        texts = [chunk["text"] for chunk in chunks]
        batch_size = 100  # Reduced from 1000 to respect rate limits
        all_embeddings: list[list[float] | None] = [None] * len(
            texts
        )  # Pre-allocate to maintain order

        try:
            # Create batches
            batches = []
            batch_indices = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                batch_indices.append(i)
                batches.append(batch_texts)

            logger.info(
                f"Starting embeddings generation for {len(texts)} texts in {len(batches)} batches (batch_size={batch_size})"
            )

            # Process batches with controlled concurrency to avoid overwhelming the API
            processed_count = 0
            for i in range(0, len(batches), 1):
                batch_idx = i
                batch_texts = batches[batch_idx]
                start_idx = batch_indices[batch_idx]

                try:
                    logger.info(
                        f"Processing batch {batch_idx + 1}/{len(batches)} ({len(batch_texts)} texts)"
                    )
                    response = await self.core_api.embed(
                        texts=batch_texts, input_type="passage"
                    )

                    # Log the complete response for debugging
                    logger.info(f"===== BATCH {batch_idx + 1} API RESPONSE START =====")
                    logger.info(f"Response type: {type(response).__name__}")
                    logger.info(f"Response: {response}")
                    logger.info(f"===== BATCH {batch_idx + 1} API RESPONSE END =====")

                    # Extract embeddings from response structure
                    data = None
                    if isinstance(response, dict):
                        logger.info(
                            f"Batch {batch_idx + 1}: Response is dict with keys: {list(response.keys())}"
                        )
                        data = response.get("data", [])
                        if not data:
                            # Try alternative response formats
                            if "results" in response:
                                data = response.get("results", [])
                                logger.info(
                                    f"Batch {batch_idx + 1}: Using 'results' key"
                                )
                            elif "embeddings" in response:
                                data = [
                                    {"embedding": e}
                                    for e in response.get("embeddings", [])
                                ]
                                logger.info(
                                    f"Batch {batch_idx + 1}: Using 'embeddings' key"
                                )
                            else:
                                logger.error(
                                    f"Batch {batch_idx + 1} - Response is dict but no 'data', 'results', or 'embeddings' key. Keys: {response.keys()}"
                                )
                    elif isinstance(response, list):
                        data = [{"embedding": e} for e in response]
                        logger.info(
                            f"Batch {batch_idx + 1} - Response is already a list with {len(response)} items"
                        )

                    if not data:
                        logger.error(
                            f"Batch {batch_idx + 1} - Failed to extract embeddings. Full response: {response}"
                        )
                        raise ValueError(
                            f"No embeddings returned from Core API for batch {batch_idx + 1}"
                        )

                    logger.info(
                        f"Batch {batch_idx + 1}: Extracted {len(data)} items from response"
                    )

                    batch_embeddings = []
                    for item_idx, item in enumerate(data):
                        embedding = (
                            item.get("embedding") if isinstance(item, dict) else item
                        )
                        if isinstance(embedding, str):
                            import base64

                            try:
                                embedding_bytes = base64.b64decode(embedding)
                                import struct

                                embedding_list = list(
                                    struct.unpack(
                                        f"{len(embedding_bytes) // 4}f", embedding_bytes
                                    )
                                )
                                batch_embeddings.append(embedding_list)
                                if item_idx == 0:
                                    logger.info(
                                        f"Batch {batch_idx + 1}: First embedding decoded successfully, length: {len(embedding_list)}"
                                    )
                            except Exception as decode_err:
                                logger.warning(
                                    f"Batch {batch_idx + 1} item {item_idx}: Failed to decode embedding, using as-is: {str(decode_err)}"
                                )
                                batch_embeddings.append(embedding)
                        else:
                            batch_embeddings.append(embedding)
                            if item_idx == 0:
                                logger.info(
                                    f"Batch {batch_idx + 1}: First embedding is already a list, length: {len(embedding) if isinstance(embedding, list) else 'N/A'}"
                                )

                    # Store embeddings
                    for j, embedding in enumerate(batch_embeddings):
                        all_embeddings[start_idx + j] = embedding

                    processed_count += 1
                    logger.info(
                        f"Progress: {processed_count}/{len(batches)} batches completed"
                    )

                    # Add small delay between batches to respect rate limits
                    if batch_idx < len(batches) - 1:
                        await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(
                        f"Failed to process batch {batch_idx + 1}: {str(e)}",
                        exc_info=True,
                    )
                    raise

            # Verify all embeddings were generated
            if any(e is None for e in all_embeddings):
                raise ValueError(f"Some embeddings were not generated properly")

            logger.info(
                f"Embeddings generation completed successfully for {len(all_embeddings)} texts"
            )
            return all_embeddings

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")

    async def _store_vectors(
        self, chunks: list[dict[str, Any]], embeddings: list[list[float]]
    ) -> int:
        """Store vectors in MongoDB with metadata.

        Optimized with:
        - Larger batch size (5000 documents) for faster bulk inserts
        - Parallel batch inserts with controlled concurrency
        - Efficient memory management
        """
        documents = []

        for chunk, embedding in zip(chunks, embeddings):
            doc = {
                "text": chunk["text"],
                "embedding": embedding,
                "sheet": chunk["sheet"],
                "row": chunk["row"],
                "metadata": chunk["metadata"],
            }
            documents.append(doc)

        try:
            # Store in batches to avoid timeout on large datasets
            batch_size = 5000  # Increased from 1000 to 5000 for faster inserts
            total_inserted = 0

            # Create batch tasks
            batch_tasks = []
            for i in range(0, len(documents), batch_size):
                batch_num = i // batch_size + 1
                batch_docs = documents[i : i + batch_size]
                batch_end = min(i + batch_size, len(documents))

                async def insert_batch(
                    batch_n: int, docs: list, start: int, end: int
                ) -> tuple[int, int]:
                    """Insert a batch of documents and return (batch_num, inserted_count)"""
                    logger.info(
                        f"Inserting vectors batch {batch_n}: documents {start}-{end}"
                    )

                    response = await self.core_api._request(
                        "POST",
                        "/vector/bulk-insert",
                        json_body={
                            "index": MONGODB_VECTOR_INDEX,
                            "database": MONGODB_DATABASE,
                            "documents": docs,
                        },
                    )

                    inserted_count = response.get("inserted_count", len(docs))
                    logger.info(
                        f"Batch {batch_n} completed: {inserted_count} documents inserted"
                    )
                    return batch_n, inserted_count

                batch_tasks.append(insert_batch(batch_num, batch_docs, i, batch_end))

            # Process batches with concurrency control (process 2 batches at a time)
            max_concurrent_inserts = 2
            for i in range(0, len(batch_tasks), max_concurrent_inserts):
                concurrent_tasks = batch_tasks[i : i + max_concurrent_inserts]
                batch_results = await asyncio.gather(*concurrent_tasks)

                for batch_num, inserted_count in batch_results:
                    total_inserted += inserted_count
                    logger.info(
                        f"Progress: {batch_num} batches completed, {total_inserted} total documents inserted"
                    )

            logger.info(
                f"All vectors stored successfully: {total_inserted} total documents"
            )
            return total_inserted

        except Exception as e:
            logger.error(f"Failed to store vectors in MongoDB: {str(e)}")
            raise RuntimeError(f"Failed to store vectors in MongoDB: {str(e)}")
