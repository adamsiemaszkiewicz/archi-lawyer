# -*- coding: utf-8 -*-
from src.common.consts.directories import DATA_DIR
from src.common.settings.base import Settings
from src.common.utils.logger import get_logger
from src.embed_gen import EmbeddingGenerator
from src.pdf_loader import PDFLoader
from src.vector_store import VectorStore

_logger = get_logger(__name__)


def main() -> None:
    settings = Settings()

    filename = "NonA_Well-being_Thermal Baths.pdf"
    document_fp = DATA_DIR / filename
    chunk_size = 1000
    chunk_overlap = 100

    index_name = "thermal-baths"
    embedding_model = "text-embedding-ada-002"
    embedding_dimension = 1536
    metric = "cosine"

    _logger.info(f"Processing PDF: {filename}")
    pdf_processor = PDFLoader(filepath=document_fp, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    documents = pdf_processor.load_and_chunk_data()

    _logger.info("Generating document embeddings.")
    embedding_generator = EmbeddingGenerator(api_key=settings.openai.api_key, model=embedding_model)
    embeddings = embedding_generator.generate_embeddings(documents)

    _logger.info("Upserting documents into Pinecone index.")
    vector_store = VectorStore(
        api_key=settings.pinecone.api_key, index_name=index_name, dimension=embedding_dimension, metric=metric
    )
    vector_store.upsert_documents(data=documents, embeddings=embeddings)


if __name__ == "__main__":
    main()
