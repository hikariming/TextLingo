/**
 * PDF.js Worker 配置
 * 在打包后确保 PDF Worker 能够正确加载
 * Worker 文件由 vite-plugin-static-copy 复制到 assets 目录
 */

import { pdfjs } from "react-pdf";

// 配置 PDF.js worker
// 在开发环境下，我们需要使用 ?url 导入来获取正确的文件路径
// 在生产环境下，文件会被复制到 assets 目录
if (import.meta.env.DEV) {
    pdfjs.GlobalWorkerOptions.workerSrc = new URL(
        "pdfjs-dist/build/pdf.worker.min.mjs",
        import.meta.url
    ).href;
} else {
    pdfjs.GlobalWorkerOptions.workerSrc = new URL(
        "/assets/pdf.worker.min.mjs",
        import.meta.url
    ).href;
}

export { pdfjs };
