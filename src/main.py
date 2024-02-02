# -*- coding: utf-8 -*-
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain_core.language_models.llms import BaseLLM

from src.common.settings.base import Settings


class Model:
    def __init__(self, api_key: str, temperature: float = 0.2) -> None:
        self.api_key = api_key
        self.model = OpenAI(temperature=temperature, openai_api_key=api_key)


def main(model: BaseLLM, issue_description: str) -> str:

    template = """You're a helpful chatbot designed to assist architects by providing quick, accurate legal information
        related to architectural practices, regulations, contracts, zoning laws, and more.
        Please provide assistance with the following issue: {issue_description}"""

    prompt = PromptTemplate(input_variables=["issue_description"], template=template)

    name_chain = LLMChain(llm=model, prompt=prompt, output_key="response")

    response = name_chain({"issue_description": issue_description})

    return response["response"]


if __name__ == "__main__":
    settings = Settings()

    model = Model(api_key=settings.oai.api_key).model

    issue_description = "What's the allowed width of the corridor in the residential building?"

    response = main(model=model, issue_description=issue_description)
