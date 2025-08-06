import { useCompanyData, type CompanyTicker } from "@/api/companyApi";
import FinancialDashboard from "@/components/custom/financial-dashboard";
import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function AnalysisPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<CompanyTicker>("ASML");
  const { data, isLoading, isError } = useCompanyData(activeTab);

  return (
    <div className="p-4 mx-auto max-w-6xl">
      <div className="flex justify-between">
        <h1 className="text-4xl font-bold text-center mb-6">
          Take Home Assignment by Ammar Faruqui
        </h1>
        <Button className="ml-auto" onClick={() => navigate("/")}>
          Home
        </Button>
      </div>
      <Navbar
        tabs={["ASML", "ADYEN", "ROG"]}
        activeTab={activeTab}
        onSelect={(tab) => setActiveTab(tab as CompanyTicker)}
      />
      {isLoading ? (
        <div className="flex justify-center items-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2">Loading ASML data...</span>
        </div>
      ) : isError || !data ? (
        <div className="flex justify-center items-center p-8">
          <div className="text-red-600">
            Error loading ASML data. Please contact meeee, since something might
            be down 😔
          </div>
        </div>
      ) : (
        <>
          <FinancialDashboard data={data.data} ticker={activeTab} />
        </>
      )}
    </div>
  );
}
