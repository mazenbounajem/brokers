import os
import sys
import fitz
from PIL import Image
import pytesseract

def extract_text_from_image(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        text_file_path = os.path.splitext(image_path)[0] + ".txt"
        with open(text_file_path, "w", encoding="utf-8") as text_file:
            text_file.write(text)
    except Exception as e:
        print(f"Error extracting text from {image_path}: {e}")

def extract_images_from_pdf(pdf_path, output_folder):
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' does not exist.")
        return
    if os.path.exists(output_folder):
        for filename in os.listdir(output_folder):
            file_path = os.path.join(output_folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    import shutil
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        os.makedirs(output_folder)
    doc = fitz.open(pdf_path)
    for page_index in range(len(doc)):
        for img_index, img in enumerate(doc[page_index].get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_path = f"{output_folder}/image_{page_index}_{img_index}.{image_ext}"
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            extract_text_from_image(image_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdftoimages.py <pdf_path> [output_folder]")
        sys.exit(1)
    pdf_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "extracted_images"
    extract_images_from_pdf(pdf_path, output_folder)
