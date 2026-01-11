import React from "react";
import { cn } from "../../lib/utils";

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div className="relative">
        <select
          className={cn(
            "flex h-10 w-full appearance-none rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm",
            "text-white",
            "focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "pr-10", // Space for arrow
            className
          )}
          ref={ref}
          {...props}
        >
          {children}
        </select>
        {/* Custom arrow */}
        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-gray-500"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </div>
    );
  }
);

Select.displayName = "Select";

export { Select };
