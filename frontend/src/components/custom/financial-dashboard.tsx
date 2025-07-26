import { useEffect, useState } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ChartContainer, ChartTooltip } from "@/components/ui/chart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { TrendingUp, TrendingDown, Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CompanyData } from "@/types";

// Default metrics config
type MetricsConfig = {
  [key: string]: { label: string; color: string; unit: string };
};

const defaultMetrics: MetricsConfig = {
  "total-assets": { label: "Total Assets", color: "#3b82f6", unit: "$" },
  revenue: { label: "Revenue", color: "#10b981", unit: "$" },
  "net-income": { label: "Net Income", color: "#8b5cf6", unit: "$" },
};

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

const formatCompactCurrency = (value: number) => {
  if (value >= 1000000000) {
    return `$${(value / 1000000000).toFixed(1)}B`;
  } else if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(0)}M`;
  }
  return formatCurrency(value);
};

type FinancialDashboardProps = {
  data: CompanyData[];
  metrics?: MetricsConfig;
};

export default function FinancialDashboard({
  data,
  metrics = defaultMetrics,
}: FinancialDashboardProps) {
  // Group data by metric and deduplicate by year
  const groupedData = data.reduce((acc, item) => {
    if (!acc[item.metric]) acc[item.metric] = [];

    // Check if this year already exists for this metric
    const existingYearIndex = acc[item.metric].findIndex(
      (existing) => existing.year === item.year
    );

    if (existingYearIndex === -1) {
      // Year doesn't exist, add the item
      acc[item.metric].push(item);
    }
    // If year already exists, we skip this item (keep the first occurrence)

    return acc;
  }, {} as Record<string, CompanyData[]>);

  // Sort each metric's data by year to ensure proper ordering
  Object.keys(groupedData).forEach((metric) => {
    groupedData[metric].sort((a, b) => a.year - b.year);
  });

  // Get all unique metrics from the data
  const dataMetricKeys = Object.keys(groupedData);
  // Use the first metric as default if available
  const [selectedMetric, setSelectedMetric] = useState<string>(
    dataMetricKeys[0] || ""
  );
  const [hoveredPoint, setHoveredPoint] = useState<any>(null);
  const [open, setOpen] = useState(false);

  const currentData = groupedData[selectedMetric] || [];
  const currentMetric = metrics[selectedMetric] || {
    label: selectedMetric,
    color: "#000",
    unit: "",
  };
  const latestValue = currentData[currentData.length - 1];
  const previousValue = currentData[currentData.length - 2];
  const yearOverYearChange =
    latestValue && previousValue
      ? ((latestValue.value - previousValue.value) / previousValue.value) * 100
      : 0;
  const isPositiveGrowth = yearOverYearChange > 0;

  const chartConfig = {
    value: {
      label: currentMetric.label,
      color: currentMetric.color,
    },
  };

  useEffect(() => {
    data.length > 0 && setSelectedMetric(dataMetricKeys[0]);
  }, [data]);

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      {/* Main Chart Card */}
      <Card className="shadow-lg border-0 bg-white">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <Popover open={open} onOpenChange={setOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={open}
                      className="w-[400px] justify-between border-slate-200"
                    >
                      {selectedMetric
                        ? metrics[selectedMetric]?.label || selectedMetric
                        : "Select metric..."}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[400px] p-0">
                    <Command>
                      <CommandInput
                        placeholder="Search metrics..."
                        className="h-9"
                      />
                      <CommandList>
                        <CommandEmpty>No metric found.</CommandEmpty>
                        <CommandGroup>
                          {dataMetricKeys.map((key) => (
                            <CommandItem
                              key={key}
                              value={key}
                              onSelect={(currentValue) => {
                                setSelectedMetric(
                                  currentValue === selectedMetric
                                    ? ""
                                    : currentValue
                                );
                                setOpen(false);
                              }}
                            >
                              {metrics[key]?.label || key}
                              <Check
                                className={cn(
                                  "ml-auto h-4 w-4",
                                  selectedMetric === key
                                    ? "opacity-100"
                                    : "opacity-0"
                                )}
                              />
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
                <Badge variant="secondary" className="text-xs">
                  {currentData.length > 0
                    ? `${currentData.length}-Year View`
                    : "No Data"}
                </Badge>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-3xl font-bold text-slate-900">
                  {latestValue ? formatCompactCurrency(latestValue.value) : "-"}
                </div>
                <div
                  className={`flex items-center gap-1 text-sm font-medium ${
                    isPositiveGrowth ? "text-emerald-600" : "text-red-600"
                  }`}
                >
                  {isPositiveGrowth ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : (
                    <TrendingDown className="h-4 w-4" />
                  )}
                  {Math.abs(yearOverYearChange).toFixed(1)}% YoY
                </div>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <ChartContainer config={chartConfig} className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={currentData}
                margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                onMouseMove={(e) => {
                  if (e.activePayload && e.activePayload[0]) {
                    setHoveredPoint(e.activePayload[0].payload);
                  }
                }}
                onMouseLeave={() => setHoveredPoint(null)}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="year"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#64748b", fontSize: 12 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#64748b", fontSize: 12 }}
                  tickFormatter={formatCompactCurrency}
                />
                <ChartTooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-white p-4 border border-slate-200 rounded-lg shadow-lg">
                          <p className="font-semibold text-slate-900 mb-2">
                            {label}
                          </p>
                          <div className="space-y-1">
                            <p className="text-sm text-slate-600">
                              {currentMetric.label}:{" "}
                              <span className="font-semibold text-slate-900">
                                {formatCurrency(data.value)}
                              </span>
                            </p>
                            {/* No growth property in CompanyData, so omit this */}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={currentMetric.color}
                  strokeWidth={3}
                  dot={{
                    fill: currentMetric.color,
                    strokeWidth: 2,
                    stroke: "#fff",
                    r: 4,
                  }}
                  activeDot={{
                    r: 6,
                    fill: currentMetric.color,
                    stroke: "#fff",
                    strokeWidth: 2,
                    filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.1))",
                  }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>

          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-slate-100">
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">Current Value</p>
              <p className="text-lg font-semibold text-slate-900">
                {latestValue ? formatCompactCurrency(latestValue.value) : "-"}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">6-Year Growth</p>
              <p className="text-lg font-semibold text-emerald-600">
                {currentData.length > 0 && latestValue
                  ? `+${(
                      ((latestValue.value - currentData[0].value) /
                        currentData[0].value) *
                      100
                    ).toFixed(1)}%`
                  : "-"}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">
                Average Annual Growth
              </p>
              <p className="text-lg font-semibold text-slate-900">
                {currentData.length > 1 && latestValue
                  ? (
                      ((latestValue.value / currentData[0].value) **
                        (1 / (currentData.length - 1)) -
                        1) *
                      100
                    ).toFixed(1)
                  : "-"}
                %
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
