#!/usr/bin/env python3
"""
DeepSeek模型测试脚本
用于快速测试OpenRouter的DeepSeek模型是否正常工作
"""

import os
import sys
import asyncio
import json
from typing import Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

class DeepSeekTester:
    """DeepSeek模型测试器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        
        if not self.api_key:
            raise ValueError("请设置OPENROUTER_API_KEY环境变量或传入api_key参数")
    
    def create_client(self, model: str) -> ChatOpenAI:
        """创建OpenAI客户端"""
        return ChatOpenAI(
            model=model,
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            temperature=0.7,
            max_tokens=1000,
            timeout=30
        )
    
    async def test_model(self, model: str, test_message: str = "你好，请简单介绍一下你自己") -> dict:
        """测试指定模型"""
        try:
            print(f"\n🚀 测试模型: {model}")
            print(f"📝 测试消息: {test_message}")
            print("-" * 50)
            
            client = self.create_client(model)
            
            messages = [
                SystemMessage(content="你是一个有用的AI助手，请用中文回答。"),
                HumanMessage(content=test_message)
            ]
            
            response = await client.ainvoke(messages)
            
            result = {
                "success": True,
                "model": model,
                "response": response.content,
                "usage": getattr(response, 'usage_metadata', None)
            }
            
            print(f"✅ 响应成功:")
            print(f"📄 内容: {response.content[:200]}{'...' if len(response.content) > 200 else ''}")
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "model": model,
                "error": str(e)
            }
            
            print(f"❌ 测试失败: {e}")
            return error_result
    
    async def test_all_deepseek_models(self):
        """测试所有DeepSeek模型"""
        models = [
            "deepseek/deepseek-chat",
            "deepseek/deepseek-coder"
        ]
        
        test_messages = {
            "deepseek/deepseek-chat": "你好，请用中文简单介绍一下DeepSeek模型的特点",
            "deepseek/deepseek-coder": "请写一个Python函数，计算斐波那契数列的第n项"
        }
        
        results = []
        
        for model in models:
            test_message = test_messages.get(model, "你好，请简单介绍一下你自己")
            result = await self.test_model(model, test_message)
            results.append(result)
            
            # 稍微延迟避免请求过快
            await asyncio.sleep(1)
        
        return results
    
    def print_summary(self, results: list):
        """打印测试结果摘要"""
        print("\n" + "=" * 60)
        print("🎯 测试结果摘要")
        print("=" * 60)
        
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]
        
        print(f"✅ 成功: {len(successful)} 个模型")
        print(f"❌ 失败: {len(failed)} 个模型")
        
        if successful:
            print("\n🎉 成功的模型:")
            for result in successful:
                print(f"  - {result['model']}")
        
        if failed:
            print("\n💥 失败的模型:")
            for result in failed:
                print(f"  - {result['model']}: {result.get('error', 'Unknown error')}")
        
        print("\n📋 详细结果保存到: test_results.json")

async def main():
    """主函数"""
    print("🔧 DeepSeek模型测试工具")
    print("=" * 40)
    
    # 检查API密钥
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ 错误: 请先设置OPENROUTER_API_KEY环境变量")
        print("💡 设置方法:")
        print("   export OPENROUTER_API_KEY='sk-or-v1-your-api-key-here'")
        return
    
    print(f"🔑 API Key: {api_key[:20]}...{api_key[-4:]}")
    
    try:
        tester = DeepSeekTester(api_key)
        results = await tester.test_all_deepseek_models()
        
        # 保存结果到文件
        with open("test_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        tester.print_summary(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 