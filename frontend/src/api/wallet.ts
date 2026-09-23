import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import type {
  WalletGrantBody,
  WalletLedgerListResponse,
  WalletPublic,
} from '../types/marketplace'

export function getWallet(): Promise<WalletPublic> {
  return apiRequest<WalletPublic>('/v1/wallet', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getWalletLedger(params?: {
  limit?: number
  offset?: number
}): Promise<WalletLedgerListResponse> {
  const query = new URLSearchParams()
  if (params?.limit !== undefined) {
    query.set('limit', String(params.limit))
  }
  if (params?.offset !== undefined) {
    query.set('offset', String(params.offset))
  }
  const suffix = query.size > 0 ? `?${query}` : ''
  return apiRequest<WalletLedgerListResponse>(`/v1/wallet/ledger${suffix}`, {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function grantWalletTokens(body: WalletGrantBody): Promise<WalletPublic> {
  return apiRequest<WalletPublic>('/v1/wallet/staff/grants', {
    method: 'POST',
    auth: true,
    body,
    headers: apiLocaleHeaders(),
  })
}
