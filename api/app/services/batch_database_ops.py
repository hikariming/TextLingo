"""
批量数据库操作服务
用于优化数据库操作，减少 Supabase API 调用次数和成本
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
from supabase import Client

from .supabase_client import supabase_service

logger = structlog.get_logger()


@dataclass
class BatchOperationResult:
    """批量操作结果"""
    success_count: int
    failure_count: int
    errors: List[str]
    total_processed: int
    operation_time: float


class BatchDatabaseOperations:
    """批量数据库操作服务"""
    
    def __init__(self, batch_size: int = 100, max_retries: int = 3):
        self.supabase = supabase_service.get_client()
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.logger = logger.bind(service="batch_db_ops")
    
    async def batch_upsert_with_retry(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        on_conflict: str,
        progress_callback: Optional[callable] = None
    ) -> BatchOperationResult:
        """
        批量插入或更新数据，带重试机制
        
        Args:
            table_name: 表名
            data: 要插入的数据列表
            on_conflict: 冲突处理策略
            progress_callback: 进度回调函数
            
        Returns:
            BatchOperationResult: 操作结果
        """
        start_time = time.time()
        total_items = len(data)
        success_count = 0
        failure_count = 0
        errors = []
        
        # 分批处理
        for i in range(0, total_items, self.batch_size):
            batch = data[i:i + self.batch_size]
            batch_start = i
            batch_end = min(i + self.batch_size, total_items)
            
            try:
                # 尝试批量插入
                success = await self._upsert_batch_with_retry(
                    table_name, batch, on_conflict
                )
                
                if success:
                    success_count += len(batch)
                    self.logger.info(f"成功处理批次 {batch_start}-{batch_end} 共 {len(batch)} 条记录")
                else:
                    failure_count += len(batch)
                    errors.append(f"批次 {batch_start}-{batch_end} 处理失败")
                    
            except Exception as e:
                failure_count += len(batch)
                error_msg = f"批次 {batch_start}-{batch_end} 处理异常: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
            
            # 更新进度
            if progress_callback:
                progress = int((batch_end / total_items) * 100)
                progress_callback(progress)
        
        operation_time = time.time() - start_time
        
        return BatchOperationResult(
            success_count=success_count,
            failure_count=failure_count,
            errors=errors,
            total_processed=total_items,
            operation_time=operation_time
        )
    
    async def _upsert_batch_with_retry(
        self,
        table_name: str,
        batch: List[Dict[str, Any]],
        on_conflict: str
    ) -> bool:
        """
        单批次插入重试机制
        
        Args:
            table_name: 表名
            batch: 批次数据
            on_conflict: 冲突处理策略
            
        Returns:
            bool: 是否成功
        """
        for attempt in range(self.max_retries):
            try:
                result = self.supabase.table(table_name).upsert(
                    batch, on_conflict=on_conflict
                ).execute()
                
                if result.data:
                    return True
                else:
                    self.logger.warning(f"批次插入返回空数据，尝试 {attempt + 1}/{self.max_retries}")
                    
            except Exception as e:
                self.logger.warning(f"批次插入失败，尝试 {attempt + 1}/{self.max_retries}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # 等待一段时间再重试
                    await self._wait_with_backoff(attempt)
                else:
                    self.logger.error(f"批次插入最终失败: {str(e)}")
                    return False
        
        return False
    
    async def _wait_with_backoff(self, attempt: int):
        """
        指数退避等待
        
        Args:
            attempt: 尝试次数
        """
        wait_time = (2 ** attempt) * 0.1  # 0.1s, 0.2s, 0.4s, ...
        await asyncio.sleep(wait_time)
    
    async def batch_query_with_pagination(
        self,
        table_name: str,
        select_columns: str = "*",
        filter_conditions: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        分页查询大量数据
        
        Args:
            table_name: 表名
            select_columns: 选择的列
            filter_conditions: 过滤条件
            order_by: 排序条件
            limit: 每页限制
            
        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        all_results = []
        offset = 0
        
        while True:
            try:
                query = self.supabase.table(table_name).select(select_columns)
                
                # 添加过滤条件
                if filter_conditions:
                    for column, value in filter_conditions.items():
                        query = query.eq(column, value)
                
                # 添加排序和分页
                if order_by:
                    query = query.order(order_by)
                
                query = query.range(offset, offset + limit - 1)
                
                result = query.execute()
                
                if not result.data:
                    break
                
                all_results.extend(result.data)
                
                # 如果返回的数据少于限制，说明已经到最后一页
                if len(result.data) < limit:
                    break
                
                offset += limit
                
            except Exception as e:
                self.logger.error(f"分页查询失败: {str(e)}")
                break
        
        return all_results
    
    async def batch_delete_with_conditions(
        self,
        table_name: str,
        conditions: Dict[str, Any],
        batch_size: int = 50
    ) -> BatchOperationResult:
        """
        批量删除数据
        
        Args:
            table_name: 表名
            conditions: 删除条件
            batch_size: 批量大小
            
        Returns:
            BatchOperationResult: 操作结果
        """
        start_time = time.time()
        total_deleted = 0
        errors = []
        
        try:
            # 首先查询要删除的记录ID
            query = self.supabase.table(table_name).select("id")
            for column, value in conditions.items():
                query = query.eq(column, value)
            
            result = query.execute()
            
            if not result.data:
                return BatchOperationResult(
                    success_count=0,
                    failure_count=0,
                    errors=[],
                    total_processed=0,
                    operation_time=time.time() - start_time
                )
            
            # 分批删除
            ids_to_delete = [row["id"] for row in result.data]
            
            for i in range(0, len(ids_to_delete), batch_size):
                batch_ids = ids_to_delete[i:i + batch_size]
                
                try:
                    delete_result = self.supabase.table(table_name).delete().in_("id", batch_ids).execute()
                    
                    if delete_result.data:
                        total_deleted += len(delete_result.data)
                    
                except Exception as e:
                    error_msg = f"删除批次失败: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            return BatchOperationResult(
                success_count=total_deleted,
                failure_count=len(ids_to_delete) - total_deleted,
                errors=errors,
                total_processed=len(ids_to_delete),
                operation_time=time.time() - start_time
            )
            
        except Exception as e:
            error_msg = f"批量删除失败: {str(e)}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            
            return BatchOperationResult(
                success_count=0,
                failure_count=0,
                errors=errors,
                total_processed=0,
                operation_time=time.time() - start_time
            )
    
    async def optimize_table_operations(
        self,
        operations: List[Dict[str, Any]]
    ) -> List[BatchOperationResult]:
        """
        优化多表操作
        
        Args:
            operations: 操作列表，每个操作包含 table_name, operation_type, data 等
            
        Returns:
            List[BatchOperationResult]: 操作结果列表
        """
        results = []
        
        # 按表名分组操作
        grouped_operations = {}
        for op in operations:
            table_name = op.get("table_name")
            if table_name not in grouped_operations:
                grouped_operations[table_name] = []
            grouped_operations[table_name].append(op)
        
        # 逐表处理
        for table_name, table_ops in grouped_operations.items():
            # 进一步按操作类型分组
            upsert_data = []
            
            for op in table_ops:
                if op.get("operation_type") == "upsert":
                    upsert_data.extend(op.get("data", []))
            
            if upsert_data:
                result = await self.batch_upsert_with_retry(
                    table_name,
                    upsert_data,
                    on_conflict=table_ops[0].get("on_conflict", "id")
                )
                results.append(result)
        
        return results
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取数据库连接信息
        
        Returns:
            Dict[str, Any]: 连接信息
        """
        return {
            "batch_size": self.batch_size,
            "max_retries": self.max_retries,
            "service": "batch_database_operations"
        }


# 创建全局实例
batch_db_ops = BatchDatabaseOperations()


# 异步支持
import asyncio

async def create_optimized_batch_ops(batch_size: int = 100) -> BatchDatabaseOperations:
    """
    创建优化的批量操作实例
    
    Args:
        batch_size: 批量大小
        
    Returns:
        BatchDatabaseOperations: 批量操作实例
    """
    return BatchDatabaseOperations(batch_size=batch_size) 