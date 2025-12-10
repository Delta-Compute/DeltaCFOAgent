"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import { Loader2, ExternalLink, Info } from "lucide-react";
import { toast } from "sonner";

import {
  reports as reportsApi,
  type SankeyFlowData,
  type SankeyBreakdownData,
  type SankeyBreakdownItem,
  type Transaction,
} from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface SankeyFlowChartProps {
  startDate?: string;
  endDate?: string;
  className?: string;
}

// Color palette for nodes - professional colors with visual distinction
const COLORS = {
  revenue: "#059669", // emerald-600 (green for income)
  expense: "#dc2626", // red-600 (red for expenses)
  hub: "#6366f1", // indigo-500 (purple for central hub)
  category: "#64748b", // slate-500 (fallback)
  subcategory: "#94a3b8", // slate-400 (fallback)
};

export function SankeyFlowChart({
  startDate,
  endDate,
  className,
}: SankeyFlowChartProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sankeyData, setSankeyData] = useState<SankeyFlowData | null>(null);

  // Drill-down modal state
  const [selectedNode, setSelectedNode] = useState<{
    name: string;
    type?: string;
  } | null>(null);
  const [breakdown, setBreakdown] = useState<SankeyBreakdownData | null>(null);
  const [isLoadingBreakdown, setIsLoadingBreakdown] = useState(false);

  // Load Sankey data
  const loadSankeyData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params: Record<string, string> = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      params.min_amount = "500";
      params.max_categories = "10";

      const result = await reportsApi.getSankeyFlow(params);

      if (result.success && result.data) {
        // API returns { data: { sankey: {...}, parameters: {...} } }, wrapped by get() as { data: { data: {...} } }
        const flowData = (result.data as { data?: SankeyFlowData })?.data || result.data;
        setSankeyData(flowData as SankeyFlowData);
      } else {
        throw new Error(result.error?.message || "Failed to load Sankey data");
      }
    } catch (err) {
      console.error("Failed to load Sankey data:", err);
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setIsLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    loadSankeyData();
  }, [loadSankeyData]);

  // Handle node click for drill-down
  const handleNodeClick = async (nodeName: string, nodeType?: string) => {
    // Only skip drill-down for the hub node - allow drilling into revenue and expense categories
    if (!nodeType || nodeType === "hub") {
      return; // Don't drill down on the Cash Flow Hub node
    }

    setSelectedNode({ name: nodeName, type: nodeType });
    setIsLoadingBreakdown(true);
    setBreakdown(null);

    try {
      // Use the node type directly from the sankey data
      // Revenue nodes have positive amounts, expense nodes have negative amounts
      const apiNodeType: "revenue" | "expense" = nodeType === "revenue" ? "revenue" : "expense";

      const result = await reportsApi.getSankeyBreakdown({
        node_name: nodeName,
        node_type: apiNodeType,
        start_date: startDate,
        end_date: endDate,
      });

      if (result.success && result.data) {
        setBreakdown(result.data);
      } else {
        toast.error("Failed to load breakdown details");
      }
    } catch {
      toast.error("Failed to load breakdown details");
    } finally {
      setIsLoadingBreakdown(false);
    }
  };

  // Navigate to dashboard with filter for the selected category/keyword
  const openTransactionDrillDown = (keyword: string, category: string) => {
    const params = new URLSearchParams();
    params.set("search", keyword);
    params.set("category", category);
    window.open(`/dashboard?${params.toString()}`, "_blank");
  };

  // Transform data for Plotly Sankey
  const plotlyData = useMemo(() => {
    if (!sankeyData?.sankey?.nodes?.length) return null;

    const nodes = sankeyData.sankey.nodes;
    const links = sankeyData.sankey.links;

    // Create color array based on node type
    const nodeColors = nodes.map(node => {
      return COLORS[node.type as keyof typeof COLORS] || COLORS.category;
    });

    // Create link colors (lighter versions of source node colors)
    const linkColors = links.map(link => {
      const sourceNode = nodes[link.source];
      const baseColor = COLORS[sourceNode?.type as keyof typeof COLORS] || COLORS.category;
      // Add transparency for links
      return baseColor + "40"; // 25% opacity
    });

    return {
      type: "sankey" as const,
      orientation: "h" as const,
      arrangement: "snap" as const, // This enables dragging nodes
      node: {
        pad: 20,
        thickness: 15,
        line: {
          color: "rgba(0,0,0,0.1)",
          width: 0.5,
        },
        label: nodes.map(n => n.name),
        color: nodeColors,
        customdata: nodes.map(n => ({ name: n.name, type: n.type, value: n.value })),
        hovertemplate: "<b>%{label}</b><br>%{value:$,.0f}<extra></extra>",
      },
      link: {
        source: links.map(l => l.source),
        target: links.map(l => l.target),
        value: links.map(l => l.value),
        color: linkColors,
        hovertemplate: "%{source.label} -> %{target.label}<br>%{value:$,.0f}<extra></extra>",
      },
    };
  }, [sankeyData]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center h-[400px] gap-4">
          <p className="text-muted-foreground">{error}</p>
          <Button variant="outline" onClick={loadSankeyData}>
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!sankeyData || !sankeyData.sankey?.nodes?.length || !plotlyData) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-[400px]">
          <p className="text-muted-foreground">No flow data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className={className}>
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                Cash Flow Visualization
                <Info className="h-4 w-4 text-muted-foreground" />
              </CardTitle>
              <CardDescription>
                Click directly on any colored bar to drill down into transactions
              </CardDescription>
            </div>
            <div className="flex gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded"
                  style={{ backgroundColor: COLORS.revenue }}
                />
                <span>Revenue: {formatCurrency(sankeyData.summary.total_revenue)}</span>
              </div>
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded"
                  style={{ backgroundColor: COLORS.expense }}
                />
                <span>Expenses: {formatCurrency(sankeyData.summary.total_expenses)}</span>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="w-full overflow-x-auto">
            <Plot
              data={[plotlyData]}
              layout={{
                font: { size: 11, family: "Inter, sans-serif" },
                margin: { l: 10, r: 10, t: 10, b: 10 },
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
                hovermode: "closest",
              }}
              config={{
                displayModeBar: false,
                responsive: true,
              }}
              style={{ width: "100%", height: 450, cursor: "pointer" }}
              onClick={(event) => {
                // Handle node clicks for drill-down
                // Users can click directly on nodes - no need to catch the hover tooltip
                if (event.points && event.points.length > 0) {
                  const point = event.points[0];
                  // Check if it's a node click (not a link)
                  if (point.pointNumber !== undefined && sankeyData?.sankey?.nodes) {
                    const nodeIndex = point.pointNumber;
                    const node = sankeyData.sankey.nodes[nodeIndex];
                    if (node) {
                      handleNodeClick(node.name, node.type);
                    }
                  }
                }
              }}
            />
          </div>
        </CardContent>
      </Card>

      {/* Breakdown Modal */}
      <Dialog open={!!selectedNode} onOpenChange={() => setSelectedNode(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>{selectedNode?.name} Breakdown</span>
            </DialogTitle>
            <DialogDescription>
              Detailed breakdown of transactions in this category
            </DialogDescription>
          </DialogHeader>

          {isLoadingBreakdown ? (
            <div className="flex items-center justify-center h-40">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : breakdown ? (
            <div className="space-y-4">
              {/* Summary */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">
                <div>
                  <p className="text-sm text-muted-foreground">Total Amount</p>
                  <p className="text-xl font-bold">
                    {formatCurrency(breakdown.total_amount)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Transactions</p>
                  <p className="text-xl font-bold">
                    {breakdown.transaction_count}
                  </p>
                </div>
              </div>

              {/* Breakdown by keyword */}
              {breakdown.breakdown && breakdown.breakdown.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">By Source/Destination</h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead className="text-right">Count</TableHead>
                        <TableHead className="text-right">%</TableHead>
                        <TableHead className="w-[50px]" />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {breakdown.breakdown.map((item: SankeyBreakdownItem, index: number) => (
                        <TableRow
                          key={`${item.keyword}-${index}`}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() =>
                            openTransactionDrillDown(
                              item.keyword,
                              selectedNode?.name || ""
                            )
                          }
                        >
                          <TableCell className="font-medium">
                            {item.keyword}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatCurrency(item.amount)}
                          </TableCell>
                          <TableCell className="text-right">
                            {item.count}
                          </TableCell>
                          <TableCell className="text-right">
                            {item.percentage.toFixed(1)}%
                          </TableCell>
                          <TableCell>
                            <ExternalLink className="h-4 w-4 text-muted-foreground" />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {/* Top Transactions */}
              {breakdown.top_transactions &&
                breakdown.top_transactions.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">Top Transactions</h4>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Date</TableHead>
                          <TableHead>Description</TableHead>
                          <TableHead className="text-right">Amount</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {breakdown.top_transactions
                          .slice(0, 5)
                          .map((txn: Transaction, index: number) => (
                            <TableRow key={txn.id || `txn-${index}`}>
                              <TableCell>
                                {new Date(txn.date).toLocaleDateString()}
                              </TableCell>
                              <TableCell className="max-w-[300px] truncate">
                                {txn.description}
                              </TableCell>
                              <TableCell className="text-right">
                                {formatCurrency(Math.abs(txn.amount))}
                              </TableCell>
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No breakdown data available
            </p>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
