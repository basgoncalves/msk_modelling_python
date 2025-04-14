from docx import Document
import os
import sys
import PyPDF2


filepaths = input("Enter the path of the PDF file: ")
filepaths = filepaths.strip('"')
if not os.path.isabs(filepaths):
    filepaths = os.path.abspath(filepaths)

try:
    pdf_file = open(filepaths, 'rb')
except FileNotFoundError:
    print(f"File not found: {filepaths}")
    sys.exit(1)

pdf_reader = PyPDF2.PdfReader(pdf_file)
if pdf_reader.is_encrypted:
    try:
        pdf_reader.decrypt('')
    except Exception as e:
        print(f"Failed to decrypt PDF: {e}")
        sys.exit(1)

pdf_writer = PyPDF2.PdfWriter()
pages = pdf_reader.pages
for page_num, page in enumerate(pages):
    # check if the page has any annotations
    if '/Annots' in page:
        annotations = page['/Annots']
        import pdb; pdb.set_trace()
        for annot in annotations:
            annot_obj = annot.getObject()
            if annot_obj['/Subtype'] == '/Text':
                print(f"Annotation on page {page_num + 1}: {annot_obj['/Contents']}")
                import pdb; pdb.set_trace()
        
            
            