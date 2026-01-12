from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class LibraryType(str, Enum):
    TEXT = "text"
    NOVEL = "novel"

class ArticleStatus(str, Enum):
    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class TranslationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    NATIVE = "native"

class ShareRange(str, Enum):
    ALL = "all"
    FRIENDS = "friends"
    PREMIUM = "premium"

# 文章库相关模型
class MaterialLibraryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    library_type: LibraryType = LibraryType.TEXT
    target_language: str = "zh-CN"
    explanation_language: str = "zh-CN"
    is_public: bool = False

class MaterialLibraryCreate(MaterialLibraryBase):
    pass

class MaterialLibraryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    library_type: Optional[LibraryType] = None
    target_language: Optional[str] = None
    explanation_language: Optional[str] = None
    is_public: Optional[bool] = None

class MaterialLibraryResponse(MaterialLibraryBase):
    id: str
    user_id: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# 文章相关模型
class MaterialArticleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    file_type: str = "text"
    file_size: Optional[int] = None
    file_path: Optional[str] = None
    original_filename: Optional[str] = None
    library_id: Optional[str] = None
    
    target_language: str = "zh-CN"
    difficulty_level: Optional[DifficultyLevel] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    
    is_public: bool = False
    share_range: ShareRange = ShareRange.ALL
    
    is_ai_generated: bool = False
    generation_prompt: Optional[str] = None
    enable_deep_explanation: bool = False
    
    description: Optional[str] = None
    word_count: Optional[int] = None
    estimated_time: Optional[int] = None

class MaterialArticleCreate(MaterialArticleBase):
    pass

class MaterialArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    file_path: Optional[str] = None
    original_filename: Optional[str] = None
    library_id: Optional[str] = None
    
    target_language: Optional[str] = None
    difficulty_level: Optional[DifficultyLevel] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    
    is_public: Optional[bool] = None
    share_range: Optional[ShareRange] = None
    
    is_ai_generated: Optional[bool] = None
    generation_prompt: Optional[str] = None
    enable_deep_explanation: Optional[bool] = None
    
    description: Optional[str] = None

class MaterialArticleResponse(MaterialArticleBase):
    id: str
    user_id: str
    status: ArticleStatus
    translation_status: TranslationStatus
    share_date: Optional[datetime] = None
    view_count: int
    like_count: int
    comment_count: int
    is_purchased: bool
    created_at: datetime
    updated_at: datetime
    
    # 统计字段（从视图计算得出）
    segment_count: int = 0
    ai_explanation_count: int = 0
    ai_explanation_coverage_percent: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)

# 文章分段相关模型
class GrammarItem(BaseModel):
    name: str
    explanation: str

class VocabularyItem(BaseModel):
    word: str
    reading: Optional[str] = None
    meaning: str

# AI解释相关模型
class AIVocabularyItem(BaseModel):
    word: str
    meaning: str
    usage: str
    example: Optional[str] = None

class AIGrammarPoint(BaseModel):
    point: str
    explanation: str
    example: Optional[str] = None

class SegmentAIExplanation(BaseModel):
    translation: str
    explanation: str
    vocabulary: List[AIVocabularyItem] = []
    grammar_points: List[AIGrammarPoint] = []
    cultural_context: Optional[str] = None
    difficulty_level: Optional[str] = "intermediate"
    learning_tips: Optional[str] = None

class MaterialSegmentBase(BaseModel):
    original_text: str = Field(..., min_length=1)
    translation: str = ""
    reading_text: str = ""
    is_new_paragraph: bool = False
    segment_order: int = Field(..., ge=0)
    grammar_items: List[GrammarItem] = []
    vocabulary_items: List[VocabularyItem] = []

class MaterialSegmentCreate(MaterialSegmentBase):
    article_id: str

class MaterialSegmentUpdate(BaseModel):
    original_text: Optional[str] = Field(None, min_length=1)
    translation: Optional[str] = None
    reading_text: Optional[str] = None
    is_new_paragraph: Optional[bool] = None
    segment_order: Optional[int] = Field(None, ge=0)
    grammar_items: Optional[List[GrammarItem]] = None
    vocabulary_items: Optional[List[VocabularyItem]] = None

class MaterialSegmentResponse(MaterialSegmentBase):
    id: str
    article_id: str
    created_at: datetime
    updated_at: datetime
    
    # AI解释缓存字段
    ai_explanation: Optional[SegmentAIExplanation] = None
    ai_explanation_model: Optional[str] = None
    ai_explanation_created_at: Optional[datetime] = None
    ai_explanation_updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# 批量创建分段
class MaterialSegmentBatchCreate(BaseModel):
    article_id: str
    segments: List[MaterialSegmentBase]

# 收藏夹相关模型
class MaterialCollectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_default: bool = False

class MaterialCollectionCreate(MaterialCollectionBase):
    pass

class MaterialCollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_default: Optional[bool] = None

class MaterialCollectionResponse(MaterialCollectionBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# 收藏夹添加文章
class MaterialCollectionArticleAdd(BaseModel):
    collection_id: str
    article_id: str
    note: Optional[str] = None

# 查询参数
class MaterialLibraryQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    library_type: Optional[LibraryType] = None
    is_public: Optional[bool] = None
    search: Optional[str] = None

class MaterialArticleQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    library_id: Optional[str] = None
    status: Optional[ArticleStatus] = None
    is_public: Optional[bool] = None
    difficulty_level: Optional[DifficultyLevel] = None
    category: Optional[str] = None
    search: Optional[str] = None

# 分页响应
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

class MaterialLibraryListResponse(BaseModel):
    items: List[MaterialLibraryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class MaterialArticleListResponse(BaseModel):
    items: List[MaterialArticleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class MaterialSegmentListResponse(BaseModel):
    items: List[MaterialSegmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int 