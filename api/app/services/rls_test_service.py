from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import logging

from app.services.supabase_client import supabase_service
from app.schemas.rls_test import (
    RlsTestDataCreate, 
    RlsTestDataUpdate, 
    RlsTestDataResponse,
    RlsTestDataListResponse,
    RlsTestStats
)

logger = logging.getLogger(__name__)


class RlsTestService:
    """RLS测试服务类 - 专门用于测试和调试RLS权限配置"""
    
    def __init__(self):
        """
        初始化RLS测试服务, 默认使用service_client
        """
        self.service_client = supabase_service.get_client()
        logger.info(f"RlsTestService initialized with service_client.")

    def _get_user_client(self, access_token: str):
        """根据access_token获取用户客户端"""
        if not access_token:
            raise ValueError("此操作需要用户访问令牌。")
        return supabase_service.get_user_client(access_token)

    async def create_test_data(self, user_id: uuid.UUID, data: RlsTestDataCreate, access_token: str) -> RlsTestDataResponse:
        """创建RLS测试数据"""
        try:
            user_client = self._get_user_client(access_token)
            insert_data = {
                "user_id": str(user_id),
                "title": data.title,
                "content": data.content,
                "is_private": data.is_private,
                "test_data": data.test_data or {}
            }
            
            logger.info(f"尝试创建RLS测试数据: user_id={user_id}, title={data.title}")
            
            response = user_client.table("rls_test_data").insert(insert_data).execute()
            
            if not response.data or len(response.data) == 0:
                raise Exception("插入失败：未返回数据")
            
            result = response.data[0]
            logger.info(f"RLS测试数据创建成功: id={result.get('id')}")
            
            return RlsTestDataResponse(**result)
            
        except Exception as e:
            logger.error(f"创建RLS测试数据失败: {str(e)}")
            raise Exception(f"创建测试数据失败: {str(e)}")

    async def get_test_data_by_id(self, user_id: uuid.UUID, data_id: int, access_token: str) -> Optional[RlsTestDataResponse]:
        """根据ID获取RLS测试数据"""
        try:
            user_client = self._get_user_client(access_token)
            logger.info(f"尝试获取RLS测试数据: user_id={user_id}, data_id={data_id}")
            
            response = user_client.table("rls_test_data").select("*").eq("id", data_id).execute()
            
            if not response.data or len(response.data) == 0:
                logger.warning(f"RLS测试数据未找到: data_id={data_id}")
                return None
            
            result = response.data[0]
            logger.info(f"RLS测试数据获取成功: id={result.get('id')}")
            
            return RlsTestDataResponse(**result)
            
        except Exception as e:
            logger.error(f"获取RLS测试数据失败: {str(e)}")
            raise Exception(f"获取测试数据失败: {str(e)}")

    async def list_test_data(
        self, 
        user_id: uuid.UUID, 
        access_token: str,
        page: int = 1, 
        per_page: int = 10,
        is_private: Optional[bool] = None
    ) -> RlsTestDataListResponse:
        """获取用户的RLS测试数据列表"""
        try:
            user_client = self._get_user_client(access_token)
            logger.info(f"尝试获取RLS测试数据列表: user_id={user_id}, page={page}, per_page={per_page}")
            
            query = user_client.table("rls_test_data").select("*", count="exact")
            
            if is_private is not None:
                query = query.eq("is_private", is_private)
            
            offset = (page - 1) * per_page
            query = query.order("created_at", desc=True).range(offset, offset + per_page - 1)
            
            response = query.execute()
            
            total = response.count if response.count is not None else 0
            items = [RlsTestDataResponse(**item) for item in response.data]
            
            logger.info(f"RLS测试数据列表获取成功: 返回{len(items)}条记录，总计{total}条")
            
            return RlsTestDataListResponse(
                items=items,
                total=total,
                page=page,
                per_page=per_page,
                has_next=total > page * per_page,
                has_prev=page > 1
            )
            
        except Exception as e:
            logger.error(f"获取RLS测试数据列表失败: {str(e)}")
            raise Exception(f"获取测试数据列表失败: {str(e)}")

    async def update_test_data(
        self, 
        user_id: uuid.UUID, 
        data_id: int, 
        data: RlsTestDataUpdate,
        access_token: str
    ) -> Optional[RlsTestDataResponse]:
        """更新RLS测试数据"""
        try:
            user_client = self._get_user_client(access_token)
            logger.info(f"尝试更新RLS测试数据: user_id={user_id}, data_id={data_id}")
            
            update_data = data.model_dump(exclude_unset=True)
            
            if not update_data:
                raise ValueError("没有提供要更新的数据")
            
            response = user_client.table("rls_test_data").update(update_data).eq("id", data_id).execute()
            
            if not response.data or len(response.data) == 0:
                logger.warning(f"RLS测试数据更新失败: data_id={data_id} (可能不存在或无权限)")
                return None
            
            result = response.data[0]
            logger.info(f"RLS测试数据更新成功: id={result.get('id')}")
            
            return RlsTestDataResponse(**result)
            
        except Exception as e:
            logger.error(f"更新RLS测试数据失败: {str(e)}")
            raise Exception(f"更新测试数据失败: {str(e)}")

    async def delete_test_data(self, user_id: uuid.UUID, data_id: int, access_token: str) -> bool:
        """删除RLS测试数据"""
        try:
            user_client = self._get_user_client(access_token)
            logger.info(f"尝试删除RLS测试数据: user_id={user_id}, data_id={data_id}")
            
            response = user_client.table("rls_test_data").delete().eq("id", data_id).execute()
            
            if not response.data or len(response.data) == 0:
                logger.warning(f"RLS测试数据删除失败: data_id={data_id} (可能不存在或无权限)")
                return False
            
            logger.info(f"RLS测试数据删除成功: id={data_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除RLS测试数据失败: {str(e)}")
            raise Exception(f"删除测试数据失败: {str(e)}")

    async def get_test_stats(self, user_id: uuid.UUID, access_token: str) -> RlsTestStats:
        """获取用户的RLS测试数据统计信息"""
        try:
            user_client = self._get_user_client(access_token)
            logger.info(f"尝试获取RLS测试数据统计: user_id={user_id}")
            
            total_response = user_client.table("rls_test_data").select("id", count="exact").execute()
            total_records = total_response.count if total_response.count is not None else 0
            
            private_response = user_client.table("rls_test_data").select("id", count="exact").eq("is_private", True).execute()
            private_records = private_response.count if private_response.count is not None else 0
            
            today = datetime.now(timezone.utc).date()
            today_response = user_client.table("rls_test_data").select("id", count="exact").gte("created_at", f"{today}T00:00:00Z").execute()
            created_today = today_response.count if today_response.count is not None else 0
            
            public_records = total_records - private_records
            
            logger.info(f"RLS测试数据统计获取成功: 总计{total_records}条，私有{private_records}条，今日{created_today}条")
            
            return RlsTestStats(
                total_records=total_records,
                private_records=private_records,
                public_records=public_records,
                created_today=created_today,
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(f"获取RLS测试数据统计失败: {str(e)}")
            raise Exception(f"获取测试数据统计失败: {str(e)}")

    async def test_rls_permissions(self, user_id: uuid.UUID, access_token: str) -> Dict[str, Any]:
        """测试RLS权限配置"""
        try:
            logger.info(f"开始RLS权限测试: user_id={user_id}")
            
            test_results = {
                "user_id": str(user_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tests": {}
            }
            
            test_data_create = RlsTestDataCreate(
                title="RLS权限测试",
                content="这是一个RLS权限测试数据",
                is_private=True,
                test_data={"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            created = None
            try:
                created = await self.create_test_data(user_id, test_data_create, access_token)
                test_results["tests"]["create"] = {"success": True, "data_id": created.id}
            except Exception as e:
                test_results["tests"]["create"] = {"success": False, "error": str(e)}

            if created:
                try:
                    retrieved = await self.get_test_data_by_id(user_id, created.id, access_token)
                    test_results["tests"]["read"] = {"success": True, "data_found": retrieved is not None}
                except Exception as e:
                    test_results["tests"]["read"] = {"success": False, "error": str(e)}

                try:
                    update_data = RlsTestDataUpdate(content="更新后的测试内容")
                    updated = await self.update_test_data(user_id, created.id, update_data, access_token)
                    test_results["tests"]["update"] = {"success": True, "data_updated": updated is not None}
                except Exception as e:
                    test_results["tests"]["update"] = {"success": False, "error": str(e)}

                try:
                    deleted = await self.delete_test_data(user_id, created.id, access_token)
                    test_results["tests"]["delete"] = {"success": True, "data_deleted": deleted}
                except Exception as e:
                    test_results["tests"]["delete"] = {"success": False, "error": str(e)}
            else:
                 test_results["tests"]["read"] = {"success": False, "error": "无法测试（创建失败）"}
                 test_results["tests"]["update"] = {"success": False, "error": "无法测试（创建失败）"}
                 test_results["tests"]["delete"] = {"success": False, "error": "无法测试（创建失败）"}

            successful_tests = sum(1 for test in test_results["tests"].values() if test.get("success"))
            total_tests = len(test_results["tests"])
            test_results["overall"] = {
                "success_rate": f"{successful_tests}/{total_tests}",
                "all_passed": successful_tests == total_tests
            }
            
            logger.info(f"RLS权限测试完成: 成功{successful_tests}/{total_tests}个测试")
            
            return test_results
            
        except Exception as e:
            logger.error(f"RLS权限测试失败: {str(e)}")
            raise Exception(f"RLS权限测试失败: {str(e)}") 