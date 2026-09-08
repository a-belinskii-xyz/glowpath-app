import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { cancelSubscription, getPlanCatalog, startCheckout } from '../api/billing'
import { Alert } from '../components/Alert'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { CheckIcon, SparkleIcon } from '../components/icons'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { ApiError, formatApiError } from '../lib/errors'
import { isGuestDiaryMode } from '../lib/guestMode'
import type {
  BillingInterval,
  CurrentSubscriptionPublic,
  PaymentProviderId,
  PlanCatalogResponse,
  PlanPublic,
  PlanSlug,
} from '../types/billing'

const PLAN_GLOW: Record<PlanSlug, string> = {
  free: '#93c5fd',
  plus: '#f59e0b',
  pro: '#a78bfa',
}

function priceFor(plan: PlanPublic, interval: BillingInterval) {
  return plan.prices.find((price) => price.interval === interval) ?? null
}

function formatMoney(amountMinor: number, currency: string, locale: string) {
  const value = amountMinor / 100
  const fractionDigits = Number.isInteger(value) ? 0 : 2
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value)
}

function hasEntitlement(plan: PlanPublic, entitlement: string) {
  return plan.entitlements.includes(entitlement)
}

export function PlansPage() {
  const { t, locale } = useLocale()
  const { user, isAuthenticated, refreshUser } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const guestShell = isGuestDiaryMode()
  const numberLocale = intlLocale(locale)

  const [catalog, setCatalog] = useState<PlanCatalogResponse | null>(null)
  const [interval, setInterval] = useState<BillingInterval>('month')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [busyPlan, setBusyPlan] = useState<PlanSlug | null>(null)
  const [cancelOpen, setCancelOpen] = useState(false)
  const [isCanceling, setIsCanceling] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)

  usePageAmbientGlow([PLAN_GLOW.free, PLAN_GLOW.plus, PLAN_GLOW.pro])

  const reload = useCallback(async () => {
    const next = await getPlanCatalog()
    setCatalog(next)
    if (next.current.billing_interval) {
      setInterval(next.current.billing_interval)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    void reload()
      .then(() => {
        if (!cancelled) {
          setError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(formatApiError(err, t, 'errors.requestFailed'))
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [reload, t])

  useEffect(() => {
    const checkout = searchParams.get('checkout')
    if (!checkout) {
      return
    }
    if (checkout === 'success') {
      setNotice(t('plans.checkoutSuccess'))
    } else if (checkout === 'cancel') {
      setNotice(t('plans.checkoutCanceled'))
    }
    const next = new URLSearchParams(searchParams)
    next.delete('checkout')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams, t])

  const current: CurrentSubscriptionPublic | null = catalog?.current ?? null
  const currentRank = catalog?.items.find((plan) => plan.slug === current?.plan_slug)?.rank ?? 0

  const periodLabel = useMemo(() => {
    if (!current?.current_period_end) {
      return null
    }
    const date = new Date(current.current_period_end)
    if (Number.isNaN(date.getTime())) {
      return null
    }
    return new Intl.DateTimeFormat(numberLocale, { dateStyle: 'medium' }).format(date)
  }, [current?.current_period_end, numberLocale])

  const handleCheckout = async (plan: PlanPublic) => {
    if (busyPlan || plan.is_default) {
      return
    }
    if (!isAuthenticated || guestShell) {
      return
    }
    setBusyPlan(plan.slug)
    setError(null)
    setNotice(null)
    try {
      const provider: PaymentProviderId | undefined =
        catalog && catalog.providers.length === 1 ? catalog.providers[0] : undefined
      const result = await startCheckout({
        plan_slug: plan.slug,
        interval,
        provider,
      })
      if (result.checkout_url) {
        window.location.assign(result.checkout_url)
        return
      }
      if (result.completed) {
        await refreshUser()
        await reload()
        setNotice(t('plans.checkoutSuccess'))
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('plans.verifyToSubscribe'))
      } else {
        setError(formatApiError(err, t, 'errors.requestFailed'))
      }
    } finally {
      setBusyPlan(null)
    }
  }

  const handleCancel = async () => {
    setIsCanceling(true)
    setCancelError(null)
    try {
      await cancelSubscription()
      await refreshUser()
      await reload()
      setCancelOpen(false)
      setNotice(t('plans.cancelScheduled'))
    } catch (err) {
      setCancelError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setIsCanceling(false)
    }
  }

  const ctaFor = (plan: PlanPublic) => {
    const isCurrent = current?.plan_slug === plan.slug
    if (isCurrent && plan.is_default) {
      return { label: t('plans.currentPlan'), disabled: true, to: null as string | null }
    }
    if (isCurrent) {
      return { label: t('plans.currentPlan'), disabled: true, to: null }
    }
    if (!isAuthenticated || guestShell) {
      if (plan.is_default) {
        return { label: t('plans.includedFree'), disabled: true, to: null }
      }
      return { label: t('plans.createAccount'), disabled: false, to: '/register' }
    }
    if (plan.is_default) {
      return { label: t('plans.includedFree'), disabled: true, to: null }
    }
    if ((catalog?.items.find((item) => item.slug === plan.slug)?.rank ?? 0) < currentRank) {
      return { label: t('plans.lowerPlan'), disabled: true, to: null }
    }
    return {
      label: t('plans.upgradeTo', { plan: t(`plans.${plan.slug}.name` as 'plans.free.name') }),
      disabled: false,
      to: null,
    }
  }

  return (
    <section className="page page-plans">
      <header className="page-header">
        <h1>{t('plans.title')}</h1>
      </header>
      <p className="plans-lead">{t('plans.lead')}</p>

      <PageErrorAlert error={error} />
      {notice ? <Alert variant="success">{notice}</Alert> : null}

      {isAuthenticated && user && user.email && !user.email_verified ? (
        <Alert variant="warning">{t('plans.verifyToSubscribe')}</Alert>
      ) : null}

      {current?.is_paid ? (
        <div className="plans-current-banner">
          <SparkleIcon />
          <div>
            <p className="plans-current-title">
              {t('plans.youAreOn', { plan: t(`plans.${current.plan_slug}.name` as 'plans.plus.name') })}
            </p>
            <p className="muted">
              {current.cancel_at_period_end && periodLabel
                ? t('plans.cancelsOn', { date: periodLabel })
                : periodLabel
                  ? t('plans.renewsOn', { date: periodLabel })
                  : t('plans.paidAccess')}
            </p>
          </div>
          {current.cancel_at_period_end ? null : (
            <button type="button" className="button button-secondary" onClick={() => setCancelOpen(true)}>
              {t('plans.cancel')}
            </button>
          )}
        </div>
      ) : null}

      <div className="plans-interval" role="group" aria-label={t('plans.intervalLabel')}>
        <button
          type="button"
          className={`plans-interval-btn${interval === 'month' ? ' is-active' : ''}`}
          onClick={() => setInterval('month')}
        >
          {t('plans.monthly')}
        </button>
        <button
          type="button"
          className={`plans-interval-btn${interval === 'year' ? ' is-active' : ''}`}
          onClick={() => setInterval('year')}
        >
          {t('plans.yearly')}
          <span className="plans-save-chip">{t('plans.yearlySave')}</span>
        </button>
      </div>

      {isLoading || !catalog ? (
        <p className="muted">{t('common.loadingPlans')}</p>
      ) : (
        <>
          <div className="plans-grid">
            {catalog.items.map((plan) => {
              const price = priceFor(plan, interval)
              const cta = ctaFor(plan)
              const isCurrent = current?.plan_slug === plan.slug
              return (
                <article
                  key={plan.slug}
                  className={`plans-card plans-card--${plan.slug}${plan.is_highlight ? ' is-highlight' : ''}${isCurrent ? ' is-current' : ''}`}
                >
                  {plan.is_highlight ? <p className="plans-popular">{t('plans.mostPopular')}</p> : null}
                  <h2>{t(`plans.${plan.slug}.name` as 'plans.free.name')}</h2>
                  <p className="plans-tagline">{t(`plans.${plan.slug}.tagline` as 'plans.free.tagline')}</p>
                  <p className="plans-price">
                    {price
                      ? t(interval === 'year' ? 'plans.priceYear' : 'plans.priceMonth', {
                          price: formatMoney(price.amount_minor, price.currency, numberLocale),
                        })
                      : t('plans.freePrice')}
                  </p>
                  <p className="plans-description">{t(`plans.${plan.slug}.description` as 'plans.free.description')}</p>
                  <ul className="plans-highlights">
                    {plan.highlight_entitlements.map((key) => (
                      <li key={key}>
                        <CheckIcon />
                        <span>{t(`plans.entitlements.${key}` as 'plans.entitlements.core_diary')}</span>
                      </li>
                    ))}
                  </ul>
                  {cta.to ? (
                    <Link to={cta.to} className="button plans-cta">
                      {cta.label}
                    </Link>
                  ) : (
                    <button
                      type="button"
                      className="button plans-cta"
                      disabled={cta.disabled || busyPlan !== null}
                      onClick={() => void handleCheckout(plan)}
                    >
                      <StableButtonLabel
                        active={busyPlan === plan.slug ? t('plans.redirecting') : cta.label}
                        labels={[cta.label, t('plans.redirecting')]}
                      />
                    </button>
                  )}
                </article>
              )
            })}
          </div>

          <section className="plans-compare" aria-labelledby="plans-compare-heading">
            <h2 id="plans-compare-heading">{t('plans.compareTitle')}</h2>
            <div className="plans-compare-scroll">
              <table className="plans-compare-table">
                <thead>
                  <tr>
                    <th scope="col">{t('plans.feature')}</th>
                    {catalog.items.map((plan) => (
                      <th key={plan.slug} scope="col">
                        {t(`plans.${plan.slug}.name` as 'plans.free.name')}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {catalog.comparison_entitlements.map((key) => (
                    <tr key={key}>
                      <th scope="row">{t(`plans.entitlements.${key}` as 'plans.entitlements.core_diary')}</th>
                      {catalog.items.map((plan) => {
                        const included = hasEntitlement(plan, key)
                        return (
                          <td key={plan.slug} className={included ? 'is-yes' : 'is-no'}>
                            {included ? (
                              <>
                                <CheckIcon />
                                <span className="visually-hidden">{t('common.yes')}</span>
                              </>
                            ) : (
                              <span aria-hidden="true">—</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <p className="plans-footnote muted">{t('plans.footnote')}</p>
        </>
      )}

      <ConfirmDialog
        open={cancelOpen}
        title={t('plans.cancelTitle')}
        message={t('plans.cancelMessage')}
        confirmLabel={t('plans.cancelConfirm')}
        variant="danger"
        isBusy={isCanceling}
        error={cancelError}
        onConfirm={() => void handleCancel()}
        onCancel={() => {
          if (!isCanceling) {
            setCancelOpen(false)
            setCancelError(null)
          }
        }}
      />
    </section>
  )
}
