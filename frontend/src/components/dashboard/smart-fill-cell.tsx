"use client";

import { ReactNode, useState } from "react";
import { Loader2, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface SmartFillCellProps {
  rowId: string;
  field: string;
  value: string;
  description: string;
  onSmartFill: (description: string, field: string, value: string) => Promise<void>;
  children: ReactNode;
  className?: string;
}

export function SmartFillCell({
  field,
  value,
  description,
  onSmartFill,
  children,
  className,
}: SmartFillCellProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleDoubleClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    if (!value || isLoading) return;

    setIsLoading(true);
    try {
      await onSmartFill(description, field, value);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={cn("relative group", className)}>
      {children}
      {/* Smart fill handle - appears on hover when cell has a value */}
      {value && (
        <div
          className={cn(
            "absolute bottom-0 right-0 w-4 h-4 rounded-sm cursor-pointer",
            "opacity-0 group-hover:opacity-100 transition-opacity",
            "flex items-center justify-center",
            isLoading ? "bg-gray-400" : "bg-blue-500 hover:bg-blue-600"
          )}
          onDoubleClick={handleDoubleClick}
          title="Double-click to fill similar transactions"
        >
          {isLoading ? (
            <Loader2 className="h-3 w-3 text-white animate-spin" />
          ) : (
            <ChevronDown className="h-3 w-3 text-white" />
          )}
        </div>
      )}
    </div>
  );
}
