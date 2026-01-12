"""
RLS调试API端点
用于生产环境RLS问题诊断
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import structlog

from app.core.dependencies import get_current_user
from app.services.rls_debug_service import rls_debug_service

logger = structlog.get_logger()
router = APIRouter()


@router.get("/rls-status", summary="检查RLS状态", description="全面诊断RLS配置和运行状态")
async def check_rls_status(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    检查RLS（Row Level Security）状态
    
    返回：
    - 环境信息
    - 连接状态  
    - 认证状态
    - RLS策略状态
    - 数据库操作测试结果
    """
    try:
        diagnosis = await rls_debug_service.diagnose_rls_status()
        
        # 记录诊断请求
        logger.info("RLS状态诊断请求", 
                   user_id=current_user.id,
                   diagnosis_summary=diagnosis.get("summary", {}))
        
        return {
            "success": True,
            "data": diagnosis,
            "message": "RLS状态诊断完成"
        }
        
    except Exception as e:
        logger.error(f"RLS状态检查失败: {e}", user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"RLS状态检查失败: {str(e)}")


@router.get("/rls-report", summary="生成RLS调试报告", description="生成详细的RLS问题诊断报告")
async def generate_rls_report(
    test_creation: bool = Query(False, description="是否测试文章创建功能"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    生成完整的RLS调试报告
    
    参数：
    - test_creation: 是否包含文章创建测试
    
    返回：
    - 完整诊断信息
    - 问题分析
    - 修复建议
    - 环境对比
    """
    try:
        user_id = current_user.id if test_creation else None
        
        report = await rls_debug_service.generate_debug_report(user_id)
        
        logger.info("RLS调试报告生成", 
                   user_id=current_user.id,
                   test_creation=test_creation,
                   report_status=report.get("summary", {}).get("status"))
        
        return {
            "success": True,
            "data": report,
            "message": "RLS调试报告生成完成"
        }
        
    except Exception as e:
        logger.error(f"RLS报告生成失败: {e}", user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"RLS报告生成失败: {str(e)}")


@router.post("/test-article-creation", summary="测试文章创建", description="测试RLS对文章创建的影响")
async def test_article_creation(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    测试文章创建功能
    
    创建一个测试文章，验证RLS策略是否正常工作
    测试后会自动删除创建的文章
    """
    try:
        user_id = current_user.id
        if not user_id:
            raise HTTPException(status_code=400, detail="无效的用户ID")
        
        test_result = await rls_debug_service.test_article_creation(user_id)
        
        logger.info("文章创建测试完成", 
                   user_id=user_id,
                   success=test_result.get("success"),
                   error=test_result.get("error"))
        
        if test_result.get("success"):
            return {
                "success": True,
                "data": test_result,
                "message": "文章创建测试成功，RLS策略工作正常"
            }
        else:
            return {
                "success": False,
                "data": test_result,
                "message": f"文章创建测试失败: {test_result.get('error', '未知错误')}"
            }
            
    except Exception as e:
        logger.error(f"文章创建测试失败: {e}", user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"文章创建测试失败: {str(e)}")


@router.get("/environment-info", summary="获取环境信息", description="获取当前部署环境的详细信息")
async def get_environment_info(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取环境信息
    
    返回：
    - 部署平台信息
    - 环境变量状态
    - Supabase配置状态
    """
    try:
        debug_service = rls_debug_service
        env_info = debug_service._get_environment_info()
        connection_status = await debug_service._check_connection_status()
        
        return {
            "success": True,
            "data": {
                "environment": env_info,
                "connection": connection_status,
                "platform_recommendations": _get_platform_recommendations(env_info)
            },
            "message": "环境信息获取成功"
        }
        
    except Exception as e:
        logger.error(f"环境信息获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"环境信息获取失败: {str(e)}")


def _get_platform_recommendations(env_info: Dict[str, Any]) -> list:
    """根据平台提供特定建议"""
    platform = env_info.get("platform", {})
    recommendations = []
    
    if platform.get("railway"):
        recommendations.extend([
            "Railway环境：确保使用Redis插件并配置CELERY_BROKER_URL",
            "Railway环境：检查环境变量是否正确设置",
            "Railway环境：如果RLS失效，可能是网络代理导致认证头丢失"
        ])
    elif platform.get("replit"):
        recommendations.extend([
            "Replit环境：检查Secrets配置是否完整",
            "Replit环境：确保容器重启后环境变量持久化",
            "Replit环境：如果出现间歇性问题，考虑迁移到Railway"
        ])
    elif platform.get("local"):
        recommendations.extend([
            "本地环境：确保.env文件配置正确",
            "本地环境：如果本地正常但生产环境异常，检查网络配置差异"
        ])
    
    return recommendations


@router.get("/quick-fix", summary="获取快速修复方案", description="根据当前环境提供快速修复RLS问题的方案")
async def get_quick_fix_solutions(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取快速修复方案
    
    基于当前环境和问题类型，提供针对性的修复建议
    """
    try:
        # 先诊断当前状态
        diagnosis = await rls_debug_service.diagnose_rls_status()
        recommendations = await rls_debug_service.get_rls_recommendations(diagnosis)
        
        # 根据问题严重程度分类解决方案
        solutions = {
            "immediate": [],  # 立即执行
            "short_term": [], # 短期解决
            "long_term": []   # 长期优化
        }
        
        # 如果有严重问题，提供立即修复方案
        if any("❌" in r for r in recommendations):
            solutions["immediate"].extend([
                "在Supabase Dashboard执行：rls-debug-solutions.sql中的'立即修复方案'",
                "临时禁用过于严格的RLS策略",
                "验证SUPABASE_SERVICE_ROLE_KEY配置"
            ])
        
        # 短期解决方案
        solutions["short_term"].extend([
            "实施分层RLS策略，区分service_role和用户权限",
            "添加RLS调试和监控机制",
            "优化生产环境的网络配置"
        ])
        
        # 长期优化方案  
        solutions["long_term"].extend([
            "迁移到更稳定的部署平台（如Railway）",
            "实施全面的RLS安全策略",
            "建立RLS问题的自动监控和告警"
        ])
        
        return {
            "success": True,
            "data": {
                "current_status": diagnosis.get("summary", {}),
                "recommendations": recommendations,
                "solutions": solutions,
                "priority": "high" if any("❌" in r for r in recommendations) else "low"
            },
            "message": "快速修复方案生成完成"
        }
        
    except Exception as e:
        logger.error(f"快速修复方案生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"快速修复方案生成失败: {str(e)}")



@router.get("/test-internal-network", summary="测试内部网络连接", description="测试Railway内部网络连接")
async def test_internal_network() -> Dict[str, Any]:
    """
    测试Railway内部网络连接
    
    测试连接到Node.js API服务
    """
    import httpx
    import socket
    import os
    
    results = {
        "environment": {
            "RAILWAY_ENVIRONMENT": os.getenv("RAILWAY_ENVIRONMENT"),
            "RAILWAY_PROJECT_ID": os.getenv("RAILWAY_PROJECT_ID"),
            "RAILWAY_SERVICE_ID": os.getenv("RAILWAY_SERVICE_ID"),
            "RAILWAY_PRIVATE_DOMAIN": os.getenv("RAILWAY_PRIVATE_DOMAIN"),
            "PORT": os.getenv("PORT", "8000"),
            # 列出所有RAILWAY相关环境变量
            "all_railway_vars": {k: v for k, v in os.environ.items() if k.startswith("RAILWAY")}
        },
        "dns_tests": [],
        "connection_tests": []
    }
    
    # 测试DNS解析
    hostnames = [
        "node-api.railway.internal",
        "node-api",
        "textlingo2-node-api.railway.internal",
        "textlingo2-node-api"
    ]
    
    for hostname in hostnames:
        try:
            # 尝试解析主机名
            addr_info = socket.getaddrinfo(hostname, None)
            addresses = list(set([addr[4][0] for addr in addr_info]))
            results["dns_tests"].append({
                "hostname": hostname,
                "resolved": True,
                "addresses": addresses
            })
        except Exception as e:
            results["dns_tests"].append({
                "hostname": hostname,
                "resolved": False,
                "error": str(e)
            })
    
    # 测试HTTP连接
    test_urls = [
        "http://node-api.railway.internal:4000",
        "http://node-api:4000",
        "http://node-api.railway.internal",
        "http://node-api",
        "http://textlingo2-node-api.railway.internal:4000",
        "http://textlingo2-node-api:4000"
    ]
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for url in test_urls:
            try:
                response = await client.get(f"{url}/health")
                results["connection_tests"].append({
                    "url": url,
                    "success": True,
                    "status": response.status_code,
                    "response": response.text[:200]  # 前200字符
                })
            except Exception as e:
                results["connection_tests"].append({
                    "url": url,
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
    
    # 添加建议
    results["recommendations"] = []
    if not any(test["success"] for test in results["connection_tests"]):
        results["recommendations"].extend([
            "内部网络连接失败，建议检查：",
            "1. Node.js服务是否正在运行",
            "2. Node.js服务是否监听在0.0.0.0:4000",
            "3. 两个服务是否在同一个Railway项目和环境中",
            "4. 可以暂时使用公网地址：https://newapi.textlingo.app"
        ])
    
    return {
        "success": True,
        "data": results,
        "message": "内部网络测试完成"
    }


# 注册路由到调试模块
debug_router = router