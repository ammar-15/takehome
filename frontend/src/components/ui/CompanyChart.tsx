"use client"

import { useState, useEffect } from "react"
import { Line, LineChart, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ChartContainer } from "@/components/ui/chart"
import { ChartTooltip } from "@/components/ui/chart-tooltip"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown } from "lucide-react"

interface FinancialDataPoint {
  year: string;
  value: number;
  growth?: number; // Optional, as it might be calculated
}

interface FinancialMetricData {
  [key: string]: FinancialDataPoint[];
}

interface BackendFinancialData {
  [statementType: string]: {
    [year: string]: {
      [metric: string]: number;
    };
  };
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

const formatCompactCurrency = (value: number) => {
  if (value >= 1000000000) {
    return `$${(value / 1000000000).toFixed(1)}B`
  } else if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(0)}M`
  }
  return formatCurrency(value)
}

interface CompanyChartProps {
  ticker?: string;
}

export default function CompanyChart({ ticker = "ASML" }: CompanyChartProps) {
  const [financialData, setFinancialData] = useState<FinancialMetricData | null>(null);
  const [selectedMetricKey, setSelectedMetricKey] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);


  useEffect(() => {
    const fetchFinancialData = async () => {
      try {
        setLoading(true);
        const response = await fetch(`http://localhost:3001/api/company_data/${ticker}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: BackendFinancialData = await response.json();

        const transformedData: FinancialMetricData = {};
        const availableMetrics: { key: string; label: string; color: string; unit: string }[] = [];

        // Flatten and transform data from backend structure
        for (const statementType in data) {
          for (const year in data[statementType]) {
            for (const metric in data[statementType][year]) {
              const metricKey = `${statementType}:${metric}`;
              const metricLabel = `${statementType}: ${metric}`;

              if (!transformedData[metricKey]) {
                transformedData[metricKey] = [];
                // Assign a consistent color for each metric (can be improved)
                const color = `#${Math.floor(Math.random()*16777215).toString(16)}`; 
                availableMetrics.push({ key: metricKey, label: metricLabel, color, unit: "$" });
              }
              transformedData[metricKey].push({ year, value: data[statementType][year][metric] });
            }
          }
        }

        // Sort data points by year and calculate growth
        for (const key in transformedData) {
          transformedData[key].sort((a, b) => parseInt(a.year) - parseInt(b.year));
          for (let i = 1; i < transformedData[key].length; i++) {
            const current = transformedData[key][i];
            const previous = transformedData[key][i - 1];
            if (previous.value !== 0) {
              current.growth = ((current.value - previous.value) / previous.value) * 100;
            } else {
              current.growth = 0;
            }
          }
        }

        setFinancialData(transformedData);
        if (availableMetrics.length > 0) {
          setSelectedMetricKey(availableMetrics[0].key);
        }

      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    fetchFinancialData();
  }, [ticker]);

  const getAvailableMetrics = () => {
    const metrics: { key: string; label: string; color: string; unit: string }[] = [];
    if (financialData) {
      for (const statementType in financialData) {
        // Assuming financialData keys are already in the format "StatementType:Metric"
        // We need to reconstruct the label and key from the transformed data
        const parts = statementType.split(':');
        const label = parts.length > 1 ? `${parts[0]}: ${parts[1]}` : statementType;
        const key = statementType;
        // Assign a consistent color for each metric (can be improved)
        const color = `#${Math.floor(Math.random()*16777215).toString(16)}`; 
        metrics.push({ key, label, color, unit: "$" });
      }
    }
    return metrics;
  };

  const currentData = selectedMetricKey && financialData ? financialData[selectedMetricKey] : [];
  const currentMetricInfo = selectedMetricKey && financialData ? 
    getAvailableMetrics().find(m => m.key === selectedMetricKey) : null;

  const latestValue = currentData.length > 0 ? currentData[currentData.length - 1] : null;
  const previousValue = currentData.length > 1 ? currentData[currentData.length - 2] : null;

  let yearOverYearChange = 0;
  let isPositiveGrowth = false;

  if (latestValue && previousValue && previousValue.value !== 0) {
    yearOverYearChange = ((latestValue.value - previousValue.value) / previousValue.value) * 100;
    isPositiveGrowth = yearOverYearChange > 0;
  }

  const chartConfig = {
    value: {
      label: currentMetricInfo?.label || "Value",
      color: currentMetricInfo?.color || "#3b82f6",
    },
  };

  if (loading) return <div className="text-center p-4">Loading financial data...</div>;
  if (error) return <div className="text-center p-4 text-red-500">Error: {error}</div>;
  if (!financialData || Object.keys(financialData).length === 0) return <div className="text-center p-4">No financial data available for {ticker.toUpperCase()}.</div>;

  return (
    <div className="w-full max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Financial Overview</h1>
          <p className="text-slate-600">Track key financial metrics over time</p>
        </div>
        {/* The toggle button is now in App.tsx */}
      </div>

      {/* Main Chart Card */}
      <Card className="shadow-lg border-0 bg-white">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <Select
                  value={selectedMetricKey || undefined}
                  onValueChange={(value: string) => setSelectedMetricKey(value)}
                >
                  <SelectTrigger className="w-[200px] border-slate-200">
                    <SelectValue placeholder="Select a metric" />
                  </SelectTrigger>
                  <SelectContent>
                    {getAvailableMetrics().map((metric) => (
                      <SelectItem key={metric.key} value={metric.key}>
                        {metric.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Badge variant="secondary" className="text-xs">
                  {currentData.length > 0 ? `${currentData.length}-Year View` : ""}
                </Badge>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-3xl font-bold text-slate-900">
                  {latestValue ? formatCompactCurrency(latestValue.value) : "N/A"}
                </div>
                <div
                  className={`flex items-center gap-1 text-sm font-medium ${isPositiveGrowth ? "text-emerald-600" : "text-red-600"}`}
                >
                  {isPositiveGrowth ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  {yearOverYearChange.toFixed(1)}% YoY
                </div>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {selectedMetricKey && currentData.length > 0 ? (
            <ChartContainer config={chartConfig} className="h-[400px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={currentData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                  onMouseMove={(e: any) => {
  if (e?.activePayload?.[0]?.payload) {
  }
}}

                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 12 }} />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#64748b", fontSize: 12 }}
                    tickFormatter={formatCompactCurrency}
                  />
                  <Tooltip content={<ChartTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke={currentMetricInfo?.color || "#3b82f6"}
                    strokeWidth={3}
                    dot={{
                      fill: currentMetricInfo?.color || "#3b82f6",
                      strokeWidth: 2,
                      stroke: "#fff",
                      r: 4,
                    }}
                    activeDot={{
                      r: 6,
                      fill: currentMetricInfo?.color || "#3b82f6",
                      stroke: "#fff",
                      strokeWidth: 2,
                      filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.1))",
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </ChartContainer>
          ) : (
            <div className="h-[400px] flex items-center justify-center text-slate-500">
              Select a metric to view the chart.
            </div>
          )}

          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-slate-100">
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">Current Value</p>
              <p className="text-lg font-semibold text-slate-900">
                {latestValue ? formatCompactCurrency(latestValue.value) : "N/A"}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">Year-over-Year Change</p>
              <p className={`text-lg font-semibold ${isPositiveGrowth ? "text-emerald-600" : "text-red-600"}`}>
                {yearOverYearChange.toFixed(1)}%
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">Growth Trend</p>
              <p className={`text-lg font-semibold ${isPositiveGrowth ? "text-emerald-600" : "text-red-600"}`}>
                {isPositiveGrowth ? "Trending Up" : "Trending Down"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
