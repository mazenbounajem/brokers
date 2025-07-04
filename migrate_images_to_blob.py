import os
from app import db, Project

def migrate_images_to_blob():
    projects = Project.query.all()
    for project in projects:
        image_paths = project.get_image_paths()
        image_blobs = {}
        for path in image_paths:
            # Adjust path to instance directory if needed
            adjusted_path = path
            if not os.path.isabs(path):
                adjusted_path = os.path.join('instance', path)
            if os.path.exists(adjusted_path):
                with open(adjusted_path, 'rb') as f:
                    image_data = f.read()
                    filename = os.path.basename(path)
                    image_blobs[filename] = image_data
            else:
                print(f"Warning: Image file {adjusted_path} does not exist.")
        project.image_blobs = image_blobs
    try:
        db.session.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate_images_to_blob()
