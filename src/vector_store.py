# -*- coding: utf-8 -*-
import time
from pathlib import Path
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_core.documents import Document
from langchain_openai.embeddings import OpenAIEmbeddings
from pinecone import Pinecone, PodSpec

from src.common.consts.directories import DATA_DIR
from src.common.settings.base import Settings
from src.common.utils.logger import timed


@timed
def load_pdf_data(filepath: Path, chunk_size: int, chunk_overlap: int) -> List[Document]:
    loader = UnstructuredPDFLoader(filepath)
    data = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    data = splitter.split_documents(data)

    return data


def create_embeddings(index_name: str, data: List[Document], st_api_key: str, oai_api_key: str) -> None:

    pc = Pinecone(st_api_key)
    spec = PodSpec("gcp-starter")

    if index_name in pc.list_indexes().names():
        pc.delete_index(index_name)

    pc.create_index(name=index_name, dimension=1536, metric="euclidean", spec=spec)

    while not pc.describe_index(index_name).status["ready"]:
        time.sleep(1)

    embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=oai_api_key)

    index = pc.Index(index_name)
    time.sleep(1)

    index.describe_index_stats()
    # Generate embeddings for each document
    texts = [doc.page_content for doc in data]
    embeddings = embedding_model.embed_documents(texts)

    # Prepare vectors for upsertion, ensuring ids are strings
    vectors_to_upsert = [{"id": str(n), "values": embedding} for n, embedding in enumerate(embeddings)]

    # Upsert vectors into the Pinecone index
    index.upsert(vectors=vectors_to_upsert)


if __name__ == "__main__":
    settings = Settings()

    filename = "NonA_Well-being_Thermal Baths.pdf"
    index_name = "thermal-baths"
    # filename = "The_Merged_Approved_Documents_Mar23.pdf"
    document_fp = DATA_DIR / filename
    data = load_pdf_data(filepath=document_fp, chunk_size=1000, chunk_overlap=100)

    create_embeddings(
        index_name=index_name, data=data, st_api_key=settings.st.api_key, oai_api_key=settings.oai.api_key
    )
