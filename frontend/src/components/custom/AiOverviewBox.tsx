import { useCompanyData } from "@/api/companyApi";
import { useAISummary } from "@/api/aiClient"; 
import brain from "../../../public/brain.svg";

type Props = {
  ticker: string;
  metric: string;
};

type CompanyDataRow = {
  year: number;
  statement_type: string;
  metric: string;
  value: number;
};

export default function AiOverviewBox({ ticker, metric }: Props) {
  const { data: rawData, isLoading: isDataLoading, isError } = useCompanyData(ticker);
  const rows = (rawData?.data ?? []) as CompanyDataRow[];

  const { data: summary, isLoading, isError: isSummaryError } = useAISummary(
    ticker,
    metric,
    rows
  );

  if (isDataLoading || isLoading) {
    return (
      <div className="mt-4 text-sm italic text-slate-500">
         Loading AI overview...🥀
      </div>
    );
  }

  if (isError || isSummaryError) {
    return (
      <div className="mt-4 text-sm text-red-500">
        Failed to load overview. 😭
      </div>
    );
  }

  return (
    <div className="mt-6 bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm leading-relaxed text-slate-800">
      <div className="flex items-center mb-2">
      <img src={brain} alt="AI Brain" className="w-6 h-6 inline-block mr-2" />
      <p className="font-medium text-slate-700 items-center">AI Overview:</p>
      </div>
      <p>{summary}</p>
    </div>
  );
}
