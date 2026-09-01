export type PlanSlug = 'free' | 'plus' | 'pro'
export type BillingInterval = 'month' | 'year'
export type PaymentProviderId = 'fake' | 'stripe' | 'sber'

export type PlanPricePublic = {
  interval: BillingInterval
  amount_minor: number
  currency: string
}

export type PlanPublic = {
  slug: PlanSlug
  rank: number
  is_default: boolean
  is_highlight: boolean
  entitlements: string[]
  highlight_entitlements: string[]
  prices: PlanPricePublic[]
}

export type CurrentSubscriptionPublic = {
  plan_slug: PlanSlug
  status: string | null
  billing_interval: BillingInterval | null
  provider: PaymentProviderId | null
  current_period_end: string | null
  cancel_at_period_end: boolean
  is_paid: boolean
  entitlements: string[]
}

export type PlanCatalogResponse = {
  currency: string
  comparison_entitlements: string[]
  items: PlanPublic[]
  providers: PaymentProviderId[]
  default_provider: PaymentProviderId
  current: CurrentSubscriptionPublic
}

export type CheckoutRequest = {
  plan_slug: PlanSlug
  interval: BillingInterval
  provider?: PaymentProviderId
}

export type CheckoutResponse = {
  payment_id: string
  provider: PaymentProviderId
  completed: boolean
  checkout_url: string | null
  client_secret: string | null
  plan_slug: PlanSlug
  subscription_status: string | null
}
