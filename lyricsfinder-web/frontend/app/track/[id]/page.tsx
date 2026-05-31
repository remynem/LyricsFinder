'use client'

import { useRouter, useParams } from 'next/navigation'
import { ArrowLeft, Share2, Play, Pause, ExternalLink } from 'lucide-react'
import toast from 'react-hot-toast'
import { useState } from 'react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'

export default function TrackPage() {
  const router = useRouter()
  const { id } = useParams<{ id: string }>()
  const { results, lastQuery } = useStore()
  const [playing, setPlaying] = useState(false)
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null)

  // Get data directly from search results in memory — no DB call needed
  const match = results.find(r => r.track_id === id)

  if (!match) {
    return (
      <main className="min-h-screen bg-white flex flex-col items-center justify-center p-8">
        <div className="text-4xl mb-4">🎵</div>
        <p className="font-medium">Chanson introuvable</p>
        <button onClick={() => router.back()} className="mt-4 text-sm underline" style={{ color: 'var(--primary)' }}>
          Retour aux résultats
        </button>
      </main>
    )
  }

  const togglePlay = () => {
    const url = match.audio_preview?.spotify_preview_url
    if (!url) { toast('Pas de preview disponible'); return }
    if (!audio) {
      const a = new Audio(url)
      a.onended = () => setPlaying(false)
      a.play(); setAudio(a); setPlaying(true)
    } else if (playing) { audio.pause(); setPlaying(false) }
    else { audio.play(); setPlaying(true) }
  }

  const handleShare = async () => {
    try { await navigator.share({ title: match.title, url: window.location.href }) }
    catch { navigator.clipboard.writeText(window.location.href); toast.success('Lien copié') }
  }

  const handleFeedback = async (ok: boolean) => {
    if (!lastQuery) return
    await api.sendFeedback({ query_id: lastQuery.queryId, track_id: id, is_correct: ok })
    toast(ok ? '👍 Merci !' : '👎 Noté')
    if (!ok) router.back()
  }

  const pct = Math.round(match.confidence_score * 100)

  // Build lyrics display from context
  const contextLines = match.best_segment.context
    ? match.best_segment.context.split('\n')
    : [match.best_segment.text]

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
          <h1 className="text-xl font-semibold">{match.title}</h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--muted)' }}>
            {match.artist}
            {match.release_year && ` · ${match.release_year}`}
            {match.language && ` · ${match.language.toUpperCase()}`}
          </p>
          <span className="inline-block mt-2 text-xs px-2 py-0.5 rounded-full font-medium"
                style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
            {pct}% de confiance
          </span>

          <div className="mt-4 flex justify-center gap-2 flex-wrap">
            <button onClick={togglePlay}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-white"
              style={{ background: 'var(--primary)' }}>
              {playing ? <Pause size={16} /> : <Play size={16} />}
              {playing ? 'Pause' : 'Preview'}
            </button>
          </div>
        </div>

        {/* Matched segment highlighted */}
        <div className="px-4 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
          <p className="text-xs font-medium mb-3 uppercase tracking-wide" style={{ color: 'var(--muted)' }}>
            Fragment correspondant
          </p>
          <div className="rounded-xl px-4 py-3 space-y-1"
               style={{ background: 'var(--surface)', borderLeft: '3px solid var(--primary)' }}>
            {contextLines.map((line, i) => {
              const isMatch = line.toLowerCase().includes(
                match.best_segment.text.toLowerCase().slice(0, 15)
              )
              return (
                <p key={i} className="text-sm leading-relaxed"
                   style={{ color: isMatch ? 'var(--primary)' : 'var(--muted)', fontWeight: isMatch ? 600 : 400 }}>
                  {line || '\u00A0'}
                </p>
              )
            })}
          </div>
        </div>

        {/* Full context as lyrics excerpt */}
        <div className="px-4 py-4">
          <p className="text-xs font-medium mb-3 uppercase tracking-wide" style={{ color: 'var(--muted)' }}>
            Extrait de paroles
          </p>
          <div className="space-y-1">
            {contextLines.map((line, i) => (
              <p key={i} className="text-sm leading-loose" style={{ color: 'var(--text)' }}>
                {line || '\u00A0'}
              </p>
            ))}
          </div>
          <p className="mt-6 text-xs" style={{ color: 'var(--muted)' }}>
            © {match.artist}. Extrait via LyricsFinder. Tous droits réservés.
          </p>
        </div>

        {/* Feedback */}
        <div className="px-4 pb-10 flex gap-2">
          <button onClick={() => handleFeedback(true)}
            className="flex-1 py-2.5 rounded-xl text-sm border transition-colors hover:bg-gray-50"
            style={{ borderColor: 'var(--border)' }}>
            👍 C'est la bonne
          </button>
          <button onClick={() => handleFeedback(false)}
            className="flex-1 py-2.5 rounded-xl text-sm border transition-colors"
            style={{ borderColor: '#fecaca', color: 'var(--danger)' }}>
            👎 Ce n'est pas la bonne
          </button>
        </div>
      </div>
    </main>
  )
}
