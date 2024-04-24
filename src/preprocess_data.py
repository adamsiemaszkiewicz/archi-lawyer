
import re

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents.base import Document
from src.common.consts.directories import DATA_DIR

def strip_prefix(text):
    # Define the prefix pattern with flexibility for white spaces
    prefix_pattern = r"^\s*Załącznik\s*do\s*obwieszczenia\s*Ministra\s*Inwestycji\s*i\s*Rozwoju\s*z\s*dnia\s*8\s*kwietnia\s*2019\s*r\.\s*\(poz\.\s*1065\)\s*"
    
    # Use regex to check if the string starts with the prefix pattern
    if re.match(prefix_pattern, text):
        # If it does, strip the prefix
        stripped_string = re.sub(prefix_pattern, "", text)
        return stripped_string.strip()  # Remove any remaining white spaces
        
    # If the prefix is not found, return the original string
    return text

def remove_header(text):
    # Define the pattern, accounting for variable digits and flexible whitespace/newlines
    pattern = r"\s*\n*Dziennik Ustaw –\s*\d+\s*– Poz\. 1065\s*\n*"
    
    # Replace the pattern with an empty string to remove it
    return re.sub(pattern, r'\n', text, flags=re.MULTILINE)

def wrap_footer(text):
    # Define the pattern to find footer text after two newlines (with optional whitespace)
    pattern = r"(\n\s*\n)(\S[\s\S]*)$"
    
    # Function to wrap the footer text in a marker
    def wrapper(match):
        return match.group(1) + "[Odniesienia - początek]\n" + match.group(2) + "\n[Odniesienia - koniec]\n"
    
    # Replace the pattern with wrapped footer text
    return re.sub(pattern, wrapper, text, flags=re.MULTILINE)

def link_annotations(text):
    # Pattern to find 'word ending with [number)]' where 'word' starts with alphabetic characters
    pattern = r'(\b[a-zA-Z]+\w*)(\d+\))'
    # Replacement pattern that formats the word and number into a reference format
    result = re.sub(pattern, r'\1 (patrz Odniesienie \2)', text)
    # Adjust the parenthesis in the result to correctly format numbers
    result = re.sub(r'(\d+)\)', r'\1', result)
    return result

def merge_newline_divided_words(text):
    # Regex pattern to find words split across newlines by a hyphen
    pattern = r'(\w+)-\s*\n\s*(\w+)'
    
    # Function to replace each match
    def replacer(match):
        # Merge the parts without the hyphen
        return match.group(1) + match.group(2)
    
    # Substitute newline divided words using the replacer function
    merged_text = re.sub(pattern, replacer, text)
    return merged_text

def contains_new_section(text):
    # Define the regex pattern: 'DZIAŁ ' followed by one or more Roman numeral characters
    pattern = r'D\s*Z\s*I\s*A\s*Ł\s+[IVXLCDM]+'
    
    # Use re.search to find the pattern in the input string
    match = re.search(pattern, text)
    
    # Return True if a match is found, otherwise False
    return match is not None





if __name__ == "__main__":
    pdf_fp = DATA_DIR / "D20191065.pdf"

    loader = PyPDFLoader(
        file_path=pdf_fp.as_posix()
    )
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
    tmp_document = Document(
        page_content="", 
        metadata={
            "section_id": section_idx,
            "paragraph_id": 0,
            "document_id": f"{pdf_fp.name}"
            }
        )

    
    for page_no, document in enumerate(full_document):

        if contains_new_section(document.page_content):

            split_page_content = re.split(r'D\s*Z\s*I\s*A\s*Ł\s+[IVXLCDM]+', document.page_content)

            tmp_document.page_content += split_page_content[0]

            restructured_document.append(tmp_document)

            section_idx += 1
            tmp_document = Document(
                page_content="", 
                metadata={
                    "section_id": section_idx,
                    "paragraph_id": 0,
                    "document_id": f"{pdf_fp.name}"
                    }
                )
            tmp_document.page_content = split_page_content[1]

        else:
            tmp_document.page_content += document.page_content

    print("dupa")

        
