import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import { isGuestDiaryMode } from '../lib/guestMode'
import * as guestStore from '../guest/store'
import type {
  NoteTemplateListResponse,
  NoteTemplatePatch,
  NoteTemplatePublic,
  NoteTemplateReorderRequest,
  NoteTemplateWrite,
} from '../types/noteTemplate'

export function listNoteTemplates(): Promise<NoteTemplateListResponse> {
  if (isGuestDiaryMode()) {
    return guestStore.listGuestNoteTemplates()
  }
  return apiRequest<NoteTemplateListResponse>('/v1/note-templates', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function createNoteTemplate(body: NoteTemplateWrite): Promise<NoteTemplatePublic> {
  return apiRequest<NoteTemplatePublic>('/v1/note-templates', {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function patchNoteTemplate(
  templateId: string,
  body: NoteTemplatePatch,
): Promise<NoteTemplatePublic> {
  return apiRequest<NoteTemplatePublic>(`/v1/note-templates/${templateId}`, {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function deleteNoteTemplate(templateId: string): Promise<void> {
  return apiRequest<void>(`/v1/note-templates/${templateId}`, {
    method: 'DELETE',
    auth: true,
  })
}

export function reorderNoteTemplates(
  body: NoteTemplateReorderRequest,
): Promise<NoteTemplateListResponse> {
  return apiRequest<NoteTemplateListResponse>('/v1/note-templates/reorder', {
    method: 'PUT',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}
