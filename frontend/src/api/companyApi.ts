import { useQuery } from '@tanstack/react-query';

export type CompanyTicker = string;

interface CompanyData {
  data: any[];
}

interface CompanyMeta {
  name: string;
  ticker: string;
  ir_url: string;
}

const fetchCompanyData = async (ticker: string): Promise<CompanyData> => {
  const url = `${import.meta.env.VITE_API_BASE_URL}/api/company/${ticker}`;
  
  const response = await fetch(url, {
    headers: {
      "ngrok-skip-browser-warning": "true",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch data for ${ticker}`);
  }

  return response.json();
};

const fetchCompanyMeta = async (ticker: string): Promise<CompanyMeta> => {
  const url = `${import.meta.env.VITE_API_BASE_URL}/api/company/${ticker}/meta`;
  
  const response = await fetch(url, {
    headers: {
      "ngrok-skip-browser-warning": "true",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch metadata for ${ticker}`);
  }

  return response.json();
};

export const useCompanyData = (ticker: string) => {
  return useQuery({
    queryKey: ['company', ticker],
    queryFn: () => fetchCompanyData(ticker),
    enabled: !!ticker,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useCompanyMeta = (ticker: string) => {
  return useQuery({
    queryKey: ['company-meta', ticker],
    queryFn: () => fetchCompanyMeta(ticker),
    enabled: !!ticker,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}; 