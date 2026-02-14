export interface Article {
    id: string;
    title: string;
    content: string;
    /** 素材来源类型: web | article | youtube | local_video | audio | book */
    source_type?: "web" | "article" | "youtube" | "local_video" | "audio" | "book";
    source_url?: string;
    media_path?: string;
    /** 书籍文件路径 (EPUB/TXT/PDF) */
    book_path?: string;
    /** 书籍类型: "epub" | "txt" | "pdf" */
    book_type?: "epub" | "txt" | "pdf";
    created_at: string;
    translated: boolean;
    segments?: ArticleSegment[];
}

export interface ArticleSegment {
    id: string;
    article_id: string;
    order: number;
    text: string;
    reading_text?: string;
    translation?: string;
    explanation?: SegmentExplanation;
    start_time?: number;
    end_time?: number;
    created_at: string;
    /** 是否是新段落开始（true则另起一行显示，false则紧跟上一段显示） */
    is_new_paragraph?: boolean;
}

export interface SegmentExplanation {
    translation: string;
    explanation: string;
    reading_text?: string;
    vocabulary?: VocabularyItem[];
    grammar_points?: GrammarPoint[];
    cultural_context?: string;
    difficulty_level?: string;
    learning_tips?: string;
}

export interface VocabularyItem {
    word: string;
    meaning: string;
    usage: string;
    example?: string;
    reading?: string;
}

export interface GrammarPoint {
    point: string;
    explanation: string;
    example?: string;
}

// 单词收藏
export interface FavoriteVocabulary {
    id: string;
    word: string;
    meaning: string;
    usage: string;
    example?: string;
    reading?: string;
    source_article_id?: string;
    source_article_title?: string;
    created_at: string;
}

// 语法收藏
export interface FavoriteGrammar {
    id: string;
    point: string;
    explanation: string;
    example?: string;
    source_article_id?: string;
    source_article_title?: string;
    created_at: string;
}

// 书签
export interface Bookmark {
    id: string;
    /** 书籍文件路径 */
    book_path: string;
    /** 书籍类型: "txt" | "pdf" | "epub" */
    book_type: "txt" | "pdf" | "epub";
    /** 书签标题 */
    title: string;
    /** 可选笔记 */
    note?: string;
    /** 用户选中的文字摘录 */
    selected_text?: string;
    /** PDF/TXT 页码（从1开始） */
    page_number?: number;
    /** EPUB CFI 位置字符串 */
    epub_cfi?: string;
    /** 创建时间 */
    created_at: string;
    /** 书签颜色标签（可选） */
    color?: string;
}
