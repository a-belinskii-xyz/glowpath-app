import { apiRequest } from './client'
import type {
  CheckoutRequest,
  CheckoutResponse,
  CurrentSubscriptionPublic,
  PlanCatalogResponse,
} from '../types/billing'

export function getPlanCatalog(): Promise<PlanCatalogResponse> {
  return apiRequest<PlanCatalogResponse>('/v1/billing/plans', { auth: true })
}

export function getSubscription(): Promise<CurrentSubscriptionPublic> {
  return apiRequest<CurrentSubscriptionPublic>('/v1/billing/subscription', { auth: true })
}

export function startCheckout(body: CheckoutRequest): Promise<CheckoutResponse> {
  return apiRequest<CheckoutResponse>('/v1/billing/checkout', {
    method: 'POST',
    body,
    auth: true,
  })
}

export function cancelSubscription(): Promise<CurrentSubscriptionPublic> {
  return apiRequest<CurrentSubscriptionPublic>('/v1/billing/cancel', {
    method: 'POST',
    auth: true,
  })
}
