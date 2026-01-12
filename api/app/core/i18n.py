"""
国际化 (i18n) 支持模块
为 FastAPI 后端提供多语言消息支持
"""

from typing import Dict, Optional
from enum import Enum

class SupportedLanguage(str, Enum):
    """支持的语言"""
    EN = "en"
    ZH = "zh"
    ZH_TW = "zh-TW"
    JA = "ja"

# 消息字典
MESSAGES = {
    SupportedLanguage.EN: {
        # Novel upload messages
        "novel_created_success": "Novel created successfully",
        "file_upload_success": "File uploaded successfully",
        "novel_creation_failed": "Failed to create novel: {error}",
        "file_upload_failed": "File upload failed: {error}",
        "supported_formats_error": "Currently supports TXT and EPUB file formats",
        "file_size_exceeded": "File size cannot exceed 50MB",
        "file_empty": "File content is empty",
        "novel_not_found": "Novel not found or you don't have permission to access",
        "novel_update_success": "Novel updated successfully",
        "novel_update_failed": "Failed to update novel: {error}",
        "novel_delete_success": "Novel deleted successfully",
        "novel_delete_failed": "Failed to delete novel: {error}",
        "novel_list_failed": "Failed to get novel list: {error}",
        "novel_details_failed": "Failed to get novel details: {error}",
        "batch_delete_success": "Successfully deleted {count} novels",
        "batch_delete_failed": "Failed to batch delete novels: {error}",
        "public_status_updated": "Novel has been set to {status}",
        "public_status_update_failed": "Failed to toggle novel public status: {error}",
        "stats_get_failed": "Failed to get statistics: {error}",
        "chapter_count_update_success": "Chapter count updated successfully",
        "chapter_count_update_failed": "Failed to update chapter count: {error}",
        "ownership_check_failed": "Failed to check ownership: {error}",
        "segmentation_preview_success": "Segmentation preview successful",
        "segmentation_preview_failed": "Failed to preview segmentation: {error}",
        "segmentation_success": "Segmentation processing successful",
        "segmentation_failed": "Failed to process segmentation: {error}",
        "segmentation_stats_success": "Successfully got segmentation statistics",
        "segmentation_stats_failed": "Failed to get segmentation statistics: {error}",
        "segments_list_success": "Successfully got segments list",
        "segments_list_failed": "Failed to get segments list: {error}",
        "progress_get_success": "Successfully got reading progress",
        "progress_get_failed": "Failed to get reading progress: {error}",
        "progress_update_success": "Reading progress updated successfully",
        "progress_update_failed": "Failed to update reading progress: {error}",
        "progress_delete_success": "Reading progress deleted successfully",
        "progress_delete_failed": "Failed to delete reading progress: {error}",
        "progress_list_success": "Successfully got reading progress list",
        "progress_list_failed": "Failed to get reading progress list: {error}",
        "reading_stats_success": "Successfully got reading statistics",
        "reading_stats_failed": "Failed to get reading statistics: {error}",
        "novel_id_mismatch": "Novel ID in request doesn't match path parameter",
        "system_auth_required": "System-level interface requires special authorization",
        "no_progress_found": "No reading progress found",
        "progress_not_found": "Reading progress not found",
        # Status text
        "public": "public",
        "private": "private"
    },
    SupportedLanguage.ZH: {
        # Novel upload messages
        "novel_created_success": "小说创建成功",
        "file_upload_success": "文件上传成功",
        "novel_creation_failed": "创建小说失败: {error}",
        "file_upload_failed": "文件上传失败: {error}",
        "supported_formats_error": "目前支持 TXT 和 EPUB 格式的文件",
        "file_size_exceeded": "文件大小不能超过50MB",
        "file_empty": "文件内容为空",
        "novel_not_found": "小说不存在或您无权访问",
        "novel_update_success": "小说更新成功",
        "novel_update_failed": "更新小说失败: {error}",
        "novel_delete_success": "小说删除成功",
        "novel_delete_failed": "删除小说失败: {error}",
        "novel_list_failed": "获取小说列表失败: {error}",
        "novel_details_failed": "获取小说详情失败: {error}",
        "batch_delete_success": "成功删除{count}部小说",
        "batch_delete_failed": "批量删除小说失败: {error}",
        "public_status_updated": "小说已设置为{status}",
        "public_status_update_failed": "切换小说公开状态失败: {error}",
        "stats_get_failed": "获取统计信息失败: {error}",
        "chapter_count_update_success": "章节数更新成功",
        "chapter_count_update_failed": "更新章节数失败: {error}",
        "ownership_check_failed": "检查所有权失败: {error}",
        "segmentation_preview_success": "分段预览成功",
        "segmentation_preview_failed": "预览分段失败: {error}",
        "segmentation_success": "分段处理成功",
        "segmentation_failed": "分段处理失败: {error}",
        "segmentation_stats_success": "获取统计信息成功",
        "segmentation_stats_failed": "获取统计信息失败: {error}",
        "segments_list_success": "获取分段列表成功",
        "segments_list_failed": "获取分段列表失败: {error}",
        "progress_get_success": "获取阅读进度成功",
        "progress_get_failed": "获取阅读进度失败: {error}",
        "progress_update_success": "阅读进度更新成功",
        "progress_update_failed": "更新阅读进度失败: {error}",
        "progress_delete_success": "阅读进度删除成功",
        "progress_delete_failed": "删除阅读进度失败: {error}",
        "progress_list_success": "获取阅读进度列表成功",
        "progress_list_failed": "获取阅读进度列表失败: {error}",
        "reading_stats_success": "获取阅读统计成功",
        "reading_stats_failed": "获取阅读统计失败: {error}",
        "novel_id_mismatch": "请求中的小说ID与路径参数不匹配",
        "system_auth_required": "系统级接口需要特殊授权",
        "no_progress_found": "暂无阅读进度",
        "progress_not_found": "阅读进度不存在",
        # Status text
        "public": "公开",
        "private": "私有"
    },
    SupportedLanguage.ZH_TW: {
        # Novel upload messages
        "novel_created_success": "小說創建成功",
        "file_upload_success": "檔案上傳成功",
        "novel_creation_failed": "創建小說失敗: {error}",
        "file_upload_failed": "檔案上傳失敗: {error}",
        "supported_formats_error": "目前支援 TXT 和 EPUB 格式的檔案",
        "file_size_exceeded": "檔案大小不能超過50MB",
        "file_empty": "檔案內容為空",
        "novel_not_found": "小說不存在或您無權訪問",
        "novel_update_success": "小說更新成功",
        "novel_update_failed": "更新小說失敗: {error}",
        "novel_delete_success": "小說刪除成功",
        "novel_delete_failed": "刪除小說失敗: {error}",
        "novel_list_failed": "獲取小說列表失敗: {error}",
        "novel_details_failed": "獲取小說詳情失敗: {error}",
        "batch_delete_success": "成功刪除{count}部小說",
        "batch_delete_failed": "批量刪除小說失敗: {error}",
        "public_status_updated": "小說已設置為{status}",
        "public_status_update_failed": "切換小說公開狀態失敗: {error}",
        "stats_get_failed": "獲取統計信息失敗: {error}",
        "chapter_count_update_success": "章節數更新成功",
        "chapter_count_update_failed": "更新章節數失敗: {error}",
        "ownership_check_failed": "檢查所有權失敗: {error}",
        "segmentation_preview_success": "分段預覽成功",
        "segmentation_preview_failed": "預覽分段失敗: {error}",
        "segmentation_success": "分段處理成功",
        "segmentation_failed": "分段處理失敗: {error}",
        "segmentation_stats_success": "獲取統計信息成功",
        "segmentation_stats_failed": "獲取統計信息失敗: {error}",
        "segments_list_success": "獲取分段列表成功",
        "segments_list_failed": "獲取分段列表失敗: {error}",
        "progress_get_success": "獲取閱讀進度成功",
        "progress_get_failed": "獲取閱讀進度失敗: {error}",
        "progress_update_success": "閱讀進度更新成功",
        "progress_update_failed": "更新閱讀進度失敗: {error}",
        "progress_delete_success": "閱讀進度刪除成功",
        "progress_delete_failed": "刪除閱讀進度失敗: {error}",
        "progress_list_success": "獲取閱讀進度列表成功",
        "progress_list_failed": "獲取閱讀進度列表失敗: {error}",
        "reading_stats_success": "獲取閱讀統計成功",
        "reading_stats_failed": "獲取閱讀統計失敗: {error}",
        "novel_id_mismatch": "請求中的小說ID與路徑參數不匹配",
        "system_auth_required": "系統級接口需要特殊授權",
        "no_progress_found": "暫無閱讀進度",
        "progress_not_found": "閱讀進度不存在",
        # Status text
        "public": "公開",
        "private": "私有"
    },
    SupportedLanguage.JA: {
        # Novel upload messages
        "novel_created_success": "小説の作成が成功しました",
        "file_upload_success": "ファイルのアップロードが成功しました",
        "novel_creation_failed": "小説の作成に失敗しました: {error}",
        "file_upload_failed": "ファイルのアップロードに失敗しました: {error}",
        "supported_formats_error": "現在TXTとEPUBファイル形式をサポートしています",
        "file_size_exceeded": "ファイルサイズは50MBを超えることはできません",
        "file_empty": "ファイルの内容が空です",
        "novel_not_found": "小説が存在しないか、アクセス権限がありません",
        "novel_update_success": "小説の更新が成功しました",
        "novel_update_failed": "小説の更新に失敗しました: {error}",
        "novel_delete_success": "小説の削除が成功しました",
        "novel_delete_failed": "小説の削除に失敗しました: {error}",
        "novel_list_failed": "小説リストの取得に失敗しました: {error}",
        "novel_details_failed": "小説詳細の取得に失敗しました: {error}",
        "batch_delete_success": "{count}つの小説の削除が成功しました",
        "batch_delete_failed": "小説の一括削除に失敗しました: {error}",
        "public_status_updated": "小説が{status}に設定されました",
        "public_status_update_failed": "小説の公開状態の切り替えに失敗しました: {error}",
        "stats_get_failed": "統計情報の取得に失敗しました: {error}",
        "chapter_count_update_success": "章数の更新が成功しました",
        "chapter_count_update_failed": "章数の更新に失敗しました: {error}",
        "ownership_check_failed": "所有権の確認に失敗しました: {error}",
        "segmentation_preview_success": "セグメント化プレビューが成功しました",
        "segmentation_preview_failed": "セグメント化プレビューに失敗しました: {error}",
        "segmentation_success": "セグメント化処理が成功しました",
        "segmentation_failed": "セグメント化処理に失敗しました: {error}",
        "segmentation_stats_success": "統計情報の取得が成功しました",
        "segmentation_stats_failed": "統計情報の取得に失敗しました: {error}",
        "segments_list_success": "セグメントリストの取得が成功しました",
        "segments_list_failed": "セグメントリストの取得に失敗しました: {error}",
        "progress_get_success": "読書進度の取得が成功しました",
        "progress_get_failed": "読書進度の取得に失敗しました: {error}",
        "progress_update_success": "読書進度の更新が成功しました",
        "progress_update_failed": "読書進度の更新に失敗しました: {error}",
        "progress_delete_success": "読書進度の削除が成功しました",
        "progress_delete_failed": "読書進度の削除に失敗しました: {error}",
        "progress_list_success": "読書進度リストの取得が成功しました",
        "progress_list_failed": "読書進度リストの取得に失敗しました: {error}",
        "reading_stats_success": "読書統計の取得が成功しました",
        "reading_stats_failed": "読書統計の取得に失敗しました: {error}",
        "novel_id_mismatch": "リクエスト内の小説IDがパスパラメータと一致しません",
        "system_auth_required": "システムレベルのインターフェースには特別な認証が必要です",
        "no_progress_found": "読書進度がありません",
        "progress_not_found": "読書進度が存在しません",
        # Status text
        "public": "公開",
        "private": "プライベート"
    }
}

def get_language_from_header(accept_language: Optional[str]) -> SupportedLanguage:
    """
    从 Accept-Language 头部获取语言设置
    
    Args:
        accept_language: Accept-Language 头部值
        
    Returns:
        SupportedLanguage: 支持的语言枚举
    """
    if not accept_language:
        return SupportedLanguage.EN
    
    # 解析 Accept-Language 头部
    # 例如: "zh-CN,zh;q=0.9,en;q=0.8"
    languages = []
    for lang_part in accept_language.split(','):
        lang = lang_part.split(';')[0].strip().lower()
        languages.append(lang)
    
    # 按优先级匹配支持的语言
    for lang in languages:
        if lang.startswith('zh'):
            if 'tw' in lang or 'hant' in lang:
                return SupportedLanguage.ZH_TW
            else:
                return SupportedLanguage.ZH
        elif lang.startswith('ja'):
            return SupportedLanguage.JA
        elif lang.startswith('en'):
            return SupportedLanguage.EN
    
    # 默认返回英语
    return SupportedLanguage.EN

def get_message(key: str, language: SupportedLanguage = SupportedLanguage.EN, **kwargs) -> str:
    """
    获取指定语言的消息
    
    Args:
        key: 消息键
        language: 语言
        **kwargs: 格式化参数
        
    Returns:
        str: 格式化后的消息
    """
    try:
        message_dict = MESSAGES.get(language, MESSAGES[SupportedLanguage.EN])
        message = message_dict.get(key, MESSAGES[SupportedLanguage.EN].get(key, key))
        return message.format(**kwargs) if kwargs else message
    except (KeyError, ValueError):
        # 如果格式化失败，返回英语版本
        fallback_message = MESSAGES[SupportedLanguage.EN].get(key, key)
        try:
            return fallback_message.format(**kwargs) if kwargs else fallback_message
        except (KeyError, ValueError):
            return fallback_message

def get_localized_status_text(is_public: bool, language: SupportedLanguage = SupportedLanguage.EN) -> str:
    """
    获取本地化的状态文本
    
    Args:
        is_public: 是否公开
        language: 语言
        
    Returns:
        str: 本地化的状态文本
    """
    status_key = "public" if is_public else "private"
    return get_message(status_key, language)