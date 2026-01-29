# 书签功能实现完成说明

## 🎉 完全实现完成！

所有三种格式（TXT、PDF、EPUB）的书签功能已全部完成！

## ✅ 已完成的部分

### 1. 后端实现（Rust）

#### 数据结构 (`src-tauri/src/types.rs`)
```rust
pub struct Bookmark {
    pub id: String,
    pub book_path: String,        // 书籍文件路径
    pub book_type: String,         // "txt" | "pdf" | "epub"
    pub title: String,             // 书签标题
    pub note: Option<String>,      // 可选笔记
    pub page_number: Option<i32>,  // PDF/TXT 页码
    pub epub_cfi: Option<String>,  // EPUB CFI 位置字符串
    pub created_at: String,
    pub color: Option<String>,     // 书签颜色标签
}
```

#### 存储函数 (`src-tauri/src/storage.rs`)
- ✅ `save_bookmark()` - 保存书签到文件
- ✅ `load_bookmark()` - 加载单个书签
- ✅ `list_bookmarks()` - 列出所有书签
- ✅ `delete_bookmark()` - 删除书签
- ✅ `list_bookmarks_for_book()` - 列出指定书籍的所有书签
- 存储位置: `$APP_DATA_DIR/bookmarks/{bookmark_id}`

#### Tauri 命令 (`src-tauri/src/commands.rs` + `src-tauri/src/lib.rs`)
- ✅ `add_bookmark_cmd` - 添加书签
- ✅ `list_bookmarks_cmd` - 列出所有书签
- ✅ `list_bookmarks_for_book_cmd` - 列出指定书籍的书签
- ✅ `update_bookmark_cmd` - 更新书签
- ✅ `delete_bookmark_cmd` - 删除书签

### 2. 前端实现

#### 类型定义 (`src/types/index.ts`)
```typescript
export interface Bookmark {
    id: string;
    book_path: string;
    book_type: "txt" | "pdf" | "epub";
    title: string;
    note?: string;
    page_number?: number;
    epub_cfi?: string;
    created_at: string;
    color?: string;
}
```

#### 书签侧边栏组件 (`src/components/features/BookmarkSidebar.tsx`)
- ✅ 显示书签列表
- ✅ 编辑书签（标题、笔记）
- ✅ 删除书签
- ✅ 点击书签跳转到对应位置
- ✅ 格式化显示位置信息（页码/EPUB位置）
- ✅ 响应式设计，固定在右侧

#### TxtReader 书签功能 (`src/components/features/TxtReader.tsx`)
- ✅ 添加 `bookPath` 属性支持
- ✅ 添加书签按钮（BookmarkPlus 图标）
- ✅ 书签列表按钮（Bookmark 图标）
- ✅ 添加书签对话框（输入标题和笔记）
- ✅ 保存当前页码到书签
- ✅ 从书签跳转到指定页码
- ✅ 集成 BookmarkSidebar 组件

#### PdfReader 书签功能 (`src/components/features/PdfReader.tsx`)
- ✅ 导入必要的依赖和组件
- ✅ 添加书签相关状态
- ✅ 实现添加书签功能（保存页码）
- ✅ 实现跳转到书签功能
- ✅ 在工具栏添加书签按钮
- ✅ 集成 BookmarkSidebar 组件
- ✅ 添加书签对话框

#### EpubReader 书签功能 (`src/components/features/EpubReader.tsx`)
- ✅ 导入必要的依赖和组件
- ✅ 添加书签相关状态
- ✅ 实现添加书签功能（保存 EPUB CFI）
- ✅ 实现跳转到书签功能（使用 CFI）
- ✅ 在工具栏添加书签按钮
- ✅ 集成 BookmarkSidebar 组件
- ✅ 添加书签对话框

---

## 📝 实现总结

### 3. 已实现的 PdfReader 书签功能

已在 `src/components/features/PdfReader.tsx` 中实现：

```typescript
// 1. 添加导入
import { invoke } from "@tauri-apps/api/core";
import { Bookmark as BookmarkIcon, BookmarkPlus } from "lucide-react";
import { BookmarkSidebar } from "./BookmarkSidebar";
import { Bookmark } from "../../types";
import { Dialog, DialogContent, ... } from "../ui/dialog";

// 2. 添加状态
const [isBookmarkSidebarOpen, setIsBookmarkSidebarOpen] = useState(false);
const [isAddBookmarkDialogOpen, setIsAddBookmarkDialogOpen] = useState(false);
const [bookmarkTitle, setBookmarkTitle] = useState("");
const [bookmarkNote, setBookmarkNote] = useState("");

// 3. 添加处理函数
const handleOpenAddBookmark = () => {
    setBookmarkTitle(`第 ${pageNumber} 页`);
    setBookmarkNote("");
    setIsAddBookmarkDialogOpen(true);
};

const handleAddBookmark = async () => {
    try {
        await invoke("add_bookmark_cmd", {
            bookPath,
            bookType: "pdf",
            title: bookmarkTitle,
            note: bookmarkNote || null,
            pageNumber: pageNumber, // PDF页码从1开始
            epubCfi: null,
            color: null,
        });
        setIsAddBookmarkDialogOpen(false);
    } catch (error) {
        console.error("Failed to add bookmark:", error);
    }
};

const handleJumpToBookmark = (bookmark: Bookmark) => {
    if (bookmark.page_number) {
        setPageNumber(bookmark.page_number);
    }
    setIsBookmarkSidebarOpen(false);
};

// 4. 在工具栏添加书签按钮（找到工具栏JSX位置）
{bookPath && (
    <div className="flex items-center gap-1">
        <Button
            variant="ghost"
            size="sm"
            onClick={handleOpenAddBookmark}
            title="添加书签"
        >
            <BookmarkPlus size={16} />
        </Button>
        <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsBookmarkSidebarOpen(true)}
            title="书签列表"
        >
            <BookmarkIcon size={16} />
        </Button>
    </div>
)}

// 5. 在返回JSX的末尾添加（</div> 之前）
{/* 书签侧边栏 */}
<BookmarkSidebar
    bookPath={bookPath}
    bookType="pdf"
    onJumpToBookmark={handleJumpToBookmark}
    isOpen={isBookmarkSidebarOpen}
    onClose={() => setIsBookmarkSidebarOpen(false)}
/>

{/* 添加书签对话框 */}
<Dialog open={isAddBookmarkDialogOpen} onOpenChange={setIsAddBookmarkDialogOpen}>
    <DialogContent>
        <DialogHeader>
            <DialogTitle>添加书签</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
            <div className="space-y-2">
                <Label htmlFor="bookmark-title">标题</Label>
                <Input
                    id="bookmark-title"
                    value={bookmarkTitle}
                    onChange={(e) => setBookmarkTitle(e.target.value)}
                    placeholder="书签标题"
                />
            </div>
            <div className="space-y-2">
                <Label htmlFor="bookmark-note">笔记（可选）</Label>
                <Textarea
                    id="bookmark-note"
                    value={bookmarkNote}
                    onChange={(e) => setBookmarkNote(e.target.value)}
                    placeholder="添加笔记..."
                    rows={3}
                />
            </div>
            <div className="text-sm text-muted-foreground">
                将在第 {pageNumber} 页添加书签
            </div>
        </div>
        <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddBookmarkDialogOpen(false)}>
                取消
            </Button>
            <Button onClick={handleAddBookmark}>添加</Button>
        </DialogFooter>
    </DialogContent>
</Dialog>
```

### 4. 已实现的 EpubReader 书签功能

已在 `src/components/features/EpubReader.tsx` 中实现：

```typescript
// 与 PdfReader 实现类似，但使用 EPUB CFI

// 1. 保存书签时使用 EPUB CFI
const handleAddBookmark = async () => {
    try {
        await invoke("add_bookmark_cmd", {
            bookPath,
            bookType: "epub",
            title: bookmarkTitle,
            note: bookmarkNote || null,
            pageNumber: null,
            epubCfi: currentLocation, // 使用 react-reader 提供的 CFI
            color: null,
        });
        setIsAddBookmarkDialogOpen(false);
    } catch (error) {
        console.error("Failed to add bookmark:", error);
    }
};

// 2. 跳转时使用 CFI
const handleJumpToBookmark = (bookmark: Bookmark) => {
    if (bookmark.epub_cfi && renditionRef.current) {
        renditionRef.current.display(bookmark.epub_cfi);
    }
    setIsBookmarkSidebarOpen(false);
};
```

---

## 🎯 使用方式

### 1. TXT 阅读器（已完成）
```typescript
<TxtReader
    content={txtContent}
    title="我的书籍"
    bookPath="/path/to/book.txt"  // 必须传入才能启用书签功能
    onTextSelect={handleTextSelect}
/>
```

### 2. PDF 阅读器（待完成）
```typescript
<PdfReader
    bookPath="/path/to/book.pdf"
    title="我的PDF"
    onTextSelect={handleTextSelect}
/>
```

### 3. EPUB 阅读器（待完成）
```typescript
<EpubReader
    bookPath="/path/to/book.epub"
    title="我的EPUB"
    onTextSelect={handleTextSelect}
/>
```

---

## 📝 注意事项

1. **页码约定**：
   - TXT: 内部使用 0-indexed，存储时转换为 1-indexed
   - PDF: 本身就是 1-indexed，直接存储
   - EPUB: 使用 CFI 字符串，不使用页码

2. **BookPath 必须唯一**：每个书籍的 bookPath 必须是唯一标识符，建议使用完整的文件路径

3. **书签数据持久化**：书签数据存储在 `$APP_DATA_DIR/bookmarks/` 目录下，每个书签一个 JSON 文件

4. **UI 组件依赖**：
   - Button, Input, Textarea, Label（来自 shadcn/ui）
   - Dialog 组件（来自 shadcn/ui）
   - Lucide React 图标

---

## ✅ 实现完成清单

- [x] Rust 后端数据结构和存储
- [x] Rust Tauri 命令接口
- [x] 前端 TypeScript 类型定义
- [x] BookmarkSidebar 组件
- [x] TxtReader 书签功能
- [x] PdfReader 书签功能
- [x] EpubReader 书签功能

## 🔧 后续增强建议

1. **在 BookReader.tsx 中传递 bookPath 参数**：确保各阅读器能正确接收 bookPath
2. **完整测试**：
   - 测试添加、编辑、删除书签
   - 测试书签跳转功能
   - 测试跨会话持久化
3. **可选增强功能**：
   - 书签颜色标签功能（已有字段支持）
   - 书签搜索功能
   - 书签导出/导入功能
   - 书签排序（按时间/按位置）
   - 书签分组功能

---

## 📚 参考文件路径

### 后端
- `textlingo-desktop/src-tauri/src/types.rs` - 数据类型定义
- `textlingo-desktop/src-tauri/src/storage.rs` - 存储函数
- `textlingo-desktop/src-tauri/src/commands.rs` - Tauri 命令
- `textlingo-desktop/src-tauri/src/lib.rs` - 命令注册

### 前端
- `textlingo-desktop/src/types/index.ts` - TypeScript 类型
- `textlingo-desktop/src/components/features/BookmarkSidebar.tsx` - 侧边栏组件
- `textlingo-desktop/src/components/features/TxtReader.tsx` - TXT 阅读器（已完成）
- `textlingo-desktop/src/components/features/PdfReader.tsx` - PDF 阅读器（待完成）
- `textlingo-desktop/src/components/features/EpubReader.tsx` - EPUB 阅读器（待完成）
