from models.material import Material
from extensions import mongo
from bson import ObjectId
from datetime import datetime

class MaterialService:
    @staticmethod
    def create_material(title, file_type, file_size, file_path, user_id, original_filename=None, original_file_path=None, status="pending_segmentation", factory_id=None):
        material = Material(
            title=title,
            file_type=file_type,
            file_size=file_size,
            file_path=file_path,
            original_file_path=original_file_path,
            original_filename=original_filename,
            user_id=user_id,
            status=status,
            factory_id=factory_id
        )
        result = mongo.db.materials.insert_one(material.to_dict())
        material_dict = material.to_dict()
        material_dict['_id'] = str(result.inserted_id)
        print(material_dict)
        return material_dict

    @staticmethod
    def get_materials(user_id, page=1, per_page=10):
        skip = (page - 1) * per_page
        materials = mongo.db.materials.find({"user_id": user_id}).skip(skip).limit(per_page)
        return list(materials)

    @staticmethod
    def get_material_by_id(material_id):
        if not material_id:
            return None
        try:
            material = mongo.db.materials.find_one({"_id": ObjectId(material_id)})
            if material:
                # Convert ObjectId to string
                material['_id'] = str(material['_id'])
            return material
        except:
            return None

    @staticmethod
    def update_material(material_id, updates):
        if not material_id:
            return None
        try:
            updates['updated_at'] = datetime.utcnow()
            if 'status' in updates:
                updates['translation_status'] = updates.get('translation_status', 'processing')
            
            return mongo.db.materials.update_one(
                {"_id": ObjectId(material_id)},
                {"$set": updates}
            )
        except:
            return None

    @staticmethod
    def delete_material(material_id):
        return mongo.db.materials.delete_one({"_id": ObjectId(material_id)})