"""
Dify工作流配置管理器
管理多个Dify工作流的配置，包括URL、token、积分消耗等
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
import json
import os


class FlowType(str, Enum):
    """工作流类型"""
    WORKFLOW = "workflow"
    CHATFLOW = "chatflow"


class DifyInputConfig(BaseModel):
    """Dify 工作流输入参数定义"""
    name: str = Field(..., description="参数名")
    type: str = Field(default="string", description="参数类型 (string, file)")
    required: bool = Field(default=False, description="是否必须")


class DifyModelConfig(BaseModel):
    """Dify 模型配置"""
    id: str = Field(..., description="模型ID")
    name: str = Field(..., description="模型显示名称")
    input_token_cost: int = Field(..., description="输入token成本(每1000个)")
    output_token_cost: int = Field(..., description="输出token成本(每1000个)")
    base_cost: int = Field(..., description="基础费用(积分)")
    required_tier: str = Field(default="free", description="所需会员等级")
    max_tokens: int = Field(default=128000, description="最大token数")
    supports_function_calling: bool = Field(default=False, description="是否支持函数调用")
    rate_limit_per_minute: int = Field(default=60, description="每分钟请求限制")
    is_active: bool = Field(default=True, description="是否启用")
    supported_file_types: List[str] = Field(default=[], description="支持的文件类型")
    capabilities: List[str] = Field(default=[], description="模型能力")
    description: str = Field(default="", description="模型描述")


class DifyFlowConfig(BaseModel):
    """单个Dify工作流配置"""
    # 基础信息
    id: str = Field(..., description="工作流唯一标识")
    name: str = Field(..., description="工作流显示名称")
    api_url: str = Field(..., description="Dify API基础URL")
    api_token: str = Field(..., description="Dify API Token")
    
    # 工作流特性
    flow_type: FlowType = Field(..., description="工作流类型")
    points_cost: int = Field(default=30, description="每次调用消耗的积分")
    
    # 性能配置
    max_tokens: int = Field(default=4096, description="最大token数")
    timeout: int = Field(default=30, description="超时时间(秒)")
    rate_limit_per_minute: int = Field(default=60, description="每分钟请求限制")
    
    # 状态
    is_active: bool = Field(default=True, description="是否启用")
    
    # 输入定义
    input_schema: List[DifyInputConfig] = Field(default=[], description="工作流输入参数定义")
    
    # 支持的模型（仅适用于通用助手类型的工作流）
    supported_models: List[DifyModelConfig] = Field(default=[], description="支持的模型配置")
    billing_type: Optional[str] = Field(None, description="计费类型")

    # 描述信息
    description: str = Field(default="", description="工作流描述")
    use_cases: List[str] = Field(default=[], description="适用场景")


class FlowTypeConfig(BaseModel):
    """工作流类型配置"""
    type: FlowType
    name: str = Field(..., description="类型名称")
    description: str = Field(..., description="类型描述")


class DefaultSettings(BaseModel):
    """默认设置"""
    timeout: int = Field(default=30, description="默认超时时间")
    retry_attempts: int = Field(default=3, description="重试次数")
    retry_delay: int = Field(default=1, description="重试延迟(秒)")


class DifyConfig:
    """Dify配置管理器"""
    
    def __init__(self, config_file: str = "app/config/dify_config.json"):
        self.config_file = config_file
        self.flows: Dict[str, DifyFlowConfig] = {}
        self.flow_types: Dict[FlowType, FlowTypeConfig] = {}
        self.default_settings: DefaultSettings = DefaultSettings()
        self.config: Dict[str, Any] = {}  # 保存原始配置数据
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = data  # 保存原始配置数据
                    
                # 加载工作流配置
                for flow_data in data.get("dify_flows", []):
                    # 处理支持的模型配置
                    if "supported_models" in flow_data:
                        model_configs = []
                        for model_data in flow_data["supported_models"]:
                            model_config = DifyModelConfig(**model_data)
                            model_configs.append(model_config)
                        flow_data["supported_models"] = model_configs
                    
                    flow = DifyFlowConfig(**flow_data)
                    self.flows[flow.id] = flow
                
                # 加载工作流类型配置
                for type_data in data.get("flow_types", []):
                    flow_type_config = FlowTypeConfig(**type_data)
                    self.flow_types[flow_type_config.type] = flow_type_config
                
                # 加载默认设置
                if "default_settings" in data:
                    self.default_settings = DefaultSettings(**data["default_settings"])
                    
                print(f"成功加载Dify配置文件: {len(self.flows)} 个工作流, {len(self.flow_types)} 个类型")
            else:
                print(f"Dify配置文件 {self.config_file} 不存在，将创建默认配置")
                self._create_default_config()
                
        except Exception as e:
            print(f"加载Dify配置文件失败: {e}")
            print("将创建默认配置")
            self._create_default_config()
            
        # 验证配置完整性
        validation = self.validate_config()
        if not validation["valid"]:
            print("⚠️  Dify配置验证失败:")
            for error in validation["errors"]:
                print(f"   错误: {error}")
        if validation["warnings"]:
            print("⚠️  Dify配置警告:")
            for warning in validation["warnings"]:
                print(f"   警告: {warning}")
    
    def _create_default_config(self):
        """创建默认配置"""
        # 创建默认工作流类型配置
        default_flow_types = [
            FlowTypeConfig(
                type=FlowType.WORKFLOW,
                name="工作流",
                description="用于复杂的多步骤任务处理"
            ),
            FlowTypeConfig(
                type=FlowType.CHATFLOW,
                name="对话流",
                description="用于连续的对话交互"
            )
        ]
        
        for flow_type_config in default_flow_types:
            self.flow_types[flow_type_config.type] = flow_type_config
        
        # 创建默认设置
        self.default_settings = DefaultSettings()
        
        # 保存默认配置
        self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            data = {
                "dify_flows": [flow.dict() for flow in self.flows.values()],
                "flow_types": [flow_type.dict() for flow_type in self.flow_types.values()],
                "default_settings": self.default_settings.dict()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"保存Dify配置文件失败: {e}")
    
    def get_flow(self, flow_id: str) -> Optional[DifyFlowConfig]:
        """获取指定工作流配置"""
        return self.flows.get(flow_id)
    
    def get_flows_by_type(self, flow_type: FlowType) -> List[DifyFlowConfig]:
        """根据类型获取工作流列表"""
        return [flow for flow in self.flows.values() if flow.flow_type == flow_type and flow.is_active]
    
    def get_all_active_flows(self) -> List[DifyFlowConfig]:
        """获取所有活跃的工作流"""
        return [flow for flow in self.flows.values() if flow.is_active]
    
    def add_flow(self, flow_config: DifyFlowConfig):
        """添加新的工作流配置"""
        self.flows[flow_config.id] = flow_config
        self.save_config()
    
    def update_flow(self, flow_id: str, **kwargs):
        """更新工作流配置"""
        if flow_id in self.flows:
            for key, value in kwargs.items():
                if hasattr(self.flows[flow_id], key):
                    setattr(self.flows[flow_id], key, value)
            self.save_config()
    
    def deactivate_flow(self, flow_id: str):
        """停用工作流"""
        if flow_id in self.flows:
            self.flows[flow_id].is_active = False
            self.save_config()
    
    def activate_flow(self, flow_id: str):
        """启用工作流"""
        if flow_id in self.flows:
            self.flows[flow_id].is_active = True
            self.save_config()
    
    def reload_config(self):
        """重新加载配置"""
        self.flows.clear()
        self.flow_types.clear()
        self._load_config()
        
    def validate_config(self) -> Dict[str, Any]:
        """验证配置完整性"""
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # 检查工作流配置
        if not self.flows:
            validation_result["warnings"].append("没有配置任何Dify工作流")
        
        # 检查工作流类型配置
        if not self.flow_types:
            validation_result["warnings"].append("没有工作流类型配置")
        
        # 检查每个工作流的必要参数
        for flow_id, flow in self.flows.items():
            if not flow.api_url:
                validation_result["errors"].append(f"工作流 {flow_id} 缺少 api_url")
            if not flow.api_token:
                validation_result["errors"].append(f"工作流 {flow_id} 缺少 api_token")
            if flow.points_cost <= 0:
                validation_result["warnings"].append(f"工作流 {flow_id} 的积分消耗为0或负数")
        
        return validation_result


# 创建全局配置实例
dify_config = DifyConfig()


# 辅助函数
def get_default_flow(flow_type: FlowType = FlowType.CHATFLOW) -> Optional[DifyFlowConfig]:
    """获取默认的工作流配置"""
    flows = dify_config.get_flows_by_type(flow_type)
    return flows[0] if flows else None


def get_flow_by_id(flow_id: str) -> Optional[DifyFlowConfig]:
    """根据ID获取工作流配置"""
    return dify_config.get_flow(flow_id) 