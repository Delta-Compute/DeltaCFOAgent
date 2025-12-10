"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Brain,
  Plus,
  Search,
  RefreshCw,
  Edit,
  Trash2,
  MoreHorizontal,
  Sparkles,
  CheckCircle2,
  Loader2,
  Filter,
} from "lucide-react";
import { toast } from "sonner";

import {
  knowledge,
  type ClassificationPattern,
  type CreatePatternData,
} from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Switch } from "@/components/ui/switch";
import { ErrorState, LoadingState } from "@/components/ui/empty-state";
import { StatsCard, StatsGrid } from "@/components/dashboard/stats-card";

// Category options
const categories = [
  "Revenue",
  "Cost of Goods Sold",
  "Operating Expense",
  "Payroll Expense",
  "Marketing Expense",
  "Administrative Expense",
  "Rent & Utilities",
  "Professional Services",
  "Travel & Entertainment",
  "Other Income",
  "Other Expense",
  "Tax",
  "Interest",
  "Depreciation",
];

export default function TenantKnowledgePage() {
  // State
  const [patterns, setPatterns] = useState<ClassificationPattern[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  // Dialogs
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedPattern, setSelectedPattern] =
    useState<ClassificationPattern | null>(null);

  // Form state
  const [formData, setFormData] = useState<CreatePatternData>({
    pattern: "",
    category: "",
    subcategory: "",
    confidence: 0.8,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // Load patterns
  const loadPatterns = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await knowledge.list();
      if (result.success && result.data) {
        setPatterns(result.data);
      } else {
        throw new Error(result.error?.message || "Failed to load patterns");
      }
    } catch (err) {
      console.error("Failed to load patterns:", err);
      setError(err instanceof Error ? err.message : "Failed to load patterns");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPatterns();
  }, [loadPatterns]);

  // Filter patterns
  const filteredPatterns = patterns.filter((pattern) => {
    const matchesSearch =
      search === "" ||
      pattern.pattern.toLowerCase().includes(search.toLowerCase()) ||
      pattern.category.toLowerCase().includes(search.toLowerCase()) ||
      (pattern.subcategory?.toLowerCase().includes(search.toLowerCase()) ??
        false);

    const matchesCategory =
      categoryFilter === "all" || pattern.category === categoryFilter;

    return matchesSearch && matchesCategory;
  });

  // Stats
  const stats = {
    total: patterns.length,
    active: patterns.filter((p) => p.is_active).length,
    categories: new Set(patterns.map((p) => p.category)).size,
    avgConfidence:
      patterns.length > 0
        ? patterns.reduce((sum, p) => sum + p.confidence, 0) / patterns.length
        : 0,
  };

  // Create pattern
  async function handleCreate() {
    setIsSubmitting(true);
    try {
      const result = await knowledge.create(formData);
      if (result.success) {
        toast.success("Pattern created successfully");
        setShowCreateDialog(false);
        resetForm();
        loadPatterns();
      } else {
        toast.error(result.error?.message || "Failed to create pattern");
      }
    } catch {
      toast.error("Failed to create pattern");
    } finally {
      setIsSubmitting(false);
    }
  }

  // Update pattern
  async function handleUpdate() {
    if (!selectedPattern) return;
    setIsSubmitting(true);
    try {
      const result = await knowledge.update(selectedPattern.id, formData);
      if (result.success) {
        toast.success("Pattern updated successfully");
        setShowEditDialog(false);
        setSelectedPattern(null);
        resetForm();
        loadPatterns();
      } else {
        toast.error(result.error?.message || "Failed to update pattern");
      }
    } catch {
      toast.error("Failed to update pattern");
    } finally {
      setIsSubmitting(false);
    }
  }

  // Delete pattern
  async function handleDelete() {
    if (!selectedPattern) return;
    setIsSubmitting(true);
    try {
      const result = await knowledge.delete(selectedPattern.id);
      if (result.success) {
        toast.success("Pattern deleted successfully");
        setShowDeleteDialog(false);
        setSelectedPattern(null);
        loadPatterns();
      } else {
        toast.error(result.error?.message || "Failed to delete pattern");
      }
    } catch {
      toast.error("Failed to delete pattern");
    } finally {
      setIsSubmitting(false);
    }
  }

  // Toggle active status
  async function toggleActive(pattern: ClassificationPattern) {
    try {
      const result = await knowledge.update(pattern.id, {
        is_active: !pattern.is_active,
      });
      if (result.success) {
        toast.success(
          `Pattern ${pattern.is_active ? "disabled" : "enabled"}`
        );
        loadPatterns();
      } else {
        toast.error(result.error?.message || "Failed to update pattern");
      }
    } catch {
      toast.error("Failed to update pattern");
    }
  }

  // Generate patterns from AI
  async function handleGenerate() {
    setIsGenerating(true);
    try {
      const result = await knowledge.generate();
      if (result.success && result.data) {
        toast.success(
          `Generated ${result.data.count} new patterns`
        );
        loadPatterns();
      } else {
        toast.error(result.error?.message || "Failed to generate patterns");
      }
    } catch {
      toast.error("Failed to generate patterns");
    } finally {
      setIsGenerating(false);
    }
  }

  // Open edit dialog
  function openEditDialog(pattern: ClassificationPattern) {
    setSelectedPattern(pattern);
    setFormData({
      pattern: pattern.pattern,
      category: pattern.category,
      subcategory: pattern.subcategory || "",
      confidence: pattern.confidence,
      entity_id: pattern.entity_id,
    });
    setShowEditDialog(true);
  }

  // Open delete dialog
  function openDeleteDialog(pattern: ClassificationPattern) {
    setSelectedPattern(pattern);
    setShowDeleteDialog(true);
  }

  // Reset form
  function resetForm() {
    setFormData({
      pattern: "",
      category: "",
      subcategory: "",
      confidence: 0.8,
    });
  }

  if (isLoading) {
    return <LoadingState message="Loading knowledge patterns..." />;
  }

  if (error) {
    return (
      <ErrorState
        title="Failed to load patterns"
        description={error}
        onRetry={loadPatterns}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">
            Knowledge Patterns
          </h1>
          <p className="text-muted-foreground">
            Manage transaction classification patterns
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerate}
            disabled={isGenerating}
          >
            {isGenerating ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="mr-2 h-4 w-4" />
            )}
            Generate with AI
          </Button>
          <Button variant="outline" size="sm" onClick={loadPatterns}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button
            onClick={() => {
              resetForm();
              setShowCreateDialog(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Pattern
          </Button>
        </div>
      </div>

      {/* Stats */}
      <StatsGrid>
        <StatsCard
          title="Total Patterns"
          value={stats.total.toString()}
          icon={Brain}
        />
        <StatsCard
          title="Active Patterns"
          value={stats.active.toString()}
          icon={CheckCircle2}
        />
        <StatsCard
          title="Categories"
          value={stats.categories.toString()}
          icon={Filter}
        />
        <StatsCard
          title="Avg Confidence"
          value={`${(stats.avgConfidence * 100).toFixed(0)}%`}
          icon={Sparkles}
        />
      </StatsGrid>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search patterns..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[200px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Patterns Table */}
      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Pattern</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Subcategory</TableHead>
                <TableHead className="text-center w-[100px]">
                  Confidence
                </TableHead>
                <TableHead className="text-center w-[80px]">Active</TableHead>
                <TableHead className="w-[100px]">Updated</TableHead>
                <TableHead className="w-[50px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredPatterns.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="text-center text-muted-foreground py-8"
                  >
                    No patterns found
                  </TableCell>
                </TableRow>
              ) : (
                filteredPatterns.map((pattern) => (
                  <TableRow key={pattern.id}>
                    <TableCell>
                      <code className="text-sm bg-muted px-2 py-1 rounded">
                        {pattern.pattern}
                      </code>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{pattern.category}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {pattern.subcategory || "-"}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge
                        variant={
                          pattern.confidence >= 0.8
                            ? "default"
                            : pattern.confidence >= 0.5
                            ? "secondary"
                            : "outline"
                        }
                      >
                        {(pattern.confidence * 100).toFixed(0)}%
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <Switch
                        checked={pattern.is_active}
                        onCheckedChange={() => toggleActive(pattern)}
                      />
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(pattern.updated_at)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => openEditDialog(pattern)}
                          >
                            <Edit className="mr-2 h-4 w-4" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => openDeleteDialog(pattern)}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Pattern</DialogTitle>
            <DialogDescription>
              Create a new classification pattern for transactions
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="pattern">Pattern *</Label>
              <Input
                id="pattern"
                placeholder="e.g., AMAZON*, STRIPE*"
                value={formData.pattern}
                onChange={(e) =>
                  setFormData({ ...formData, pattern: e.target.value })
                }
              />
              <p className="text-xs text-muted-foreground">
                Use * as wildcard for partial matches
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="category">Category *</Label>
              <Select
                value={formData.category}
                onValueChange={(value) =>
                  setFormData({ ...formData, category: value })
                }
              >
                <SelectTrigger id="category">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="subcategory">Subcategory</Label>
              <Input
                id="subcategory"
                placeholder="e.g., Cloud Services"
                value={formData.subcategory}
                onChange={(e) =>
                  setFormData({ ...formData, subcategory: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confidence">
                Confidence ({((formData.confidence || 0.8) * 100).toFixed(0)}%)
              </Label>
              <Input
                id="confidence"
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={formData.confidence}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    confidence: parseFloat(e.target.value),
                  })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCreateDialog(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={
                isSubmitting || !formData.pattern || !formData.category
              }
            >
              {isSubmitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Plus className="mr-2 h-4 w-4" />
              )}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Pattern</DialogTitle>
            <DialogDescription>
              Update the classification pattern
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-pattern">Pattern *</Label>
              <Input
                id="edit-pattern"
                value={formData.pattern}
                onChange={(e) =>
                  setFormData({ ...formData, pattern: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-category">Category *</Label>
              <Select
                value={formData.category}
                onValueChange={(value) =>
                  setFormData({ ...formData, category: value })
                }
              >
                <SelectTrigger id="edit-category">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-subcategory">Subcategory</Label>
              <Input
                id="edit-subcategory"
                value={formData.subcategory}
                onChange={(e) =>
                  setFormData({ ...formData, subcategory: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-confidence">
                Confidence ({((formData.confidence || 0.8) * 100).toFixed(0)}%)
              </Label>
              <Input
                id="edit-confidence"
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={formData.confidence}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    confidence: parseFloat(e.target.value),
                  })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowEditDialog(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleUpdate}
              disabled={
                isSubmitting || !formData.pattern || !formData.category
              }
            >
              {isSubmitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="mr-2 h-4 w-4" />
              )}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Pattern</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the pattern &quot;
              {selectedPattern?.pattern}&quot;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
