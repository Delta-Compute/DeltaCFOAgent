"use client";

import { useState, useMemo } from "react";
import { Check, ChevronsUpDown, Building2, User, Store, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { type BusinessEntity } from "@/lib/api";

// Entity type icons
const entityIcons: Record<string, typeof Building2> = {
  internal: Building2,
  customer: User,
  vendor: Store,
  partner: Building2,
  exchange: Building2,
  bank: Building2,
};

interface EntitySelectorProps {
  value?: string;
  entities?: BusinessEntity[];
  onChange?: (entity: BusinessEntity | null) => void;
  onValueChange?: (value: string | undefined) => void;
  placeholder?: string;
  disabled?: boolean;
  allowClear?: boolean;
  filterType?: string;
  isLoading?: boolean;
  className?: string;
}

export function EntitySelector({
  value,
  entities = [],
  onChange,
  onValueChange,
  placeholder = "Select entity...",
  disabled = false,
  allowClear = true,
  filterType,
  isLoading = false,
  className,
}: EntitySelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  // Filter entities by type if specified
  const filteredByType = useMemo(() => {
    if (!filterType) return entities;
    return entities.filter((e) => e.type === filterType);
  }, [entities, filterType]);

  // Find selected entity
  const selectedEntity = filteredByType.find((e) => e.id === value || e.name === value);

  // Filter entities by search
  const filteredEntities = search
    ? filteredByType.filter((e) =>
        e.name.toLowerCase().includes(search.toLowerCase())
      )
    : filteredByType;

  function handleSelect(entity: BusinessEntity | null) {
    onChange?.(entity);
    onValueChange?.(entity?.id);
    setOpen(false);
    setSearch("");
  }

  const Icon = selectedEntity
    ? entityIcons[selectedEntity.type || "internal"]
    : Building2;

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn("w-full justify-between", className)}
        >
          <span className="flex items-center gap-2 truncate">
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : selectedEntity ? (
              <>
                <Icon className="h-4 w-4 text-muted-foreground" />
                {selectedEntity.name}
              </>
            ) : (
              <span className="text-muted-foreground">{placeholder}</span>
            )}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-[300px] p-0" align="start">
        <div className="p-2">
          <Input
            placeholder="Search entities..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8"
          />
        </div>
        <DropdownMenuSeparator />
        <div className="max-h-[300px] overflow-y-auto">
          {allowClear && selectedEntity && (
            <>
              <DropdownMenuItem
                onClick={() => handleSelect(null)}
                className="text-muted-foreground"
              >
                Clear selection
              </DropdownMenuItem>
              <DropdownMenuSeparator />
            </>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="ml-2 text-sm text-muted-foreground">
                Loading...
              </span>
            </div>
          ) : filteredEntities.length === 0 ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No entities found.
            </div>
          ) : (
            <>
              {/* Group by type */}
              {["internal", "customer", "vendor", "partner"].map((entityType) => {
                const typeEntities = filteredEntities.filter(
                  (e) => e.type === entityType
                );
                if (typeEntities.length === 0) return null;

                const TypeIcon = entityIcons[entityType];

                return (
                  <div key={entityType}>
                    <DropdownMenuLabel className="flex items-center gap-2 text-xs uppercase">
                      <TypeIcon className="h-3 w-3" />
                      {entityType}
                    </DropdownMenuLabel>
                    {typeEntities.map((entity) => (
                      <DropdownMenuItem
                        key={entity.id}
                        onClick={() => handleSelect(entity)}
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            selectedEntity?.id === entity.id
                              ? "opacity-100"
                              : "opacity-0"
                          )}
                        />
                        {entity.name}
                      </DropdownMenuItem>
                    ))}
                  </div>
                );
              })}
            </>
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
