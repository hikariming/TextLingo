#!/usr/bin/env python3
"""
简单的 API 测试脚本
用于验证 TextLingo2 后端 API 的基本功能
"""

import requests
import json
import sys
from typing import Optional

# API 基础 URL
BASE_URL = "http://localhost:8000"
API_V1_PREFIX = "/api/v1"

class APITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        
    def test_health_check(self):
        """测试健康检查端点"""
        print("🔍 测试健康检查...")
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✅ 健康检查通过")
                print(f"   响应: {response.json()}")
                return True
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False
    
    def test_user_register(self, email: str, password: str, full_name: str = "Test User"):
        """测试用户注册"""
        print(f"🔍 测试用户注册: {email}")
        try:
            data = {
                "email": email,
                "password": password,
                "full_name": full_name
            }
            response = requests.post(
                f"{self.base_url}{API_V1_PREFIX}/auth/register",
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
                print("✅ 用户注册成功")
                print(f"   用户ID: {result['user']['id']}")
                print(f"   邮箱: {result['user']['email']}")
                return True
            else:
                print(f"❌ 用户注册失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 用户注册异常: {e}")
            return False
    
    def test_user_login(self, email: str, password: str):
        """测试用户登录"""
        print(f"🔍 测试用户登录: {email}")
        try:
            data = {
                "email": email,
                "password": password
            }
            response = requests.post(
                f"{self.base_url}{API_V1_PREFIX}/auth/login",
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
                print("✅ 用户登录成功")
                print(f"   用户ID: {result['user']['id']}")
                print(f"   邮箱: {result['user']['email']}")
                return True
            else:
                print(f"❌ 用户登录失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 用户登录异常: {e}")
            return False
    
    def test_get_current_user(self):
        """测试获取当前用户信息"""
        print("🔍 测试获取当前用户信息...")
        if not self.access_token:
            print("❌ 没有访问令牌，请先登录")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(
                f"{self.base_url}{API_V1_PREFIX}/auth/me",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 获取用户信息成功")
                print(f"   用户ID: {result['id']}")
                print(f"   邮箱: {result['email']}")
                print(f"   全名: {result.get('full_name', 'N/A')}")
                return True
            else:
                print(f"❌ 获取用户信息失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 获取用户信息异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行 TextLingo2 API 测试\n")
        
        results = []
        
        # 测试健康检查
        results.append(self.test_health_check())
        print()
        
        # 测试用户注册
        test_email = "test@mail.textlingo.app"
        test_password = "test123456"
        results.append(self.test_user_register(test_email, test_password))
        print()
        
        # 如果注册失败，尝试登录
        if not results[-1]:
            print("📝 注册失败，尝试登录已存在的用户...")
            results.append(self.test_user_login(test_email, test_password))
            print()
        
        # 测试获取当前用户信息
        results.append(self.test_get_current_user())
        print()
        
        # 测试结果总结
        passed = sum(results)
        total = len(results)
        
        print("📊 测试结果总结:")
        print(f"   总测试数: {total}")
        print(f"   通过数: {passed}")
        print(f"   失败数: {total - passed}")
        
        if passed == total:
            print("🎉 所有测试通过！")
        else:
            print("⚠️  部分测试失败，请检查配置和服务状态")
        
        return passed == total


def main():
    """主函数"""
    print("TextLingo2 API 测试工具\n")
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
        print(f"使用自定义 API URL: {base_url}")
    else:
        base_url = BASE_URL
        print(f"使用默认 API URL: {base_url}")
    
    print(f"确保 API 服务在 {base_url} 上运行\n")
    
    tester = APITester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 