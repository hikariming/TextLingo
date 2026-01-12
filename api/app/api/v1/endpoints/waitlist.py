from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import logging
from app.core.dependencies import get_supabase_client

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

class WaitlistRequest(BaseModel):
    """Waitlist注册请求模型"""
    email: EmailStr
    plan_type: str
    discount_code: Optional[str] = None
    source: str = "pricing_page"
    language: str = "en"
    bonus_months: int = 1
    notes: Optional[str] = None

    @validator('plan_type')
    def validate_plan_type(cls, v):
        """验证计划类型"""
        allowed_plans = ['plus', 'pro', 'max', 'jpop_special', 'student_special']
        if v not in allowed_plans:
            raise ValueError(f'计划类型必须是以下之一: {allowed_plans}')
        return v

    @validator('language')
    def validate_language(cls, v):
        """验证语言"""
        allowed_languages = ['en', 'zh', 'ja']
        if v not in allowed_languages:
            raise ValueError(f'语言必须是以下之一: {allowed_languages}')
        return v

class WaitlistResponse(BaseModel):
    """Waitlist注册响应模型"""
    success: bool
    message: str
    bonus_months: int
    email: str

@router.post("/join", response_model=WaitlistResponse)
async def join_waitlist(
    request: WaitlistRequest,
    supabase = Depends(get_supabase_client)
):
    """
    用户加入waitlist
    
    - **email**: 用户邮箱
    - **plan_type**: 计划类型 (plus, pro, max, jpop_special, student_special)
    - **discount_code**: 优惠码 (JPOP50, STUDENT30等)
    - **source**: 来源 (pricing_page, special_offer)
    - **language**: 用户语言 (en, zh, ja)
    - **bonus_months**: 额外赠送月数
    - **notes**: 备注信息
    """
    try:
        # 检查邮箱是否已存在
        existing_user = supabase.table('waitlist').select('*').eq('email', request.email).execute()
        
        if existing_user.data:
            # 更新现有记录
            update_data = {
                'plan_type': request.plan_type,
                'discount_code': request.discount_code,
                'source': request.source,
                'language': request.language,
                'bonus_months': request.bonus_months,
                'notes': request.notes
            }
            
            result = supabase.table('waitlist').update(update_data).eq('email', request.email).execute()
            
            if result.data:
                logger.info(f"Waitlist updated for email: {request.email}")
                return WaitlistResponse(
                    success=True,
                    message="您已成功更新waitlist信息！我们会在付费功能开启时第一时间通知您。",
                    bonus_months=request.bonus_months,
                    email=request.email
                )
        else:
            # 创建新记录
            insert_data = {
                'email': request.email,
                'plan_type': request.plan_type,
                'discount_code': request.discount_code,
                'source': request.source,
                'language': request.language,
                'bonus_months': request.bonus_months,
                'notes': request.notes
            }
            
            result = supabase.table('waitlist').insert(insert_data).execute()
            
            if result.data:
                logger.info(f"New waitlist entry created for email: {request.email}")
                return WaitlistResponse(
                    success=True,
                    message="感谢您的关注！我们会在付费功能开启时第一时间通知您，并额外赠送1个月会员！",
                    bonus_months=request.bonus_months,
                    email=request.email
                )
        
        # 如果没有返回数据，说明操作失败
        raise HTTPException(status_code=500, detail="无法保存waitlist信息")
            
    except Exception as e:
        logger.error(f"Error joining waitlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")

@router.get("/stats")
async def get_waitlist_stats(supabase = Depends(get_supabase_client)):
    """
    获取waitlist统计信息（可选，用于管理员查看）
    """
    try:
        # 总数统计
        total_result = supabase.table('waitlist').select('*', count='exact').execute()
        total_count = total_result.count
        
        # 按计划类型统计
        plan_stats = {}
        for plan in ['plus', 'pro', 'max', 'jpop_special', 'student_special']:
            plan_result = supabase.table('waitlist').select('*', count='exact').eq('plan_type', plan).execute()
            plan_stats[plan] = plan_result.count
        
        # 按语言统计
        language_stats = {}
        for lang in ['en', 'zh', 'ja']:
            lang_result = supabase.table('waitlist').select('*', count='exact').eq('language', lang).execute()
            language_stats[lang] = lang_result.count
        
        return {
            "total_count": total_count,
            "plan_stats": plan_stats,
            "language_stats": language_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting waitlist stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")