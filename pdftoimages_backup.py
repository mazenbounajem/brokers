import fitz

def extract_images_from_pdf(pdf_path, output_folder):
    doc = fitz.open(pdf_path)
    for page_index in range(len(doc)):
        for img_index, img in enumerate(doc[page_index].get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            with open(f"{output_folder}/image_{page_index}_{img_index}.{image_ext}", "wb") as f:
                f.write(image_bytes)

pdf_path = "C:\\Users\\USER\\Downloads\\__OBG EXCLUSIVE PROJECTS.pdf"
output_folder = "extracted_images"
extract_images_from_pdf(pdf_path, output_folder)
