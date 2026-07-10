import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import type {
  AttachmentKind,
  AttachmentPublic,
  ListMoodEntriesParams,
  MoodEntryCreate,
  MoodEntryListResponse,
  MoodEntryPatch,
  MoodEntryPublic,
} from '../types/mood'
import { uploadAttachment } from './upload'

function moodHeaders(): Record<string, string> {
  return apiLocaleHeaders()
}

function buildListQuery(params: ListMoodEntriesParams = {}): string {
  const search = new URLSearchParams()
  if (params.limit !== undefined) {
    search.set('limit', String(params.limit))
  }
  if (params.offset !== undefined) {
    search.set('offset', String(params.offset))
  }
  if (params.recorded_from) {
    search.set('recorded_from', params.recorded_from)
  }
  if (params.recorded_to) {
    search.set('recorded_to', params.recorded_to)
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

export function listMoodEntries(params: ListMoodEntriesParams = {}): Promise<MoodEntryListResponse> {
  return apiRequest<MoodEntryListResponse>(`/v1/mood-entries${buildListQuery(params)}`, {
    auth: true,
    headers: moodHeaders(),
  })
}

export function getMoodEntry(entryId: string): Promise<MoodEntryPublic> {
  return apiRequest<MoodEntryPublic>(`/v1/mood-entries/${entryId}`, {
    auth: true,
    headers: moodHeaders(),
  })
}

export function createMoodEntry(body: MoodEntryCreate): Promise<MoodEntryPublic> {
  return apiRequest<MoodEntryPublic>('/v1/mood-entries', {
    method: 'POST',
    body,
    auth: true,
    headers: moodHeaders(),
  })
}

export function patchMoodEntry(entryId: string, body: MoodEntryPatch): Promise<MoodEntryPublic> {
  return apiRequest<MoodEntryPublic>(`/v1/mood-entries/${entryId}`, {
    method: 'PATCH',
    body,
    auth: true,
    headers: moodHeaders(),
  })
}

export function deleteMoodEntry(entryId: string): Promise<void> {
  return apiRequest<void>(`/v1/mood-entries/${entryId}`, {
    method: 'DELETE',
    auth: true,
    headers: moodHeaders(),
  })
}

export function uploadMoodEntryAttachment(
  entryId: string,
  kind: AttachmentKind,
  file: File,
): Promise<AttachmentPublic> {
  return uploadAttachment(`/v1/mood-entries/${entryId}/attachments`, kind, file)
}

export function deleteMoodEntryAttachment(entryId: string, attachmentId: string): Promise<void> {
  return apiRequest<void>(`/v1/mood-entries/${entryId}/attachments/${attachmentId}`, {
    method: 'DELETE',
    auth: true,
    headers: moodHeaders(),
  })
}

export function getMoodEntryAttachmentUrl(entryId: string, attachmentId: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
  return `${base}/v1/mood-entries/${entryId}/attachments/${attachmentId}`
}
