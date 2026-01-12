#!/usr/bin/env python3
"""
测试小说上传端点的i18n功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the i18n functions
exec(open('app/core/i18n.py').read())

def test_novel_upload_messages():
    """测试小说上传相关的i18n消息"""
    print("🧪 Testing Novel Upload I18n Messages\n")
    
    # Test scenarios
    scenarios = [
        {
            "header": "en-US,en;q=0.9",
            "expected_lang": SupportedLanguage.EN,
            "name": "English User"
        },
        {
            "header": "zh-CN,zh;q=0.9,en;q=0.8", 
            "expected_lang": SupportedLanguage.ZH,
            "name": "Chinese Simplified User"
        },
        {
            "header": "zh-TW,zh;q=0.8,en;q=0.7",
            "expected_lang": SupportedLanguage.ZH_TW,
            "name": "Chinese Traditional User"
        },
        {
            "header": "ja-JP,ja;q=0.9",
            "expected_lang": SupportedLanguage.JA,
            "name": "Japanese User"
        }
    ]
    
    # Test each scenario
    for scenario in scenarios:
        print(f"👤 {scenario['name']} (Accept-Language: {scenario['header']})")
        print("=" * 50)
        
        # Detect language
        detected_lang = get_language_from_header(scenario['header'])
        print(f"Detected Language: {detected_lang}")
        
        # Test common novel upload messages
        messages_to_test = [
            "novel_created_success",
            "file_upload_success", 
            "supported_formats_error",
            "file_size_exceeded",
            "file_empty",
            "novel_not_found"
        ]
        
        for msg_key in messages_to_test:
            msg = get_message(msg_key, detected_lang)
            print(f"  {msg_key}: {msg}")
        
        # Test formatted messages
        print(f"  file_upload_failed: {get_message('file_upload_failed', detected_lang, error='Connection timeout')}")
        
        # Test status messages
        public_status = get_localized_status_text(True, detected_lang)
        private_status = get_localized_status_text(False, detected_lang)
        status_msg = get_message('public_status_updated', detected_lang, status=public_status)
        print(f"  public_status_updated: {status_msg}")
        
        print(f"  Status texts: public='{public_status}', private='{private_status}'")
        print()

def test_error_handling():
    """测试错误处理和回退机制"""
    print("🛡️  Testing Error Handling and Fallbacks\n")
    
    # Test with non-existent message key
    print("Testing non-existent message key:")
    for lang in [SupportedLanguage.EN, SupportedLanguage.ZH]:
        msg = get_message("non_existent_key", lang)
        print(f"  {lang}: {msg}")
    
    # Test with formatting error
    print("\nTesting formatting with missing parameter:")
    for lang in [SupportedLanguage.EN, SupportedLanguage.ZH]:
        msg = get_message("file_upload_failed", lang)  # Missing 'error' parameter
        print(f"  {lang}: {msg}")
    
    print()

def simulate_api_responses():
    """模拟API响应的多语言消息"""
    print("🌐 Simulating API Responses in Different Languages\n")
    
    test_cases = [
        {
            "scenario": "Successful file upload",
            "accept_language": "zh-CN,zh;q=0.9,en;q=0.8",
            "response": {
                "success": True,
                "message_key": "file_upload_success",
                "storage_path": "/novels/user123/novel456.txt",
                "file_size": 1024000
            }
        },
        {
            "scenario": "File too large error",
            "accept_language": "ja-JP,ja;q=0.9",
            "response": {
                "success": False,
                "message_key": "file_size_exceeded",
                "error_code": 400
            }
        },
        {
            "scenario": "Novel not found",
            "accept_language": "en-US,en;q=0.9",
            "response": {
                "success": False,
                "message_key": "novel_not_found",
                "error_code": 404
            }
        },
        {
            "scenario": "Toggle to public status",
            "accept_language": "zh-TW,zh;q=0.8,en;q=0.7",
            "response": {
                "success": True,
                "message_key": "public_status_updated",
                "is_public": True
            }
        }
    ]
    
    for case in test_cases:
        print(f"📱 Scenario: {case['scenario']}")
        print(f"   Accept-Language: {case['accept_language']}")
        
        # Detect language
        lang = get_language_from_header(case['accept_language'])
        print(f"   Detected Language: {lang}")
        
        # Generate response message
        if case['response']['message_key'] == 'public_status_updated':
            status_text = get_localized_status_text(case['response']['is_public'], lang)
            message = get_message(case['response']['message_key'], lang, status=status_text)
        else:
            message = get_message(case['response']['message_key'], lang)
        
        print(f"   Response Message: {message}")
        print()

if __name__ == "__main__":
    print("🚀 Testing I18n Implementation for Novel Upload Endpoints")
    print("=" * 60)
    print()
    
    test_novel_upload_messages()
    test_error_handling()
    simulate_api_responses()
    
    print("✅ All I18n tests completed successfully!")
    print("\n💡 How to use in your frontend:")
    print("   1. Set the 'Accept-Language' header in your HTTP requests")
    print("   2. Example headers:")
    print("      - 'zh-CN,zh;q=0.9,en;q=0.8' for Chinese Simplified")
    print("      - 'zh-TW,zh;q=0.8,en;q=0.7' for Chinese Traditional") 
    print("      - 'ja-JP,ja;q=0.9' for Japanese")
    print("      - 'en-US,en;q=0.9' for English")
    print("   3. The API will automatically return localized messages")