"""
测试文章阅读材料功能的完整测试文件
包含：创建文章库、上传文章、分段功能的测试
"""

import pytest
import asyncio
import json
import httpx
from typing import Dict, Any
from app.services.material_service import material_service
from app.schemas.material_schemas import (
    MaterialLibraryCreate, MaterialArticleCreate, MaterialSegmentCreate,
    MaterialSegmentBatchCreate, MaterialSegmentBase
)

# 测试配置
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "beiming1201@gmail.com"
TEST_PASSWORD = "AAAA123456"

class AuthHelper:
    """认证辅助类"""
    
    def __init__(self):
        self.token = None
        self.user_id = None
    
    async def login(self):
        """登录获取认证信息"""
        async with httpx.AsyncClient() as client:
            login_data = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            
            response = await client.post(f"{API_BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                
                if not self.token or not self.user_id:
                    raise Exception(f"登录成功但无法获取认证信息: {data}")
                
                print(f"✅ 登录成功，用户ID: {self.user_id}")
                return True
            else:
                raise Exception(f"登录失败: {response.status_code} - {response.text}")
    
    def get_user_id(self):
        """获取用户ID"""
        if not self.user_id:
            raise Exception("用户未登录")
        return self.user_id

# 全局认证辅助实例
auth_helper = AuthHelper()

class TestMaterialService:
    """测试材料服务的类"""
    
    def __init__(self):
        self.created_library_id = None
        self.created_article_id = None
        self.created_segment_ids = []
    
    async def test_create_library(self):
        """测试创建文章库"""
        print("🧪 测试创建文章库...")
        
        library_data = MaterialLibraryCreate(
            name="测试文章库",
            description="这是一个测试的文章库",
            library_type="text",
            target_language="zh-CN",
            explanation_language="zh-CN",
            is_public=False
        )
        
        try:
            user_id = auth_helper.get_user_id()
            library = await material_service.create_library(user_id, library_data)
            self.created_library_id = library.id
            
            print(f"✅ 文章库创建成功")
            print(f"   库ID: {library.id}")
            print(f"   库名: {library.name}")
            print(f"   描述: {library.description}")
            print(f"   类型: {library.library_type}")
            print(f"   目标语言: {library.target_language}")
            print(f"   创建时间: {library.created_at}")
            print()
            
            return library
        except Exception as e:
            print(f"❌ 文章库创建失败: {e}")
            raise
    
    async def test_list_libraries(self):
        """测试获取文章库列表"""
        print("🧪 测试获取文章库列表...")
        
        from app.schemas.material_schemas import MaterialLibraryQuery
        
        query = MaterialLibraryQuery(
            page=1,
            page_size=10,
            library_type="text",
            is_public=False
        )
        
        try:
            user_id = auth_helper.get_user_id()
            libraries, total = await material_service.list_libraries(user_id, query)
            
            print(f"✅ 文章库列表获取成功")
            print(f"   总数: {total}")
            print(f"   当前页库数: {len(libraries)}")
            
            for library in libraries:
                print(f"   - {library.name} (ID: {library.id})")
            print()
            
            return libraries, total
        except Exception as e:
            print(f"❌ 文章库列表获取失败: {e}")
            raise
    
    async def test_create_article(self):
        """测试创建文章"""
        print("🧪 测试创建文章...")
        
        article_data = MaterialArticleCreate(
            title="测试文章：日语学习指南",
            content="""
            こんにちは。今日は日本語の勉強について話しましょう。
            日本語は難しい言語ですが、毎日練習すれば上達できます。
            最初に、ひらがなとカタカナを覚えることが重要です。
            次に、基本的な単語を学びましょう。
            そして、簡単な文法を理解することが大切です。
            頑張って勉強してください。
            """,
            file_type="text",
            library_id=self.created_library_id,
            target_language="ja",
            difficulty_level="beginner",
            category="语言学习",
            tags=["日语", "学习", "初级"],
            is_public=False,
            description="这是一篇关于日语学习的测试文章"
        )
        
        try:
            user_id = auth_helper.get_user_id()
            article = await material_service.create_article(user_id, article_data)
            self.created_article_id = article.id
            
            print(f"✅ 文章创建成功")
            print(f"   文章ID: {article.id}")
            print(f"   标题: {article.title}")
            print(f"   内容长度: {len(article.content)} 字符")
            print(f"   所属库ID: {article.library_id}")
            print(f"   目标语言: {article.target_language}")
            print(f"   难度等级: {article.difficulty_level}")
            print(f"   分类: {article.category}")
            print(f"   标签: {article.tags}")
            print(f"   创建时间: {article.created_at}")
            print()
            
            return article
        except Exception as e:
            print(f"❌ 文章创建失败: {e}")
            raise
    
    async def test_create_independent_article(self):
        """测试创建独立文章（不属于任何库）"""
        print("🧪 测试创建独立文章...")
        
        article_data = MaterialArticleCreate(
            title="独立文章：日语谚语集",
            content="""
            日本には多くのことわざがあります。
            「努力は必ず報われる」- 努力すれば必ず良い結果が得られる。
            「継続は力なり」- 続けることが一番大切です。
            「失敗は成功の母」- 失敗から学ぶことが多い。
            これらのことわざを覚えて、日本語の理解を深めましょう。
            """,
            file_type="text",
            library_id=None,  # 不属于任何库
            target_language="ja",
            difficulty_level="intermediate",
            category="文化",
            tags=["日语", "谚语", "文化"],
            is_public=True,
            description="这是一篇独立的日语谚语文章"
        )
        
        try:
            user_id = auth_helper.get_user_id()
            article = await material_service.create_article(user_id, article_data)
            
            print(f"✅ 独立文章创建成功")
            print(f"   文章ID: {article.id}")
            print(f"   标题: {article.title}")
            print(f"   所属库ID: {article.library_id if article.library_id else '无（独立文章）'}")
            print(f"   是否公开: {article.is_public}")
            print()
            
            return article
        except Exception as e:
            print(f"❌ 独立文章创建失败: {e}")
            raise
    
    async def test_list_articles(self):
        """测试获取文章列表"""
        print("🧪 测试获取文章列表...")
        
        from app.schemas.material_schemas import MaterialArticleQuery
        
        query = MaterialArticleQuery(
            page=1,
            page_size=10,
            library_id=self.created_library_id,
            difficulty_level="beginner"
        )
        
        try:
            user_id = auth_helper.get_user_id()
            articles, total = await material_service.list_articles(user_id, query)
            
            print(f"✅ 文章列表获取成功")
            print(f"   总数: {total}")
            print(f"   当前页文章数: {len(articles)}")
            
            for article in articles:
                print(f"   - {article.title} (ID: {article.id})")
                print(f"     难度: {article.difficulty_level}, 分类: {article.category}")
            print()
            
            return articles, total
        except Exception as e:
            print(f"❌ 文章列表获取失败: {e}")
            raise
    
    async def test_create_single_segment(self):
        """测试创建单个分段"""
        print("🧪 测试创建单个分段...")
        
        segment_data = MaterialSegmentCreate(
            article_id=self.created_article_id,
            original_text="こんにちは。今日は日本語の勉強について話しましょう。",
            translation="你好。今天我们来谈论日语学习。",
            reading_text="こんにちは。きょうは にほんごの べんきょうについて はなしましょう。",
            is_new_paragraph=True,
            segment_order=0,
            grammar_items=[
                {"name": "について", "explanation": "关于、对于的意思，用来表示话题"},
                {"name": "ましょう", "explanation": "礼貌的邀请或建议形式"}
            ],
            vocabulary_items=[
                {"word": "今日", "reading": "きょう", "meaning": "今天"},
                {"word": "日本語", "reading": "にほんご", "meaning": "日语"},
                {"word": "勉強", "reading": "べんきょう", "meaning": "学习"}
            ]
        )
        
        try:
            user_id = auth_helper.get_user_id()
            segment = await material_service.create_segment(user_id, segment_data)
            self.created_segment_ids.append(segment.id)
            
            print(f"✅ 分段创建成功")
            print(f"   分段ID: {segment.id}")
            print(f"   原文: {segment.original_text}")
            print(f"   翻译: {segment.translation}")
            print(f"   读音: {segment.reading_text}")
            print(f"   段落顺序: {segment.segment_order}")
            print(f"   语法项目数: {len(segment.grammar_items)}")
            print(f"   词汇项目数: {len(segment.vocabulary_items)}")
            print()
            
            return segment
        except Exception as e:
            print(f"❌ 分段创建失败: {e}")
            raise
    
    async def test_create_batch_segments(self):
        """测试批量创建分段"""
        print("🧪 测试批量创建分段...")
        
        segments_data = [
            MaterialSegmentBase(
                original_text="日本語は難しい言語ですが、毎日練習すれば上達できます。",
                translation="日语是一门困难的语言，但如果每天练习就能提高。",
                reading_text="にほんごは むずかしい げんごですが、まいにち れんしゅうすれば じょうたつできます。",
                is_new_paragraph=False,
                segment_order=1,
                grammar_items=[
                    {"name": "ですが", "explanation": "但是、虽然的意思，表示转折"},
                    {"name": "すれば", "explanation": "假设条件形式，如果...的话"}
                ],
                vocabulary_items=[
                    {"word": "難しい", "reading": "むずかしい", "meaning": "困难的"},
                    {"word": "毎日", "reading": "まいにち", "meaning": "每天"},
                    {"word": "練習", "reading": "れんしゅう", "meaning": "练习"}
                ]
            ),
            MaterialSegmentBase(
                original_text="最初に、ひらがなとカタカナを覚えることが重要です。",
                translation="首先，记住平假名和片假名很重要。",
                reading_text="さいしょに、ひらがなと カタカナを おぼえることが じゅうようです。",
                is_new_paragraph=False,
                segment_order=2,
                grammar_items=[
                    {"name": "ことが重要です", "explanation": "做...很重要的表达方式"}
                ],
                vocabulary_items=[
                    {"word": "最初", "reading": "さいしょ", "meaning": "最初、开始"},
                    {"word": "覚える", "reading": "おぼえる", "meaning": "记住、记忆"},
                    {"word": "重要", "reading": "じゅうよう", "meaning": "重要"}
                ]
            ),
            MaterialSegmentBase(
                original_text="次に、基本的な単語を学びましょう。",
                translation="接下来，让我们学习基本的单词。",
                reading_text="つぎに、きほんてきな たんごを まなびましょう。",
                is_new_paragraph=False,
                segment_order=3,
                grammar_items=[
                    {"name": "基本的な", "explanation": "基本的、基础的形容词形式"}
                ],
                vocabulary_items=[
                    {"word": "次に", "reading": "つぎに", "meaning": "接下来"},
                    {"word": "基本的", "reading": "きほんてき", "meaning": "基本的"},
                    {"word": "単語", "reading": "たんご", "meaning": "单词"}
                ]
            )
        ]
        
        batch_data = MaterialSegmentBatchCreate(
            article_id=self.created_article_id,
            segments=segments_data
        )
        
        try:
            user_id = auth_helper.get_user_id()
            segments = await material_service.create_segments_batch(user_id, batch_data)
            self.created_segment_ids.extend([segment.id for segment in segments])
            
            print(f"✅ 批量分段创建成功")
            print(f"   创建分段数: {len(segments)}")
            
            for i, segment in enumerate(segments):
                print(f"   {i+1}. {segment.original_text[:30]}...")
                print(f"      翻译: {segment.translation[:30]}...")
                print(f"      语法项目: {len(segment.grammar_items)}")
                print(f"      词汇项目: {len(segment.vocabulary_items)}")
            print()
            
            return segments
        except Exception as e:
            print(f"❌ 批量分段创建失败: {e}")
            raise
    
    async def test_get_article_segments(self):
        """测试获取文章分段列表"""
        print("🧪 测试获取文章分段列表...")
        
        try:
            user_id = auth_helper.get_user_id()
            segments, total = await material_service.get_article_segments(
                user_id, 
                self.created_article_id,
                page=1,
                page_size=100
            )
            
            print(f"✅ 文章分段列表获取成功")
            print(f"   总分段数: {total}")
            print(f"   当前页分段数: {len(segments)}")
            
            for segment in segments:
                print(f"   顺序 {segment.segment_order}: {segment.original_text[:40]}...")
            print()
            
            return segments, total
        except Exception as e:
            print(f"❌ 文章分段列表获取失败: {e}")
            raise
    
    async def test_update_segment(self):
        """测试更新分段"""
        print("🧪 测试更新分段...")
        
        if not self.created_segment_ids:
            print("❌ 没有可更新的分段")
            return
        
        segment_id = self.created_segment_ids[0]
        
        from app.schemas.material_schemas import MaterialSegmentUpdate
        
        update_data = MaterialSegmentUpdate(
            translation="你好！今天我们来谈论关于日语学习的话题。",
            reading_text="こんにちは！きょうは にほんごの べんきょうについて はなします。",
            grammar_items=[
                {"name": "について", "explanation": "关于、对于的意思，用来表示话题"},
                {"name": "ましょう", "explanation": "礼貌的邀请或建议形式（已更新）"}
            ]
        )
        
        try:
            user_id = auth_helper.get_user_id()
            segment = await material_service.update_segment(user_id, segment_id, update_data)
            
            print(f"✅ 分段更新成功")
            print(f"   分段ID: {segment.id}")
            print(f"   更新后翻译: {segment.translation}")
            print(f"   更新后读音: {segment.reading_text}")
            print(f"   语法项目数: {len(segment.grammar_items)}")
            print()
            
            return segment
        except Exception as e:
            print(f"❌ 分段更新失败: {e}")
            raise
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行文章阅读材料功能完整测试...\n")
        
        # 首先进行登录认证
        print("🔐 正在进行用户认证...")
        await auth_helper.login()
        print()
        
        try:
            # 测试文章库功能
            await self.test_create_library()
            await self.test_list_libraries()
            
            # 测试文章功能
            await self.test_create_article()
            await self.test_create_independent_article()
            await self.test_list_articles()
            
            # 测试分段功能
            await self.test_create_single_segment()
            await self.test_create_batch_segments()
            await self.test_get_article_segments()
            await self.test_update_segment()
            
            print("🎉 所有测试完成！")
            print(f"   测试用户: {TEST_EMAIL}")
            print(f"   用户ID: {auth_helper.get_user_id()}")
            print(f"   创建的文章库ID: {self.created_library_id}")
            print(f"   创建的文章ID: {self.created_article_id}")
            print(f"   创建的分段数: {len(self.created_segment_ids)}")
            
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
            raise


async def main():
    """主测试函数"""
    test_service = TestMaterialService()
    await test_service.run_all_tests()


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 文章阅读材料功能测试")
    print("=" * 60)
    print()
    
    # 运行测试
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n测试结束")
    print("=" * 60) 