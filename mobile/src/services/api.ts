/**
 * API service — wraps the FastAPI backend.
 * All calls go through this module; swap base URL via env vars.
 */

import axios, { AxiosError } from 'axios';
import Constants from 'expo-constants';

const BASE_URL =
  Constants.expoConfig?.extra?.apiUrl ??
  process.env.EXPO_PUBLIC_API_URL ??
  'http://localhost:8000';

const API_KEY =
  Constants.expoConfig?.extra?.apiKey ??
  process.env.EXPO_PUBLIC_API_KEY ??
  'dev-key';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
});

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SearchRequest {
  query_text: string;
  top_k?: number;
  language_hint?: string;
  use_translation?: boolean;
  filter_year_min?: number;
  filter_year_max?: number;
  filter_language?: string;
}

export interface AudioPreview {
  spotify_preview_url: string | null;
  spotify_track_url: string | null;
}

export interface BestSegment {
  text: string;
  line_offset: number;
  context: string;
}

export interface SearchResult {
  track_id: string;
  title: string;
  artist: string;
  album: string | null;
  release_year: number | null;
  language: string | null;
  confidence_score: number;
  best_segment: BestSegment;
  audio_preview: AudioPreview | null;
}

export interface SearchResponse {
  query_id: string;
  detected_language: string;
  results: SearchResult[];
  total: number;
  latency_ms: number;
}

export interface TrackDetail {
  track_id: string;
  title: string;
  artist: string;
  album: string | null;
  release_year: number | null;
  language: string | null;
  lyrics_excerpt: string; // Licence-limited excerpt
  full_lyrics_available: boolean;
  segments: { text: string; line_offset: number }[];
  audio_preview: AudioPreview | null;
  external_links: {
    spotify?: string;
    apple_music?: string;
    genius?: string;
  };
}

// ─── API calls ────────────────────────────────────────────────────────────────

export const api = {
  async search(req: SearchRequest): Promise<SearchResponse> {
    const { data } = await client.post<SearchResponse>('/search', req);
    return data;
  },

  async getTrack(trackId: string): Promise<TrackDetail> {
    const { data } = await client.get<TrackDetail>(`/track/${trackId}`);
    return data;
  },

  async sendFeedback(params: {
    query_id: string;
    track_id: string;
    is_correct: boolean;
    clicked_position?: number;
  }): Promise<void> {
    await client.post('/feedback', params);
  },
};

// ─── Error handling ───────────────────────────────────────────────────────────

export function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.response?.data?.detail) {
      return String(error.response.data.detail);
    }
    if (error.code === 'ECONNABORTED') return 'Request timed out. Try again.';
    if (!error.response) return 'No connection to server.';
    return `Server error ${error.response.status}`;
  }
  if (error instanceof Error) return error.message;
  return 'Unknown error';
}
