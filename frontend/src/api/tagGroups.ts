import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import type {
  ReorderRequest,
  TagGroupListResponse,
  TagGroupPatch,
  TagGroupPublic,
  TagGroupWrite,
  TagPatch,
  TagPublic,
  TagWrite,
} from '../types/tag'

export function listTagGroups(): Promise<TagGroupListResponse> {
  return apiRequest<TagGroupListResponse>('/v1/tag-groups', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function createTagGroup(body: TagGroupWrite): Promise<TagGroupPublic> {
  return apiRequest<TagGroupPublic>('/v1/tag-groups', {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function patchTagGroup(groupId: string, body: TagGroupPatch): Promise<TagGroupPublic> {
  return apiRequest<TagGroupPublic>(`/v1/tag-groups/${groupId}`, {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function deleteTagGroup(groupId: string): Promise<void> {
  return apiRequest<void>(`/v1/tag-groups/${groupId}`, {
    method: 'DELETE',
    auth: true,
  })
}

export function reorderTagGroups(body: ReorderRequest): Promise<TagGroupListResponse> {
  return apiRequest<TagGroupListResponse>('/v1/tag-groups/reorder', {
    method: 'PUT',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function createTag(groupId: string, body: TagWrite): Promise<TagPublic> {
  return apiRequest<TagPublic>(`/v1/tag-groups/${groupId}/tags`, {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function patchTag(groupId: string, tagId: string, body: TagPatch): Promise<TagPublic> {
  return apiRequest<TagPublic>(`/v1/tag-groups/${groupId}/tags/${tagId}`, {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function deleteTag(groupId: string, tagId: string): Promise<void> {
  return apiRequest<void>(`/v1/tag-groups/${groupId}/tags/${tagId}`, {
    method: 'DELETE',
    auth: true,
  })
}

export function reorderTags(groupId: string, body: ReorderRequest): Promise<TagGroupPublic> {
  return apiRequest<TagGroupPublic>(`/v1/tag-groups/${groupId}/tags/reorder`, {
    method: 'PUT',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}
