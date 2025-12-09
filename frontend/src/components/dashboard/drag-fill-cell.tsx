"use client";

import { ReactNode, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";

interface DragFillCellProps {
  rowId: string;
  field: string;
  value: string;
  isSource: boolean;
  isTarget: boolean;
  onDragStart: (rowId: string, field: string, value: string) => void;
  onDragEnter: (rowId: string) => void;
  children: ReactNode;
  className?: string;
}

export function DragFillCell({
  rowId,
  field,
  value,
  isSource,
  isTarget,
  onDragStart,
  onDragEnter,
  children,
  className,
}: DragFillCellProps) {
  const cellRef = useRef<HTMLDivElement>(null);

  const handleDragHandleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onDragStart(rowId, field, value);
    },
    [rowId, field, value, onDragStart]
  );

  const handleMouseEnter = useCallback(() => {
    onDragEnter(rowId);
  }, [rowId, onDragEnter]);

  return (
    <div
      ref={cellRef}
      className={cn(
        "relative group",
        isSource && "bg-blue-100 dark:bg-blue-950/30",
        isTarget && "bg-blue-50 dark:bg-blue-950/20",
        className
      )}
      onMouseEnter={handleMouseEnter}
    >
      {children}
      {/* Drag handle - small square at bottom-right corner */}
      <div
        className={cn(
          "absolute bottom-0 right-0 w-2 h-2 bg-blue-500 cursor-crosshair",
          "opacity-0 group-hover:opacity-100 transition-opacity",
          isSource && "opacity-100"
        )}
        onMouseDown={handleDragHandleMouseDown}
        title="Drag to fill down"
      />
    </div>
  );
}
