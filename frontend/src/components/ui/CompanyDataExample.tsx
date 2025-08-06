import { useCompanyData } from "@/api/companyApi";
import type { CompanyTicker } from "@/api/companyApi";

interface CompanyDataExampleProps {
  ticker: CompanyTicker;
}

export default function CompanyDataExample({
  ticker,
}: CompanyDataExampleProps) {
  const { data, isLoading, error, isError, refetch } = useCompanyData(ticker);

  return (
    <div className="p-4 border rounded-lg">
      <h3 className="text-lg font-semibold mb-4">Company Data for {ticker}</h3>

      <div className="space-y-4">
        {isLoading && <div className="text-blue-600">Loading...</div>}

        {isError && (
          <div className="text-red-600">
            <p>Error: {error?.message}</p>
            <button
              onClick={() => refetch()}
              className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        )}

        {data && (
          <div>
            <div className="text-green-600 mb-2">
              ✓ Data loaded successfully
            </div>
            <div className="text-sm text-gray-600">
              Records: {data.data?.length || 0}
            </div>
            <button
              onClick={() => refetch()}
              className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Refresh Data
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
