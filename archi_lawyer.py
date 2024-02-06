# -*- coding: utf-8 -*-
import os
import time
from typing import Dict, Optional

import streamlit as st
from langchain.chains import RetrievalQAWithSourcesChain
from langchain_community.vectorstores.pinecone import Pinecone as LangChainPinecone
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_openai.llms import OpenAI
from pinecone import Pinecone

from src.common.settings.base import Settings

# Load settings from a configuration file or environment variables
settings = Settings()

# Constants for the application
INDEX_NAME = "building-regulations"
PROMPT_TEMPLATE = """You're a specialized chatbot tasked with assisting architects by providing precise information on
British building regulations, as detailed in the provided document.

Ensure your answers are:
- Directly derived from the document's contents.
- Clear and concise, facilitating quick comprehension.
- Free of personal opinions or external advice.

In instances where the document does not contain the necessary information, or if you're uncertain, clearly state
this to the user, indicating that the response is based on best judgment rather than document specifics.

Question:"""
TEMPERATURE = 0.3


def initialize_pinecone_client(api_key: str) -> Pinecone:
    """Initializes and returns a Pinecone client."""
    return Pinecone(api_key=api_key)


def get_response(user_query: str) -> Dict[str, Optional[str]]:
    """Generates a response for the user's query based on British building regulations.

    Args:
        user_query (str): The user's query.

    Returns:
        Dict[str, Optional[str]]: A dictionary containing the 'answer' and optionally 'sources'.
    """
    full_query = PROMPT_TEMPLATE + user_query
    pc_client = initialize_pinecone_client(api_key=settings.pinecone.api_key)

    embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=settings.openai.api_key)
    index = pc_client.Index(INDEX_NAME)

    # Wait for index connection
    time.sleep(1)

    index.describe_index_stats()

    vectorstore = LangChainPinecone(index=index, embedding=embedding_model, text_key="context")
    llm = OpenAI(temperature=TEMPERATURE, openai_api_key=settings.openai.api_key)
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})

    qa_chain = RetrievalQAWithSourcesChain.from_chain_type(llm=llm, retriever=retriever)
    response = qa_chain(full_query)

    return response


# Streamlit interface setup
st.title("Architect Assistant Chatbot")
st.write(
    """
This chatbot is designed to assist with queries related to British building regulations.
Simply enter your question below and receive concise, regulation-based answers.

**Knowledge base**:
[The merged Approved Documents](https://www.gov.uk/guidance/building-regulations-and-approved-documents-index)
(last updated 8 March 2023)

**Sample Question**:
_In the context of food preparation areas, what are the key requirements for sink provision according to Requirement G6,
and how does it differ in dwellings and buildings other than dwellings?_

**Location of the answer in the document**:
Page 739 of the document
"""
)

# User input
user_query = st.text_area("Enter your question here:")
if st.button("Get Response"):
    if user_query:
        response = get_response(user_query)
        st.write("Answer:", response.get("answer", "No answer found."))
        sources = response.get("sources")
        if sources:
            st.write("Source:", os.path.basename(sources))
        else:
            st.write("No specific source cited.")
    else:
        st.error("Please enter a question.")
