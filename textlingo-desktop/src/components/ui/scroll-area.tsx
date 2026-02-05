/**
 * ScrollArea 组件
 * 提供自定义滚动区域样式，用于可滚动内容区域
 */

import { forwardRef, HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

// ScrollArea 组件属性接口
interface ScrollAreaProps extends HTMLAttributes<HTMLDivElement> {
    /** 滚动区域的子内容 */
    children: React.ReactNode;
}

/**
 * ScrollArea 组件
 * 提供一个带自定义滚动条样式的可滚动容器
 */
export const ScrollArea = forwardRef<HTMLDivElement, ScrollAreaProps>(
    ({ className, children, ...props }, ref) => {
        return (
            <div
                ref={ref}
                className={cn(
                    "overflow-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent hover:scrollbar-thumb-muted-foreground/40",
                    className
                )}
                {...props}
            >
                {children}
            </div>
        );
    }
);

ScrollArea.displayName = "ScrollArea";
