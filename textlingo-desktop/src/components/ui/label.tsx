/**
 * Label 组件
 * 用于表单字段的标签显示
 */

import { forwardRef, LabelHTMLAttributes } from "react";

// Label 组件属性接口
interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
    /** 是否禁用状态 */
    disabled?: boolean;
}

/**
 * Label 组件
 * 支持 ref 转发和自定义样式
 */
export const Label = forwardRef<HTMLLabelElement, LabelProps>(
    ({ className = "", disabled, ...props }, ref) => {
        return (
            <label
                ref={ref}
                className={`text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 ${disabled ? "cursor-not-allowed opacity-70" : ""
                    } ${className}`.trim()}
                {...props}
            />
        );
    }
);

Label.displayName = "Label";
