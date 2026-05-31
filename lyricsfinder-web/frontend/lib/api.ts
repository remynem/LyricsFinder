import axios, { AxiosError } from 'axios'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const API_KEY  = process.env.NEXT_PUBLIC_API_KEY  ?? 'dev-key'

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 20_000,
  headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
})

export interface SearchResult {
  track_id: string
  title: string
  artist: string
  album: string | null
  release_year: number | null
  language: string | null
  confidence_score: number
  best_segment: { text: string; line_offset: number; context: string }
  audio_preview: { spotify_preview_url: string | null; spotify_track_url: string | null } | null
}

export interface SearchResponse {
  query_id: string
  detected_language: string
  results: SearchResult[]
  total: number
  latency_ms: number
}

export interface TrackDetail {
  track_id: string
  title: string
  artist: string
  album: string | null
  release_year: number | null
  language: string | null
  lyrics_excerpt: string
  full_lyrics_available: boolean
  audio_preview: { spotify_preview_url: string | null; spotify_track_url: string | null } | null
  external_links: { spotify?: string }
}

export const api = {
  async search(params: {
    query_text: string
    top_k?: number
    use_translation?: boolean
    filter_language?: string
    filter_year_min?: number
    filter_year_max?: number
  }): Promise<SearchResponse> {
    const { data } = await client.post<SearchResponse>('/search', params)
    return data
  },

  async getTrack(trackId: string): Promise<TrackDetail> {
    const { data } = await client.get<TrackDetail>(`/track/${trackId}`)
    return data
  },

  async sendFeedback(p: { query_id: string; track_id: string; is_correct: boolean }): Promise<void> {
    await client.post('/feedback', p)
  },
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.response?.data?.detail) return String(error.response.data.detail)
    if (!error.response) return 'Impossible de joindre le serveur.'
    return `Erreur ${error.response.status}`
  }
  if (error instanceof Error) return error.message
  return 'Erreur inconnue'
}
