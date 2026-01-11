import sys
import os
import yaml
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time
from models.user_vocabulary import UserVocabulary
from services.user_vocabulary_service import UserVocabularyService
from mongoengine.connection import connect, disconnect
from models.setting import Setting

def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'api', 'config.yml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

class TestUserVocabulary:
    """测试用户词汇系统的各项功能"""
    
    @classmethod
    def setup_class(cls):
        """测试类开始前的设置"""
        config = load_config()
        disconnect()
        connect('textlingo', host=config['mongodb']['uri'])
        
    def setup_method(self):
        """每个测试方法开始前的设置"""
        # 清空测试数据
        UserVocabulary.objects.delete()
        Setting.objects.delete()
        # 设置默认的每日复习限制
        Setting.set_setting('daily_review_limit', '20', '每日复习单词数量限制')
        
    def teardown_method(self):
        """每个测试方法结束后的清理"""
        UserVocabulary.objects.delete()
        Setting.objects.delete()

    # 基础功能测试
    def test_create_vocabulary(self):
        """测试创建词汇的基本功能"""
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
        assert vocab.review_stage == 0
        assert vocab.familiarity_level == 0
        assert not vocab.mastered

    # 复习进度测试
    def test_review_progression(self):
        """测试复习进度推进逻辑"""
        vocab = UserVocabularyService.create_vocabulary(
            word="进度测试",
            meaning="progress test"
        )
        
        # 验证初始状态
        assert vocab.review_stage == 0
        
        # 测试6个阶段的进度
        for expected_stage in range(1, 6):
            result = UserVocabularyService.mark_word_remembered(str(vocab.id))
            
            # 验证阶段递增
            assert result['review_stage'] == expected_stage
            
            # 验证复习时间间隔
            vocab.reload()
            expected_interval = UserVocabulary.get_next_review_interval(expected_stage - 1)
            expected_next_review = datetime.utcnow().replace(hour=2, minute=0, second=0, microsecond=0)
            if datetime.utcnow().hour >= 2:
                expected_next_review += timedelta(days=1)
            expected_next_review += timedelta(days=expected_interval)
            
            time_diff = abs((vocab.next_review_at - expected_next_review).total_seconds())
            assert time_diff < 60, f"Stage {expected_stage}: Expected {expected_next_review}, got {vocab.next_review_at}"

    # 遗忘重置测试
    def test_forget_reset(self):
        """测试遗忘后的重置机制"""
        vocab = UserVocabularyService.create_vocabulary(
            word="重置测试",
            meaning="reset test"
        )
        
        # 先推进到第3阶段
        for _ in range(3):
            UserVocabularyService.mark_word_remembered(str(vocab.id))
        
        vocab.reload()
        assert vocab.review_stage == 3
        
        # 测试遗忘重置
        result = UserVocabularyService.mark_word_forgotten(str(vocab.id))
        
        # 验证重置结果
        assert result['review_stage'] == 0
        assert result['familiarity_level'] == 0
        assert not result['mastered']
        
        # 验证下次复习时间
        vocab.reload()
        expected_next_review = datetime.utcnow().replace(hour=2, minute=0, second=0, microsecond=0)
        if datetime.utcnow().hour >= 2:
            expected_next_review += timedelta(days=1)
        
        time_diff = abs((vocab.next_review_at - expected_next_review).total_seconds())
        assert time_diff < 60

    # 掌握条件测试
    def test_mastery_condition(self):
        """测试词汇掌握的条件判断"""
        vocab = UserVocabularyService.create_vocabulary(
            word="掌握测试",
            meaning="mastery test"
        )
        
        # 前5次复习不应该达到掌握
        for _ in range(5):
            result = UserVocabularyService.mark_word_remembered(str(vocab.id))
            vocab.reload()
            assert not vocab.mastered
        
        # 第6次复习后应该达到掌握
        result = UserVocabularyService.mark_word_remembered(str(vocab.id))
        vocab.reload()
        assert vocab.mastered
        assert vocab.familiarity_level == 5
        assert vocab.review_stage == 5

    # 每日限制测试
    def test_daily_review_limit(self):
        """测试每日复习数量限制"""
        # 创建25个词汇
        for i in range(25):
            UserVocabularyService.create_vocabulary(
                word=f"测试{i}",
                meaning=f"test{i}"
            )
        
        # 验证限制为20个
        review_words = UserVocabulary.get_next_review_words()
        assert len(list(review_words)) == 20

    # 时间边界测试
    def test_review_time_boundary(self):
        """测试凌晨2点边界的处理"""
        # 测试2点前的情况
        with freeze_time("2024-01-01 01:59:00"):
            vocab1 = UserVocabularyService.create_vocabulary(
                word="边界测试1",
                meaning="boundary test 1"
            )
            result = UserVocabularyService.mark_word_remembered(str(vocab1.id))
            vocab1.reload()
            
            expected_next_review = datetime(2024, 1, 1, 2, 0, 0) + \
                                 timedelta(days=UserVocabulary.get_next_review_interval(0))
            time_diff = abs((vocab1.next_review_at - expected_next_review).total_seconds())
            assert time_diff < 60

        # 测试2点后的情况
        with freeze_time("2024-01-01 02:01:00"):
            vocab2 = UserVocabularyService.create_vocabulary(
                word="边界测试2",
                meaning="boundary test 2"
            )
            result = UserVocabularyService.mark_word_remembered(str(vocab2.id))
            vocab2.reload()
            
            expected_next_review = datetime(2024, 1, 2, 2, 0, 0) + \
                                 timedelta(days=UserVocabulary.get_next_review_interval(0))
            time_diff = abs((vocab2.next_review_at - expected_next_review).total_seconds())
            assert time_diff < 60

    # 统计数据测试
    def test_review_stats(self):
        """测试复习统计数据"""
        # 创建测试数据
        vocab1 = UserVocabularyService.create_vocabulary(word="统计1", meaning="stats1")
        vocab2 = UserVocabularyService.create_vocabulary(word="统计2", meaning="stats2")
        vocab3 = UserVocabularyService.create_vocabulary(word="统计3", meaning="stats3")
        
        # 进行复习操作
        UserVocabularyService.mark_word_remembered(str(vocab1.id))
        UserVocabularyService.mark_word_forgotten(str(vocab2.id))
        
        # 验证统计结果
        stats = UserVocabularyService.get_review_stats()
        assert stats['total_review'] > 0
        assert stats['reviewed_count'] == 2
        assert stats['accuracy_rate'] == 50.0

    # 连续复习测试
    def test_consecutive_reviews(self):
        """测试连续复习的行为"""
        vocab = UserVocabularyService.create_vocabulary(
            word="连续测试",
            meaning="consecutive test"
        )
        
        # 测试连续记住
        result1 = UserVocabularyService.mark_word_remembered(str(vocab.id))
        result2 = UserVocabularyService.mark_word_remembered(str(vocab.id))
        assert result1['review_stage'] == 1
        assert result2['review_stage'] == 2
        
        # 测试遗忘后再次记住
        UserVocabularyService.mark_word_forgotten(str(vocab.id))
        result3 = UserVocabularyService.mark_word_remembered(str(vocab.id))
        assert result3['review_stage'] == 1