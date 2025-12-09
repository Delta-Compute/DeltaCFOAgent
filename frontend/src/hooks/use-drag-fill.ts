"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { transactions, type BulkUpdateItem } from "@/lib/api";
import { toast } from "sonner";

export interface DragFillState {
  isDragging: boolean;
  sourceRowId: string | null;
  sourceField: string | null;
  sourceValue: string;
  targetRowIds: string[];
}

interface RowData {
  id: string;
}

export interface UseDragFillOptions<T extends RowData> {
  data: T[];
  onUpdate?: () => void;
}

export function useDragFill<T extends RowData>({
  data,
  onUpdate,
}: UseDragFillOptions<T>) {
  const [dragState, setDragState] = useState<DragFillState>({
    isDragging: false,
    sourceRowId: null,
    sourceField: null,
    sourceValue: "",
    targetRowIds: [],
  });

  const rowRefs = useRef<Map<string, HTMLElement>>(new Map());

  // Register a row element
  const registerRow = useCallback((id: string, element: HTMLElement | null) => {
    if (element) {
      rowRefs.current.set(id, element);
    } else {
      rowRefs.current.delete(id);
    }
  }, []);

  // Start drag
  const startDrag = useCallback(
    (rowId: string, field: string, value: string) => {
      setDragState({
        isDragging: true,
        sourceRowId: rowId,
        sourceField: field,
        sourceValue: value,
        targetRowIds: [],
      });
    },
    []
  );

  // Update drag target (called on mouse move)
  const updateDragTarget = useCallback(
    (targetRowId: string) => {
      if (!dragState.isDragging || !dragState.sourceRowId) return;

      // Find indices
      const sourceIndex = data.findIndex((d) => d.id === dragState.sourceRowId);
      const targetIndex = data.findIndex((d) => d.id === targetRowId);

      if (sourceIndex === -1 || targetIndex === -1) return;

      // Build list of rows between source and target
      const minIndex = Math.min(sourceIndex, targetIndex);
      const maxIndex = Math.max(sourceIndex, targetIndex);

      const targetIds = data
        .slice(minIndex, maxIndex + 1)
        .filter((d) => d.id !== dragState.sourceRowId)
        .map((d) => d.id);

      setDragState((prev) => ({
        ...prev,
        targetRowIds: targetIds,
      }));
    },
    [dragState.isDragging, dragState.sourceRowId, data]
  );

  // End drag and apply updates
  const endDrag = useCallback(async () => {
    if (
      !dragState.isDragging ||
      !dragState.sourceField ||
      dragState.targetRowIds.length === 0
    ) {
      setDragState({
        isDragging: false,
        sourceRowId: null,
        sourceField: null,
        sourceValue: "",
        targetRowIds: [],
      });
      return;
    }

    // Build updates
    const updates: BulkUpdateItem[] = dragState.targetRowIds.map((rowId) => ({
      transaction_id: rowId,
      field: dragState.sourceField!,
      value: dragState.sourceValue,
    }));

    // Reset state first
    setDragState({
      isDragging: false,
      sourceRowId: null,
      sourceField: null,
      sourceValue: "",
      targetRowIds: [],
    });

    // Apply updates
    if (updates.length > 0) {
      toast.info(`Updating ${updates.length} transactions...`);

      try {
        const response = await transactions.bulkUpdate(updates);

        if (response.success && response.data) {
          toast.success(
            `Successfully updated ${response.data.updated_count} transactions`
          );
          onUpdate?.();
        } else {
          toast.error(
            response.error?.message || "Failed to update transactions"
          );
        }
      } catch (error) {
        console.error("Bulk update error:", error);
        toast.error("Failed to update transactions");
      }
    }
  }, [dragState, onUpdate]);

  // Cancel drag
  const cancelDrag = useCallback(() => {
    setDragState({
      isDragging: false,
      sourceRowId: null,
      sourceField: null,
      sourceValue: "",
      targetRowIds: [],
    });
  }, []);

  // Check if a row is the source
  const isSourceRow = useCallback(
    (rowId: string) => {
      return dragState.isDragging && dragState.sourceRowId === rowId;
    },
    [dragState.isDragging, dragState.sourceRowId]
  );

  // Check if a row is a target
  const isTargetRow = useCallback(
    (rowId: string) => {
      return dragState.isDragging && dragState.targetRowIds.includes(rowId);
    },
    [dragState.isDragging, dragState.targetRowIds]
  );

  // Global mouse up handler
  useEffect(() => {
    const handleMouseUp = () => {
      if (dragState.isDragging) {
        endDrag();
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && dragState.isDragging) {
        cancelDrag();
      }
    };

    document.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [dragState.isDragging, endDrag, cancelDrag]);

  return {
    dragState,
    startDrag,
    updateDragTarget,
    endDrag,
    cancelDrag,
    isSourceRow,
    isTargetRow,
    registerRow,
  };
}
