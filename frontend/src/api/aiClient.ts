import { useQuery } from "@tanstack/react-query";

type CompanyDataRow = {
  year: number;
  statement_type: string;
  metric: string;
  value: number;
};

const generateAISummary = async (
  ticker: string,
  metric: string,
  data: CompanyDataRow[]
): Promise<string> => {
  const [statementType, metricLabel] = metric.split(":").map((s) => s.trim());
  console.log("Statement Type:", statementType);


  const rows = [...data].sort((a, b) => a.year - b.year);

  // Group by "Statement: Metric"
  const grouped = rows.reduce((acc, row) => {
    const key = `${row.statement_type}: ${row.metric}`;
    if (!acc[key]) acc[key] = [];
    acc[key].push(`${row.year}: ${row.value}`);
    return acc;
  }, {} as Record<string, string[]>);

  const formatted = Object.entries(grouped)
    .map(([key, values]) => `${key}\n${values.join("\n")}`)
    .join("\n\n");

  const prompt = `
You are a professional financial analyst reviewing historical financial data for the public company "${ticker}".

Your primary focus is on **"${metricLabel}"**, but you may cross-reference other financial metrics from the full dataset to explain potential causes or relationships. For example, if you're looking at "Net Income", you might reference "Revenue" or "Operating Expenses" to justify changes.

Write a concise and unbiased, insightful 2–3 sentence analysis of "${metricLabel}" over time. Mention the trend, any inflection points, and one supporting metric that adds context.

### Full Financial Data:
${formatted}
`;

  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${import.meta.env.VITE_OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: "gpt-4o",
      messages: [{ role: "user", content: prompt }],
      temperature: 0.4,
    }),
  });

  const json = await res.json();
  return json.choices?.[0]?.message?.content || "No summary generated.";
};


export const useAISummary = (
  ticker: string,
  metric: string,
  data: CompanyDataRow[]
) => {
  return useQuery({
    queryKey: ["ai-summary", ticker, metric],
    queryFn: () => generateAISummary(ticker, metric, data),
    enabled: !!ticker && !!metric && data.length > 0,
    staleTime: Infinity,
  });
};
