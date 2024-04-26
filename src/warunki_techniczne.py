# -*- coding: utf-8 -*-
import logging
import re
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents.base import Document

from src.common.consts.directories import DATA_DIR

logging.basicConfig(level=logging.INFO)


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


def preprocess_documents(documents: List[Document]) -> List[Document]:
    for doc in documents:
        page_content = doc.page_content

        page_content = remove_header(page_content)
        page_content = strip_prefix(page_content)
        page_content = wrap_footer(page_content)
        page_content = link_annotations(page_content)
        page_content = merge_newline_divided_words(page_content)

        doc.page_content = page_content.strip()

    return documents


def contains_new_section(text: str) -> bool:
    # Define the regex pattern: 'DZIAŁ ' followed by one or more Roman numeral characters
    pattern = r"D\s*Z\s*I\s*A\s*Ł\s+[IVXLCDM]+"

    # Use re.search to find the pattern in the input string
    match = re.search(pattern, text)

    # Return True if a match is found, otherwise False
    return bool(match)


def int_to_roman(num: int) -> str:
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syms[i]
            num -= val[i]
        i += 1
    return roman_num


def restructure_documents_by_sections(documents: List[Document]) -> List[Document]:
    """
    Restructure documents by sections, adding a formatted header to each section.
    For section 0, the header is 'WSTĘP', and for others, it is 'DZIAŁ XXX' with Roman numerals.

    Args:
        documents (List[Document]): List of documents to restructure.

    Returns:
        List[Document]: List of restructured documents with section headers.
    """
    restructured_document = []
    section_idx = 0
    current_page_number = 0  # Tracking current page number

    # Initial section start with an introductory header
    header = "WSTĘP\n---------\n\n"
    current_section = Document(
        page_content=header, metadata={"section_id": section_idx, "document_id": pdf_fp.name, "pages": []}
    )

    section_pattern = r"(D\s*Z\s*I\s*A\s*Ł\s+[IVXLCDM]+)"  # Pattern to match the whole 'DZIAŁ XXX' text

    for doc in documents:
        current_page_number += 1  # Increment page number as we go through each document
        page_content = doc.page_content
        search_result = re.search(section_pattern, page_content)

        if search_result:
            index_start = search_result.start()
            index_end = search_result.end()

            content_before = page_content[:index_start]
            content_after = page_content[index_end:]

            if content_before.strip():  # Ensure not to add empty strings
                current_section.page_content += content_before
                current_section.metadata["pages"].append(current_page_number)

            if current_section.page_content:
                restructured_document.append(current_section)

            # Start a new section
            section_idx += 1
            roman_num = int_to_roman(section_idx) if section_idx > 0 else "WSTĘP"
            header = f"DZIAŁ {roman_num}\n---------\n\n" if section_idx > 0 else "WSTĘP\n---------\n\n"
            current_section = Document(
                page_content=header + content_after,
                metadata={"section_id": section_idx, "document_id": pdf_fp.name, "pages": [current_page_number]},
            )
        else:
            current_section.page_content += page_content + "\n"
            current_section.metadata["pages"].append(current_page_number)

    if current_section.page_content:
        current_section.metadata["pages"] = list(set(current_section.metadata["pages"]))
        current_section.metadata["pages"].sort()
        restructured_document.append(current_section)

    return restructured_document


def restructure_by_paragraphs(documents: List[Document]) -> List[Document]:
    restructured_paragraphs = []
    paragraph_idx = 0

    for section in documents:
        section_number_roman = int_to_roman(section.metadata["section_id"])
        current_paragraph = Document(
            page_content="",
            metadata={
                "paragraph_id": paragraph_idx,
                "section_id": section.metadata["section_id"],
                "document_id": section.metadata["document_id"],
                "pages": [],
            },
        )

        page_content = section.page_content
        page_numbers = section.metadata["pages"]

        # Pattern to match 'Rozdział ' followed by numbers possibly followed by a letter
        paragraph_pattern = r"R\s*o\s*z\s*d\s*z\s*i\s*a\s*ł\s+(\d+[a-zA-Z]?)"
        matches = list(re.finditer(paragraph_pattern, page_content))

        last_index = 0
        for match in matches:
            index_start = match.start()
            index_end = match.end()

            content_before = page_content[last_index:index_start]
            chapter_number = match.group(1).strip()

            header = f"DZIAŁ {section_number_roman}\nRozdział {chapter_number}\n---------------\n"

            if content_before.strip():
                current_paragraph.page_content = header + content_before
                current_paragraph.metadata["pages"] = page_numbers
                restructured_paragraphs.append(current_paragraph)

            paragraph_idx += 1
            current_paragraph = Document(
                page_content="",
                metadata={
                    "paragraph_id": paragraph_idx,
                    "section_id": section.metadata["section_id"],
                    "document_id": section.metadata["document_id"],
                    "pages": page_numbers,
                },
            )

            last_index = index_end

        # Append the remainder of the section content after the last match
        remainder = page_content[last_index:]
        if remainder.strip():
            header = (
                f"DZIAŁ {section_number_roman}\n"
                f"Rozdział {matches[-1].group(1).strip() if matches else '1'}\n"
                "---------------\n"
            )
            current_paragraph.page_content = header + remainder
            current_paragraph.metadata["pages"] = page_numbers
            restructured_paragraphs.append(current_paragraph)

    return restructured_paragraphs


if __name__ == "__main__":
    pdf_fp = DATA_DIR / "D20191065.pdf"

    loader = PyPDFLoader(file_path=pdf_fp.as_posix())
    original_documents = loader.load()

    preprocessed_documents = preprocess_documents(original_documents)

    restructured_sections = restructure_documents_by_sections(preprocessed_documents)
    restructured_paragraphs = restructure_by_paragraphs(restructured_sections)
