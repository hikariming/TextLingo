from flask import Flask
from extensions import mongo
from flask_cors import CORS
import yaml

def create_app():
    app = Flask(__name__)
    # 配置CORS，允许所有来源
    CORS(app, resources={r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": "*"
    }})
    
    # 从YAML文件加载配置
    with open('config.yml', 'r') as file:
        config = yaml.safe_load(file)
    
    # 设置配置
    app.config['MONGO_URI'] = config['mongodb']['uri']
    app.config['SECRET_KEY'] = config['secret_key']
    
    # 初始化 MongoDB
    mongo.init_app(app)
    
    # 注册蓝图
    from controllers.user_controller import user_bp
    from controllers.material_controller import material_bp
    app.register_blueprint(material_bp)
    app.register_blueprint(user_bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
