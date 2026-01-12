from functools import wraps
from typing import Optional, Callable, Any
import structlog
from app.services import points_service
from app.schemas.points import ServiceType, ConsumePointsRequest

logger = structlog.get_logger()


def consume_points_for_ai(
    service_type: ServiceType,
    aimodel_name: Optional[str] = None,
    description: Optional[str] = None
):
    """
    积分消费装饰器，用于AI服务自动扣费
    
    Args:
        service_type: 服务类型
        aimodel_name: 模型名称
        description: 服务描述
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 尝试从参数中获取用户ID和其他相关信息
            user_id = None
            tokens_used = 0
            request_id = None
            
            # 从位置参数中查找用户ID
            if args and hasattr(args[0], 'user_id'):
                user_id = args[0].user_id
            elif args and isinstance(args[0], str):  # 假设第一个参数是user_id
                user_id = args[0]
            
            # 从关键字参数中查找相关信息
            if 'user_id' in kwargs:
                user_id = kwargs['user_id']
            if 'tokens_used' in kwargs:
                tokens_used = kwargs['tokens_used']
            if 'request_id' in kwargs:
                request_id = kwargs['request_id']
            
            if not user_id:
                logger.error("无法从参数中获取用户ID，跳过积分扣费")
                return await func(*args, **kwargs)
            
            # 检查积分是否足够
            check_result = await points_service.check_sufficient_points(
                user_id, service_type, aimodel_name, tokens_used
            )
            
            if not check_result.get("sufficient", False):
                logger.warning(
                    "用户积分不足",
                    user_id=user_id,
                    current_points=check_result.get("current_points"),
                    required_points=check_result.get("required_points")
                )
                raise Exception(f"积分不足，当前积分: {check_result.get('current_points')}, 需要积分: {check_result.get('required_points')}")
            
            try:
                # 执行原始函数
                result = await func(*args, **kwargs)
                
                # 如果函数执行成功，扣除积分
                consume_request = ConsumePointsRequest(
                    service_type=service_type,
                    aimodel_name=aimodel_name,
                    tokens_used=tokens_used,
                    description=description or f"{service_type.value}服务",
                    request_id=request_id
                )
                
                consume_result = await points_service.consume_points(user_id, consume_request)
                
                if consume_result.success:
                    logger.info(
                        "积分扣费成功",
                        user_id=user_id,
                        points_consumed=consume_result.points_consumed,
                        points_after=consume_result.points_after,
                        transaction_id=consume_result.transaction_id
                    )
                else:
                    logger.error(
                        "积分扣费失败",
                        user_id=user_id,
                        error=consume_result.error,
                        message=consume_result.message
                    )
                
                return result
                
            except Exception as e:
                logger.error(f"函数执行失败，未扣除积分: {e}", user_id=user_id)
                raise
        
        return wrapper
    return decorator


async def consume_points_manual(
    user_id: str,
    service_type: ServiceType,
    aimodel_name: Optional[str] = None,
    tokens_used: int = 0,
    description: Optional[str] = None,
    request_id: Optional[str] = None
) -> bool:
    """
    手动消费积分
    
    Args:
        user_id: 用户ID
        service_type: 服务类型
        aimodel_name: 模型名称
        tokens_used: 使用的token数量
        description: 描述
        request_id: 请求ID
    
    Returns:
        bool: 是否扣费成功
    """
    try:
        consume_request = ConsumePointsRequest(
            service_type=service_type,
            aimodel_name=aimodel_name,
            tokens_used=tokens_used,
            description=description or f"{service_type.value}服务",
            request_id=request_id
        )
        
        result = await points_service.consume_points(user_id, consume_request)
        
        if result.success:
            logger.info(
                "手动积分扣费成功",
                user_id=user_id,
                points_consumed=result.points_consumed,
                transaction_id=result.transaction_id
            )
            return True
        else:
            logger.error(
                "手动积分扣费失败",
                user_id=user_id,
                error=result.error,
                message=result.message
            )
            return False
            
    except Exception as e:
        logger.error(f"手动积分扣费异常: {e}", user_id=user_id)
        return False


async def check_points_before_ai_call(
    user_id: str,
    service_type: ServiceType,
    aimodel_name: Optional[str] = None,
    estimated_tokens: int = 0
) -> dict:
    """
    在AI调用前检查积分是否足够
    
    Args:
        user_id: 用户ID
        service_type: 服务类型
        aimodel_name: 模型名称
        estimated_tokens: 预估token数量
    
    Returns:
        dict: 检查结果
    """
    try:
        return await points_service.check_sufficient_points(
            user_id, service_type, aimodel_name, estimated_tokens
        )
    except Exception as e:
        logger.error(f"检查积分异常: {e}", user_id=user_id)
        return {"sufficient": False, "error": str(e)}