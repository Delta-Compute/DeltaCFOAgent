"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Edit, Check } from "lucide-react";
import { toast } from "sonner";

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

interface BulkEditModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedIds: string[];
  entityOptions: string[];
  onUpdated: () => void;
}

export function BulkEditModal({
  open,
  onOpenChange,
  selectedIds,
  entityOptions,
  onUpdated,
}: BulkEditModalProps) {
  const [isApplying, setIsApplying] = useState(false);
  const [entity, setEntity] = useState("");
  const [category, setCategory] = useState("");
  const [subcategory, setSubcategory] = useState("");
  const [justification, setJustification] = useState("");

  // Reset form when modal closes
  function handleOpenChange(newOpen: boolean) {
    if (!newOpen) {
      setEntity("");
      setCategory("");
      setSubcategory("");
      setJustification("");
    }
    onOpenChange(newOpen);
  }

  async function handleApply() {
    if (!entity && !category && !subcategory && !justification) {
      toast.warning("Please select at least one field to update");
      return;
    }

    setIsApplying(true);

    try {
      // Build updates array
      const updates: Array<{ transaction_id: string; field: string; value: string }> = [];

      selectedIds.forEach((txId) => {
        if (entity) {
          updates.push({
            transaction_id: txId,
            field: "classified_entity",
            value: entity,
          });
        }
        if (category) {
          updates.push({
            transaction_id: txId,
            field: "accounting_category",
            value: category,
          });
        }
        if (subcategory) {
          updates.push({
            transaction_id: txId,
            field: "subcategory",
            value: subcategory,
          });
        }
        if (justification) {
          updates.push({
            transaction_id: txId,
            field: "justification",
            value: justification,
          });
        }
      });

      const response = await fetch("/api/bulk_update_transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ updates }),
      });

      const data = await response.json();

      if (data.success) {
        toast.success(`Updated ${selectedIds.length} transaction(s)`);
        onUpdated();
        handleOpenChange(false);
      } else {
        toast.error(data.error || "Failed to update transactions");
      }
    } catch {
      toast.error("Failed to update transactions");
    } finally {
      setIsApplying(false);
    }
  }

  const hasChanges = entity || category || subcategory || justification;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Edit className="h-5 w-5" />
            Bulk Edit Transactions
          </DialogTitle>
          <DialogDescription>
            Apply changes to {selectedIds.length} selected transaction(s).
            Only filled fields will be updated.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Entity */}
          <div className="space-y-2">
            <Label htmlFor="bulk-entity">Business Entity</Label>
            <Select value={entity} onValueChange={setEntity}>
              <SelectTrigger id="bulk-entity">
                <SelectValue placeholder="Select entity..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">-- No change --</SelectItem>
                {entityOptions.map((ent) => (
                  <SelectItem key={ent} value={ent}>
                    {ent}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Category */}
          <div className="space-y-2">
            <Label htmlFor="bulk-category">Accounting Category</Label>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger id="bulk-category">
                <SelectValue placeholder="Select category..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">-- No change --</SelectItem>
                {accountingCategories.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat.replace(/_/g, " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Subcategory */}
          <div className="space-y-2">
            <Label htmlFor="bulk-subcategory">Subcategory</Label>
            <Input
              id="bulk-subcategory"
              value={subcategory}
              onChange={(e) => setSubcategory(e.target.value)}
              placeholder="Enter subcategory..."
            />
          </div>

          {/* Justification */}
          <div className="space-y-2">
            <Label htmlFor="bulk-justification">Justification</Label>
            <Input
              id="bulk-justification"
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="Enter justification..."
            />
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleApply} disabled={!hasChanges || isApplying}>
            {isApplying ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Check className="mr-2 h-4 w-4" />
            )}
            Apply to {selectedIds.length} Transaction(s)
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
