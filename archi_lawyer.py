# -*- coding: utf-8 -*-
import time
from typing import Dict

import streamlit as st
from langchain.chains import RetrievalQAWithSourcesChain
from langchain_community.vectorstores.pinecone import Pinecone as LangChainPinecone
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_openai.llms import OpenAI
from pinecone import Pinecone

from src.common.settings.base import Settings

settings = Settings()
index_name = "thermal-baths"
prompt_template = """You're a helpful chatbot designed to assist architects by providing quick, accurate information
    related to Himalayan Thermal Baths competition.

    Please be exhaustive in your answers, but base them only on the information available in the document.
    Refrain from providing personal opinions or advice.
    If you're not sure about the answer or you use your own knowledge instead of basing your response on the contents
    of the document, please inform the user about it.

    The question:
    """
temperature = 0.5


def get_response(user_query: str) -> Dict[str, str]:
    """Generates a response for the user's query by appending it to a predefined prompt template.

    Args:
        user_query (str): The user's query.

    Returns:
        Dict[str, str]: A dictionary containing the response and source information.
    """

    # Append the user's query to the prompt template
    full_query = prompt_template + user_query

    pc = Pinecone(api_key=settings.pinecone.api_key)

    # Initialize OpenAI embeddings and Pinecone client
    embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=settings.openai.api_key)
    index = pc.Index(index_name)

    # Wait a moment for connection
    time.sleep(1)

    index.describe_index_stats()

    # Initialize LangChain Pinecone vector store
    vectorstore = LangChainPinecone(index=index, embedding=embedding_model, text_key="context")

    # Initialize LLM for generative QA
    llm = OpenAI(temperature=temperature, openai_api_key=settings.openai.api_key)

    qa = RetrievalQAWithSourcesChain.from_chain_type(llm=llm, retriever=vectorstore.as_retriever())
    response = qa(full_query)

    return response


# Streamlit interface setup
st.title("Architect Assistant Chatbot")

# User input
user_query = st.text_area("Enter your question here:")

if st.button("Get Response"):
    if user_query:
        response = get_response(user_query)
        answer = response["answer"]
        sources = response.get("sources")
        st.write(answer)
        st.write("Source(s):")
        st.write(sources)
    else:
        st.error("Please enter a question.")
