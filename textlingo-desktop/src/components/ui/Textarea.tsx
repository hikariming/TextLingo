import React from "react";
import { cn } from "../../lib/utils";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm",
          "text-white placeholder:text-gray-500",
          "focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "resize-y",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);

Textarea.displayName = "Textarea";

export { Textarea };
