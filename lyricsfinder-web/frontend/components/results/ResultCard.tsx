'use client'

import { useRouter } from 'next/navigation'
import { Play, FileText, X } from 'lucide-react'
import { SearchResult, api } from '@/lib/api'

interface Props {
  result: SearchResult
  rank: number
  queryId: string
  isTop: boolean
}

export function ResultCard({ result, rank, queryId, isTop }: Props) {
  const router = useRouter()
  const pct = Math.round(result.confidence_score * 100)
  const badgeStyle = pct >= 85
    ? { background: '#dcfce7', color: '#15803d' }
    : pct >= 60
    ? { background: '#fef9c3', color: '#a16207' }
    : { background: '#fee2e2', color: '#b91c1c' }

  const handlePlay = (e: React.MouseEvent) => {
    e.stopPropagation()
    const url = result.audio_preview?.spotify_preview_url
    if (url) new Audio(url).play()
    else alert('Pas de preview disponible')
  }

  const handleWrong = async (e: React.MouseEvent) => {
    e.stopPropagation()
    await api.sendFeedback({ query_id: queryId, track_id: result.track_id, is_correct: false })
  }

  return (
    <article
      onClick={() => router.push(`/track/${result.track_id}`)}
      className="rounded-2xl border p-4 cursor-pointer transition-all active:scale-[0.99] bg-white"
      style={{ borderColor: isTop ? 'var(--primary)' : 'var(--border)', borderWidth: isTop ? '1.5px' : '1px' }}
    >
      {isTop && (
        <span className="inline-block text-xs px-2 py-0.5 rounded-full mb-2 font-medium"
              style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
          Meilleur résultat
        </span>
      )}

      <div className="flex gap-3 items-start">
        <div className="w-11 h-11 rounded-xl flex items-center justify-center text-xl flex-shrink-0"
             style={{ background: 'var(--surface)' }}>🎵</div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{result.title}</p>
          <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--muted)' }}>
            {result.artist}{result.release_year && ` · ${result.release_year}`}
          </p>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0" style={badgeStyle}>
          {pct}%
        </span>
      </div>

      {/* Snippet */}
      <div className="mt-3 rounded-xl px-3 py-2 text-sm"
           style={{ background: 'var(--surface)', borderLeft: '2.5px solid var(--primary)' }}>
        <p style={{ color: 'var(--primary)', fontWeight: 500 }}>{result.best_segment.text}</p>
      </div>

      {/* Actions */}
      <div className="mt-3 flex gap-2">
        {result.audio_preview?.spotify_preview_url && (
          <button onClick={handlePlay}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-white"
            style={{ background: '#1DB954' }}>
            <Play size={12} /> Preview
          </button>
        )}
        <button onClick={e => { e.stopPropagation(); router.push(`/track/${result.track_id}`) }}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs border"
          style={{ borderColor: 'var(--border)' }}>
          <FileText size={12} /> Paroles
        </button>
        <button onClick={handleWrong}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs border ml-auto"
          style={{ borderColor: '#fecaca', color: 'var(--danger)' }}>
          <X size={12} /> Mauvaise
        </button>
      </div>
    </article>
  )
}
