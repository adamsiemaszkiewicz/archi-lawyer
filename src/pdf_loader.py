# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_core.documents import Document

from src.common.utils.logger import get_logger

_logger = get_logger(__name__)


class PDFLoader:
    """
    Processes PDF documents by loading and then splitting them into chunks.

    Attributes:
        filepath (Path): The file path of the PDF document to process.
        chunk_size (int): The size of each chunk in characters.
        chunk_overlap (int): The overlap between chunks in characters.
    """

    def __init__(self, filepath: Path, chunk_size: int, chunk_overlap: int):
        self.filepath = filepath
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_and_chunk_data(self) -> List[Document]:
        """
        Loads the PDF document and splits it into chunks.

        Returns:
            List[Document]: A list of document chunks.
        """
        _logger.info(f"Loading and chunking PDF: {self.filepath}")

        loader = UnstructuredPDFLoader(self.filepath.as_posix())
        data = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        chunks = splitter.split_documents(data)

        _logger.info(f"Generated {len(chunks)} chunks from the document.")

        return chunks
