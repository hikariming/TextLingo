import React, { useEffect, useRef } from "react";
import { cn } from "../../lib/utils";

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

import { createPortal } from "react-dom";

export function Dialog({ isOpen, onClose, title, children, className }: DialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    // 外层容器：使用 fixed 定位覆盖整个视口，flex 实现垂直和水平居中
    <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto">
      {/* Backdrop - 遮罩层，使用主题兼容的半透明背景 */}
      <div
        className="fixed inset-0 bg-background/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog - 弹窗主体，使用主题变量替代硬编码颜色 */}
      <div
        ref={dialogRef}
        className={cn(
          // 使用 popover 主题变量，确保与当前主题匹配
          "relative z-[101] w-full max-w-lg rounded-xl bg-popover border border-border",
          "shadow-2xl p-6 mx-4 my-4",
          className
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div className="mb-4">
            {/* 标题使用主题前景色 */}
            <h2 className="text-xl font-semibold text-popover-foreground">{title}</h2>
          </div>
        )}
        {children}

        {/* Close button - 关闭按钮使用主题兼容的颜色 */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-popover-foreground transition-colors"
          aria-label="Close"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>,
    document.body
  );
}

interface DialogHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export function DialogHeader({ children, className }: DialogHeaderProps) {
  return (
    <div className={cn("mb-4", className)}>
      {children}
    </div>
  );
}

interface DialogContentProps {
  children: React.ReactNode;
  className?: string;
}

export function DialogContent({ children, className }: DialogContentProps) {
  return <div className={cn("", className)}>{children}</div>;
}

interface DialogFooterProps {
  children: React.ReactNode;
  className?: string;
}

export function DialogFooter({ children, className }: DialogFooterProps) {
  return (
    <div className={cn("flex justify-end gap-3 mt-6", className)}>
      {children}
    </div>
  );
}
