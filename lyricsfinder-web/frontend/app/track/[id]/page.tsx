'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { ArrowLeft, Share2, Play, Pause, ExternalLink } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, TrackDetail, getErrorMessage } from '@/lib/api'
import { useStore } from '@/lib/store'

export default function TrackPage() {
  const router = useRouter()
  const { id } = useParams<{ id: string }>()
  const [track, setTrack] = useState<TrackDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [playing, setPlaying] = useState(false)
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null)
  const { results, lastQuery } = useStore()
  const match = results.find(r => r.track_id === id)

  useEffect(() => {
    api.getTrack(id)
      .then(setTrack)
      .catch(e => toast.error(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [id])

  const togglePlay = () => {
    const url = track?.audio_preview?.spotify_preview_url
    if (!url) { toast('Pas de preview disponible'); return }
    if (!audio) {
      const a = new Audio(url)
      a.onended = () => setPlaying(false)
      a.play(); setAudio(a); setPlaying(true)
    } else if (playing) { audio.pause(); setPlaying(false) }
    else { audio.play(); setPlaying(true) }
  }

  const handleShare = async () => {
    try { await navigator.share({ title: track?.title, url: window.location.href }) }
    catch { navigator.clipboard.writeText(window.location.href); toast.success('Lien copié') }
  }

  const handleFeedback = async (ok: boolean) => {
    if (!lastQuery) return
    await api.sendFeedback({ query_id: lastQuery.queryId, track_id: id, is_correct: ok })
    toast(ok ? '👍 Merci !' : '👎 Noté')
    if (!ok) router.back()
  }

  if (loading) return (
    <div className="p-4 space-y-4">
      <div className="skeleton h-6 w-32" />
      <div className="skeleton h-20 w-20 rounded-2xl mx-auto" />
      <div className="skeleton h-5 w-48 mx-auto" />
      <div className="skeleton h-32 w-full rounded-xl" />
    </div>
  )

  return (
    <main className="min-h-screen bg-white">
      <header className="sticky top-0 z-10 bg-white border-b px-4 py-3 flex items-center gap-3"
              style={{ borderColor: 'var(--border)' }}>
        <button onClick={() => router.back()} className="p-1" aria-label="Retour">
          <ArrowLeft size={20} />
        </button>
        <span className="flex-1 text-sm font-medium">Détail</span>
        <button onClick={handleShare} className="p-1" aria-label="Partager">
          <Share2 size={18} />
        </button>
      </header>

      <div className="fade-in">
        {/* Hero */}
        <div className="px-4 py-6 text-center border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl mb-4 text-4xl"
               style={{ background: 'var(--primary-light)' }}>🎵</div>
          <h1 className="text-xl font-semibold">{track?.title}</h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--muted)' }}>
            {track?.artist}{track?.release_year && ` · ${track.release_year}`}
          </p>
          {match && (
            <span className="inline-block mt-2 text-xs px-2 py-0.5 rounded-full font-medium"
                  style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
              {Math.round(match.confidence_score * 100)}% de confiance
            </span>
          )}
          <div className="mt-4 flex justify-center gap-2 flex-wrap">
            <button onClick={togglePlay}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-white"
              style={{ background: 'var(--primary)' }}>
              {playing ? <Pause size={16} /> : <Play size={16} />}
              {playing ? 'Pause' : 'Preview'}
            </button>
            {track?.external_links?.spotify && (
              <a href={track.external_links.spotify} target="_blank" rel="noopener noreferrer"
                 className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm border"
                 style={{ borderColor: 'var(--border)' }}>
                <ExternalLink size={14} /> Spotify
              </a>
            )}
          </div>
        </div>

        {/* Matched segment */}
        {match && (
          <div className="px-4 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
            <p className="text-xs font-medium mb-2 uppercase tracking-wide" style={{ color: 'var(--muted)' }}>
              Fragment correspondant
            </p>
            <div className="rounded-xl px-3 py-2" style={{ background: 'var(--surface)', borderLeft: '2.5px solid var(--primary)' }}>
              <p className="text-sm font-medium" style={{ color: 'var(--primary)' }}>{match.best_segment.text}</p>
            </div>
          </div>
        )}

        {/* Lyrics */}
        <div className="px-4 py-4">
          <p className="text-xs font-medium mb-3 uppercase tracking-wide" style={{ color: 'var(--muted)' }}>
            Paroles (extrait)
          </p>
          {track?.lyrics_excerpt ? (
            <div className="space-y-1">
              {track.lyrics_excerpt.split('\n').map((line, i) => (
                <p key={i} className="text-sm leading-relaxed">{line || ' '}</p>
              ))}
            </div>
          ) : (
            <p className="text-sm" style={{ color: 'var(--muted)' }}>Paroles non disponibles.</p>
          )}
          <p className="mt-4 text-xs" style={{ color: 'var(--muted)' }}>
            © {track?.artist}. Extrait via Musixmatch. Tous droits réservés.
          </p>
        </div>

        {/* Feedback */}
        <div className="px-4 pb-8 flex gap-2">
          <button onClick={() => handleFeedback(true)}
            className="flex-1 py-2 rounded-xl text-sm border" style={{ borderColor: 'var(--border)' }}>
            👍 C'est la bonne
          </button>
          <button onClick={() => handleFeedback(false)}
            className="flex-1 py-2 rounded-xl text-sm border" style={{ borderColor: '#fecaca', color: 'var(--danger)' }}>
            👎 Ce n'est pas la bonne
          </button>
        </div>
      </div>
    </main>
  )
}
