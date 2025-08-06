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
import AiOverviewBox from "@/components/custom/AiOverviewBox";
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
  ticker: string;
  metrics?: MetricsConfig;
};

export default function FinancialDashboard({
  data,
  ticker,
  metrics = defaultMetrics,
}: FinancialDashboardProps) {
  const groupedData = data.reduce((acc, item) => {
    if (!acc[item.metric]) acc[item.metric] = [];

    const existingYearIndex = acc[item.metric].findIndex(
      (existing) => existing.year === item.year
    );

    if (existingYearIndex === -1) {
      acc[item.metric].push(item);
    }

    return acc;
  }, {} as Record<string, CompanyData[]>);

  Object.keys(groupedData).forEach((metric) => {
    groupedData[metric].sort((a, b) => a.year - b.year);
  });

  const dataMetricKeys = Object.keys(groupedData);
  const [selectedMetric, setSelectedMetric] = useState<string>(
    dataMetricKeys[0] || ""
  );
  const [open, setOpen] = useState(false);

  const currentData = groupedData[selectedMetric] || [];
  const scaledChartData = currentData.map((entry) => ({
    ...entry,
    value:
      entry.value === 0 || entry.value === null || entry.value === undefined
        ? null
        : entry.value / 1_000_000,
  }));
  const fullRangeData = [...scaledChartData];
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
                data={scaledChartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                onMouseMove={(e) => {
                  if (e.activePayload && e.activePayload[0]) {
                  }
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="year"
                  axisLine={false}
                  tickLine={false}
                  tick={({ x, y, payload }) => {
                    const year = payload.value;
                    const point = scaledChartData.find((d) => d.year === year);
                    const hasValue = point && point.value !== null;

                    return (
                      <g transform={`translate(${x},${y})`}>
                        <text
                          x={0}
                          y={0}
                          dy={16}
                          textAnchor="middle"
                          fill="#64748b"
                          fontSize={12}
                        >
                          {year}
                        </text>
                        {!hasValue && (
                          <text
                            x={0}
                            y={16}
                            dy={16}
                            textAnchor="middle"
                            fill="#ef4444"
                            fontSize={10}
                          >
                            No data
                          </text>
                        )}
                      </g>
                    );
                  }}
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
                      const data = payload?.[0]?.payload;
                      if (!data) return null;
                      return (
                        <div className="bg-white p-4 border border-slate-200 rounded-lg shadow-lg">
                          <p className="font-semibold text-slate-900 mb-2">
                            {label}
                          </p>
                          <div className="space-y-1">
                            <p className="text-sm text-slate-600">
                              {currentMetric.label}:{" "}
                              <span className="font-semibold text-slate-900">
                                {formatCurrency(data.value)}M
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
              <p className="text-sm text-slate-600 mb-1">
                {fullRangeData.length}-Year Growth
              </p>
              <p
                className={cn(
                  "text-lg font-semibold",
                  (() => {
                    const start = fullRangeData[0]?.value;
                    const end = fullRangeData[fullRangeData.length - 1]?.value;
                    return start != null && end != null && start < end
                      ? "text-emerald-600"
                      : "text-red-600";
                  })()
                )}
              >
                {(() => {
                  if (
                    fullRangeData.length >= 2 &&
                    fullRangeData[0]?.value != null &&
                    fullRangeData[fullRangeData.length - 1]?.value != null
                  ) {
                    const startValue = fullRangeData[0].value!;
                    const endValue =
                      fullRangeData[fullRangeData.length - 1].value!;
                    const growth = ((endValue - startValue) / startValue) * 100;
                    return `${growth.toFixed(1)}%`;
                  } else {
                    return "-";
                  }
                })()}
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
          <AiOverviewBox
  ticker={ticker}
  metric={`${currentData[0]?.statement_type}: ${currentData[0]?.metric}`}
/>
        </CardContent>
      </Card>
    </div>
  );
}
