"use client";

import { useState, useCallback, useRef } from "react";
import { transactions, type Transaction } from "@/lib/api";
import { toast } from "sonner";

// Represents a single edit operation
export interface EditOperation {
  transactionId: string;
  field: string;
  oldValue: string;
  newValue: string;
  timestamp: number;
}

// Batch multiple edits together (for bulk operations)
export interface EditBatch {
  operations: EditOperation[];
  timestamp: number;
  description: string;
}

const MAX_UNDO_STACK_SIZE = 50;

export function useUndoRedo() {
  const [undoStack, setUndoStack] = useState<EditBatch[]>([]);
  const [redoStack, setRedoStack] = useState<EditBatch[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  // Track pending batch for grouping rapid edits
  const pendingBatchRef = useRef<EditBatch | null>(null);
  const batchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Push a single edit to the undo stack
  const pushEdit = useCallback(
    (
      transactionId: string,
      field: string,
      oldValue: string,
      newValue: string,
      description?: string
    ) => {
      const operation: EditOperation = {
        transactionId,
        field,
        oldValue,
        newValue,
        timestamp: Date.now(),
      };

      // Create a new batch for this edit
      const batch: EditBatch = {
        operations: [operation],
        timestamp: Date.now(),
        description: description || `Updated ${field}`,
      };

      setUndoStack((prev) => {
        const newStack = [...prev, batch];
        // Keep stack size limited
        if (newStack.length > MAX_UNDO_STACK_SIZE) {
          return newStack.slice(-MAX_UNDO_STACK_SIZE);
        }
        return newStack;
      });

      // Clear redo stack when a new edit is made
      setRedoStack([]);
    },
    []
  );

  // Push a batch of edits (for bulk operations)
  const pushBatch = useCallback(
    (operations: EditOperation[], description: string) => {
      if (operations.length === 0) return;

      const batch: EditBatch = {
        operations,
        timestamp: Date.now(),
        description,
      };

      setUndoStack((prev) => {
        const newStack = [...prev, batch];
        if (newStack.length > MAX_UNDO_STACK_SIZE) {
          return newStack.slice(-MAX_UNDO_STACK_SIZE);
        }
        return newStack;
      });

      // Clear redo stack when a new edit is made
      setRedoStack([]);
    },
    []
  );

  // Undo the last batch of edits
  const undo = useCallback(async (): Promise<boolean> => {
    if (undoStack.length === 0 || isProcessing) return false;

    setIsProcessing(true);

    try {
      const lastBatch = undoStack[undoStack.length - 1];

      // Apply reverse operations
      for (const op of lastBatch.operations) {
        const result = await transactions.updateField(
          op.transactionId,
          op.field,
          op.oldValue
        );
        if (!result.success) {
          throw new Error(`Failed to undo ${op.field} change`);
        }
      }

      // Move batch from undo to redo stack
      setUndoStack((prev) => prev.slice(0, -1));
      setRedoStack((prev) => [...prev, lastBatch]);

      toast.success(`Undone: ${lastBatch.description}`);
      return true;
    } catch (error) {
      console.error("Undo failed:", error);
      toast.error("Failed to undo changes");
      return false;
    } finally {
      setIsProcessing(false);
    }
  }, [undoStack, isProcessing]);

  // Redo the last undone batch
  const redo = useCallback(async (): Promise<boolean> => {
    if (redoStack.length === 0 || isProcessing) return false;

    setIsProcessing(true);

    try {
      const lastBatch = redoStack[redoStack.length - 1];

      // Apply forward operations
      for (const op of lastBatch.operations) {
        const result = await transactions.updateField(
          op.transactionId,
          op.field,
          op.newValue
        );
        if (!result.success) {
          throw new Error(`Failed to redo ${op.field} change`);
        }
      }

      // Move batch from redo to undo stack
      setRedoStack((prev) => prev.slice(0, -1));
      setUndoStack((prev) => [...prev, lastBatch]);

      toast.success(`Redone: ${lastBatch.description}`);
      return true;
    } catch (error) {
      console.error("Redo failed:", error);
      toast.error("Failed to redo changes");
      return false;
    } finally {
      setIsProcessing(false);
    }
  }, [redoStack, isProcessing]);

  // Clear all history
  const clearHistory = useCallback(() => {
    setUndoStack([]);
    setRedoStack([]);
  }, []);

  return {
    pushEdit,
    pushBatch,
    undo,
    redo,
    clearHistory,
    canUndo: undoStack.length > 0 && !isProcessing,
    canRedo: redoStack.length > 0 && !isProcessing,
    isProcessing,
    undoCount: undoStack.length,
    redoCount: redoStack.length,
  };
}
