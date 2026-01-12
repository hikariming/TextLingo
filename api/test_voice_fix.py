#!/usr/bin/env python3
"""
语音服务修复测试脚本
"""

import sys
import os
import asyncio
import json

# 添加 app 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.voice_service import voice_service
from app.core.config import settings


async def test_voice_fix():
    """测试语音服务修复"""
    print("=== 语音服务修复测试 ===")
    
    # 检查配置
    print(f"API Key 配置: {'✓' if settings.minimax_api_key else '✗'}")
    print(f"Group ID 配置: {'✓' if settings.minimax_groupid else '✗'}")
    
    if not settings.minimax_api_key or not settings.minimax_groupid:
        print("❌ Minimax API配置不完整，请检查.env文件")
        return
    
    # 测试简单文本转语音
    print("\n=== 测试修复后的文本转语音 ===")
    test_text = "你好，这是修复测试。"
    
    try:
        print(f"转换文本: {test_text}")
        print("使用参数:")
        print("  - voice_id: 'male-qn-qingse'")
        print("  - speed: 1.0")
        print("  - pitch: 0")
        print("  - volume: 1.0")
        print("  - sample_rate: 32000")
        print("  - bitrate: 128000")
        
        # 创建一个测试用户ID（在实际测试中应该使用真实的用户ID）
        test_user_id = "test_user_voice_synthesis"
        
        result = await voice_service.text_to_speech(
            text=test_text,
            user_id=test_user_id,
            voice_id="male-qn-qingse",
            speed=1.0,
            pitch=0,
            volume=1.0,
            sample_rate=32000,
            bitrate=128000,
            audio_format="mp3",
            auto_charge=False  # 测试时不扣费
        )
        
        if result["success"]:
            audio_data = result["audio_data"]
            print(f"✅ 语音转换成功！音频数据大小: {len(audio_data)} 字节")
            print(f"   文本长度: {result['text_length']} 字符")
            print(f"   音频大小: {result['audio_size']} 字节")
            
            if result.get("points_transaction"):
                print(f"   积分信息: 消耗 {result['points_transaction']['points_consumed']} 积分")
            
            # 保存测试音频文件
            output_file = "test_voice_fix_output.mp3"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"✅ 音频文件已保存为: {output_file}")
            
            return True
        else:
            print(f"❌ 语音转换失败: {result['message']}")
            print(f"   错误类型: {result.get('error', 'unknown')}")
            return False
            
    except Exception as e:
        print(f"❌ 语音转换异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_voice_fix())
    if success:
        print("\n🎉 修复成功！语音服务现在可以正常工作了。")
    else:
        print("\n❌ 修复未完成，请检查错误信息。") 