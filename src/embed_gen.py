# -*- coding: utf-8 -*-
from typing import List

from langchain_core.documents import Document
from langchain_openai.embeddings import OpenAIEmbeddings

from src.common.utils.logger import get_logger

_logger = get_logger(__name__)


class EmbeddingGenerator:
    """
    Generates embeddings for a list of documents using the OpenAI API.

    Attributes:
        embedding_model (OpenAIEmbeddings): The OpenAI embedding model to use.
    """

    def __init__(self, api_key: str, model: str):
        self.embedding_model = OpenAIEmbeddings(model=model, openai_api_key=api_key)

    def generate_embeddings(self, documents: List[Document]) -> List[List[float]]:
        """
        Generates embeddings for each document in the list.

        Args:
            documents (List[Document]): A list of documents to generate embeddings for.

        Returns:
            List[List[float]]: A list of embeddings, one per document.
        """
        _logger.info(f"Generating embeddings for {len(documents)} documents.")

        texts = [doc.page_content for doc in documents]
        embeddings = self.embedding_model.embed_documents(texts)

        _logger.info("Embeddings generated.")

        return embeddings
