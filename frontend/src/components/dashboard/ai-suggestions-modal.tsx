"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Loader2, Sparkles, Check, AlertCircle, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { formatCurrency, cn } from "@/lib/utils";

// Types for AI suggestions
interface AISuggestion {
  field: string;
  current_value: string;
  suggested_value: string;
  reasoning: string;
  confidence: number;
}

interface SuggestionsResponse {
  message?: string;
  suggestions: AISuggestion[];
  reasoning: string;
  new_confidence: number;
  similar_count?: number;
  patterns_count?: number;
  transaction?: {
    transaction_id: string;
    description: string;
    amount: number;
    confidence: number;
    classified_entity?: string;
    accounting_category?: string;
    subcategory?: string;
  };
}

interface AISuggestionsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  transactionId: string | null;
  transaction?: {
    id: string;
    description: string;
    amount: number;
    currency?: string;
    confidence_score?: number;
    category?: string;
    entity_name?: string;
  } | null;
  onSuggestionsApplied: () => void;
  entityOptions?: string[];
}

// Field display names
const fieldLabels: Record<string, string> = {
  classified_entity: "Business Entity",
  accounting_category: "Accounting Category",
  subcategory: "Subcategory",
  justification: "Justification",
  category: "Category",
};

// Accounting category options
const accountingCategories = [
  "OPERATING_EXPENSE",
  "CAPITAL_EXPENSE",
  "REVENUE",
  "COST_OF_GOODS_SOLD",
  "PAYROLL",
  "TAX",
  "INTEREST",
  "DEPRECIATION",
  "OTHER",
];

export function AISuggestionsModal({
  open,
  onOpenChange,
  transactionId,
  transaction,
  onSuggestionsApplied,
  entityOptions = [],
}: AISuggestionsModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestionsData, setSuggestionsData] = useState<SuggestionsResponse | null>(null);

  // Track selected suggestions and edited values
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<number>>(new Set());
  const [editedValues, setEditedValues] = useState<Record<number, string>>({});

  // Fetch suggestions when modal opens
  useEffect(() => {
    if (open && transactionId) {
      fetchSuggestions();
    } else {
      // Reset state when closed
      setSuggestionsData(null);
      setSelectedSuggestions(new Set());
      setEditedValues({});
      setError(null);
    }
  }, [open, transactionId]);

  async function fetchSuggestions() {
    if (!transactionId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/ai/get-suggestions?transaction_id=${transactionId}`);
      const data = await response.json();

      if (data.suggestions && data.suggestions.length > 0) {
        setSuggestionsData(data);
        // Pre-select all suggestions by default
        setSelectedSuggestions(new Set(data.suggestions.map((_: AISuggestion, i: number) => i)));
        // Initialize edited values with suggested values
        const initialValues: Record<number, string> = {};
        data.suggestions.forEach((s: AISuggestion, i: number) => {
          initialValues[i] = s.suggested_value;
        });
        setEditedValues(initialValues);
      } else if (data.message) {
        // High confidence - no suggestions needed
        setSuggestionsData({ ...data, suggestions: [] });
      } else {
        setError("No suggestions available for this transaction");
      }
    } catch {
      setError("Failed to fetch AI suggestions");
    } finally {
      setIsLoading(false);
    }
  }

  // Toggle suggestion selection
  function toggleSuggestion(index: number) {
    setSelectedSuggestions((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }

  // Select/Deselect all
  function selectAll(select: boolean) {
    if (select && suggestionsData?.suggestions) {
      setSelectedSuggestions(new Set(suggestionsData.suggestions.map((_, i) => i)));
    } else {
      setSelectedSuggestions(new Set());
    }
  }

  // Update edited value
  function updateEditedValue(index: number, value: string) {
    setEditedValues((prev) => ({ ...prev, [index]: value }));
  }

  // Apply selected suggestions
  async function applySelectedSuggestions() {
    if (!transactionId || !suggestionsData || selectedSuggestions.size === 0) return;

    setIsApplying(true);
    let successCount = 0;
    let errorCount = 0;

    try {
      for (const index of Array.from(selectedSuggestions)) {
        const suggestion = suggestionsData.suggestions[index];
        const editedValue = editedValues[index] || suggestion.suggested_value;

        const response = await fetch("/api/ai/apply-suggestion", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            transaction_id: transactionId,
            suggestion: {
              ...suggestion,
              suggested_value: editedValue,
            },
          }),
        });

        const data = await response.json();
        if (data.success) {
          successCount++;
        } else {
          errorCount++;
        }
      }

      if (successCount > 0) {
        toast.success(`Applied ${successCount} suggestion${successCount !== 1 ? "s" : ""}`);
        onSuggestionsApplied();
        onOpenChange(false);
      }
      if (errorCount > 0) {
        toast.error(`Failed to apply ${errorCount} suggestion${errorCount !== 1 ? "s" : ""}`);
      }
    } catch {
      toast.error("Failed to apply suggestions");
    } finally {
      setIsApplying(false);
    }
  }

  // Get confidence badge
  function getConfidenceBadge(score: number) {
    const percent = Math.round(score * 100);
    if (percent >= 80) {
      return (
        <Badge className="bg-green-600 hover:bg-green-700">
          {percent}%
        </Badge>
      );
    }
    if (percent >= 55) {
      return (
        <Badge className="bg-yellow-600 hover:bg-yellow-700">
          {percent}%
        </Badge>
      );
    }
    return (
      <Badge className="bg-red-600 hover:bg-red-700">{percent}%</Badge>
    );
  }

  // Render input for suggestion value based on field type
  function renderValueInput(suggestion: AISuggestion, index: number) {
    const value = editedValues[index] ?? suggestion.suggested_value;
    const isSelected = selectedSuggestions.has(index);

    if (suggestion.field === "classified_entity" && entityOptions.length > 0) {
      return (
        <Select
          value={value}
          onValueChange={(v) => updateEditedValue(index, v)}
          disabled={!isSelected}
        >
          <SelectTrigger className="h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {entityOptions.map((entity) => (
              <SelectItem key={entity} value={entity}>
                {entity}
              </SelectItem>
            ))}
            {!entityOptions.includes(value) && (
              <SelectItem value={value}>{value}</SelectItem>
            )}
          </SelectContent>
        </Select>
      );
    }

    if (suggestion.field === "accounting_category") {
      return (
        <Select
          value={value}
          onValueChange={(v) => updateEditedValue(index, v)}
          disabled={!isSelected}
        >
          <SelectTrigger className="h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {accountingCategories.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {cat.replace(/_/g, " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
    }

    // Default: text input
    return (
      <Input
        value={value}
        onChange={(e) => updateEditedValue(index, e.target.value)}
        disabled={!isSelected}
        className="h-8"
      />
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            AI Smart Recommendations
          </DialogTitle>
          <DialogDescription>
            Review and apply AI-generated suggestions to improve classification
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-auto space-y-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <p className="mt-4 text-muted-foreground">
                Analyzing transaction with AI...
              </p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12">
              <AlertCircle className="h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-muted-foreground">{error}</p>
              <Button variant="outline" className="mt-4" onClick={fetchSuggestions}>
                Try Again
              </Button>
            </div>
          ) : suggestionsData ? (
            <>
              {/* Transaction Info */}
              <div className="rounded-lg border bg-muted/30 p-4">
                <h4 className="font-medium mb-2">Transaction</h4>
                <p className="text-sm truncate">
                  {transaction?.description || suggestionsData.transaction?.description}
                </p>
                <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                  <span>
                    Amount:{" "}
                    <span className={cn(
                      "font-medium",
                      (transaction?.amount || 0) >= 0 ? "text-green-600" : "text-red-600"
                    )}>
                      {formatCurrency(
                        transaction?.amount || suggestionsData.transaction?.amount || 0,
                        transaction?.currency
                      )}
                    </span>
                  </span>
                  <span>
                    Current Confidence:{" "}
                    {getConfidenceBadge(
                      transaction?.confidence_score ||
                      suggestionsData.transaction?.confidence ||
                      0
                    )}
                  </span>
                </div>
              </div>

              {/* AI Assessment */}
              {suggestionsData.reasoning && (
                <div className="rounded-lg border bg-blue-50 dark:bg-blue-950/20 p-4">
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />
                    AI Assessment
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    {suggestionsData.reasoning}
                  </p>
                  {suggestionsData.new_confidence > 0 && (
                    <div className="mt-2 text-sm">
                      New Confidence: {getConfidenceBadge(suggestionsData.new_confidence)}
                    </div>
                  )}
                </div>
              )}

              {/* High confidence message */}
              {suggestionsData.message && suggestionsData.suggestions.length === 0 && (
                <div className="rounded-lg border bg-green-50 dark:bg-green-950/20 p-4">
                  <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                    <Check className="h-5 w-5" />
                    <span className="font-medium">{suggestionsData.message}</span>
                  </div>
                </div>
              )}

              {/* Suggestions List */}
              {suggestionsData.suggestions.length > 0 && (
                <>
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium">
                      Suggestions ({selectedSuggestions.size} of {suggestionsData.suggestions.length} selected)
                    </h4>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => selectAll(true)}
                      >
                        Select All
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => selectAll(false)}
                      >
                        Deselect All
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {suggestionsData.suggestions.map((suggestion, index) => (
                      <div
                        key={index}
                        className={cn(
                          "rounded-lg border p-4 transition-colors",
                          selectedSuggestions.has(index)
                            ? "border-primary bg-primary/5"
                            : "bg-muted/30"
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <Checkbox
                            checked={selectedSuggestions.has(index)}
                            onCheckedChange={() => toggleSuggestion(index)}
                            className="mt-1"
                          />
                          <div className="flex-1 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-medium">
                                {fieldLabels[suggestion.field] || suggestion.field}
                              </span>
                              {getConfidenceBadge(suggestion.confidence)}
                            </div>

                            <div className="flex items-center gap-2 text-sm">
                              <span className="text-muted-foreground">
                                {suggestion.current_value || "Not set"}
                              </span>
                              <ArrowRight className="h-4 w-4 text-muted-foreground" />
                              <div className="flex-1 max-w-[200px]">
                                {renderValueInput(suggestion, index)}
                              </div>
                            </div>

                            <p className="text-xs text-muted-foreground italic">
                              {suggestion.reasoning}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Apply Button */}
                  <div className="pt-4 border-t">
                    <Button
                      className="w-full"
                      onClick={applySelectedSuggestions}
                      disabled={selectedSuggestions.size === 0 || isApplying}
                    >
                      {isApplying ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Check className="mr-2 h-4 w-4" />
                      )}
                      Apply {selectedSuggestions.size} Selected Suggestion{selectedSuggestions.size !== 1 ? "s" : ""}
                    </Button>
                  </div>
                </>
              )}
            </>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
