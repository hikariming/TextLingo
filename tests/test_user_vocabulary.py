import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

import pytest
from datetime import datetime, timedelta
from models.user_vocabulary import UserVocabulary
from services.user_vocabulary_service import UserVocabularyService
from mongoengine.connection import connect, disconnect
from models.setting import Setting

class TestUserVocabulary:
    @classmethod
    def setup_class(cls):
        """测试类开始前的设置"""
        disconnect()  # 断开可能存在的连接
        connect('textlingo', host='mongodb://admin_my_lingo:132welovehohohoyo95@119.91.225.127:26888/?authSource=admin')
    
    def setup_method(self):
        """每个测试方法开始前的设置"""
        UserVocabulary.objects.delete()  # 清空测试数据
        Setting.objects.delete()  # 清空设置
        # 设置默认的每日复习限制
        Setting.set_setting('daily_review_limit', '20', '每日复习单词数量限制')
    
    def teardown_method(self):
        """每个测试方法结束后的清理"""
        UserVocabulary.objects.delete()
        Setting.objects.delete()

    def test_create_vocabulary(self):
        """测试创建单词"""
        vocab = UserVocabularyService.create_vocabulary(
            word="测试",
            meaning="test",
            reading="ceshi"
        )
        assert vocab is not None
        assert vocab.word == "测试"
        assert vocab.meaning == "test"
        assert vocab.reading == "ceshi"
        assert vocab.next_review_at is not None

    def test_review_flow(self):
        """测试完整的复习流程"""
        # 创建测试单词
        vocab = UserVocabularyService.create_vocabulary(
            word="测试",
            meaning="test"
        )
        vocab_id = str(vocab.id)

        # 测试获取待复习单词
        next_word = UserVocabularyService.get_next_review_word()
        assert next_word is not None
        assert next_word['word'] == "测试"

        # 测试标记为记住
        result = UserVocabularyService.mark_word_remembered(vocab_id)
        assert result['review_stage'] == 1
        assert result['review_count'] == 1
        assert result['correct_count'] == 1

        # 测试标记为忘记
        result = UserVocabularyService.mark_word_forgotten(vocab_id)
        assert result['review_stage'] == 0
        assert result['review_count'] == 2
        assert result['correct_count'] == 1

    def test_review_intervals(self):
        """测试复习间隔"""
        vocab = UserVocabularyService.create_vocabulary(
            word="间隔测试",
            meaning="interval test"
        )
        vocab_id = str(vocab.id)

        print("\n=== Test Debug Info ===")
        print(f"创建单词时间: {vocab.created_at}")
        print(f"初始复习时间: {vocab.next_review_at}")

        # 记录初始时间作为基准
        current_time = datetime.utcnow()
        next_review_base = current_time.replace(hour=2, minute=0, second=0, microsecond=0)
        if current_time.hour >= 2:
            next_review_base = next_review_base + timedelta(days=1)

        print(f"测试基准时间: {next_review_base}")

        # 测试不同阶段的复习间隔
        intervals = [1, 2, 4, 7, 15, 30]  # 预期的间隔天数
        
        for i, expected_interval in enumerate(intervals):
            result = UserVocabularyService.mark_word_remembered(vocab_id)
            next_review = result['next_review_at']
            
            # 如果 next_review 是字符串，需要先转换为 datetime 对象
            if isinstance(next_review, str):
                try:
                    next_review_date = datetime.fromisoformat(next_review.replace('Z', '+00:00'))
                except ValueError:
                    next_review_date = datetime.strptime(next_review, '%Y-%m-%dT%H:%M:%S.%f')
            else:
                next_review_date = next_review
            
            # 更新基准时间为当前时间的下一个凌晨2点
            current_time = datetime.utcnow()
            next_review_base = current_time.replace(hour=2, minute=0, second=0, microsecond=0)
            if current_time.hour >= 2:
                next_review_base = next_review_base + timedelta(days=1)
                
            # 计算预期的下次复习时间
            expected_date = next_review_base + timedelta(days=expected_interval)
            
            # 计算时间差（秒）
            time_diff = abs((next_review_date - expected_date).total_seconds())
            
            # 断言时间差小于60秒
            assert time_diff < 60, (
                f"复习间隔不正确：\n"
                f"阶段: {i}\n"
                f"期望间隔: {expected_interval} 天\n"
                f"基准时间: {next_review_base}\n"
                f"预期时间: {expected_date}\n"
                f"实际时间: {next_review_date}\n"
                f"时间差: {time_diff} 秒"
            )
            
            # 更新基准时间为实际的下次复习时间
            next_review_base = next_review_date

    def test_daily_limit(self):
        """测试每日复习限制"""
        # 创建25个单词
        for i in range(25):
            UserVocabularyService.create_vocabulary(
                word=f"测试{i}",
                meaning=f"test{i}"
            )

        # 设置每日限制为20个
        Setting.set_setting('daily_review_limit', '20', '每日复习单词数量限制')

        # 获取待复习单词
        words = UserVocabulary.get_next_review_words()
        assert len(list(words)) == 20  # 应该只返回20个单词

    def test_mastery_progression(self):
        """测试掌握度进展"""
        vocab = UserVocabularyService.create_vocabulary(
            word="掌握测试",
            meaning="mastery test"
        )
        vocab_id = str(vocab.id)

        # 连续正确回答6次
        for _ in range(6):
            result = UserVocabularyService.mark_word_remembered(vocab_id)

        # 检查是否达到掌握状态
        final_result = UserVocabularyService.get_vocabulary(vocab_id)
        assert final_result.mastered == True
        assert final_result.familiarity_level == 5

    def test_review_stats(self):
        """测试复习统计"""
        # 创建一些测试数据
        vocab1 = UserVocabularyService.create_vocabulary(
            word="统计测试1",
            meaning="stats test 1"
        )
        vocab2 = UserVocabularyService.create_vocabulary(
            word="统计测试2",
            meaning="stats test 2"
        )

        # 模拟一些复习操作
        UserVocabularyService.mark_word_remembered(str(vocab1.id))
        UserVocabularyService.mark_word_forgotten(str(vocab2.id))

        # 获取统计信息
        stats = UserVocabularyService.get_review_stats()
        assert stats['reviewed_count'] == 2
        assert stats['accuracy_rate'] == 50.0  # 一个记住一个忘记，正确率50%