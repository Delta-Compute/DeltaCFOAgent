"use client";

import { useState } from "react";
import { AlertTriangle, Info, AlertCircle, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type ConfirmDialogVariant = "default" | "destructive" | "warning" | "success";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void | Promise<void>;
  onCancel?: () => void;
  variant?: ConfirmDialogVariant;
  isLoading?: boolean;
}

const variantConfig: Record<
  ConfirmDialogVariant,
  {
    icon: typeof AlertTriangle;
    iconClass: string;
    buttonVariant: "default" | "destructive" | "outline" | "secondary";
  }
> = {
  default: {
    icon: Info,
    iconClass: "text-primary",
    buttonVariant: "default",
  },
  destructive: {
    icon: AlertCircle,
    iconClass: "text-destructive",
    buttonVariant: "destructive",
  },
  warning: {
    icon: AlertTriangle,
    iconClass: "text-yellow-500",
    buttonVariant: "default",
  },
  success: {
    icon: CheckCircle,
    iconClass: "text-green-500",
    buttonVariant: "default",
  },
};

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  onConfirm,
  onCancel,
  variant = "default",
  isLoading = false,
}: ConfirmDialogProps) {
  const [loading, setLoading] = useState(false);
  const config = variantConfig[variant];
  const Icon = config.icon;

  async function handleConfirm() {
    setLoading(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (error) {
      console.error("Confirm action failed:", error);
    } finally {
      setLoading(false);
    }
  }

  function handleCancel() {
    onCancel?.();
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <div className="flex items-center gap-4">
            <div
              className={cn(
                "flex h-12 w-12 items-center justify-center rounded-full bg-muted"
              )}
            >
              <Icon className={cn("h-6 w-6", config.iconClass)} />
            </div>
            <div>
              <DialogTitle>{title}</DialogTitle>
              {description && (
                <DialogDescription className="mt-1">
                  {description}
                </DialogDescription>
              )}
            </div>
          </div>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={handleCancel} disabled={loading || isLoading}>
            {cancelText}
          </Button>
          <Button
            variant={config.buttonVariant}
            onClick={handleConfirm}
            disabled={loading || isLoading}
          >
            {loading || isLoading ? "Please wait..." : confirmText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Hook for easier usage
export function useConfirmDialog() {
  const [state, setState] = useState<{
    open: boolean;
    title: string;
    description?: string;
    confirmText?: string;
    cancelText?: string;
    variant?: ConfirmDialogVariant;
    onConfirm: () => void | Promise<void>;
    onCancel?: () => void;
  }>({
    open: false,
    title: "",
    onConfirm: () => {},
  });

  function confirm(options: {
    title: string;
    description?: string;
    confirmText?: string;
    cancelText?: string;
    variant?: ConfirmDialogVariant;
  }): Promise<boolean> {
    return new Promise((resolve) => {
      setState({
        ...options,
        open: true,
        onConfirm: () => resolve(true),
        onCancel: () => resolve(false),
      });
    });
  }

  function close() {
    setState((prev) => ({ ...prev, open: false }));
  }

  return {
    confirm,
    close,
    dialogProps: {
      open: state.open,
      onOpenChange: (open: boolean) => setState((prev) => ({ ...prev, open })),
      title: state.title,
      description: state.description,
      confirmText: state.confirmText,
      cancelText: state.cancelText,
      variant: state.variant,
      onConfirm: state.onConfirm,
      onCancel: state.onCancel,
    },
  };
}
