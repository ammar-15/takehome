import { useCompanyData, type CompanyTicker } from "@/api/companyApi";
import CompiledTable from "@/components/CompiledTable";

interface CompanyDataComponentProps {
  ticker: CompanyTicker;
}

export default function CompanyDataComponent({
  ticker,
}: CompanyDataComponentProps) {
  const { data, isLoading, isError } = useCompanyData(ticker);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Loading {ticker} data...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="text-red-600">
          <p>
            Error loading {ticker} data. Please contact meeee, since something
            might be down 😔
          </p>
        </div>
      </div>
    );
  }

  return <CompiledTable ticker={ticker} data={data?.data || null} />;
}
