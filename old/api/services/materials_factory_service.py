from models.materials_factory import MaterialsFactory
from models.material import Material
from mongoengine.errors import DoesNotExist

class MaterialsFactoryService:
    @staticmethod
    def create_factory(name, description=None):
        factory = MaterialsFactory(
            name=name,
            description=description
        )
        factory.save()
        return factory

    @staticmethod
    def get_factory(factory_id):
        return MaterialsFactory.objects.get(id=factory_id)

    @staticmethod
    def list_factories():
        return MaterialsFactory.objects.all()

    @staticmethod
    def update_factory(factory_id, data):
        factory = MaterialsFactory.objects.get(id=factory_id)
        factory.update(**data)
        factory.reload()
        return factory

    @staticmethod
    def delete_factory(factory_id):
        factory = MaterialsFactory.objects.get(id=factory_id)
        factory.delete()
        return True

    @staticmethod
    def get_factory_materials(factory_id):
        """
        获取指定工厂的所有材料
        两种方式获取材料:
        1. 通过 factory.materials 引用
        2. 通过 Material 中的 factory_id 字段
        """
        try:
            # 首先检查工厂是否存在
            factory = MaterialsFactory.objects.get(id=factory_id)
            
            # 直接通过 Material 模型查询属于该工厂的所有材料
            materials = Material.objects(factory_id=str(factory_id))
            
            # 如果没有找到材料，返回空列表而不是 None
            return list(materials)
            
        except DoesNotExist:
            return None
        except Exception as e:
            print(f"Error getting factory materials: {str(e)}")
            return None

    @staticmethod
    def add_material_to_factory(factory_id, material_id):
        """
        添加材料到工厂
        """
        try:
            factory = MaterialsFactory.objects.get(id=factory_id)
            material = Material.objects.get(id=material_id)
            
            # 更新 material 的 factory_id
            material.factory_id = str(factory.id)
            material.save()
            
            # 更新 factory 的 materials 列表
            if material not in factory.materials:
                factory.materials.append(material)
                factory.save()
            
            return factory
        except DoesNotExist:
            return None

    @staticmethod
    def remove_material_from_factory(factory_id, material_id):
        """
        从工厂中移除材料
        """
        try:
            factory = MaterialsFactory.objects.get(id=factory_id)
            material = Material.objects.get(id=material_id)
            
            # 清除 material 的 factory_id
            material.factory_id = None
            material.save()
            
            # 从 factory 的 materials 列表中移除
            if material in factory.materials:
                factory.materials.remove(material)
                factory.save()
            
            return factory
        except DoesNotExist:
            return None