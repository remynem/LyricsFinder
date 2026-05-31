'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Search, X, SlidersHorizontal, Music2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, getErrorMessage } from '@/lib/api'
import { useStore } from '@/lib/store'

const HINTS = [
  'comme un petit cœur qui bat',
  'somewhere over the rainbow',
  'la la la',
  'Freude schöner Götterfunken',
]

export default function HomePage() {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const { setResults, setLastQuery, filters, setFilters } = useStore()

  const handleSearch = async (q = query) => {
    const trimmed = q.trim()
    if (!trimmed) { inputRef.current?.focus(); return }
    setLoading(true)
    try {
      const res = await api.search({
        query_text: trimmed,
        top_k: 10,
        use_translation: filters.useTranslation,
        filter_language: filters.language || undefined,
        filter_year_min: filters.yearMin || undefined,
        filter_year_max: filters.yearMax || undefined,
      })
      setResults(res.results)
      setLastQuery({ text: trimmed, queryId: res.query_id, detectedLang: res.detected_language })
      router.push('/results')
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 pb-24 pt-16 bg-white">
      {/* Logo */}
      <div className="mb-8 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4"
             style={{ background: 'var(--primary-light)' }}>
          <Music2 size={32} style={{ color: 'var(--primary)' }} />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">LyricsFinder</h1>
        <p className="mt-1 text-sm" style={{ color: 'var(--muted)' }}>
          Tape un fragment, on trouve la chanson
        </p>
      </div>

      {/* Search box */}
      <div className="w-full max-w-lg">
        <div className="flex items-center gap-2 px-4 py-3 rounded-2xl border"
             style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
          <Search size={18} style={{ color: 'var(--muted)', flexShrink: 0 }} />
          <input
            ref={inputRef}
            type="text"
            className="flex-1 bg-transparent text-base outline-none"
            placeholder="comme un petit cœur qui bat…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
          />
          {query && (
            <button onClick={() => setQuery('')} aria-label="Effacer">
              <X size={16} style={{ color: 'var(--muted)' }} />
            </button>
          )}
          <button onClick={() => setShowFilters(v => !v)} aria-label="Filtres">
            <SlidersHorizontal size={16} style={{ color: showFilters ? 'var(--primary)' : 'var(--muted)' }} />
          </button>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="mt-3 p-4 rounded-2xl border" style={{ borderColor: 'var(--border)' }}>
            <div className="grid grid-cols-2 gap-3">
              <select
                value={filters.language}
                onChange={e => setFilters({ language: e.target.value })}
                className="border rounded-xl px-3 py-2 text-sm outline-none"
                style={{ borderColor: 'var(--border)' }}
              >
                <option value="">Toutes langues</option>
                <option value="fr">Français</option>
                <option value="en">English</option>
                <option value="es">Español</option>
                <option value="de">Deutsch</option>
              </select>
              <div className="flex gap-2">
                <input type="number" placeholder="De" min={1900} max={2025}
                  value={filters.yearMin ?? ''}
                  onChange={e => setFilters({ yearMin: e.target.value ? +e.target.value : null })}
                  className="flex-1 border rounded-xl px-3 py-2 text-sm outline-none"
                  style={{ borderColor: 'var(--border)' }}
                />
                <input type="number" placeholder="À" min={1900} max={2025}
                  value={filters.yearMax ?? ''}
                  onChange={e => setFilters({ yearMax: e.target.value ? +e.target.value : null })}
                  className="flex-1 border rounded-xl px-3 py-2 text-sm outline-none"
                  style={{ borderColor: 'var(--border)' }}
                />
              </div>
            </div>
            <label className="flex items-center gap-2 mt-3 cursor-pointer text-sm">
              <input type="checkbox" checked={filters.useTranslation}
                onChange={e => setFilters({ useTranslation: e.target.checked })} />
              Traduire la requête
            </label>
          </div>
        )}

        {/* Search button */}
        <button
          onClick={() => handleSearch()}
          disabled={loading || !query.trim()}
          className="w-full mt-3 py-3 rounded-2xl text-white text-sm font-medium transition-all disabled:opacity-50"
          style={{ background: 'var(--primary)' }}
        >
          {loading ? 'Recherche…' : 'Trouver cette chanson'}
        </button>
      </div>

      {/* Hints */}
      <div className="mt-8 w-full max-w-lg">
        <p className="text-xs mb-2" style={{ color: 'var(--muted)' }}>Essaie un fragment…</p>
        <div className="flex flex-wrap gap-2">
          {HINTS.map(h => (
            <button key={h} onClick={() => { setQuery(h); handleSearch(h) }}
              className="text-xs px-3 py-1.5 rounded-full border transition-colors"
              style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
              {h}
            </button>
          ))}
        </div>
      </div>
    </main>
  )
}
