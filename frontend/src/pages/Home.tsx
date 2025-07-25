import { useEffect, useState } from "react";
import CompiledTable from "@/components/CompiledTable";
import Navbar from "@/components/Navbar";

const DEFAULT_TABS = ["ASML", "AYDEN", "ROG"];
const STORAGE_KEY_TABS = "dynamicTabs";
const STORAGE_KEY_ACTIVE = "activeTab";

export default function Home() {
  const [fetchedData, setFetchedData] = useState<any[] | null>(null);
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

  useEffect(() => {
    const storedTabs = JSON.parse(
      localStorage.getItem(STORAGE_KEY_TABS) || "null"
    );
    const storedActive = localStorage.getItem(STORAGE_KEY_ACTIVE);

    if (storedTabs && Array.isArray(storedTabs))
      setTabs([...DEFAULT_TABS, ...storedTabs]);
    if (storedActive) setActiveTab(storedActive);
  }, []);

  useEffect(() => {
    const customTabs = tabs.filter((tab) => !DEFAULT_TABS.includes(tab));
    localStorage.setItem(STORAGE_KEY_TABS, JSON.stringify(customTabs));
    localStorage.setItem(STORAGE_KEY_ACTIVE, activeTab);
  }, [tabs, activeTab]);

  useEffect(() => {
    if (!activeTab) return;

    fetch(`http://localhost:3001/api/company/${activeTab}`)
      .then((res) => res.json())
      .then((res) => setFetchedData(res.data))
      .catch(() => setFetchedData(null));
  }, [activeTab]);

  return (
    <div className="p-4">
      <h1 className="text-4xl font-bold text-center mb-6">
        Take Home Assignment by Ammar Faruqui
      </h1>
      <Navbar tabs={tabs} activeTab={activeTab} onSelect={setActiveTab} />

      {tabs.includes(activeTab) && (
        <CompiledTable ticker={activeTab} data={fetchedData} />
      )}
    </div>
  );
}
