"use client";

import { useState, useCallback } from "react";
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
} from "lucide-react";
import { toast } from "sonner";

import { upload } from "@/lib/api";
import { formatDate } from "@/lib/utils";
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

// Uploaded file interface
interface UploadedFile {
  id: string;
  name: string;
  type: "transactions" | "invoices";
  size: number;
  status: FileStatus;
  uploadedAt: string;
  processedRows?: number;
  totalRows?: number;
  errors?: string[];
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

// File size formatter
function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

// Upload Zone Component
function UploadZone({
  title,
  description,
  type,
  acceptedFormats,
  onUpload,
  isUploading,
}: {
  title: string;
  description: string;
  type: "transactions" | "invoices";
  acceptedFormats: string;
  onUpload: (files: FileList, type: "transactions" | "invoices") => void;
  isUploading: boolean;
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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {type === "transactions" ? (
            <FileSpreadsheet className="h-5 w-5" />
          ) : (
            <FileText className="h-5 w-5" />
          )}
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className={`
            relative border-2 border-dashed rounded-lg p-8 text-center transition-colors
            ${isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25"}
            ${isUploading ? "opacity-50 pointer-events-none" : "hover:border-primary/50"}
          `}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
          <p className="text-sm text-muted-foreground mb-2">
            Drag and drop files here, or click to browse
          </p>
          <p className="text-xs text-muted-foreground mb-4">
            Accepted formats: {acceptedFormats}
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
                Select Files
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// File Row Component
function FileRow({ file, onDelete }: { file: UploadedFile; onDelete: () => void }) {
  const progress = file.totalRows
    ? Math.round((file.processedRows || 0) / file.totalRows * 100)
    : 0;

  return (
    <div className="flex items-center gap-4 p-4 border rounded-lg">
      <div className="flex-shrink-0">
        {file.type === "transactions" ? (
          <FileSpreadsheet className="h-8 w-8 text-green-600" />
        ) : (
          <FileText className="h-8 w-8 text-blue-600" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium truncate">{file.name}</p>
          <StatusBadge status={file.status} />
        </div>
        <p className="text-sm text-muted-foreground">
          {formatFileSize(file.size)} - Uploaded {formatDate(file.uploadedAt)}
        </p>
        {file.status === "processing" && (
          <div className="mt-2">
            <Progress value={progress} className="h-2" />
            <p className="text-xs text-muted-foreground mt-1">
              Processing: {file.processedRows || 0} / {file.totalRows || 0} rows
            </p>
          </div>
        )}
        {file.status === "completed" && file.processedRows && (
          <p className="text-sm text-green-600 mt-1">
            Successfully processed {file.processedRows} rows
          </p>
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

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon">
          <Eye className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon">
          <Download className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={onDelete}>
          <Trash2 className="h-4 w-4 text-destructive" />
        </Button>
      </div>
    </div>
  );
}

export default function FilesPage() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  // Handle file upload
  const handleUpload = useCallback(
    async (files: FileList, type: "transactions" | "invoices") => {
      setIsUploading(true);

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
          };

          setUploadedFiles((prev) => [pendingFile, ...prev]);

          // Update to processing
          setUploadedFiles((prev) =>
            prev.map((f) =>
              f.id === fileId ? { ...f, status: "processing" as FileStatus } : f
            )
          );

          // Upload file
          const endpoint = type === "transactions" ? "/upload/transactions" : "/upload/invoices";
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
        <Button variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
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

      {/* Upload Zones */}
      <div className="grid gap-6 md:grid-cols-2">
        <UploadZone
          title="Transaction Files"
          description="Upload CSV or Excel files containing bank transactions"
          type="transactions"
          acceptedFormats=".csv,.xlsx,.xls"
          onUpload={handleUpload}
          isUploading={isUploading}
        />
        <UploadZone
          title="Invoice Files"
          description="Upload PDF invoices for processing and matching"
          type="invoices"
          acceptedFormats=".pdf,.jpg,.jpeg,.png"
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
          {uploadedFiles.length === 0 ? (
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
