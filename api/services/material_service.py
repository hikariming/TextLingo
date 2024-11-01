from models.material import Material
from extensions import mongo
from bson import ObjectId

class MaterialService:
    @staticmethod
    def create_material(title, content, file_type, file_size, file_path, user_id):
        material = Material(
            title=title,
            content=content,
            file_type=file_type,
            file_size=file_size,
            file_path=file_path,
            user_id=user_id
        )
        result = mongo.db.materials.insert_one(material.to_dict())
        return material

    @staticmethod
    def get_materials(user_id, page=1, per_page=10):
        skip = (page - 1) * per_page
        materials = mongo.db.materials.find({"user_id": user_id}).skip(skip).limit(per_page)
        return list(materials)

    @staticmethod
    def get_material_by_id(material_id):
        return mongo.db.materials.find_one({"_id": ObjectId(material_id)})

    @staticmethod
    def update_material(material_id, updates):
        updates['updated_at'] = datetime.utcnow()
        return mongo.db.materials.update_one(
            {"_id": ObjectId(material_id)},
            {"$set": updates}
        )

    @staticmethod
    def delete_material(material_id):
        return mongo.db.materials.delete_one({"_id": ObjectId(material_id)})