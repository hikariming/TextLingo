from flask import Blueprint, request, jsonify
from services.materials_factory_service import MaterialsFactoryService

materials_factory_bp = Blueprint('materials_factory', __name__)

@materials_factory_bp.route('/materials-factory', methods=['POST'])
def create_factory():
    data = request.get_json()
    factory = MaterialsFactoryService.create_factory(
        name=data['name'],
        description=data.get('description')
    )
    return jsonify(factory.to_dict()), 201

@materials_factory_bp.route('/materials-factory/<factory_id>', methods=['GET'])
def get_factory(factory_id):
    factory = MaterialsFactoryService.get_factory(factory_id)
    return jsonify(factory.to_dict())

@materials_factory_bp.route('/materials-factory', methods=['GET'])
def list_factories():
    factories = MaterialsFactoryService.list_factories()
    return jsonify([factory.to_dict() for factory in factories])

@materials_factory_bp.route('/materials-factory/<factory_id>', methods=['PUT'])
def update_factory(factory_id):
    data = request.get_json()
    factory = MaterialsFactoryService.update_factory(factory_id, data)
    return jsonify(factory.to_dict())

@materials_factory_bp.route('/materials-factory/<factory_id>', methods=['DELETE'])
def delete_factory(factory_id):
    MaterialsFactoryService.delete_factory(factory_id)
    return '', 204

@materials_factory_bp.route('/materials-factory/<factory_id>/materials', methods=['GET'])
def get_factory_materials(factory_id):
    materials = MaterialsFactoryService.get_factory_materials(factory_id)
    if materials is None:
        return jsonify({'error': 'Factory not found'}), 404
    
    return jsonify({
        'materials': [material.to_dict() for material in materials]
    })

@materials_factory_bp.route('/materials-factory/<factory_id>/materials', methods=['POST'])
def add_material_to_factory(factory_id):
    data = request.get_json()
    factory = MaterialsFactoryService.add_material_to_factory(factory_id, data['material_id'])
    return jsonify(factory.to_dict())

@materials_factory_bp.route('/materials-factory/<factory_id>/materials/<material_id>', methods=['DELETE'])
def remove_material_from_factory(factory_id, material_id):
    factory = MaterialsFactoryService.remove_material_from_factory(factory_id, material_id)
    return jsonify(factory.to_dict())