from models.materials_factory import MaterialsFactory
from models.material import Material

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
    def add_material_to_factory(factory_id, material_id):
        factory = MaterialsFactory.objects.get(id=factory_id)
        material = Material.objects.get(id=material_id)
        
        if material.id not in factory.materials:
            factory.materials.append(material)
            factory.save()
            material.factory_id = factory
            material.save()
        
        return factory

    @staticmethod
    def remove_material_from_factory(factory_id, material_id):
        factory = MaterialsFactory.objects.get(id=factory_id)
        material = Material.objects.get(id=material_id)
        
        if material.id in factory.materials:
            factory.materials.remove(material)
            factory.save()
            material.factory_id = None
            material.save()
        
        return factory