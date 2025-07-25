import { useEffect, useState } from "react";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { Skeleton } from "@/components/ui/skeleton";

type CompanyMeta = {
  name: string;
  ticker: string;
  ir_url: string;
};

type NavbarProps = {
  tabs: string[];
  activeTab: string;
  onSelect: (tab: string) => void;
};

export default function Navbar({ tabs, activeTab, onSelect }: NavbarProps) {
  const [metadata, setMetadata] = useState<Record<string, CompanyMeta>>({});

  useEffect(() => {
    const cached = localStorage.getItem("company_metadata");
    if (cached) {
      setMetadata(JSON.parse(cached));
    } else {
      Promise.all(
        tabs.map((ticker) =>
          fetch(
            `${import.meta.env.VITE_API_BASE_URL}/api/company/${ticker}/meta`,
            {
              headers: {
                "ngrok-skip-browser-warning": "true",
              },
            }
          )
            .then((res) => res.json())
            .then((data) => ({ [ticker]: data }))
        )
      ).then((metaArray) => {
        const combined = Object.assign({}, ...metaArray);
        console.log("Fetched metadata:", combined); // ✅ Log
        setMetadata(combined);
        localStorage.setItem("company_metadata", JSON.stringify(combined));
      });
    }
  }, [tabs]);

  return (
    <div className="flex space-x-4 mb-4 border-b">
      {tabs.map((tab) => (
        <HoverCard key={tab}>
          <HoverCardTrigger asChild>
            <button
              className={`px-4 py-2 ${
                activeTab === tab
                  ? "border-b-2 border-black font-semibold"
                  : "text-gray-500"
              }`}
              onClick={() => onSelect(tab)}
            >
              {tab}
            </button>
          </HoverCardTrigger>
          <HoverCardContent className="w-80">
            {metadata[tab] ? (
              <div>
                <p className="text-lg font-semibold">{metadata[tab].name}</p>
                <p className="text-sm text-muted-foreground">Ticker: {tab}</p>
                <a
                  className="text-blue-600 text-sm underline mt-1 inline-block"
                  href={metadata[tab].ir_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Investor Relations
                </a>
              </div>
            ) : (
              <Skeleton className="h-16 w-full" />
            )}
          </HoverCardContent>
        </HoverCard>
      ))}
    </div>
  );
}
