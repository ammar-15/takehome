import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Line } from "react-chartjs-2";
import AiOverviewBox from "@/components/custom/AiOverviewBox";

const IMPORTANT_METRICS = [
  "Income Statement: Net Income",
  "Income Statement: Gross Profit",
  "Balance Sheet: Total Assets",
  "Balance Sheet: Cash and Cash Equivalents",
  "Income Statement: Operating Income",
  "Income Statement: Earnings from Equity Method Investments",
];

export default function AnalysisChart({ ticker }: { ticker: string }) {
  const [data, setData] = useState<any>({});
  const [selectedMetric, setSelectedMetric] = useState(IMPORTANT_METRICS[0]);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_BASE_URL}/api/company/${ticker}`)
      .then((res) => res.json())
      .then((res) => setData(res.data || {}))
      .catch(() => setData({}));
  }, [ticker]);

  const years = Array.from({ length: 10 }, (_, i) => (2015 + i).toString());
  const values = years.map((year) => {
    for (const row of data || []) {
      if (row.year === parseInt(year) && row.metric === selectedMetric) {
        return row.value;
      }
    }
    return null;
  });

  const chartData = {
    labels: years,
    datasets: [
      {
        label: selectedMetric,
        data: values,
        fill: false,
        borderColor: "#f97316",
        backgroundColor: "#f97316",
        tension: 0.4,
      },
    ],
  };

  return (
    <Card className="p-6 bg-white shadow-sm space-y-4">
      <div className="flex justify-between items-center">
        <Select value={selectedMetric} onValueChange={(v) => setSelectedMetric(v)}>
          <SelectTrigger className="w-[300px] border-slate-200">
            <SelectValue placeholder="Select a metric" />
          </SelectTrigger>
          <SelectContent>
            {IMPORTANT_METRICS.map((metric) => (
              <SelectItem key={metric} value={metric}>
                {metric}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Badge variant="outline" className="text-orange-600 border-orange-300">
          10-Year View
        </Badge>
      </div>

      <Line data={chartData} options={{ responsive: true }} />

      {/* 🧠 AI Overview Box */}
      <AiOverviewBox ticker={ticker} metric={selectedMetric} />
    </Card>
  );
}
