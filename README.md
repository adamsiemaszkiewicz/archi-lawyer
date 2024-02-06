# 🏛️⚖️🤖 Archi Lawyer Chatbot

## Overview

The Archi Lawyer Chatbot is a sophisticated tool designed to offer architects legal insights on building codes. This chatbot leverages RAG (Retrieval-Augmented Generation) to source information from actual regulation PDFs, providing architects with precise and reliable advice. It employs OpenAI API for natural language processing, Langchain for document retrieval, and Pinecone for efficient indexing and searching.

**Knowledge Base:** [Building Regulations and Approved Documents Index](https://www.gov.uk/guidance/building-regulations-and-approved-documents-index)

## Sample Usage

To get started, you can ask questions related to building regulations. For example:

**Sample Question:**
"In the context of food preparation areas, what are the key requirements for sink provision according to Requirement G6, and how does it differ in dwellings and buildings other than dwellings?"

**Location of the answer in the document:**
Page 739 of the document

## Getting Started

### Running Locally

1. Clone this repository to your local machine.

    ```bash
    git clone https://github.com/adamsiemaszkiewicz/archi-lawyer
    ```
2. Install the necessary dependencies and activate the environment.

    ```bash
    conda env create -f environments/archi_lawyer.yaml
    ```

5. Create a `secrets.toml` file in the `.streamlit/` directory with the OpenAI API & Pinecone credentials

   ```
   openai_api_key = "your_openai_api_key"
   pinecone_api_key = "your_pinecone_api_key"
   ```
4. Run the chatbot application.

    ```bash
   streamlit run archi_lawyer.py
    ```

### Running in the Browser

You can access the Archi Lawyer Chatbot in your browser by visiting [archi-lawyer.streamlit.app](https://archi-lawyer.streamlit.app).

## Technologies Used

- **OpenAI API:** Employs advanced natural language processing to understand and generate human-like responses, making it essential for interpreting complex legal queries.
- **Langchain:** Enables retrieval-augmented generation, sourcing precise information from regulatory documents to support accurate, context-aware advice.
- **Pinecone:** Provides efficient indexing and searching capabilities, ensuring rapid access to specific information within the extensive knowledge base of building regulations.

## License

This project is licensed under the [MIT License](LICENSE).
