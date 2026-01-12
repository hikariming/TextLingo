#!/usr/bin/env python3
"""
语音API测试脚本
"""

import requests
import json
import os
from typing import Optional


class VoiceAPITester:
    """语音API测试类"""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Content-Type": "application/json"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def test_get_voices(self):
        """测试获取声音列表API"""
        print("=== 测试获取声音列表API ===")
        
        try:
            url = f"{self.base_url}/api/v1/voice/voices"
            response = requests.get(url, headers=self.headers)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✓ 成功获取声音列表")
                print(f"中文声音数量: {len(data.get('chinese_voices', []))}")
                print(f"英文声音数量: {len(data.get('english_voices', []))}")
                print(f"日文声音数量: {len(data.get('japanese_voices', []))}")
                
                # 显示前几个声音选项
                if data.get('chinese_voices'):
                    print("\n中文声音选项:")
                    for voice in data['chinese_voices'][:3]:
                        print(f"  - ID: {voice['id']}, 名称: {voice['name']}")
            else:
                print(f"❌ 请求失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    def test_voice_config(self):
        """测试语音服务配置"""
        print("\n=== 测试语音服务配置 ===")
        
        try:
            url = f"{self.base_url}/api/v1/voice/voices/test"
            response = requests.get(url, headers=self.headers)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 配置检查完成")
                print(f"整体状态: {'正常' if data.get('success') else '异常'}")
                
                details = data.get('details', {})
                print(f"API Key: {'✓' if details.get('has_api_key') else '✗'}")
                print(f"Group ID: {'✓' if details.get('has_group_id') else '✗'}")
                print(f"服务URL: {details.get('service_url', 'N/A')}")
            else:
                print(f"❌ 请求失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    def test_text_to_speech(self, text: str = "你好，这是一个API测试。"):
        """测试文本转语音API"""
        print(f"\n=== 测试文本转语音API ===")
        print(f"测试文本: {text}")
        
        try:
            url = f"{self.base_url}/api/v1/voice/text-to-speech"
            payload = {
                "text": text,
                "voice_id": "Chinese (Mandarin)_Radio_Host",
                "speed": 0.8,
                "pitch": 0,
                "volume": 1.0,
                "audio_format": "mp3"
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                # 检查是否返回音频数据
                content_type = response.headers.get('content-type', '')
                if 'audio' in content_type:
                    print(f"✓ 成功获取音频数据，大小: {len(response.content)} 字节")
                    
                    # 保存音频文件
                    output_file = "api_test_voice_output.mp3"
                    with open(output_file, "wb") as f:
                        f.write(response.content)
                    print(f"✓ 音频文件已保存为: {output_file}")
                else:
                    print(f"❌ 响应不是音频格式: {content_type}")
                    print(f"响应内容: {response.text[:200]}...")
            else:
                print(f"❌ 请求失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    def test_text_to_speech_url(self, text: str = "你好，这是一个URL API测试。"):
        """测试文本转语音URL API"""
        print(f"\n=== 测试文本转语音URL API ===")
        print(f"测试文本: {text}")
        
        try:
            url = f"{self.base_url}/api/v1/voice/text-to-speech-url"
            payload = {
                "text": text,
                "voice_id": "Chinese (Mandarin)_Radio_Host",
                "speed": 0.8,
                "pitch": 0,
                "volume": 1.0,
                "audio_format": "mp3"
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ API调用成功")
                print(f"成功状态: {data.get('success')}")
                print(f"消息: {data.get('message')}")
                print(f"音频URL: {data.get('audio_url', 'N/A')}")
            else:
                print(f"❌ 请求失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")


def main():
    """主测试函数"""
    print("语音API测试工具")
    print("=" * 50)
    
    # 配置
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    token = os.getenv("API_TOKEN")  # 如果需要认证，设置这个环境变量
    
    if not token:
        print("⚠️  未设置API_TOKEN环境变量，某些测试可能会失败")
        print("   如需完整测试，请先登录获取token并设置环境变量")
        print("   例如: export API_TOKEN='your_jwt_token_here'")
    
    # 创建测试器
    tester = VoiceAPITester(base_url, token)
    
    # 执行测试
    if token:
        tester.test_voice_config()
        tester.test_get_voices()
        tester.test_text_to_speech()
        tester.test_text_to_speech_url()
    else:
        print("\n跳过需要认证的测试...")
    
    print("\n测试完成！")


if __name__ == "__main__":
    main() 