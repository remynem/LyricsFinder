import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { SearchResult } from './api'

interface LastQuery { text: string; queryId: string; detectedLang: string }
interface Filters { language: string; yearMin: number | null; yearMax: number | null; useTranslation: boolean }

interface Store {
  results: SearchResult[]
  lastQuery: LastQuery | null
  filters: Filters
  history: LastQuery[]
  setResults: (r: SearchResult[]) => void
  setLastQuery: (q: LastQuery) => void
  setFilters: (f: Partial<Filters>) => void
}

export const useStore = create<Store>()(
  persist(
    (set) => ({
      results: [],
      lastQuery: null,
      filters: { language: '', yearMin: null, yearMax: null, useTranslation: false },
      history: [],
      setResults: (results) => set({ results }),
      setLastQuery: (query) => set((s) => ({
        lastQuery: query,
        history: [query, ...s.history.filter(h => h.text !== query.text)].slice(0, 20),
      })),
      setFilters: (f) => set((s) => ({ filters: { ...s.filters, ...f } })),
    }),
    { name: 'lyricsfinder', partialize: (s) => ({ filters: s.filters, history: s.history }) }
  )
)
