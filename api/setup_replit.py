#!/usr/bin/env python3
"""
Replit 环境设置和验证脚本
用于快速检查和配置 Replit 部署环境
"""

import os
import sys
import subprocess
from typing import List, Dict

class ReplitSetup:
    """Replit 环境设置类"""
    
    REQUIRED_SECRETS = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY", 
        "SUPABASE_SERVICE_ROLE_KEY",
        "JWT_SECRET_KEY",
        "SECRET_KEY"
    ]
    
    OPTIONAL_SECRETS = [
        "DEBUG",
        "APP_NAME",
        "CORS_ORIGINS"
    ]
    
    def __init__(self):
        self.is_replit = os.getenv("REPL_SLUG") is not None
        self.errors = []
        self.warnings = []
    
    def check_environment(self) -> bool:
        """检查 Replit 环境"""
        print("🔍 检查 Replit 环境...")
        
        if not self.is_replit:
            self.errors.append("❌ 不在 Replit 环境中")
            return False
            
        print(f"✅ Replit 环境检测成功")
        print(f"   REPL_SLUG: {os.getenv('REPL_SLUG')}")
        print(f"   REPL_OWNER: {os.getenv('REPL_OWNER', 'Unknown')}")
        return True
    
    def check_secrets(self) -> bool:
        """检查必需的环境变量"""
        print("\n🔐 检查环境变量...")
        
        missing_required = []
        missing_optional = []
        
        # 检查必需变量
        for secret in self.REQUIRED_SECRETS:
            value = os.getenv(secret)
            if not value:
                missing_required.append(secret)
                self.errors.append(f"❌ 缺少必需环境变量: {secret}")
            else:
                print(f"✅ {secret}: {'*' * min(len(value), 8)}...")
        
        # 检查可选变量
        for secret in self.OPTIONAL_SECRETS:
            value = os.getenv(secret)
            if not value:
                missing_optional.append(secret)
                self.warnings.append(f"⚠️  缺少可选环境变量: {secret}")
            else:
                print(f"✅ {secret}: {value}")
        
        if missing_required:
            print(f"\n❌ 缺少 {len(missing_required)} 个必需环境变量")
            return False
        
        if missing_optional:
            print(f"\n⚠️  缺少 {len(missing_optional)} 个可选环境变量")
        
        return True
    
    def check_dependencies(self) -> bool:
        """检查 Python 依赖"""
        print("\n📦 检查 Python 依赖...")
        
        try:
            import fastapi
            import uvicorn
            import supabase
            print("✅ 核心依赖已安装")
            print(f"   FastAPI: {fastapi.__version__}")
            print(f"   Uvicorn: {uvicorn.__version__}")
            return True
        except ImportError as e:
            self.errors.append(f"❌ 依赖缺失: {e}")
            return False
    
    def check_file_structure(self) -> bool:
        """检查文件结构"""
        print("\n📁 检查文件结构...")
        
        required_files = [
            "app/main.py",
            "requirements.txt",
            "start.sh"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
                self.errors.append(f"❌ 缺少文件: {file_path}")
            else:
                print(f"✅ {file_path}")
        
        return len(missing_files) == 0
    
    def generate_secrets_template(self) -> str:
        """生成环境变量模板"""
        template = """
# Replit Secrets 配置模板
# 在 Replit 左侧面板的 "Secrets" 中添加以下变量

# === 必需变量 ===
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-anon-key
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-service-role-key
JWT_SECRET_KEY=your-32-character-secret-key
SECRET_KEY=your-32-character-secret-key

# === 可选变量 ===
DEBUG=false
APP_NAME=TextLingo2 API
CORS_ORIGINS=["https://textlingo.app", "https://v2.textlingo.app", "https://www.textlingo.app"]

# 生成密钥命令:
# openssl rand -hex 32
"""
        return template
    
    def run_setup(self) -> bool:
        """运行完整设置检查"""
        print("🚀 TextLingo2 Replit 环境设置检查")
        print("=" * 50)
        
        checks = [
            self.check_environment(),
            self.check_file_structure(),
            self.check_dependencies(),
            self.check_secrets()
        ]
        
        print("\n" + "=" * 50)
        print("📊 检查结果:")
        
        if self.errors:
            print(f"\n❌ 发现 {len(self.errors)} 个错误:")
            for error in self.errors:
                print(f"   {error}")
        
        if self.warnings:
            print(f"\n⚠️  发现 {len(self.warnings)} 个警告:")
            for warning in self.warnings:
                print(f"   {warning}")
        
        success = all(checks)
        
        if success:
            print("\n🎉 环境检查通过！可以开始部署。")
            print("\n🚀 启动命令:")
            print("   bash start.sh")
        else:
            print("\n❌ 环境检查失败，请修复上述问题。")
            print("\n📝 环境变量模板:")
            print(self.generate_secrets_template())
        
        return success

def main():
    """主函数"""
    setup = ReplitSetup()
    success = setup.run_setup()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()