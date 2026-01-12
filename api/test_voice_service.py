#!/usr/bin/env python3
"""
语音服务测试脚本
"""

import sys
import os
import asyncio
import json

# 添加 app 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.voice_service import voice_service
from app.core.config import settings


async def test_voice_service():
    """测试语音服务"""
    print("=== 语音服务测试 ===")
    
    # 检查配置
    print(f"API Key 配置: {'✓' if settings.minimax_api_key else '✗'}")
    print(f"Group ID 配置: {'✓' if settings.minimax_groupid else '✗'}")
    
    if not settings.minimax_api_key or not settings.minimax_groupid:
        print("❌ Minimax API配置不完整，请检查.env文件")
        return
    
    # 测试获取声音列表
    print("\n=== 测试获取声音列表 ===")
    try:
        voices = voice_service.get_available_voices()
        print("✓ 成功获取声音列表")
        print(f"中文声音数量: {len(voices['chinese_voices'])}")
        print(f"英文声音数量: {len(voices['english_voices'])}")
        print(f"日文声音数量: {len(voices['japanese_voices'])}")
    except Exception as e:
        print(f"❌ 获取声音列表失败: {e}")
        return
    
    # 测试文本转语音
    print("\n=== 测试文本转语音 ===")
    test_text = "你好，这是一个语音测试。"
    
    try:
        print(f"转换文本: {test_text}")
        audio_data = voice_service.text_to_speech(
            text=test_text,
            voice_id="Chinese (Mandarin)_Radio_Host",
            speed=0.8,
            pitch=0,
            volume=1.0
        )
        
        if audio_data:
            print(f"✓ 语音转换成功，音频数据大小: {len(audio_data)} 字节")
            
            # 保存测试音频文件
            output_file = "test_voice_output.mp3"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"✓ 音频文件已保存为: {output_file}")
        else:
            print("❌ 语音转换失败，返回数据为空")
    except Exception as e:
        print(f"❌ 语音转换异常: {e}")


if __name__ == "__main__":
    asyncio.run(test_voice_service()) 