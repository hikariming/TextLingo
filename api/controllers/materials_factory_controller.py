from flask import Blueprint, request, jsonify
import sys
import os
# 添加父目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.materials_factory import MaterialsFactory
from models.material import Material
from bson import ObjectId

materials_factory_bp = Blueprint('materials_factory', __name__)

@materials_factory_bp.route('/materials-factory', methods=['POST'])
def create_factory():
    data = request.get_json()
    factory = MaterialsFactory(
        name=data['name'],
        description=data.get('description'),
        user_id=data['user_id']
    )
    factory.save()
    return jsonify(factory.to_dict()), 201

@materials_factory_bp.route('/materials-factory/<factory_id>', methods=['GET'])
def get_factory(factory_id):
    factory = MaterialsFactory.objects.get(id=factory_id)
    return jsonify(factory.to_dict())

@materials_factory_bp.route('/materials-factory', methods=['GET'])
def list_factories():
    user_id = request.args.get('user_id')
    query = {'user_id': user_id} if user_id else {}
    factories = MaterialsFactory.objects(**query)
    return jsonify([factory.to_dict() for factory in factories])

@materials_factory_bp.route('/materials-factory/<factory_id>', methods=['PUT'])
def update_factory(factory_id):
    data = request.get_json()
    factory = MaterialsFactory.objects.get(id=factory_id)
    factory.update(**data)
    factory.reload()
    return jsonify(factory.to_dict())

@materials_factory_bp.route('/materials-factory/<factory_id>', methods=['DELETE'])
def delete_factory(factory_id):
    factory = MaterialsFactory.objects.get(id=factory_id)
    factory.delete()
    return '', 204

@materials_factory_bp.route('/materials-factory/<factory_id>/materials', methods=['POST'])
def add_material_to_factory(factory_id):
    data = request.get_json()
    factory = MaterialsFactory.objects.get(id=factory_id)
    material = Material.objects.get(id=data['material_id'])
    material.factory_id = factory
    material.save()
    
    if material.id not in factory.materials:
        factory.materials.append(material)
        factory.save()
    
    return jsonify(factory.to_dict())

@materials_factory_bp.route('/materials-factory/<factory_id>/materials/<material_id>', methods=['DELETE'])
def remove_material_from_factory(factory_id, material_id):
    factory = MaterialsFactory.objects.get(id=factory_id)
    material = Material.objects.get(id=material_id)
    
    if material.id in factory.materials:
        factory.materials.remove(material)
        factory.save()
        
    material.factory_id = None
    material.save()
    
    return jsonify(factory.to_dict())