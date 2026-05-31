'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import { useStore } from '@/lib/store'
import { ResultCard } from '@/components/results/ResultCard'

export default function ResultsPage() {
  const router = useRouter()
  const { results, lastQuery } = useStore()

  useEffect(() => { if (!lastQuery) router.replace('/') }, [lastQuery, router])
  if (!lastQuery) return null

  return (
    <main className="min-h-screen bg-white">
      <header className="sticky top-0 z-10 bg-white border-b px-4 py-3 flex items-center gap-3"
              style={{ borderColor: 'var(--border)' }}>
        <button onClick={() => router.back()} className="p-1" aria-label="Retour">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">"{lastQuery.text}"</p>
          <p className="text-xs" style={{ color: 'var(--muted)' }}>
            {results.length} résultat{results.length > 1 ? 's' : ''} · {lastQuery.detectedLang.toUpperCase()} détecté
          </p>
        </div>
      </header>

      <div className="px-4 py-3 pb-10 space-y-3 fade-in">
        {results.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-4xl mb-4">🎵</div>
            <p className="font-medium">Aucun résultat</p>
            <p className="text-sm mt-1" style={{ color: 'var(--muted)' }}>
              Essaie avec plus de mots ou active la traduction
            </p>
          </div>
        ) : (
          results.map((r, i) => (
            <ResultCard key={r.track_id} result={r} rank={i} queryId={lastQuery.queryId} isTop={i === 0} />
          ))
        )}
        {results.length > 0 && (
          <p className="text-center text-xs py-4" style={{ color: 'var(--muted)' }}>
            Extraits via Musixmatch · © Tous droits réservés
          </p>
        )}
      </div>
    </main>
  )
}
