import React, { useState } from "react";
import { cn } from "../../lib/utils";

interface TabsProps {
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

interface TabsListProps {
  children: React.ReactNode;
  className?: string;
}

interface TabsTriggerProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

interface TabsContentProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

const TabsContext = React.createContext<{
  activeTab: string;
  setActiveTab: (value: string) => void;
} | null>(null);


export function Tabs({ defaultValue, value, onValueChange, children, className }: TabsProps) {
  const [internalState, setInternalState] = useState(defaultValue || "");

  const activeTab = value !== undefined ? value : internalState;

  const handleTabChange = (newValue: string) => {
    if (onValueChange) {
      onValueChange(newValue);
    }
    if (value === undefined) {
      setInternalState(newValue);
    }
  };

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab: handleTabChange }}>
      <div className={cn("", className)}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ children, className }: TabsListProps) {
  return (
    <div
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-lg bg-gray-800 p-1",
        className
      )}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({ value, children, className }: TabsTriggerProps) {
  const context = React.useContext(TabsContext);
  if (!context) throw new Error("TabsTrigger must be used within Tabs");

  const { activeTab, setActiveTab } = context;
  const isActive = activeTab === value;

  return (
    <button
      onClick={() => setActiveTab(value)}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600",
        isActive
          ? "bg-gray-700 text-white"
          : "text-gray-400 hover:text-white",
        className
      )}
    >
      {children}
    </button>
  );
}

export function TabsContent({ value, children, className }: TabsContentProps) {
  const context = React.useContext(TabsContext);
  if (!context) throw new Error("TabsContent must be used within Tabs");

  const { activeTab } = context;
  if (activeTab !== value) return null;

  return (
    <div className={cn("mt-4 focus:outline-none", className)}>{children}</div>
  );
}
