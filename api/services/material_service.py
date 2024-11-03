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
        material.save()
        return material.to_dict()

    @staticmethod
    def get_materials(user_id, page=1, per_page=10):
        skip = (page - 1) * per_page
        materials = Material.objects(user_id=user_id).skip(skip).limit(per_page)
        return [material.to_dict() for material in materials]

    @staticmethod
    def get_material_by_id(material_id):
        try:
            material = Material.objects(id=material_id).first()
            return material.to_dict() if material else None
        except:
            return None

    @staticmethod
    def update_material(material_id, updates):
        try:
            updates['updated_at'] = datetime.utcnow()
            material = Material.objects(id=material_id).first()
            if material:
                for key, value in updates.items():
                    setattr(material, key, value)
                material.save()
                return True
            return False
        except:
            return None

    @staticmethod
    def delete_material(material_id):
        return Material.objects(id=material_id).delete()