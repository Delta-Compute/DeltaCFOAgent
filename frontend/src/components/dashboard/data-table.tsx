"use client";

import { ReactNode, useState, useRef } from "react";
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/loading";

// Types
export interface Column<T> {
  key: string;
  header: string;
  sortable?: boolean;
  width?: string;
  align?: "left" | "center" | "right";
  render?: (item: T, index: number) => ReactNode;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField: keyof T;
  isLoading?: boolean;
  // Sorting
  sortKey?: string;
  sortDirection?: "asc" | "desc";
  onSort?: (key: string) => void;
  // Selection
  selectable?: boolean;
  selectedKeys?: Set<string>;
  onSelectionChange?: (keys: Set<string>) => void;
  // Pagination
  page?: number;
  pageSize?: number;
  totalItems?: number;
  onPageChange?: (page: number) => void;
  // Row click
  onRowClick?: (item: T) => void;
  // Empty state
  emptyMessage?: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  keyField,
  isLoading = false,
  sortKey,
  sortDirection,
  onSort,
  selectable = false,
  selectedKeys = new Set(),
  onSelectionChange,
  page = 1,
  pageSize = 10,
  totalItems,
  onPageChange,
  onRowClick,
  emptyMessage = "No data found",
}: DataTableProps<T>) {
  // const [hoveredRow, setHoveredRow] = useState<string | null>(null); // Available for hover effects

  // Calculate pagination
  const total = totalItems ?? data.length;
  const totalPages = Math.ceil(total / pageSize);
  const startIndex = (page - 1) * pageSize + 1;
  const endIndex = Math.min(page * pageSize, total);

  // Handle select all
  const allSelected =
    data.length > 0 &&
    data.every((item) => selectedKeys.has(String(item[keyField])));
  const someSelected =
    data.some((item) => selectedKeys.has(String(item[keyField]))) &&
    !allSelected;

  function handleSelectAll() {
    if (!onSelectionChange) return;

    if (allSelected) {
      // Deselect all visible items
      const newKeys = new Set(selectedKeys);
      data.forEach((item) => newKeys.delete(String(item[keyField])));
      onSelectionChange(newKeys);
    } else {
      // Select all visible items
      const newKeys = new Set(selectedKeys);
      data.forEach((item) => newKeys.add(String(item[keyField])));
      onSelectionChange(newKeys);
    }
  }

  // Track last clicked index for shift-click range selection
  const lastClickedIndexRef = useRef<number | null>(null);

  function handleSelectRow(item: T, index: number, shiftKey: boolean = false) {
    if (!onSelectionChange) return;

    const key = String(item[keyField]);
    const newKeys = new Set(selectedKeys);

    // Shift-click range selection
    if (shiftKey && lastClickedIndexRef.current !== null && lastClickedIndexRef.current !== index) {
      const start = Math.min(lastClickedIndexRef.current, index);
      const end = Math.max(lastClickedIndexRef.current, index);

      // Select all items in range
      for (let i = start; i <= end; i++) {
        if (data[i]) {
          newKeys.add(String(data[i][keyField]));
        }
      }
    } else {
      // Normal click - toggle selection
      if (newKeys.has(key)) {
        newKeys.delete(key);
      } else {
        newKeys.add(key);
      }
    }

    // Update last clicked index
    lastClickedIndexRef.current = index;

    onSelectionChange(newKeys);
  }

  // Render sort icon
  function renderSortIcon(columnKey: string) {
    if (sortKey !== columnKey) {
      return <ChevronsUpDown className="h-4 w-4 text-muted-foreground/50" />;
    }
    return sortDirection === "asc" ? (
      <ChevronUp className="h-4 w-4" />
    ) : (
      <ChevronDown className="h-4 w-4" />
    );
  }

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {selectable && (
                <TableHead className="w-[50px]">
                  <Skeleton className="h-4 w-4" />
                </TableHead>
              )}
              {columns.map((column) => (
                <TableHead key={column.key} style={{ width: column.width }}>
                  <Skeleton className="h-4 w-20" />
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                {selectable && (
                  <TableCell>
                    <Skeleton className="h-4 w-4" />
                  </TableCell>
                )}
                {columns.map((column) => (
                  <TableCell key={column.key}>
                    <Skeleton className="h-4 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  // Empty state
  if (data.length === 0) {
    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {selectable && <TableHead className="w-[50px]" />}
              {columns.map((column) => (
                <TableHead key={column.key} style={{ width: column.width }}>
                  {column.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
        </Table>
        <div className="flex items-center justify-center py-12 text-muted-foreground">
          {emptyMessage}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {selectable && (
                <TableHead className="w-[50px]">
                  <Checkbox
                    checked={allSelected}
                    ref={(el) => {
                      if (el) {
                        (el as HTMLButtonElement & { indeterminate: boolean }).indeterminate = someSelected;
                      }
                    }}
                    onCheckedChange={handleSelectAll}
                    aria-label="Select all"
                  />
                </TableHead>
              )}
              {columns.map((column) => (
                <TableHead
                  key={column.key}
                  style={{ width: column.width }}
                  className={cn(
                    column.align === "center" && "text-center",
                    column.align === "right" && "text-right"
                  )}
                >
                  {column.sortable && onSort ? (
                    <button
                      className="flex items-center gap-1 hover:text-foreground transition-colors"
                      onClick={() => onSort(column.key)}
                    >
                      {column.header}
                      {renderSortIcon(column.key)}
                    </button>
                  ) : (
                    column.header
                  )}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((item, index) => {
              const key = item[keyField] != null ? String(item[keyField]) : `row-${index}`;
              const isSelected = selectedKeys.has(key);
              // const isHovered = hoveredRow === key; // Available for hover effects

              return (
                <TableRow
                  key={key}
                  className={cn(
                    onRowClick && "cursor-pointer",
                    isSelected && "bg-muted/50"
                  )}
                  onClick={() => onRowClick?.(item)}
                >
                  {selectable && (
                    <TableCell
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectRow(item, index, e.shiftKey);
                      }}
                      className="cursor-pointer"
                    >
                      <Checkbox
                        checked={isSelected}
                        aria-label={`Select row ${index + 1}${lastClickedIndexRef.current !== null ? " (Shift+click for range)" : ""}`}
                      />
                    </TableCell>
                  )}
                  {columns.map((column) => (
                    <TableCell
                      key={column.key}
                      className={cn(
                        column.align === "center" && "text-center",
                        column.align === "right" && "text-right"
                      )}
                    >
                      {column.render
                        ? column.render(item, index)
                        : String(item[column.key] ?? "")}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && onPageChange && (
        <div className="flex items-center justify-between px-2">
          <div className="text-sm text-muted-foreground">
            Showing {startIndex} to {endIndex} of {total} results
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
                let pageNum: number;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (page <= 3) {
                  pageNum = i + 1;
                } else if (page >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = page - 2 + i;
                }

                return (
                  <Button
                    key={pageNum}
                    variant={page === pageNum ? "default" : "outline"}
                    size="sm"
                    className="w-8"
                    onClick={() => onPageChange(pageNum)}
                  >
                    {pageNum}
                  </Button>
                );
              })}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
