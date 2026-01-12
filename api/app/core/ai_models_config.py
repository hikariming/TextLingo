"""
AI模型统一配置文件
包含模型列表、用户权限、积分定价等配置
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
import json
import os
import math


class UserTier(str, Enum):
    """用户订阅级别"""
    FREE = "free"
    PLUS = "plus"
    PRO = "pro"
    MAX = "max"


class ModelProvider(str, Enum):
    """模型提供商"""
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    QWEN_TRANSLATION = "qwen_translation"


class BillingType(str, Enum):
    """计费类型"""
    PER_REQUEST = "per_request"
    PER_TOKEN = "per_token"
    PER_CHARACTER = "per_character"
    FREE = "free"


class ModelCapability(str, Enum):
    """模型能力"""
    CHAT = "chat"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    GENERATION = "generation"
    VISION = "vision"
    CODE = "code"


class ModelConfig(BaseModel):
    """单个模型配置"""
    # 基础信息
    id: str = Field(..., description="模型唯一标识")
    name: str = Field(..., description="模型显示名称")
    provider: ModelProvider = Field(..., description="提供商")
    aimodel_key: str = Field(..., description="调用时使用的模型标识")
    
    # 能力和特性
    capabilities: List[ModelCapability] = Field(default=[], description="模型能力列表")
    max_tokens: int = Field(default=4096, description="最大token数")
    supports_vision: bool = Field(default=False, description="是否支持视觉输入")
    supports_function_calling: bool = Field(default=False, description="是否支持函数调用")
    
    # 权限控制
    required_tier: UserTier = Field(default=UserTier.FREE, description="所需最低订阅级别")
    allowed_tiers: List[UserTier] = Field(default=[], description="允许的订阅级别")
    
    # 计费配置
    billing_type: BillingType = Field(default=BillingType.PER_TOKEN, description="计费类型")
    base_points: int = Field(default=1, description="基础积分消耗")
    points_per_1k_tokens: Optional[int] = Field(None, description="每1K tokens消耗积分")
    points_per_request: Optional[int] = Field(None, description="每次请求消耗积分")
    points_per_100_chars: Optional[int] = Field(None, description="每100字符消耗积分")
    
    # 性能配置
    temperature: float = Field(default=0.7, description="默认温度")
    timeout: int = Field(default=30, description="超时时间(秒)")
    rate_limit_per_minute: int = Field(default=60, description="每分钟请求限制")
    
    # 状态
    is_active: bool = Field(default=True, description="是否启用")
    is_beta: bool = Field(default=False, description="是否为测试版")
    
    # 描述信息
    description: str = Field(default="", description="模型描述")
    use_cases: List[str] = Field(default=[], description="适用场景")
    limitations: List[str] = Field(default=[], description="使用限制")


class UserTierConfig(BaseModel):
    """用户订阅级别配置"""
    tier: UserTier
    name: str = Field(..., description="级别名称")
    description: str = Field(..., description="级别描述")
    max_requests_per_day: int = Field(default=0, description="每日最大请求数，0表示无限制")
    max_tokens_per_request: int = Field(default=4096, description="单次请求最大token数")
    priority: int = Field(default=1, description="优先级，数字越大优先级越高")
    features: List[str] = Field(default=[], description="特性列表")


class AIModelsConfig:
    """AI模型配置管理器"""
    
    def __init__(self, config_file: str = "app/config/ai_models_config.json"):
        self.config_file = config_file
        self.models: Dict[str, ModelConfig] = {}
        self.user_tiers: Dict[UserTier, UserTierConfig] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 加载模型配置
                for model_data in data.get("models", []):
                    model = ModelConfig(**model_data)
                    self.models[model.id] = model
                
                # 加载用户级别配置
                for tier_data in data.get("user_tiers", []):
                    tier_config = UserTierConfig(**tier_data)
                    self.user_tiers[tier_config.tier] = tier_config
                    
                print(f"成功加载配置文件: {len(self.models)} 个模型, {len(self.user_tiers)} 个用户层级")
            else:
                print(f"配置文件 {self.config_file} 不存在，将创建默认用户层级配置")
                # 创建默认用户层级配置（不含模型配置）
                self._create_default_config()
                
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            print("将创建默认用户层级配置，但模型配置需要手动添加到JSON文件中")
            self._create_default_config()
            
        # 验证配置完整性
        validation = self.validate_config()
        if not validation["valid"]:
            print("⚠️  配置验证失败:")
            for error in validation["errors"]:
                print(f"   错误: {error}")
        if validation["warnings"]:
            print("⚠️  配置警告:")
            for warning in validation["warnings"]:
                print(f"   警告: {warning}")
    
    def _create_default_config(self):
        """创建默认配置"""
        # 只创建默认用户级别配置，模型配置应该从JSON文件获取
        default_tiers = [
            UserTierConfig(
                tier=UserTier.FREE,
                name="Free",
                description="基础功能，有使用限制",
                max_requests_per_day=50,
                max_tokens_per_request=1024,
                priority=1,
                features=["基础聊天", "简单分析"]
            ),
            UserTierConfig(
                tier=UserTier.PLUS,
                name="Plus",
                description="增强功能和更高限制",
                max_requests_per_day=200,
                max_tokens_per_request=4096,
                priority=2,
                features=["更多模型", "更多tokens", "优先支持"]
            ),
            UserTierConfig(
                tier=UserTier.PRO,
                name="Pro",
                description="专业用户，完整功能",
                max_requests_per_day=1000,
                max_tokens_per_request=32768,
                priority=3,
                features=["高级模型", "函数调用", "优先处理", "API访问"]
            ),
            UserTierConfig(
                tier=UserTier.MAX,
                name="Max",
                description="最高级别，无限制使用",
                max_requests_per_day=0,  # 无限制
                max_tokens_per_request=128000,
                priority=4,
                features=["所有模型", "无限使用", "专属支持", "自定义模型"]
            )
        ]
        
        for tier_config in default_tiers:
            self.user_tiers[tier_config.tier] = tier_config
        
        # 保存默认配置（但不包含模型配置，因为模型配置应该从JSON文件获取）
        self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            data = {
                "models": [model.dict() for model in self.models.values()],
                "user_tiers": [tier.dict() for tier in self.user_tiers.values()]
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_available_models(self, user_tier: UserTier, capability: Optional[ModelCapability] = None) -> List[ModelConfig]:
        """获取用户可用的模型列表"""
        available = []
        
        for model in self.models.values():
            if not model.is_active:
                continue
                
            # 检查用户级别权限
            if user_tier not in model.allowed_tiers and model.required_tier != user_tier:
                # 检查级别是否足够
                tier_priority = self.user_tiers.get(user_tier, UserTierConfig(tier=user_tier, name="", description="")).priority
                required_priority = self.user_tiers.get(model.required_tier, UserTierConfig(tier=model.required_tier, name="", description="")).priority
                
                if tier_priority < required_priority:
                    continue
            
            # 检查能力匹配
            if capability and capability not in model.capabilities:
                continue
                
            available.append(model)
        
        # 按优先级排序（免费用户优先看到便宜的模型）
        tier_priority = self.user_tiers.get(user_tier, UserTierConfig(tier=user_tier, name="", description="")).priority
        available.sort(key=lambda x: (x.base_points, x.points_per_1k_tokens or 0))
        
        return available
    
    def get_all_active_models(self, capability: Optional[ModelCapability] = None) -> List[ModelConfig]:
        """获取所有活跃的模型列表（不进行权限过滤）"""
        active_models = []
        
        for model in self.models.values():
            if not model.is_active:
                continue
            
            # 检查能力匹配
            if capability and capability not in model.capabilities:
                continue
                
            active_models.append(model)
        
        # 按积分消耗排序（便宜的优先）
        active_models.sort(key=lambda x: (x.base_points, x.points_per_1k_tokens or 0))
        
        return active_models
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """获取指定模型配置"""
        return self.models.get(model_id)
    
    def can_user_access_model(self, user_tier: UserTier, model_id: str) -> bool:
        """检查用户是否可以访问指定模型"""
        model = self.get_model(model_id)
        if not model or not model.is_active:
            return False
        
        if user_tier in model.allowed_tiers:
            return True
            
        tier_priority = self.user_tiers.get(user_tier, UserTierConfig(tier=user_tier, name="", description="")).priority
        required_priority = self.user_tiers.get(model.required_tier, UserTierConfig(tier=model.required_tier, name="", description="")).priority
        
        return tier_priority >= required_priority
    
    def calculate_points_cost(self, model_id: str, tokens_used: int = 0, characters_count: int = 0) -> int:
        """计算积分消耗"""
        model = self.get_model(model_id)
        if not model:
            return 0
        
        if model.billing_type == BillingType.FREE:
            return 0
        elif model.billing_type == BillingType.PER_REQUEST:
            return model.points_per_request or model.base_points
        elif model.billing_type == BillingType.PER_TOKEN and model.points_per_1k_tokens:
            # 按比例计算积分，而不是整数除法
            # 使用 math.ceil 确保任何使用量都至少收费 1 积分
            return max(1, math.ceil(tokens_used / 1000) * model.points_per_1k_tokens)
        elif model.billing_type == BillingType.PER_CHARACTER and model.points_per_100_chars:
            return max(1, math.ceil(characters_count / 100) * model.points_per_100_chars)
        else:
            return model.base_points
    
    def reload_config(self):
        """重新加载配置"""
        self.models.clear()
        self.user_tiers.clear()
        self._load_config()
        
    def validate_config(self) -> Dict[str, Any]:
        """验证配置完整性"""
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # 检查模型配置
        if not self.models:
            validation_result["valid"] = False
            validation_result["errors"].append("没有可用的模型配置，请检查JSON配置文件")
        
        # 检查用户层级配置
        if not self.user_tiers:
            validation_result["warnings"].append("没有用户层级配置，将使用默认设置")
        
        # 检查每个模型的必要参数
        for model_id, model in self.models.items():
            if not model.aimodel_key:
                validation_result["errors"].append(f"模型 {model_id} 缺少 aimodel_key")
            if not model.provider:
                validation_result["errors"].append(f"模型 {model_id} 缺少 provider")
        
        return validation_result


# 创建全局配置实例
ai_models_config = AIModelsConfig()


# 辅助函数
def get_user_tier_from_subscription(subscription_plan: Optional[str]) -> UserTier:
    """从订阅计划转换为用户级别"""
    # 处理 None 值，默认返回免费级别
    if subscription_plan is None:
        return UserTier.FREE
    
    plan_mapping = {
        "free": UserTier.FREE,
        "plus": UserTier.PLUS,
        "pro": UserTier.PRO,
        "max": UserTier.MAX
    }
    return plan_mapping.get(subscription_plan.lower(), UserTier.FREE)