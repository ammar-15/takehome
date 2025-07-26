import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

type NavbarProps = {
  tabs: string[];
  activeTab: string;
  onSelect: (tab: string) => void;
};

export default function Navbar({ tabs, activeTab, onSelect }: NavbarProps) {
  return (
    <Tabs value={activeTab} onValueChange={onSelect} className="mb-4">
      <TabsList
        className="grid w-fit"
        style={{
          gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))`,
        }}
      >
        {tabs.map((tab) => (
          <TabsTrigger key={tab} value={tab}>
            {tab}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
