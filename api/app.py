from flask import Flask, jsonify
from extensions import mongo
from flask_cors import CORS
import yaml
from mongoengine import connect

def create_app():
    app = Flask(__name__)
    
    # 统一的 CORS 配置
    CORS(app)
    
    # 从YAML文件加载配置
    with open('config.yml', 'r') as file:
        config = yaml.safe_load(file)
    
    # 设置配置
    app.config['MONGO_URI'] = config['mongodb']['uri']
    app.config['SECRET_KEY'] = config['secret_key']
    
    # 初始化 MongoDB 连接
    connect(db='textlingo', host=config['mongodb']['uri'])
    mongo.init_app(app)
    
    # 注册蓝图
    from controllers.user_controller import user_bp
    from controllers.material_controller import material_bp
    from controllers.materials_factory_controller import materials_factory_bp
    from controllers.material_segment_controller import material_segment_bp
    from controllers.user_vocabulary_controller import vocabulary_bp
    from controllers.user_grammar_controller import grammar_bp
    from controllers.setting_controller import setting_bp
    
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(material_bp, url_prefix='/api')
    app.register_blueprint(materials_factory_bp, url_prefix='/api')
    app.register_blueprint(material_segment_bp, url_prefix='/api')
    app.register_blueprint(vocabulary_bp, url_prefix='/api')
    app.register_blueprint(grammar_bp, url_prefix='/api')
    app.register_blueprint(setting_bp, url_prefix='/api')
    @app.route('/api/test', methods=['GET'])
    def test_cors():
        return jsonify({"message": "CORS test successful"})
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=3001, debug=True)
