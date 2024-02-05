# -*- coding: utf-8 -*-
import time
import uuid
from pathlib import Path
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_community.vectorstores.pinecone import Pinecone as LangChainPinecone
from langchain_core.documents import Document
from langchain_openai.embeddings import OpenAIEmbeddings
from pinecone import Pinecone, PodSpec

from src.common.consts.directories import DATA_DIR
from src.common.settings.base import Settings
from src.common.utils.logger import get_logger, timed

_logger = get_logger(__name__)


@timed
def load_pdf_data(filepath: Path, chunk_size: int, chunk_overlap: int) -> List[Document]:
    loader = UnstructuredPDFLoader(filepath.as_posix())
    data = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    data = splitter.split_documents(data)

    return data


def create_embeddings(index_name: str, data: List[Document], pc_api_key: str, oai_api_key: str) -> None:

    pc = Pinecone(pc_api_key)
    spec = PodSpec("gcp-starter")

    if index_name in pc.list_indexes().names():
        pc.delete_index(index_name)

    pc.create_index(name=index_name, dimension=1536, spec=spec, metric="cosine")

    while not pc.describe_index(index_name).status["ready"]:
        time.sleep(1)

    embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=oai_api_key)

    index = pc.Index(index_name)
    time.sleep(1)

    _logger.info(index.describe_index_stats())

    # Generate embeddings for each document
    texts = [doc.page_content for doc in data]
    embeddings = embedding_model.embed_documents(texts)

    vectors_to_upsert = []
    for n, embedding in enumerate(embeddings):
        doc_id = str(uuid.uuid4())  # Generate a UUID for each document chunk
        chunk_metadata = data[n].metadata  # Assuming 'data' has a 'metadata' attribute with 'chunk', 'text', and 'url'
        chunk_metadata.update({"context": texts[n]})

        vectors_to_upsert.append({"id": doc_id, "values": embedding, "metadata": chunk_metadata})

    # Upsert vectors into the Pinecone index
    index.upsert(vectors=vectors_to_upsert)

    while index.describe_index_stats()["total_vector_count"] == 0:
        time.sleep(1)

    _logger.info(index.describe_index_stats())

    index = pc.Index(index_name)

    vectorstore = LangChainPinecone(index=index, embedding=embedding_model.embed_query, text_key="context")

    query = "What is the naming convention for submission files?"

    docs = vectorstore.similarity_search(query, k=3)  # our search query  # return 3 most relevant docs

    _logger.info(docs)


if __name__ == "__main__":
    settings = Settings()

    filename = "NonA_Well-being_Thermal Baths.pdf"
    index_name = "competition-test"
    # filename = "The_Merged_Approved_Documents_Mar23.pdf"
    document_fp = DATA_DIR / filename
    data = load_pdf_data(filepath=document_fp, chunk_size=1000, chunk_overlap=100)

    create_embeddings(
        index_name=index_name, data=data, pc_api_key=settings.pinecone.api_key, oai_api_key=settings.openai.api_key
    )
