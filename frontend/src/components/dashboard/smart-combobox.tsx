"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Check, Sparkles, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { suggestions as suggestionsApi } from "@/lib/api";

export interface SmartComboboxProps {
  value: string;
  options: string[];
  placeholder?: string;
  fieldType: string;
  transactionId: string;
  onSelect: (value: string) => void;
  onCancel: () => void;
  onOpenAISuggestions?: () => void;
  className?: string;
}

export function SmartCombobox({
  value,
  options,
  placeholder = "Type or select...",
  fieldType,
  transactionId,
  onSelect,
  onCancel,
  onOpenAISuggestions,
  className,
}: SmartComboboxProps) {
  const [inputValue, setInputValue] = useState(value);
  const [isOpen, setIsOpen] = useState(true);
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);
  const [isLoadingAI, setIsLoadingAI] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Filter options based on input
  const filteredOptions = options.filter((opt) =>
    opt.toLowerCase().includes(inputValue.toLowerCase())
  );

  // Combine all items for keyboard navigation
  const allItems = [
    ...aiSuggestions.map((s) => ({ type: "ai" as const, value: s })),
    ...filteredOptions.map((o) => ({ type: "option" as const, value: o })),
  ];

  // Fetch AI suggestions with debounce
  const fetchAISuggestions = useCallback(
    async (searchValue: string) => {
      if (!searchValue || searchValue.length < 2) {
        setAiSuggestions([]);
        return;
      }

      setIsLoadingAI(true);
      try {
        const result = await suggestionsApi.get({
          field_type: fieldType === "category" ? "similar_accounting" :
                      fieldType === "subcategory" ? "similar_subcategory" :
                      fieldType === "entity_name" ? "similar_entities" : fieldType,
          transaction_id: transactionId,
          current_value: searchValue,
          value: searchValue,
        });

        if (result.success && result.data?.suggestions) {
          // Filter out suggestions that are already in options
          const uniqueSuggestions = result.data.suggestions.filter(
            (s) => !options.some((o) => o.toLowerCase() === s.toLowerCase())
          );
          setAiSuggestions(uniqueSuggestions.slice(0, 5));
        }
      } catch (error) {
        console.error("Failed to fetch AI suggestions:", error);
      } finally {
        setIsLoadingAI(false);
      }
    },
    [fieldType, transactionId, options]
  );

  // Debounced input handler
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      fetchAISuggestions(inputValue);
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [inputValue, fetchAISuggestions]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < allItems.length - 1 ? prev + 1 : prev
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;
      case "Enter":
        e.preventDefault();
        if (highlightedIndex >= 0 && allItems[highlightedIndex]) {
          onSelect(allItems[highlightedIndex].value);
        } else if (inputValue.trim()) {
          onSelect(inputValue.trim());
        }
        break;
      case "Escape":
        e.preventDefault();
        onCancel();
        break;
      case "Tab":
        e.preventDefault();
        if (highlightedIndex >= 0 && allItems[highlightedIndex]) {
          onSelect(allItems[highlightedIndex].value);
        } else if (inputValue.trim()) {
          onSelect(inputValue.trim());
        } else {
          onCancel();
        }
        break;
    }
  };

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll("[data-item]");
      items[highlightedIndex]?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightedIndex]);

  return (
    <div className={cn("relative", className)} onClick={(e) => e.stopPropagation()}>
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={(e) => {
          setInputValue(e.target.value);
          setHighlightedIndex(-1);
        }}
        onKeyDown={handleKeyDown}
        onBlur={(e) => {
          // Delay to allow click on dropdown items
          setTimeout(() => {
            if (!listRef.current?.contains(document.activeElement)) {
              if (inputValue.trim() && inputValue !== value) {
                onSelect(inputValue.trim());
              } else {
                onCancel();
              }
            }
          }, 150);
        }}
        placeholder={placeholder}
        className="h-7 w-36 px-2 text-xs border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-ring"
      />

      {isOpen && (
        <div
          ref={listRef}
          className="absolute top-8 left-0 z-50 w-48 max-h-64 overflow-auto rounded-md border bg-popover shadow-md"
        >
          {/* AI Suggestions Section */}
          {onOpenAISuggestions && (
            <button
              type="button"
              className="w-full px-2 py-1.5 text-xs text-primary font-medium flex items-center gap-1 hover:bg-accent border-b"
              onMouseDown={(e) => {
                e.preventDefault();
                onOpenAISuggestions();
              }}
            >
              <Sparkles className="h-3 w-3" />
              AI Smart Suggestions
            </button>
          )}

          {/* Loading indicator */}
          {isLoadingAI && (
            <div className="px-2 py-1.5 text-xs text-muted-foreground flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading suggestions...
            </div>
          )}

          {/* AI Suggestions */}
          {aiSuggestions.length > 0 && (
            <>
              <div className="px-2 py-1 text-[10px] text-muted-foreground uppercase tracking-wider bg-muted/50">
                AI Suggestions
              </div>
              {aiSuggestions.map((suggestion, index) => {
                const itemIndex = index;
                return (
                  <button
                    key={`ai-${suggestion}`}
                    type="button"
                    data-item
                    className={cn(
                      "w-full px-2 py-1.5 text-xs flex items-center gap-1 hover:bg-accent text-left",
                      highlightedIndex === itemIndex && "bg-accent"
                    )}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      onSelect(suggestion);
                    }}
                    onMouseEnter={() => setHighlightedIndex(itemIndex)}
                  >
                    <Sparkles className="h-3 w-3 text-primary shrink-0" />
                    <span className="truncate">{suggestion}</span>
                  </button>
                );
              })}
            </>
          )}

          {/* Existing Options */}
          {filteredOptions.length > 0 && (
            <>
              <div className="px-2 py-1 text-[10px] text-muted-foreground uppercase tracking-wider bg-muted/50">
                Existing Values
              </div>
              {filteredOptions.slice(0, 10).map((option, index) => {
                const itemIndex = aiSuggestions.length + index;
                const isSelected = option === value;
                return (
                  <button
                    key={option}
                    type="button"
                    data-item
                    className={cn(
                      "w-full px-2 py-1.5 text-xs flex items-center gap-1 hover:bg-accent text-left",
                      highlightedIndex === itemIndex && "bg-accent",
                      isSelected && "text-primary font-medium"
                    )}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      onSelect(option);
                    }}
                    onMouseEnter={() => setHighlightedIndex(itemIndex)}
                  >
                    {isSelected && <Check className="h-3 w-3 shrink-0" />}
                    <span className="truncate">{option}</span>
                  </button>
                );
              })}
            </>
          )}

          {/* Custom value hint */}
          {inputValue.trim() &&
            !filteredOptions.some(
              (o) => o.toLowerCase() === inputValue.trim().toLowerCase()
            ) &&
            !aiSuggestions.some(
              (s) => s.toLowerCase() === inputValue.trim().toLowerCase()
            ) && (
              <button
                type="button"
                className="w-full px-2 py-1.5 text-xs flex items-center gap-1 hover:bg-accent text-left border-t text-muted-foreground"
                onMouseDown={(e) => {
                  e.preventDefault();
                  onSelect(inputValue.trim());
                }}
              >
                Press Enter to use &quot;{inputValue.trim()}&quot;
              </button>
            )}

          {/* Empty state */}
          {filteredOptions.length === 0 &&
            aiSuggestions.length === 0 &&
            !isLoadingAI &&
            !inputValue.trim() && (
              <div className="px-2 py-3 text-xs text-muted-foreground text-center">
                Start typing to search...
              </div>
            )}
        </div>
      )}
    </div>
  );
}
