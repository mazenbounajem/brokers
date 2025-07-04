import os
import sys
import fitz

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
            with open(f"{output_folder}/image_{page_index}_{img_index}.{image_ext}", "wb") as f:
                f.write(image_bytes)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdftoimages.py <pdf_path> [output_folder]")
        sys.exit(1)
    pdf_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "extracted_images"
    extract_images_from_pdf(pdf_path, output_folder)
