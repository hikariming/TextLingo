#!/bin/bash

# 文章阅读材料 API 测试脚本
# 需要先启动 API 服务器并获取认证令牌

echo "================================================="
echo "🧪 文章阅读材料 API 测试"
echo "================================================="

# 配置
API_BASE_URL="http://localhost:8000/api/v1"
TEST_EMAIL="beiming1201@gmail.com"
TEST_PASSWORD="AAAA123456"

# 登录获取认证令牌
echo "🔑 登录获取认证令牌..."
LOGIN_DATA='{
    "email": "'$TEST_EMAIL'",
    "password": "'$TEST_PASSWORD'"
}'

LOGIN_RESPONSE=$(curl -X POST \
    -H "Content-Type: application/json" \
    -d "$LOGIN_DATA" \
    "$API_BASE_URL/auth/login" \
    -s)

AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$AUTH_TOKEN" ]; then
    echo "❌ 登录失败，无法获取认证令牌"
    echo "响应: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ 登录成功，获取到认证令牌"
echo ""

# 通用的 curl 函数
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local description="$4"
    
    echo ""
    echo "🔄 测试: $description"
    echo "   $method $endpoint"
    
    if [ -n "$data" ]; then
        curl -X "$method" \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE_URL$endpoint" \
            -w "\n状态码: %{http_code}\n" \
            -s
    else
        curl -X "$method" \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            "$API_BASE_URL$endpoint" \
            -w "\n状态码: %{http_code}\n" \
            -s
    fi
    
    echo ""
}

# 保存创建的资源ID
LIBRARY_ID=""
ARTICLE_ID=""
SEGMENT_ID=""

# 1. 创建文章库
echo "1️⃣ 创建文章库"
LIBRARY_DATA='{
    "name": "测试文章库",
    "description": "这是一个测试的文章库",
    "library_type": "text",
    "target_language": "zh-CN",
    "explanation_language": "zh-CN",
    "is_public": false
}'

response=$(make_request "POST" "/materials/libraries" "$LIBRARY_DATA" "创建文章库")
LIBRARY_ID=$(echo "$response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
echo "创建的文章库ID: $LIBRARY_ID"

# 2. 获取文章库列表
echo "2️⃣ 获取文章库列表"
make_request "GET" "/materials/libraries?page=1&page_size=10" "" "获取文章库列表"

# 3. 创建文章
echo "3️⃣ 创建文章"
ARTICLE_DATA='{
    "title": "测试文章：日语学习指南",
    "content": "こんにちは。今日は日本語の勉強について話しましょう。日本語は難しい言語ですが、毎日練習すれば上達できます。",
    "file_type": "text",
    "library_id": "'$LIBRARY_ID'",
    "target_language": "ja",
    "difficulty_level": "beginner",
    "category": "语言学习",
    "tags": ["日语", "学习", "初级"],
    "is_public": false,
    "description": "这是一篇关于日语学习的测试文章"
}'

response=$(make_request "POST" "/materials/articles" "$ARTICLE_DATA" "创建文章")
ARTICLE_ID=$(echo "$response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
echo "创建的文章ID: $ARTICLE_ID"

# 4. 创建独立文章（不属于任何库）
echo "4️⃣ 创建独立文章"
INDEPENDENT_ARTICLE_DATA='{
    "title": "独立文章：日语谚语集",
    "content": "日本には多くのことわざがあります。「努力は必ず報われる」- 努力すれば必ず良い結果が得られる。",
    "file_type": "text",
    "library_id": null,
    "target_language": "ja",
    "difficulty_level": "intermediate",
    "category": "文化",
    "tags": ["日语", "谚语", "文化"],
    "is_public": true,
    "description": "这是一篇独立的日语谚语文章"
}'

make_request "POST" "/materials/articles" "$INDEPENDENT_ARTICLE_DATA" "创建独立文章"

# 5. 获取文章列表
echo "5️⃣ 获取文章列表"
make_request "GET" "/materials/articles?page=1&page_size=10" "" "获取文章列表"

# 6. 获取特定文章库的文章
if [ -n "$LIBRARY_ID" ]; then
    echo "6️⃣ 获取特定文章库的文章"
    make_request "GET" "/materials/articles?library_id=$LIBRARY_ID" "" "获取特定文章库的文章"
fi

# 7. 创建文章分段
if [ -n "$ARTICLE_ID" ]; then
    echo "7️⃣ 创建文章分段"
    SEGMENT_DATA='{
        "article_id": "'$ARTICLE_ID'",
        "original_text": "こんにちは。今日は日本語の勉強について話しましょう。",
        "translation": "你好。今天我们来谈论日语学习。",
        "reading_text": "こんにちは。きょうは にほんごの べんきょうについて はなしましょう。",
        "is_new_paragraph": true,
        "segment_order": 0,
        "grammar_items": [
            {"name": "について", "explanation": "关于、对于的意思，用来表示话题"},
            {"name": "ましょう", "explanation": "礼貌的邀请或建议形式"}
        ],
        "vocabulary_items": [
            {"word": "今日", "reading": "きょう", "meaning": "今天"},
            {"word": "日本語", "reading": "にほんご", "meaning": "日语"},
            {"word": "勉強", "reading": "べんきょう", "meaning": "学习"}
        ]
    }'
    
    response=$(make_request "POST" "/materials/segments" "$SEGMENT_DATA" "创建文章分段")
    SEGMENT_ID=$(echo "$response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    echo "创建的分段ID: $SEGMENT_ID"
fi

# 8. 批量创建分段
if [ -n "$ARTICLE_ID" ]; then
    echo "8️⃣ 批量创建分段"
    BATCH_SEGMENTS_DATA='{
        "article_id": "'$ARTICLE_ID'",
        "segments": [
            {
                "original_text": "日本語は難しい言語ですが、毎日練習すれば上達できます。",
                "translation": "日语是一门困难的语言，但如果每天练习就能提高。",
                "reading_text": "にほんごは むずかしい げんごですが、まいにち れんしゅうすれば じょうたつできます。",
                "is_new_paragraph": false,
                "segment_order": 1,
                "grammar_items": [
                    {"name": "ですが", "explanation": "但是、虽然的意思，表示转折"},
                    {"name": "すれば", "explanation": "假设条件形式，如果...的话"}
                ],
                "vocabulary_items": [
                    {"word": "難しい", "reading": "むずかしい", "meaning": "困难的"},
                    {"word": "毎日", "reading": "まいにち", "meaning": "每天"},
                    {"word": "練習", "reading": "れんしゅう", "meaning": "练习"}
                ]
            },
            {
                "original_text": "最初に、ひらがなとカタカナを覚えることが重要です。",
                "translation": "首先，记住平假名和片假名很重要。",
                "reading_text": "さいしょに、ひらがなと カタカナを おぼえることが じゅうようです。",
                "is_new_paragraph": false,
                "segment_order": 2,
                "grammar_items": [
                    {"name": "ことが重要です", "explanation": "做...很重要的表达方式"}
                ],
                "vocabulary_items": [
                    {"word": "最初", "reading": "さいしょ", "meaning": "最初、开始"},
                    {"word": "覚える", "reading": "おぼえる", "meaning": "记住、记忆"},
                    {"word": "重要", "reading": "じゅうよう", "meaning": "重要"}
                ]
            }
        ]
    }'
    
    make_request "POST" "/materials/segments/batch" "$BATCH_SEGMENTS_DATA" "批量创建分段"
fi

# 9. 获取文章分段列表
if [ -n "$ARTICLE_ID" ]; then
    echo "9️⃣ 获取文章分段列表"
    make_request "GET" "/materials/articles/$ARTICLE_ID/segments?page=1&page_size=100" "" "获取文章分段列表"
fi

# 10. 自动分段文章
if [ -n "$ARTICLE_ID" ]; then
    echo "🔟 自动分段文章"
    make_request "POST" "/materials/articles/$ARTICLE_ID/auto-segment" "" "自动分段文章"
fi

# 11. 更新分段
if [ -n "$SEGMENT_ID" ]; then
    echo "1️⃣1️⃣ 更新分段"
    UPDATE_SEGMENT_DATA='{
        "translation": "你好！今天我们来谈论关于日语学习的话题。",
        "reading_text": "こんにちは！きょうは にほんごの べんきょうについて はなします。",
        "grammar_items": [
            {"name": "について", "explanation": "关于、对于的意思，用来表示话题"},
            {"name": "ましょう", "explanation": "礼貌的邀请或建议形式（已更新）"}
        ]
    }'
    
    make_request "PUT" "/materials/segments/$SEGMENT_ID" "$UPDATE_SEGMENT_DATA" "更新分段"
fi

# 12. 获取特定文章
if [ -n "$ARTICLE_ID" ]; then
    echo "1️⃣2️⃣ 获取特定文章"
    make_request "GET" "/materials/articles/$ARTICLE_ID" "" "获取特定文章"
fi

# 13. 获取特定文章库
if [ -n "$LIBRARY_ID" ]; then
    echo "1️⃣3️⃣ 获取特定文章库"
    make_request "GET" "/materials/libraries/$LIBRARY_ID" "" "获取特定文章库"
fi

# 14. 更新文章库
if [ -n "$LIBRARY_ID" ]; then
    echo "1️⃣4️⃣ 更新文章库"
    UPDATE_LIBRARY_DATA='{
        "name": "更新后的测试文章库",
        "description": "这是更新后的测试文章库描述",
        "is_public": true
    }'
    
    make_request "PUT" "/materials/libraries/$LIBRARY_ID" "$UPDATE_LIBRARY_DATA" "更新文章库"
fi

# 15. 更新文章
if [ -n "$ARTICLE_ID" ]; then
    echo "1️⃣5️⃣ 更新文章"
    UPDATE_ARTICLE_DATA='{
        "title": "更新后的测试文章：日语学习指南",
        "description": "这是更新后的测试文章描述",
        "difficulty_level": "intermediate",
        "tags": ["日语", "学习", "初级", "更新"]
    }'
    
    make_request "PUT" "/materials/articles/$ARTICLE_ID" "$UPDATE_ARTICLE_DATA" "更新文章"
fi

echo ""
echo "================================================="
echo "🎉 API 测试完成！"
echo "================================================="
echo "创建的资源:"
echo "  文章库ID: $LIBRARY_ID"
echo "  文章ID: $ARTICLE_ID"
echo "  分段ID: $SEGMENT_ID"
echo ""
echo "注意：如果要清理测试数据，请手动删除创建的资源。"
echo "=================================================" 