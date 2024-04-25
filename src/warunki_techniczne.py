# -*- coding: utf-8 -*-
import re
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents.base import Document

from src.common.consts.directories import DATA_DIR


def strip_prefix(text: str) -> str:
    # Define the prefix pattern with flexibility for white spaces
    prefix_pattern = (
        r"^\s*Załącznik\s*do\s*obwieszczenia\s*Ministra\s*Inwestycji\s*i\s*Rozwoju\s*"
        r"z\s*dnia\s*8\s*kwietnia\s*2019\s*r\.\s*\(poz\.\s*1065\)\s*"
    )

    # Use regex to check if the string starts with the prefix pattern
    if re.match(prefix_pattern, text):
        # If it does, strip the prefix
        stripped_string = re.sub(prefix_pattern, "", text)
        return stripped_string.strip()  # Remove any remaining white spaces

    # If the prefix is not found, return the original string
    return text


def remove_header(text: str) -> str:
    # Define the pattern, accounting for variable digits and flexible whitespace/newlines
    pattern = r"\s*\n*Dziennik Ustaw –\s*\d+\s*– Poz\. 1065\s*\n*"

    # Replace the pattern with an empty string to remove it
    updated_text = re.sub(pattern, r"\n", text, flags=re.MULTILINE)
    return updated_text


def wrap_footer(text: str) -> str:
    # Define the pattern to find footer text after two newlines (with optional whitespace)
    pattern = r"(\n\s*\n)(\S[\s\S]*)$"

    # Function to wrap the footer text in a marker
    def wrapper(match: re.Match) -> str:
        return match.group(1) + "[Odniesienia - początek]\n" + match.group(2) + "\n[Odniesienia - koniec]\n"

    # Replace the pattern with wrapped footer text
    updated_text = re.sub(pattern, wrapper, text, flags=re.MULTILINE)

    return updated_text


def link_annotations(text: str) -> str:
    # Pattern to find 'word ending with [number)]' where 'word' starts with alphabetic characters
    pattern = r"(\b[a-zA-Z]+\w*)(\d+\))"
    # Replacement pattern that formats the word and number into a reference format
    result = re.sub(pattern, r"\1 (patrz Odniesienie \2)", text)
    # Adjust the parenthesis in the result to correctly format numbers
    result = re.sub(r"(\d+)\)", r"\1", result)
    return result


def merge_newline_divided_words(text: str) -> str:
    # Regex pattern to find words split across newlines by a hyphen
    pattern = r"(\w+)-\s*\n\s*(\w+)"

    # Function to replace each match
    def replacer(match: re.Match) -> str:
        # Merge the parts without the hyphen
        return match.group(1) + match.group(2)

    # Substitute newline divided words using the replacer function
    merged_text = re.sub(pattern, replacer, text)
    return merged_text


def contains_new_section(text: str) -> bool:
    # Define the regex pattern: 'DZIAŁ ' followed by one or more Roman numeral characters
    pattern = r"D\s*Z\s*I\s*A\s*Ł\s+[IVXLCDM]+"

    # Use re.search to find the pattern in the input string
    match = re.search(pattern, text)

    # Return True if a match is found, otherwise False
    return bool(match)


def restructure_documents_by_sections(full_document: List[Document]) -> List[Document]:
    restructured_document = []
    section_idx = 0
    current_page_number = 0  # Tracking current page number

    current_section = Document(
        page_content="",
        metadata={"section_id": section_idx, "document_id": pdf_fp.name, "pages": []},  # This will hold page numbers
    )

    # Update pattern to match the whole 'DZIAŁ XXX' text
    section_pattern = r"(D\s*Z\s*I\s*A\s*Ł\s+[IVXLCDM]+)"

    for document in full_document:
        current_page_number += 1  # Increment page number as we go through each document
        page_content = document.page_content
        search_result = re.search(section_pattern, page_content)

        if search_result:
            # Split the text exactly at the section pattern, excluding the separator
            index_start = search_result.start()
            index_end = search_result.end()

            # Content before the section header, excluding the separator
            content_before = page_content[:index_start]
            # Content starting after the section header
            content_after = page_content[index_end:]

            # Append content before the section header to the current section
            if content_before.strip():  # Ensure not to add empty strings
                current_section.page_content += content_before
                current_section.metadata["pages"].append(current_page_number)

                if current_section.page_content:
                    restructured_document.append(current_section)

            # Start a new section
            section_idx += 1
            current_section = Document(
                page_content=content_after,
                metadata={
                    "section_id": section_idx,
                    "document_id": pdf_fp.name,
                    "pages": [current_page_number],  # Start new section with current page
                },
            )
        else:
            # If no new section is found, continue appending to the current section
            current_section.page_content += page_content + "\n"
            current_section.metadata["pages"].append(current_page_number)

    # Add the last section to the list
    if current_section.page_content:
        # Ensure no duplicates in the page list
        current_section.metadata["pages"] = list(set(current_section.metadata["pages"]))
        current_section.metadata["pages"].sort()
        restructured_document.append(current_section)

    # Sort and remove duplicates from page lists in all sections
    for section in restructured_document:
        section.metadata["pages"] = list(set(section.metadata["pages"]))
        section.metadata["pages"].sort()

    return restructured_document


if __name__ == "__main__":
    pdf_fp = DATA_DIR / "D20191065.pdf"

    loader = PyPDFLoader(file_path=pdf_fp.as_posix())
    full_document = loader.load()

    for document in full_document:
        page_content = document.page_content

        page_content = remove_header(page_content)
        page_content = strip_prefix(page_content)
        page_content = wrap_footer(page_content)
        page_content = link_annotations(page_content)
        page_content = merge_newline_divided_words(page_content)

        document.page_content = page_content

    restructured_document = restructure_documents_by_sections(full_document)
