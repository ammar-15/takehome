import { useEffect, useState } from "react";
import CompanyDataComponent from "@/components/CompanyDataComponent";
import Navbar from "@/components/Navbar";
import { useCompanyMeta, type CompanyTicker } from "@/api/companyApi";
import { TailwindBackground } from "@/components/ui/TailwindBackground";

const DEFAULT_TABS = ["ASML", "AYDEN", "ROG"];
const STORAGE_KEY_TABS = "dynamicTabs";
const STORAGE_KEY_ACTIVE = "activeTab";

export default function Home() {
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
      <div className="flex justify-between">
        <h1 className="text-4xl font-bold text-center mb-6">
          Take Home Assignment by Ammar Faruqui
        </h1>
      </div>
      <Navbar tabs={tabs} activeTab={activeTab} onSelect={setActiveTab} />

      {tabs.includes(activeTab) && (
        <div className="flex flex-col justify-start items-start">
          <div className="flex flex-row items-start justify-between w-full p-2 bg-muted rounded-md">
            {data?.name}
            <div className="text-sm text-muted-foreground">
              Source:{" "}
              <a href={data?.ir_url} target="_blank" rel="noopener noreferrer">
                {data?.ir_url}
              </a>
            </div>
          </div>
          <CompanyDataComponent ticker={activeTab as CompanyTicker} />
        </div>
      )}
    </div>
    </>
  );
}
