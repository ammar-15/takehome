import { useEffect, useState } from "react";
import CompanyDataComponent from "@/components/CompanyDataComponent";
import FinancialDashboard from "@/components/custom/financial-dashboard";
import { useCompanyData } from "@/api/companyApi";
import Navbar from "@/components/Navbar";
import { useCompanyMeta, type CompanyTicker } from "@/api/companyApi";
import { TailwindBackground } from "@/components/ui/TailwindBackground";
const DEFAULT_TABS = ["ASML", "AYDEN", "ROG"];
const STORAGE_KEY_TABS = "dynamicTabs";
const STORAGE_KEY_ACTIVE = "activeTab";

export default function Home() {
  const [viewMode, setViewMode] = useState<"table" | "chart">("table");
  const [tabs, setTabs] = useState<string[]>(() => {
    const storedTabs = JSON.parse(
      localStorage.getItem(STORAGE_KEY_TABS) || "null"
    );
    return storedTabs && Array.isArray(storedTabs)
      ? [...DEFAULT_TABS, ...storedTabs]
      : DEFAULT_TABS;
  });

  const [activeTab, setActiveTab] = useState(() => {
    return localStorage.getItem(STORAGE_KEY_ACTIVE) || "ASML";
  });

  const { data } = useCompanyMeta(activeTab);

  const {
    data: companyData,
    isLoading,
    isError,
  } = useCompanyData(activeTab as CompanyTicker);

  useEffect(() => {
    const storedTabs = JSON.parse(
      localStorage.getItem(STORAGE_KEY_TABS) || "null"
    );
    const storedActive = localStorage.getItem(STORAGE_KEY_ACTIVE);

    if (storedTabs && Array.isArray(storedTabs))
      setTabs([...DEFAULT_TABS, ...storedTabs]);
    if (storedActive) setActiveTab(storedActive);
  }, []);

  return (
    <>
      <TailwindBackground />

      <div className="p-4 mx-auto max-w-6xl">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-4xl font-bold">
            Take Home Assignment by Ammar Faruqui
          </h1>
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode("table")}
              className={`px-3 py-1 rounded-md text-sm font-medium ${
                viewMode === "table"
                  ? "bg-slate-800 text-white"
                  : "bg-slate-100 text-slate-800"
              }`}
            >
              Table View
            </button>
            <button
              onClick={() => setViewMode("chart")}
              className={`px-3 py-1 rounded-md text-sm font-medium ${
                viewMode === "chart"
                  ? "bg-slate-800 text-white"
                  : "bg-slate-100 text-slate-800"
              }`}
            >
              Chart View
            </button>
          </div>
        </div>

        <Navbar tabs={tabs} activeTab={activeTab} onSelect={setActiveTab} />

        {tabs.includes(activeTab) && (
          <div className="flex flex-col justify-start items-start">
            <div className="flex flex-row items-start justify-between w-full p-2 bg-muted rounded-md">
              <div>
                {data?.name}{" "}
                <span className="text-sm text-muted-foreground font-style: italic">
                  (data is in EUR in millions)
                </span>
              </div>
              <div className="text-sm text-muted-foreground">
                Source:{" "}
                <a
                  href={data?.ir_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {data?.ir_url}
                </a>
              </div>
            </div>
            {isLoading ? (
              <div className="p-8 text-center">Loading {activeTab} data...</div>
            ) : isError || !companyData ? (
              <div className="p-8 text-center text-red-600">
                Error loading data for {activeTab}. Please try again.
              </div>
            ) : viewMode === "table" ? (
              <CompanyDataComponent ticker={activeTab as CompanyTicker} />
            ) : (
              <FinancialDashboard data={companyData.data} ticker={activeTab} />
            )}
          </div>
        )}
      </div>
    </>
  );
}
