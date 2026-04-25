'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

export type PersonaCatalogItem = {
  slug: string;
  label: string;
  icon: string;
  description: string;
};

type PersonaCatalogContextValue = {
  catalog: PersonaCatalogItem[];
  isLoading: boolean;
};

const PersonaCatalogContext = createContext<PersonaCatalogContextValue>({
  catalog: [],
  isLoading: true,
});

export function PersonaCatalogProvider({ children }: { children: ReactNode }) {
  const [catalog, setCatalog] = useState<PersonaCatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const API = process.env.NEXT_PUBLIC_API_URL ?? '';
    fetch(`${API}/users/personas/catalog`)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setCatalog(data);
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <PersonaCatalogContext.Provider value={{ catalog, isLoading }}>
      {children}
    </PersonaCatalogContext.Provider>
  );
}

export function usePersonaCatalog() {
  return useContext(PersonaCatalogContext);
}
