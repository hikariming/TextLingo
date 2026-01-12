"""
RLS调试和监控服务
用于诊断生产环境中的Row Level Security问题
"""

import structlog
from typing import Dict, Any, List, Optional
from app.services.supabase_client import supabase_service
import os
import json

logger = structlog.get_logger()


class RLSDebugService:
    """RLS问题调试和诊断服务"""
    
    def __init__(self):
        self.client = supabase_service.get_client()
        
    async def diagnose_rls_status(self) -> Dict[str, Any]:
        """全面诊断RLS状态"""
        diagnosis = {}
        
        try:
            # 1. 检查环境信息
            diagnosis["environment"] = self._get_environment_info()
            
            # 2. 检查Supabase连接状态
            diagnosis["connection"] = await self._check_connection_status()
            
            # 3. 检查认证状态
            diagnosis["auth"] = await self._check_auth_status()
            
            # 4. 检查RLS策略状态
            diagnosis["rls_policies"] = await self._check_rls_policies()
            
            # 5. 测试数据库操作
            diagnosis["database_test"] = await self._test_database_operations()
            
            logger.info("RLS诊断完成", diagnosis=diagnosis)
            return diagnosis
            
        except Exception as e:
            logger.error(f"RLS诊断失败: {e}")
            diagnosis["error"] = str(e)
            return diagnosis
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """获取环境信息"""
        return {
            "platform": {
                "railway": os.getenv("RAILWAY_ENVIRONMENT") is not None,
                "replit": os.getenv("REPL_ID") is not None,
                "local": not any([os.getenv("RAILWAY_ENVIRONMENT"), os.getenv("REPL_ID")])
            },
            "supabase_url": os.getenv("SUPABASE_URL", "")[:50] + "..." if os.getenv("SUPABASE_URL") else "未设置",
            "has_service_key": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
            "has_anon_key": bool(os.getenv("SUPABASE_ANON_KEY"))
        }
    
    async def _check_connection_status(self) -> Dict[str, Any]:
        """检查Supabase连接状态"""
        try:
            # 简单的连接测试
            response = self.client.table("material_articles").select("count", count="exact").limit(1).execute()
            
            return {
                "connected": True,
                "client_type": type(self.client).__name__,
                "response_time": "正常"  # 可以添加实际的响应时间测量
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def _check_auth_status(self) -> Dict[str, Any]:
        """检查认证状态"""
        try:
            # 调用调试函数检查认证状态
            response = self.client.rpc('debug_auth_status').execute()
            
            if response.data:
                auth_info = response.data[0] if response.data else {}
                return {
                    "auth_uid": auth_info.get("auth_uid"),
                    "auth_role": auth_info.get("auth_role"),
                    "session_valid": auth_info.get("session_valid"),
                    "rls_enabled": auth_info.get("rls_enabled"),
                    "using_service_role": auth_info.get("auth_role") == "service_role"
                }
            else:
                return {"error": "无法获取认证状态"}
                
        except Exception as e:
            logger.warning(f"认证状态检查失败，可能是调试函数不存在: {e}")
            return {
                "error": str(e),
                "note": "可能需要先执行rls-debug-solutions.sql创建调试函数"
            }
    
    async def _check_rls_policies(self) -> Dict[str, Any]:
        """检查RLS策略状态"""
        try:
            # 检查表的RLS启用状态
            tables_sql = """
            SELECT schemaname, tablename, rowsecurity 
            FROM pg_tables 
            WHERE tablename IN ('material_articles', 'material_segments')
            """
            
            policies_sql = """
            SELECT tablename, policyname, cmd, roles, qual, with_check
            FROM pg_policies 
            WHERE tablename IN ('material_articles', 'material_segments')
            ORDER BY tablename, policyname
            """
            
            # 注意：这些SQL查询可能需要特殊权限
            # 在生产环境中可能需要通过RPC函数执行
            
            return {
                "note": "RLS策略检查需要数据库管理员权限",
                "suggestion": "使用Supabase Dashboard的SQL Editor查看策略状态"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "note": "无法直接查询pg_tables和pg_policies，需要管理员权限"
            }
    
    async def _test_database_operations(self) -> Dict[str, Any]:
        """测试数据库操作"""
        tests = {}
        
        # 测试1：简单查询
        try:
            response = self.client.table("material_articles").select("id").limit(1).execute()
            tests["simple_select"] = {
                "success": True,
                "count": len(response.data) if response.data else 0
            }
        except Exception as e:
            tests["simple_select"] = {
                "success": False,
                "error": str(e)
            }
        
        # 测试2：计数查询
        try:
            response = self.client.table("material_articles").select("count", count="exact").execute()
            tests["count_query"] = {
                "success": True,
                "total_count": response.count if hasattr(response, 'count') else "未知"
            }
        except Exception as e:
            tests["count_query"] = {
                "success": False,
                "error": str(e)
            }
        
        return tests
    
    async def test_article_creation(self, user_id: str, test_data: Optional[Dict] = None) -> Dict[str, Any]:
        """测试文章创建功能"""
        if not test_data:
            test_data = {
                "title": "RLS测试文章",
                "content": "这是一个用于测试RLS的文章内容",
                "user_id": user_id,
                "file_type": "text",
                "file_size": 100,
                "is_public": False,
                "target_language": "en",
                "difficulty_level": "beginner"
            }
        
        try:
            # 尝试创建文章
            response = self.client.table("material_articles").insert(test_data).execute()
            
            if response.data and len(response.data) > 0:
                article_id = response.data[0]["id"]
                
                # 尝试删除测试文章
                try:
                    self.client.table("material_articles").delete().eq("id", article_id).execute()
                    cleanup_success = True
                except:
                    cleanup_success = False
                
                return {
                    "success": True,
                    "article_id": article_id,
                    "cleanup_success": cleanup_success,
                    "message": "文章创建测试成功"
                }
            else:
                return {
                    "success": False,
                    "error": "创建文章但未返回数据",
                    "response": str(response)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def get_rls_recommendations(self, diagnosis: Dict[str, Any]) -> List[str]:
        """基于诊断结果提供建议"""
        recommendations = []
        
        # 检查环境
        env_info = diagnosis.get("environment", {})
        if env_info.get("platform", {}).get("railway") or env_info.get("platform", {}).get("replit"):
            recommendations.append("🌐 检测到生产环境，建议使用分层RLS策略区分service_role和用户权限")
        
        # 检查连接
        connection = diagnosis.get("connection", {})
        if not connection.get("connected", False):
            recommendations.append("🔌 Supabase连接失败，检查网络和环境变量配置")
        
        # 检查认证
        auth = diagnosis.get("auth", {})
        if auth.get("error"):
            recommendations.append("🔐 认证状态检查失败，可能需要先执行rls-debug-solutions.sql创建调试函数")
        elif not auth.get("using_service_role", False):
            recommendations.append("⚠️ 未使用service_role，检查SUPABASE_SERVICE_ROLE_KEY配置")
        
        # 检查数据库测试
        db_test = diagnosis.get("database_test", {})
        if not db_test.get("simple_select", {}).get("success", False):
            recommendations.append("❌ 基础查询失败，可能存在RLS策略阻塞")
            recommendations.append("💡 建议执行rls-debug-solutions.sql中的临时修复方案")
        
        if not recommendations:
            recommendations.append("✅ 所有检查通过，RLS配置正常")
        
        return recommendations
    
    async def generate_debug_report(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """生成完整的调试报告"""
        logger.info("开始生成RLS调试报告")
        
        # 执行诊断
        diagnosis = await self.diagnose_rls_status()
        
        # 如果提供了用户ID，测试文章创建
        if user_id:
            creation_test = await self.test_article_creation(user_id)
            diagnosis["article_creation_test"] = creation_test
        
        # 生成建议
        recommendations = await self.get_rls_recommendations(diagnosis)
        
        report = {
            "timestamp": str(logger._logger._context.get("timestamp")),
            "diagnosis": diagnosis,
            "recommendations": recommendations,
            "summary": {
                "environment_detected": diagnosis.get("environment", {}).get("platform", {}),
                "connection_status": "正常" if diagnosis.get("connection", {}).get("connected") else "异常",
                "major_issues": len([r for r in recommendations if "❌" in r or "⚠️" in r]),
                "status": "需要修复" if any("❌" in r for r in recommendations) else "基本正常"
            }
        }
        
        logger.info("RLS调试报告生成完成", 
                   status=report["summary"]["status"],
                   issues=report["summary"]["major_issues"])
        
        return report


# 创建全局实例
rls_debug_service = RLSDebugService()