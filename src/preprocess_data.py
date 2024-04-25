# -*- coding: utf-8 -*-
import re
from typing import List, Tuple

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
    return re.sub(pattern, r"\n", text, flags=re.MULTILINE)


def wrap_footer(text: str) -> str:
    # Define the pattern to find footer text after two newlines (with optional whitespace)
    pattern = r"(\n\s*\n)(\S[\s\S]*)$"

    # Function to wrap the footer text in a marker
    def wrapper(match: re.Match) -> str:
        return match.group(1) + "[Odniesienia - początek]\n" + match.group(2) + "\n[Odniesienia - koniec]\n"

    # Replace the pattern with wrapped footer text
    return re.sub(pattern, wrapper, text, flags=re.MULTILINE)


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
    return match is not None


def contains_new_paragraph(text: str) -> bool:
    # Define the regex pattern: 'Rozdział ' followed by one or more Arabic numeral characters
    pattern = r"R\s*o\s*z\s*d\s*z\s*i\s*a\s*ł\s+\d+"

    # Use re.search to find the pattern in the input string
    match = re.search(pattern, text)

    # Return True if a match is found, otherwise False
    return match is not None


def extract_appendices(document: Document) -> Tuple[Document, List[Document]]:
    # Define appendix header patterns
    appendix_headers = ["Załącznik nr 193", "Załącznik nr 294", "Załącznik nr 395"]

    # Pattern to capture content starting from each appendix header
    pattern = "|".join([re.escape(header) for header in appendix_headers])

    # Split the document content at each appendix header
    parts = re.split(f"({pattern})", document.page_content)

    # Initialize variables
    appendix_documents = []
    updated_content = parts[0]  # Start with initial content (before first appendix)
    appendix_idx = 1  # Start the appendix index at 1

    for i in range(1, len(parts), 2):
        appendix_content = parts[i + 1] if (i + 1) < len(parts) else ""

        # Create new metadata for the appendix document indicating its index and nullifying section/paragraph IDs
        new_metadata = document.metadata.copy()
        new_metadata["appendix_idx"] = appendix_idx
        new_metadata["section_id"] = None  # Nullify section_id
        new_metadata["paragraph_id"] = None  # Nullify paragraph_id

        # Add the appendix document, excluding the header text from the content
        appendix_documents.append(Document(page_content=appendix_content, metadata=new_metadata))

        # Increment the appendix index for the next appendix
        appendix_idx += 1

    # Create updated last document excluding the appendix sections
    updated_last_document = Document(page_content=updated_content, metadata=document.metadata)

    return updated_last_document, appendix_documents


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

    restructured_document = []
    section_idx = 0
    paragraph_idx = 0

    tmp_document = Document(
        page_content="",
        metadata={
            "section_id": section_idx,
            "paragraph_id": paragraph_idx,
            "document_id": f"{pdf_fp.name}",
            "pages": [],
        },
    )

    for page_no, document in enumerate(full_document):

        if contains_new_section(document.page_content):
            split_sections = re.split(r"D\s*Z\s*I\s*A\s*Ł\s+[IVXLCDM]+", document.page_content)

            if tmp_document.page_content:
                restructured_document.append(tmp_document)

            section_idx += 1
            paragraph_idx = 0

            # Start a new section document
            tmp_document = Document(
                page_content="",
                metadata={
                    "section_id": section_idx,
                    "paragraph_id": paragraph_idx,
                    "document_id": f"{pdf_fp.name}",
                    "pages": [page_no],
                },
            )

            if len(split_sections) > 1:
                tmp_document.page_content = split_sections[1]

        # Check for new paragraph within the current section
        if contains_new_paragraph(document.page_content):
            split_paragraphs = re.split(r"R\s*o\s*z\s*d\s*z\s*i\s*a\s*ł\s+\d+", document.page_content)

            if len(split_paragraphs) > 1:
                if tmp_document.page_content:
                    tmp_document.page_content += split_paragraphs[0]
                    restructured_document.append(tmp_document)

                paragraph_idx += 1

                # Start a new paragraph document
                tmp_document = Document(
                    page_content="",
                    metadata={
                        "section_id": section_idx,
                        "paragraph_id": paragraph_idx,
                        "document_id": f"{pdf_fp.name}",
                        "pages": [page_no],
                    },
                )
                tmp_document.page_content = split_paragraphs[1]
        else:
            tmp_document.page_content += document.page_content
            tmp_document.metadata["pages"].append(page_no)

        # Append the final document if it was not added yet
        if page_no == len(full_document) - 1:
            restructured_document.append(tmp_document)

    # Assuming restructured_document is the list containing the restructured documents
    last_document = restructured_document.pop(-1)
    updated_last_document, appendix_documents = extract_appendices(last_document)

    # Update the list
    restructured_document.append(updated_last_document)
    restructured_document.extend(appendix_documents)
