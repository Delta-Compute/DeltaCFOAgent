"use client";

import { useState, useEffect, useCallback } from "react";
import { Sankey, Tooltip, Layer, Rectangle } from "recharts";
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

interface SankeyFlowChartProps {
  startDate?: string;
  endDate?: string;
  className?: string;
}

// Color palette for nodes
const COLORS = {
  revenue: "#22c55e", // green-500
  expense: "#ef4444", // red-500
  category: "#3b82f6", // blue-500
  subcategory: "#8b5cf6", // violet-500
};

// Props interface for custom Sankey node (Recharts injects x, y, width, height, index, payload at runtime)
interface SankeyNodeProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  index?: number;
  payload?: { name: string; type?: string; value?: number };
  onClick?: (node: { name: string; type?: string; value?: number }) => void;
}

// Custom node component for Sankey
function SankeyNode({
  x = 0,
  y = 0,
  width = 10,
  height = 10,
  index = 0,
  payload = { name: "" },
  onClick,
}: SankeyNodeProps) {
  const nodeType = payload.type || "category";
  const color = COLORS[nodeType as keyof typeof COLORS] || COLORS.category;

  return (
    <Layer key={`sankey-node-${index}`}>
      <Rectangle
        x={x}
        y={y}
        width={width}
        height={height}
        fill={color}
        fillOpacity={0.9}
        onClick={() => onClick?.(payload)}
        style={{ cursor: onClick ? "pointer" : "default" }}
      />
      <text
        x={x < 200 ? x + width + 6 : x - 6}
        y={y + height / 2}
        textAnchor={x < 200 ? "start" : "end"}
        dominantBaseline="middle"
        fill="#333"
        fontSize={12}
        fontWeight={500}
      >
        {payload.name}
      </text>
    </Layer>
  );
}

// Props interface for custom Sankey link (Recharts injects props at runtime)
interface SankeyLinkProps {
  sourceX?: number;
  targetX?: number;
  sourceY?: number;
  targetY?: number;
  sourceControlX?: number;
  targetControlX?: number;
  linkWidth?: number;
  index?: number;
}

// Custom link component
function SankeyLink({
  sourceX = 0,
  targetX = 0,
  sourceY = 0,
  targetY = 0,
  sourceControlX = 0,
  targetControlX = 0,
  linkWidth = 1,
  index = 0,
}: SankeyLinkProps) {
  return (
    <Layer key={`sankey-link-${index}`}>
      <path
        d={`
          M${sourceX},${sourceY}
          C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}
        `}
        fill="none"
        stroke="#cbd5e1"
        strokeWidth={linkWidth}
        strokeOpacity={0.5}
      />
    </Layer>
  );
}

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
  const handleNodeClick = async (node: { name: string; type?: string }) => {
    if (!node.type || node.type === "revenue" || node.type === "expense") {
      return; // Don't drill down on main revenue/expense nodes
    }

    setSelectedNode(node);
    setIsLoadingBreakdown(true);
    setBreakdown(null);

    try {
      // Determine if this category is revenue or expense by checking link sources
      let nodeType: "revenue" | "expense" = "expense";
      if (sankeyData?.sankey) {
        const nodeIndex = sankeyData.sankey.nodes.findIndex(n => n.name === node.name);
        if (nodeIndex >= 0) {
          // Check if any link points TO this node FROM a revenue node
          const isRevenueCategory = sankeyData.sankey.links.some(link => {
            const sourceNode = sankeyData.sankey.nodes[link.source];
            return link.target === nodeIndex && sourceNode?.type === "revenue";
          });
          nodeType = isRevenueCategory ? "revenue" : "expense";
        }
      }

      const result = await reportsApi.getSankeyBreakdown({
        node_name: node.name,
        node_type: nodeType,
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

    // Set search to include the keyword for filtering
    params.set("search", keyword);
    // Set category filter
    params.set("category", category);

    window.open(`/dashboard?${params.toString()}`, "_blank");
  };

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

  if (!sankeyData || !sankeyData.sankey?.nodes?.length) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-[400px]">
          <p className="text-muted-foreground">No flow data available</p>
        </CardContent>
      </Card>
    );
  }

  // Transform API data for Recharts Sankey
  const chartData = {
    nodes: sankeyData.sankey.nodes.map((node) => ({
      name: node.name,
      type: node.type,
      value: node.value,
    })),
    links: sankeyData.sankey.links.map((link) => ({
      source: link.source,
      target: link.target,
      value: link.value,
    })),
  };

  return (
    <>
      <Card className={className}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                Cash Flow Visualization
                <Info className="h-4 w-4 text-muted-foreground" />
              </CardTitle>
              <CardDescription>
                Revenue to expense flow - click on categories to drill down
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
          <div className="w-full flex justify-center overflow-x-auto">
            <Sankey
              width={900}
              height={450}
              data={chartData}
              node={<SankeyNode onClick={handleNodeClick} />}
              link={<SankeyLink />}
              nodePadding={30}
              nodeWidth={12}
              margin={{ top: 20, right: 180, bottom: 20, left: 40 }}
            >
              <Tooltip
                content={({ payload }) => {
                  if (!payload || !payload.length) return null;
                  const data = payload[0].payload;
                  if (data.source !== undefined && data.target !== undefined) {
                    // Link tooltip
                    const sourceNode = chartData.nodes[data.source];
                    const targetNode = chartData.nodes[data.target];
                    return (
                      <div className="bg-white border rounded-lg shadow-lg p-3">
                        <p className="font-medium">
                          {sourceNode?.name} → {targetNode?.name}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {formatCurrency(data.value)}
                        </p>
                      </div>
                    );
                  }
                  // Node tooltip
                  return (
                    <div className="bg-white border rounded-lg shadow-lg p-3">
                      <p className="font-medium">{data.name}</p>
                      {data.value && (
                        <p className="text-sm text-muted-foreground">
                          {formatCurrency(data.value)}
                        </p>
                      )}
                      <p className="text-xs text-primary mt-1">
                        Click to view breakdown
                      </p>
                    </div>
                  );
                }}
              />
            </Sankey>
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
                      {breakdown.breakdown.map((item: SankeyBreakdownItem) => (
                        <TableRow
                          key={item.keyword}
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
                          .map((txn: Transaction) => (
                            <TableRow key={txn.id}>
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
