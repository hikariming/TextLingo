import React, { useEffect, useRef, useCallback } from "react";
import { cn } from "../../lib/utils";

interface DialogProps {
  /** @deprecated 使用 open 代替 */
  isOpen?: boolean;
  /** @deprecated 使用 onOpenChange 代替 */
  onClose?: () => void;
  /** 控制对话框是否打开 */
  open?: boolean;
  /** 对话框打开状态变化时的回调 */
  onOpenChange?: (open: boolean) => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

import { createPortal } from "react-dom";

export function Dialog({
  isOpen,
  onClose,
  open,
  onOpenChange,
  title,
  children,
  className
}: DialogProps) {
  // 支持两种 API：旧的 isOpen/onClose 和新的 open/onOpenChange
  const isDialogOpen = open !== undefined ? open : isOpen;
  const handleClose = useCallback(() => {
    if (onOpenChange) {
      onOpenChange(false);
    } else if (onClose) {
      onClose();
    }
  }, [onOpenChange, onClose]);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEscapeKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };

    if (isDialogOpen) {
      document.addEventListener("keydown", handleEscapeKey);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscapeKey);
      document.body.style.overflow = "unset";
    };
  }, [isDialogOpen, handleClose]);

  if (!isDialogOpen) return null;

  return createPortal(
    // 外层容器：使用 fixed 定位覆盖整个视口，flex 实现垂直和水平居中
    <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto">
      {/* Backdrop - 遮罩层，使用主题兼容的半透明背景 */}
      <div
        className="fixed inset-0 bg-background/80 backdrop-blur-sm"
        onClick={handleClose}
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
          onClick={handleClose}
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

// DialogTitle 组件属性
interface DialogTitleProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * DialogTitle 组件
 * 用于设置对话框标题
 */
export function DialogTitle({ children, className }: DialogTitleProps) {
  return (
    <h2 className={cn("text-lg font-semibold text-popover-foreground", className)}>
      {children}
    </h2>
  );
}
