import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import type { TagGroupListResponse } from '../types/tag'

export function listTagGroups(): Promise<TagGroupListResponse> {
  return apiRequest<TagGroupListResponse>('/v1/tag-groups', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}
