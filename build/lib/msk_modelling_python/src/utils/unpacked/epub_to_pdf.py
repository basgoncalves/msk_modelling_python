import ebooklib
from ebooklib import epub
from fpdf import FPDF
import os

def convert_epub_to_pdf(epub_file, pdf_file):
    book = epub.read_epub(epub_file)

    pdf = FPDF()
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, txt=item.get_content(), ln=True)

    pdf.output(pdf_file)

# Usage example
epub_file = r"C:\Users\Bas\Downloads\Stavroula Rakitzi - Clinical Psychology and Cognitive Behavioral Psychotherapy_ Recovery in Mental Health-Springer Nature (2023).epub"
pdf_file = epub_file.replace('.epub', '.pdf')   
convert_epub_to_pdf(epub_file, pdf_file)
