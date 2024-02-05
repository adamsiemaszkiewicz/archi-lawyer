# -*- coding: utf-8 -*-
import time
import uuid
from typing import List

from langchain_core.documents import Document
from pinecone import Pinecone, PodSpec

from .common.utils.logger import get_logger, timed

_logger = get_logger(__name__)


class VectorStore:
    """
    Manages interactions with the Pinecone vector store, including index creation, document upsert, and querying.

    Attributes:
        pc (Pinecone): The Pinecone client to use for interactions.
        index_name (str): The name of the Pinecone index to interact with.
        dimension (int): The dimension of the vectors to store.
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
    def upsert_documents(self, data: List[Document], embeddings: List[List[float]]) -> None:
        """
        Upserts documents and their embeddings into the Pinecone index.

        Args:
            data (List[Document]): The documents to upsert.
            embeddings (List[List[float]]): The embeddings corresponding to each document.
        """
        _logger.info(f"Upserting {len(data)} documents into index: {self.index_name}")

        index = self.pc.Index(self.index_name)

        # Wait a second for connection
        time.sleep(1)

        _logger.info(index.describe_index_stats())

        vectors_to_upsert = [
            {"id": str(uuid.uuid4()), "values": embedding, "metadata": doc.metadata}
            for doc, embedding in zip(data, embeddings)
        ]
        index.upsert(vectors=vectors_to_upsert)

        _logger.info("Documents upserted into Pinecone index.")
