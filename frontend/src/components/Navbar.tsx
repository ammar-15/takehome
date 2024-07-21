type NavbarProps = {
  tabs: string[];
  activeTab: string;
  onSelect: (tab: string) => void;
};

export default function Navbar({ tabs, activeTab, onSelect }: NavbarProps) {
  return (
    <div className="flex space-x-4 mb-4 border-b">
      {tabs.map((tab) => (
        <button
          key={tab}
          className={`px-4 py-2 ${
            activeTab === tab ? "border-b-2 border-black font-semibold" : "text-gray-500"
          }`}
          onClick={() => onSelect(tab)}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
