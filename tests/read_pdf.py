import fitz

file = "/home/hjx/workspace/semantix/tests/test_resume.pdf"
doc = fitz.open(file)

content = []
for page in doc:
    content.append(page.get_text())
    


