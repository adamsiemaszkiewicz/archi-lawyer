# -*- coding: utf-8 -*-
import time
import uuid
from typing import List

from langchain_core.documents import Document
from pinecone import Index, Pinecone, PodSpec
from retry import retry
from tqdm import tqdm

from src.common.utils.logger import get_logger, timed

_logger = get_logger(__name__)


class VectorStore:
    """
    Manages interactions with the Pinecone vector store, including index creation, document upsert, and querying.

    Attributes:
        pc (Pinecone): The Pinecone client to use for interactions.
        index_name (str): The name of the Pinecone index to interact with.
        dimension (int): The dimension of the vectors to store.
        metric (str): The distance metric used for vector comparison.
    """

    def __init__(self, api_key: str, index_name: str, dimension: int, metric: str) -> None:
        self.pc = Pinecone(api_key)
        self.index_name = index_name
        self.dimension = dimension
        self.metric = metric

        self.ensure_index()

    def ensure_index(self) -> None:
        """
        Ensures that the specified index exists in Pinecone, creating it if necessary.
        """
        _logger.info(f"Ensuring index {self.index_name} exists in Pinecone.")

        spec = PodSpec("gcp-starter")

        if self.index_name in self.pc.list_indexes().names():
            self.pc.delete_index(self.index_name)
            _logger.info(f"Deleted existing index: {self.index_name}")

        self.pc.create_index(name=self.index_name, dimension=self.dimension, spec=spec, metric=self.metric)

        # Wait for index to be initialized
        while not self.pc.describe_index(self.index_name).status["ready"]:
            time.sleep(1)

        _logger.info(f"Index {self.index_name} created or verified in Pinecone.")

    @timed
    def upsert_documents(self, data: List[Document], embeddings: List[List[float]], batch_size: int = 100) -> None:
        """
        Upserts documents and their embeddings into the Pinecone index.

        Args:
            data (List[Document]): The documents to upsert.
            embeddings (List[List[float]]): The embeddings corresponding to each document.
            batch_size (int): The number of documents to upsert in each batch.
        """
        _logger.info(f"Upserting {len(data)} documents into index: {self.index_name}")

        index = self.pc.Index(self.index_name)

        # Wait a second for connection
        time.sleep(1)

        expected_vectors = 0

        for i in tqdm(range(0, len(data), batch_size)):
            batch_data = data[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]
            self._upsert_batch(index=index, data=batch_data, embeddings=batch_embeddings)
            expected_vectors += len(batch_data)

            while index.describe_index_stats()["total_vector_count"] < expected_vectors:
                time.sleep(1)

            _logger.info(f"Batch upserted into Pinecone index.\n{index.describe_index_stats()}")

        _logger.info(f"A total of {len(data)} documents upserted into Pinecone index.\n{index.describe_index_stats()}")

    @retry(tries=10, delay=5, logger=_logger)
    def _upsert_batch(self, index: Index, data: List[Document], embeddings: List[List[float]]) -> None:
        """
        Helper function to upsert a batch of documents and their embeddings.

        Args:
            index (Index): The Pinecone index to upsert into.
            data (List[Document]): The batch of documents to upsert.
            embeddings (List[List[float]]): The embeddings corresponding to the batch of documents.
        """
        vectors_to_upsert = self._prepare_vectors_for_upsert(data, embeddings)
        try:
            index.upsert(vectors=vectors_to_upsert)
        except Exception as e:
            raise Exception(f"Failed to upsert vectors into Pinecone index: {e}")

    def _prepare_vectors_for_upsert(
        self, batch_data: List[Document], batch_embeddings: List[List[float]]
    ) -> List[dict]:
        """
        Prepares the vectors for upserting by assigning unique IDs and attaching metadata.

        Args:
            batch_data (List[Document]): The batch of documents to prepare.
            batch_embeddings (List[List[float]]): The embeddings corresponding to the batch of documents.

        Returns:
            List[dict]: A list of vectors ready for upserting, including IDs, values, and metadata.
        """
        vectors_to_upsert = []
        for doc, embedding in zip(batch_data, batch_embeddings):
            doc_id = str(uuid.uuid4())
            chunk_metadata = doc.metadata if doc.metadata else {}
            chunk_metadata.update({"context": doc.page_content})

            vectors_to_upsert.append({"id": doc_id, "values": embedding, "metadata": chunk_metadata})

        return vectors_to_upsert
