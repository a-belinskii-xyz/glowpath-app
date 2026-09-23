import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import type {
  TelegramEntryPointPublic,
  TelegramLinkCodeCreateResponse,
  TelegramLinkPublic,
} from '../types/telegram'

export function getTelegramLink(): Promise<TelegramLinkPublic> {
  return apiRequest<TelegramLinkPublic>('/v1/telegram/link', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function createTelegramLinkCode(): Promise<TelegramLinkCodeCreateResponse> {
  return apiRequest<TelegramLinkCodeCreateResponse>('/v1/telegram/link-codes', {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function unlinkTelegram(): Promise<TelegramLinkPublic> {
  return apiRequest<TelegramLinkPublic>('/v1/telegram/link', {
    method: 'DELETE',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getTelegramEntryPoint(): Promise<TelegramEntryPointPublic> {
  return apiRequest<TelegramEntryPointPublic>('/v1/telegram/entry-point')
}
