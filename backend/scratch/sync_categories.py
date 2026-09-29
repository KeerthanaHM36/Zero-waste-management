"""
Category Database & File Structure Synchronization Script.

Ensures default standard categories exist in DB, cleans up garbage test categories,
and synchronizes uploads/dataset/{category_slug} folders on disk so that only valid
active categories have dataset directories.
"""
import os
import shutil
import logging
from app.database import SessionLocal
from app.models.category import Category
from app.models.image import Image
from app.models.annotation import Annotation
from app.services.lifecycle_service import slugify_category_name
from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    {"name": "Plastic", "code": 101, "desc": "Plastic bottles, containers, and packaging"},
    {"name": "Paper & Cardboard", "code": 102, "desc": "Paper sheets, magazines, boxes, and cardboard"},
    {"name": "Metal", "code": 103, "desc": "Aluminum cans, tin foil, and metal objects"},
    {"name": "Glass", "code": 104, "desc": "Glass bottles, jars, and glass products"},
    {"name": "Organic Waste", "code": 105, "desc": "Food waste, compostable organic materials"},
    {"name": "E-Waste", "code": 106, "desc": "Electronic components and small appliances"},
]

def sync_categories_and_folders():
    db = SessionLocal()
    try:
        # 1. Clean up old test categories from DB if they have no images
        existing_cats = db.query(Category).all()
        for cat in existing_cats:
            # If category name starts with test/lifecycle prefixes and has no images attached, remove it
            name_lower = cat.class_name.lower()
            if any(name_lower.startswith(prefix) for prefix in ["lifecycletest_", "testcat_", "dupcat_", "e2ecat_", "cat_"]):
                img_count = db.query(Image).filter(Image.selected_category_id == cat.category_id).count()
                ann_count = db.query(Annotation).filter(Annotation.category_id == cat.category_id).count()
                if img_count == 0 and ann_count == 0:
                    db.delete(cat)
        db.commit()

        # 2. Seed Default Categories if missing
        existing_names = {c.class_name.lower() for c in db.query(Category).all()}
        existing_codes = {c.class_code for c in db.query(Category).all()}
        
        for def_cat in DEFAULT_CATEGORIES:
            if def_cat["name"].lower() not in existing_names and def_cat["code"] not in existing_codes:
                db.add(Category(
                    class_name=def_cat["name"],
                    class_code=def_cat["code"],
                    description=def_cat["desc"],
                    is_active=True
                ))
        db.commit()

        # 3. Get all valid category slugs
        all_cats = db.query(Category).all()
        valid_slugs = {slugify_category_name(cat.class_name) for cat in all_cats}
        valid_slugs.add("general")  # preserve fallback general folder

        dataset_root = os.path.join(settings.UPLOAD_FOLDER, "dataset")
        os.makedirs(dataset_root, exist_ok=True)

        # 4. Ensure folder structure exists for all valid categories
        for slug in valid_slugs:
            cat_dir = os.path.join(dataset_root, slug)
            os.makedirs(os.path.join(cat_dir, "images"), exist_ok=True)
            os.makedirs(os.path.join(cat_dir, "labels"), exist_ok=True)

        # 5. Clean up orphan dataset directories on disk
        for item in os.listdir(dataset_root):
            item_path = os.path.join(dataset_root, item)
            if os.path.isdir(item_path):
                if item.lower() not in valid_slugs:
                    print(f"Removing orphan dataset directory: {item_path}")
                    shutil.rmtree(item_path, ignore_errors=True)

        print(f"Category sync complete! Active categories in DB: {[c.class_name for c in all_cats]}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_categories_and_folders()
