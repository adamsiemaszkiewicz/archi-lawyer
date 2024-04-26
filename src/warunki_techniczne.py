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
    """Wraps the footer of the text within XML tags for references."""
    # Define the pattern to find footer text after two newlines (with optional whitespace)
    pattern = r"(\n\s*\n)(\S[\s\S]*)$"

    # Function to wrap the footer text in XML tags
    def wrapper(match: re.Match) -> str:
        return match.group(1) + "<przypisy>\n" + match.group(2) + "\n</przypisy>\n"

    # Replace the pattern with wrapped footer text in XML tags
    updated_text = re.sub(pattern, wrapper, text, flags=re.MULTILINE)
    return updated_text


def link_annotations(text: str) -> str:
    # Pattern to find 'word ending with [number)]' where 'word' starts with alphabetic characters
    pattern = r"(\b[a-zA-Z]+\w*)(\d+\))"
    # Replacement pattern that formats the word and number into a reference format
    result = re.sub(pattern, r"\1 <przypis>\2</przypis>)", text)
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
    """Restructures a list of documents by sections, adding XML headers to section names and titles."""
    restructured_document = []
    section_idx = 0
    section_pattern = r"(D\s*Z\s*I\s*A\s*Ł\s+[IVXLCDM]+)"

    # Initialize an empty Document to start with the introductory header
    header = "<dział>\n  <nazwa>WSTĘP</nazwa>\n</dział>\n"
    current_section = Document(page_content=header, metadata={})

    for doc in documents:
        page_content = doc.page_content
        search_result = re.search(section_pattern, page_content)

        if search_result:
            index_start = search_result.start()
            index_end = search_result.end()

            # Extract the title immediately following the section header
            title_start = page_content.find("\n", index_end) + 1
            title_end = page_content.find("\n", title_start)
            title = page_content[title_start:title_end].strip()

            content_before = page_content[:index_start]
            content_after = page_content[title_end + 1 :]

            if content_before.strip():  # Ensure not to add empty strings
                current_section.page_content += content_before

            if current_section.page_content:
                restructured_document.append(current_section)

            # Start a new section with XML-wrapped name and title
            section_idx += 1
            roman_num = int_to_roman(section_idx)
            section_name = "DZIAŁ"
            header = f"<dział>\n  <nazwa>{section_name} {roman_num}</nazwa>\n  <tytuł>{title}</tytuł>\n</dział>\n"

            current_section = Document(
                page_content=header + content_after,
                metadata={"section_id": section_idx, "document_id": doc.metadata.get("document_id", "")},
            )
        else:
            current_section.page_content += page_content + "\n"

    if current_section.page_content:
        restructured_document.append(current_section)

    return restructured_document


def restructure_documents_by_paragraphs(documents: List[Document]) -> List[Document]:
    paragraph_pattern = r"R\s*o\s*z\s*d\s*z\s*i\s*ał\s+\d+[a-z]?"
    restructured_documents = []
    paragraph_idx = 0

    for doc in documents:
        page_content = doc.page_content
        paragraph_splits = list(re.finditer(paragraph_pattern, page_content))

        if not paragraph_splits:
            # No paragraphs found, treat whole content as a single paragraph
            doc.metadata["paragraph_id"] = paragraph_idx
            restructured_documents.append(doc)
            continue

        # Process each split point
        start_idx = 0
        for match in paragraph_splits:
            end_idx = match.start()
            if start_idx != end_idx:
                # Add the previous paragraph
                paragraph_content = page_content[start_idx:end_idx].strip()
                if paragraph_content:
                    restructured_documents.append(
                        Document(page_content=paragraph_content, metadata={"paragraph_id": paragraph_idx})
                    )
                    paragraph_idx += 1

            start_idx = end_idx

        # Add the last paragraph in the document
        last_paragraph = page_content[start_idx:].strip()
        if last_paragraph:
            restructured_documents.append(
                Document(page_content=last_paragraph, metadata={"paragraph_id": paragraph_idx})
            )
            paragraph_idx += 1

    return restructured_documents


if __name__ == "__main__":
    pdf_fp = DATA_DIR / "D20191065.pdf"

    loader = PyPDFLoader(file_path=pdf_fp.as_posix())
    original_documents = loader.load()

    preprocessed_documents = preprocess_documents(original_documents)

    restructured_sections = restructure_documents_by_sections(preprocessed_documents)
    restructured_paragraphs = restructure_documents_by_paragraphs(restructured_sections)
