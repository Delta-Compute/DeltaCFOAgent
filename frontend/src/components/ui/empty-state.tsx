import { ReactNode } from "react";
import { LucideIcon, FileQuestion, Inbox, Search, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
  children?: ReactNode;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
  children,
}: EmptyStateProps) {
  return (
    <div className={cn("empty-state", className)}>
      <div className="empty-state-icon">
        <Icon className="h-full w-full" />
      </div>
      <h3 className="empty-state-title">{title}</h3>
      {description && (
        <p className="empty-state-description">{description}</p>
      )}
      {action && (
        <Button onClick={action.onClick} className="mt-4">
          {action.label}
        </Button>
      )}
      {children}
    </div>
  );
}

// Pre-configured empty states for common use cases

export function NoDataFound({
  entityName = "items",
  onAdd,
}: {
  entityName?: string;
  onAdd?: () => void;
}) {
  return (
    <EmptyState
      icon={Inbox}
      title={`No ${entityName} found`}
      description={`You don't have any ${entityName} yet. Start by adding your first one.`}
      action={
        onAdd
          ? {
              label: `Add ${entityName.replace(/s$/, "")}`,
              onClick: onAdd,
            }
          : undefined
      }
    />
  );
}

export function NoSearchResults({ query }: { query: string }) {
  return (
    <EmptyState
      icon={Search}
      title="No results found"
      description={`No items match "${query}". Try adjusting your search or filters.`}
    />
  );
}

export function NoMatchesFound() {
  return (
    <EmptyState
      icon={FileQuestion}
      title="No matches found"
      description="There are no pending matches to review. Run matching to find new matches."
    />
  );
}

export function ErrorState({
  title = "Failed to load data",
  description = "Something went wrong while loading. Please try again.",
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <EmptyState
      icon={AlertCircle}
      title={title}
      description={description}
      action={
        onRetry
          ? {
              label: "Try again",
              onClick: onRetry,
            }
          : undefined
      }
    />
  );
}

export function LoadingState({
  message = "Loading...",
  className,
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-12", className)}>
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
