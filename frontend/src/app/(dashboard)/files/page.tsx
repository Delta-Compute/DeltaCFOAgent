"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Upload,
  FileText,
  FileSpreadsheet,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Trash2,
  Download,
  Eye,
  Loader2,
  Receipt,
  Building2,
  CreditCard,
  Wallet,
  ArrowLeftRight,
} from "lucide-react";
import { toast } from "sonner";

import { upload, files as filesApi, type UploadedFileData } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useAuth } from "@/context/auth-context";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { StatsCard, StatsGrid } from "@/components/dashboard/stats-card";

// File status type
type FileStatus = "pending" | "processing" | "completed" | "failed";

// Processing stage type
type ProcessingStage = "upload" | "extract" | "pattern" | "classify" | "pass2" | "save";

// Uploaded file interface
interface UploadedFile {
  id: string;
  name: string;
  type: "transactions" | "invoices" | "receipts";
  size: number;
  status: FileStatus;
  uploadedAt: string;
  processedRows?: number;
  totalRows?: number;
  errors?: string[];
  currentStage?: ProcessingStage;
  accountCategory?: string;
  statementPeriod?: { start: string; end: string };
  activeTransactions?: number;
  archivedTransactions?: number;
}


// Status badge component
function StatusBadge({ status }: { status: FileStatus }) {
  const config: Record<FileStatus, { label: string; variant: "outline" | "secondary" | "default" | "destructive"; icon: typeof Clock }> = {
    pending: { label: "Pending", variant: "outline", icon: Clock },
    processing: { label: "Processing", variant: "secondary", icon: RefreshCw },
    completed: { label: "Completed", variant: "default", icon: CheckCircle2 },
    failed: { label: "Failed", variant: "destructive", icon: XCircle },
  };

  const { label, variant, icon: Icon } = config[status];

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className={`h-3 w-3 ${status === "processing" ? "animate-spin" : ""}`} />
      {label}
    </Badge>
  );
}

// Archive status badge component (for file rows)
function ArchiveStatusBadge({ archived, total }: { archived: number; total: number }) {
  if (archived === total && total > 0) {
    return <Badge variant="secondary" className="bg-gray-100 text-gray-700">All Archived</Badge>;
  }
  if (archived > 0) {
    return <Badge variant="secondary" className="bg-yellow-100 text-yellow-700">Partially Archived</Badge>;
  }
  return <Badge variant="default" className="bg-green-100 text-green-700">Active</Badge>;
}

// Category badge component
function CategoryBadge({ category }: { category: string }) {
  const config: Record<string, { bg: string; text: string; icon: typeof Building2 }> = {
    "Checking": { bg: "bg-blue-100", text: "text-blue-700", icon: Building2 },
    "Credit Card": { bg: "bg-purple-100", text: "text-purple-700", icon: CreditCard },
    "Crypto Exchange": { bg: "bg-orange-100", text: "text-orange-700", icon: ArrowLeftRight },
    "Crypto Wallet": { bg: "bg-yellow-100", text: "text-yellow-700", icon: Wallet },
    "Other": { bg: "bg-gray-100", text: "text-gray-700", icon: FileText },
  };

  const { bg, text, icon: Icon } = config[category] || config["Other"];

  return (
    <Badge variant="outline" className={`${bg} ${text} gap-1`}>
      <Icon className="h-3 w-3" />
      {category}
    </Badge>
  );
}

// Processing stages component
const PROCESSING_STAGES: { key: ProcessingStage; label: string }[] = [
  { key: "upload", label: "Uploading file" },
  { key: "extract", label: "Extracting transactions" },
  { key: "pattern", label: "Pattern recognition" },
  { key: "classify", label: "AI Classification" },
  { key: "pass2", label: "AI Review (Pass 2)" },
  { key: "save", label: "Saving to database" },
];

function ProcessingStages({ currentStage, isComplete }: { currentStage?: ProcessingStage; isComplete: boolean }) {
  const currentIndex = currentStage ? PROCESSING_STAGES.findIndex(s => s.key === currentStage) : -1;

  return (
    <div className="space-y-2 mt-4">
      {PROCESSING_STAGES.map((stage, index) => {
        const isActive = index === currentIndex;
        const isCompleted = isComplete || index < currentIndex;
        const isPending = index > currentIndex && !isComplete;

        return (
          <div key={stage.key} className="flex items-center gap-3">
            <div className={`
              w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium
              ${isCompleted ? "bg-green-500 text-white" : ""}
              ${isActive ? "bg-blue-500 text-white animate-pulse" : ""}
              ${isPending ? "bg-gray-200 text-gray-500" : ""}
            `}>
              {isCompleted ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : isActive ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                index + 1
              )}
            </div>
            <span className={`text-sm ${isActive ? "font-medium text-blue-600" : isCompleted ? "text-green-600" : "text-gray-500"}`}>
              {stage.label}
            </span>
            {isActive && (
              <span className="text-xs text-blue-500 animate-pulse">Processing...</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// File size formatter
function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

// Upload Zone Component
type UploadType = "transactions" | "invoices" | "receipts";

function UploadZone({
  title,
  description,
  type,
  acceptedFormats,
  onUpload,
  isUploading,
  currentStage,
  showProcessingStages = false,
}: {
  title: string;
  description: string;
  type: UploadType;
  acceptedFormats: string;
  onUpload: (files: FileList, type: UploadType) => void;
  isUploading: boolean;
  currentStage?: ProcessingStage;
  showProcessingStages?: boolean;
}) {
  const [isDragging, setIsDragging] = useState(false);

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      onUpload(e.dataTransfer.files, type);
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files.length > 0) {
      onUpload(e.target.files, type);
    }
  }

  const getIcon = () => {
    switch (type) {
      case "transactions":
        return <FileSpreadsheet className="h-5 w-5 text-green-600" />;
      case "invoices":
        return <FileText className="h-5 w-5 text-blue-600" />;
      case "receipts":
        return <Receipt className="h-5 w-5 text-purple-600" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {getIcon()}
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className={`
            relative border-2 border-dashed rounded-lg p-6 text-center transition-colors
            ${isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25"}
            ${isUploading ? "opacity-50 pointer-events-none" : "hover:border-primary/50"}
          `}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <Upload className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm text-muted-foreground mb-1">
            Drag and drop files here, or click to browse
          </p>
          <p className="text-xs text-muted-foreground mb-3">
            {acceptedFormats}
          </p>
          <input
            type="file"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            accept={acceptedFormats}
            multiple
            onChange={handleFileSelect}
            disabled={isUploading}
          />
          <Button variant="outline" size="sm" disabled={isUploading}>
            {isUploading ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Choose Files
              </>
            )}
          </Button>
        </div>

        {/* Processing Stages - only show for transactions type and when uploading */}
        {showProcessingStages && isUploading && type === "transactions" && (
          <ProcessingStages currentStage={currentStage} isComplete={false} />
        )}
      </CardContent>
    </Card>
  );
}

// File Row Component
function FileRow({ file, onDelete }: { file: UploadedFile; onDelete: () => void }) {
  const progress = file.totalRows
    ? Math.round((file.processedRows || 0) / file.totalRows * 100)
    : 0;

  const totalTxns = file.totalRows || 0;
  const activeTxns = file.activeTransactions ?? totalTxns;
  const archivedTxns = file.archivedTransactions ?? 0;

  const getFileIcon = () => {
    switch (file.type) {
      case "transactions":
        return <FileSpreadsheet className="h-8 w-8 text-green-600" />;
      case "invoices":
        return <FileText className="h-8 w-8 text-blue-600" />;
      case "receipts":
        return <Receipt className="h-8 w-8 text-purple-600" />;
    }
  };

  return (
    <div className="flex items-center gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex-shrink-0">
        {getFileIcon()}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="font-medium font-mono text-sm truncate">{file.name}</p>
          <StatusBadge status={file.status} />
          {file.accountCategory && (
            <CategoryBadge category={file.accountCategory} />
          )}
        </div>

        <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
          <span>{formatFileSize(file.size)}</span>
          <span>Uploaded {formatDate(file.uploadedAt)}</span>
          {file.statementPeriod && (
            <span className="text-blue-600 font-medium">
              {file.statementPeriod.start} to {file.statementPeriod.end}
            </span>
          )}
        </div>

        {file.status === "processing" && (
          <div className="mt-2">
            <Progress value={progress} className="h-2" />
            <div className="flex items-center gap-2 mt-1">
              <p className="text-xs text-muted-foreground">
                Processing: {file.processedRows || 0} / {file.totalRows || 0} rows
              </p>
              {file.currentStage && (
                <span className="text-xs text-blue-500">
                  ({PROCESSING_STAGES.find(s => s.key === file.currentStage)?.label})
                </span>
              )}
            </div>
          </div>
        )}

        {file.status === "completed" && totalTxns > 0 && (
          <div className="flex items-center gap-3 mt-2">
            <span className="text-sm font-semibold">{totalTxns} total</span>
            <span className="text-xs text-green-600">{activeTxns} active</span>
            {archivedTxns > 0 && (
              <span className="text-xs text-red-600">{archivedTxns} archived</span>
            )}
            <ArchiveStatusBadge archived={archivedTxns} total={totalTxns} />
          </div>
        )}

        {file.status === "failed" && file.errors && (
          <div className="mt-2">
            {file.errors.slice(0, 2).map((error, i) => (
              <p key={i} className="text-sm text-red-600">{error}</p>
            ))}
            {file.errors.length > 2 && (
              <p className="text-sm text-muted-foreground">
                +{file.errors.length - 2} more errors
              </p>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <Eye className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <Download className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onDelete}>
          <Trash2 className="h-4 w-4 text-destructive" />
        </Button>
      </div>
    </div>
  );
}

export default function FilesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [currentStage, setCurrentStage] = useState<ProcessingStage | undefined>();

  // Map backend document type to frontend file type
  const mapDocumentType = (backendType: string): UploadedFile["type"] => {
    switch (backendType?.toLowerCase()) {
      case "transaction":
      case "transactions":
        return "transactions";
      case "invoice":
      case "invoices":
        return "invoices";
      case "receipt":
      case "receipts":
        return "receipts";
      default:
        return "transactions";
    }
  };

  // Fetch files from backend on mount
  const loadFiles = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await filesApi.list();
      if (result.success && result.data) {
        // Map backend file data to frontend UploadedFile format
        const filesData = (result.data as { files?: UploadedFileData[] })?.files || [];
        const mappedFiles: UploadedFile[] = filesData.map((f: UploadedFileData) => ({
          id: f.id,
          name: f.name,
          type: mapDocumentType(f.type),
          size: f.size || 0,
          status: "completed" as FileStatus,
          uploadedAt: f.uploaded_at || new Date().toISOString(),
        }));
        setUploadedFiles(mappedFiles);
      }
    } catch (err) {
      console.error("Failed to load files:", err);
      toast.error("Failed to load files");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load files when authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      loadFiles();
    } else if (!authLoading && !isAuthenticated) {
      setIsLoading(false);
    }
  }, [authLoading, isAuthenticated, loadFiles]);

  // Handle file upload
  const handleUpload = useCallback(
    async (files: FileList, type: UploadType) => {
      setIsUploading(true);
      setCurrentStage("upload");

      try {
        const fileArray = Array.from(files);

        for (const file of fileArray) {
          // Create pending file entry
          const fileId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const pendingFile: UploadedFile = {
            id: fileId,
            name: file.name,
            type,
            size: file.size,
            status: "pending",
            uploadedAt: new Date().toISOString(),
            currentStage: "upload",
          };

          setUploadedFiles((prev) => [pendingFile, ...prev]);

          // Update to processing with stage progression
          setUploadedFiles((prev) =>
            prev.map((f) =>
              f.id === fileId ? { ...f, status: "processing" as FileStatus, currentStage: "upload" as ProcessingStage } : f
            )
          );

          // Simulate stage progression for transactions
          if (type === "transactions") {
            const stages: ProcessingStage[] = ["upload", "extract", "pattern", "classify", "pass2", "save"];
            for (const stage of stages) {
              setCurrentStage(stage);
              setUploadedFiles((prev) =>
                prev.map((f) =>
                  f.id === fileId ? { ...f, currentStage: stage } : f
                )
              );
              // Small delay to show stage progression (only for visual feedback)
              await new Promise(resolve => setTimeout(resolve, 200));
            }
          }

          // Upload file
          const endpoints: Record<UploadType, string> = {
            transactions: "/upload/transactions",
            invoices: "/upload/invoices",
            receipts: "/upload/receipts",
          };
          const endpoint = endpoints[type];
          const result = await upload(endpoint, file);

          if (result.success) {
            setUploadedFiles((prev) =>
              prev.map((f) =>
                f.id === fileId
                  ? {
                      ...f,
                      status: "completed" as FileStatus,
                      processedRows: (result.data as { rows_processed?: number })?.rows_processed || 0,
                      totalRows: (result.data as { total_rows?: number })?.total_rows || 0,
                      currentStage: undefined,
                    }
                  : f
              )
            );
            toast.success(`${file.name} uploaded successfully`);
          } else {
            setUploadedFiles((prev) =>
              prev.map((f) =>
                f.id === fileId
                  ? {
                      ...f,
                      status: "failed" as FileStatus,
                      errors: [result.error?.message || "Upload failed"],
                      currentStage: undefined,
                    }
                  : f
              )
            );
            toast.error(`Failed to upload ${file.name}`);
          }
        }
      } catch (error) {
        console.error("Upload error:", error);
        toast.error("Upload failed");
      } finally {
        setIsUploading(false);
        setCurrentStage(undefined);
      }
    },
    []
  );

  // Delete file
  function handleDeleteFile(fileId: string) {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== fileId));
    toast.success("File removed");
  }

  // Calculate stats
  const stats = {
    total: uploadedFiles.length,
    completed: uploadedFiles.filter((f) => f.status === "completed").length,
    processing: uploadedFiles.filter((f) => f.status === "processing").length,
    failed: uploadedFiles.filter((f) => f.status === "failed").length,
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">File Manager</h1>
          <p className="text-muted-foreground">
            Upload and manage transaction files and invoices
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadFiles} disabled={isLoading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <StatsGrid>
        <StatsCard
          title="Total Files"
          value={stats.total.toString()}
          icon={FileText}
        />
        <StatsCard
          title="Completed"
          value={stats.completed.toString()}
          icon={CheckCircle2}
        />
        <StatsCard
          title="Processing"
          value={stats.processing.toString()}
          icon={Clock}
        />
        <StatsCard
          title="Failed"
          value={stats.failed.toString()}
          icon={XCircle}
        />
      </StatsGrid>

      {/* Upload Zones - 3 column grid */}
      <div className="grid gap-4 md:grid-cols-3">
        <UploadZone
          title="Transaction Files"
          description="Upload CSV, Excel or PDF bank statements"
          type="transactions"
          acceptedFormats=".csv,.xlsx,.xls,.pdf"
          onUpload={handleUpload}
          isUploading={isUploading}
          currentStage={currentStage}
          showProcessingStages={true}
        />
        <UploadZone
          title="Invoices"
          description="Upload invoices for processing and matching"
          type="invoices"
          acceptedFormats=".pdf,.png,.jpg,.jpeg,.tiff,.csv,.xlsx"
          onUpload={handleUpload}
          isUploading={isUploading}
        />
        <UploadZone
          title="Payment Receipts"
          description="Upload receipts - AI will match to invoices"
          type="receipts"
          acceptedFormats=".pdf,.png,.jpg,.jpeg,.tiff,.csv,.xlsx"
          onUpload={handleUpload}
          isUploading={isUploading}
        />
      </div>

      {/* Uploaded Files */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Uploads</CardTitle>
          <CardDescription>
            Files you have uploaded recently
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading || authLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : uploadedFiles.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Upload className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No files uploaded yet</p>
              <p className="text-sm">Upload transaction files or invoices to get started</p>
            </div>
          ) : (
            <div className="space-y-4">
              {uploadedFiles.map((file) => (
                <FileRow
                  key={file.id}
                  file={file}
                  onDelete={() => handleDeleteFile(file.id)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
