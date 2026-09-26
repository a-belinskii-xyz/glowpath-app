import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { getStaffUserLedger, searchStaffUsers } from '../../api/staff'
import { grantWalletTokens } from '../../api/wallet'
import { useLocale } from '../../context/LocaleContext'
import { formatApiError } from '../../lib/errors'
import type { WalletLedgerEntryPublic } from '../../types/marketplace'
import type { StaffUserPublic } from '../../types/staff'
import { Alert } from '../Alert'
import { PageErrorAlert } from '../PageErrorAlert'

const QUICK_AMOUNTS = [50, 100, 500]

export function StaffTokensPanel() {
  const { t, locale } = useLocale()
  const [query, setQuery] = useState('')
  const [users, setUsers] = useState<StaffUserPublic[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [selected, setSelected] = useState<StaffUserPublic | null>(null)
  const [ledger, setLedger] = useState<WalletLedgerEntryPublic[]>([])
  const [amount, setAmount] = useState('100')
  const [note, setNote] = useState('')
  const [isGranting, setIsGranting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const formatNumber = (value: number) =>
    new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : 'en-US').format(value)

  const runSearch = useCallback(
    async (q: string) => {
      setIsSearching(true)
      setError(null)
      try {
        const response = await searchStaffUsers(q)
        setUsers(response.items)
      } catch (err) {
        setError(formatApiError(err, t, 'errors.requestFailed'))
      } finally {
        setIsSearching(false)
      }
    },
    [t],
  )

  useEffect(() => {
    void runSearch('')
  }, [runSearch])

  useEffect(() => {
    if (!selected) {
      setLedger([])
      return
    }
    let cancelled = false
    void getStaffUserLedger(selected.id)
      .then((response) => {
        if (!cancelled) setLedger(response.items)
      })
      .catch(() => {
        if (!cancelled) setLedger([])
      })
    return () => {
      cancelled = true
    }
  }, [selected])

  const handleSearch = (event: FormEvent) => {
    event.preventDefault()
    void runSearch(query)
  }

  const handleGrant = async (event: FormEvent) => {
    event.preventDefault()
    const value = Number.parseInt(amount, 10)
    if (!selected || !Number.isFinite(value) || value <= 0 || isGranting) return
    setIsGranting(true)
    setError(null)
    setSuccess(null)
    try {
      const wallet = await grantWalletTokens({
        user_id: selected.id,
        amount: value,
        note: note.trim() || null,
      })
      const updated = { ...selected, balance: wallet.balance }
      setSelected(updated)
      setUsers((current) => current.map((row) => (row.id === updated.id ? updated : row)))
      setSuccess(
        t('staff.granted', { amount: formatNumber(value), balance: formatNumber(wallet.balance) }),
      )
      setNote('')
    } catch (err) {
      setError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setIsGranting(false)
    }
  }

  return (
    <div className="staff-panel">
      <PageErrorAlert error={error} />
      <form className="staff-search" onSubmit={handleSearch}>
        <label className="visually-hidden" htmlFor="staff-user-search">
          {t('staff.userSearch')}
        </label>
        <input
          id="staff-user-search"
          className="form-input"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t('staff.userSearchPlaceholder')}
          autoComplete="off"
        />
        <button type="submit" className="button button-secondary" disabled={isSearching}>
          {t('staff.search')}
        </button>
      </form>

      <div className="staff-split">
        <ul className="staff-list" aria-busy={isSearching}>
          {users.length === 0 && !isSearching ? (
            <li className="muted staff-list-empty">{t('staff.noUsers')}</li>
          ) : null}
          {users.map((row) => (
            <li key={row.id}>
              <button
                type="button"
                className={`staff-list-row${selected?.id === row.id ? ' is-active' : ''}`}
                onClick={() => {
                  setSelected(row)
                  setSuccess(null)
                }}
              >
                <span className="staff-list-title">
                  {row.email ?? t('staff.telegramOnly')}
                  {row.is_staff ? (
                    <span className="status-pill status-pill--sm status-pill--muted">
                      {t('staff.staffBadge')}
                    </span>
                  ) : null}
                </span>
                <span className="staff-list-meta">
                  {t('staff.balance', { count: formatNumber(row.balance) })}
                </span>
              </button>
            </li>
          ))}
        </ul>

        {selected ? (
          <div className="card staff-card">
            <h2 className="staff-card-title">
              {t('staff.grantTitle', { user: selected.email ?? selected.id })}
            </h2>
            <p className="muted staff-card-meta">
              {t('staff.balance', { count: formatNumber(selected.balance) })} · {selected.id}
            </p>
            {success ? <Alert variant="success">{success}</Alert> : null}
            <form className="form staff-grant-form" onSubmit={handleGrant}>
              <label className="form-field" htmlFor="staff-grant-amount">
                <span className="form-label">{t('staff.amount')}</span>
                <input
                  id="staff-grant-amount"
                  className="form-input"
                  type="number"
                  min={1}
                  step={1}
                  required
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                />
              </label>
              <div className="staff-chip-row">
                {QUICK_AMOUNTS.map((value) => (
                  <button
                    key={value}
                    type="button"
                    className={`market-tag-chip${amount === String(value) ? ' is-active' : ''}`}
                    onClick={() => setAmount(String(value))}
                  >
                    +{value}
                  </button>
                ))}
              </div>
              <label className="form-field" htmlFor="staff-grant-note">
                <span className="form-label">{t('staff.note')}</span>
                <input
                  id="staff-grant-note"
                  className="form-input"
                  maxLength={500}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder={t('staff.notePlaceholder')}
                />
              </label>
              <button type="submit" className="button" disabled={isGranting}>
                {isGranting ? t('staff.granting') : t('staff.grant')}
              </button>
            </form>

            <h3 className="staff-subtitle">{t('staff.ledgerTitle')}</h3>
            {ledger.length === 0 ? (
              <p className="muted">{t('staff.ledgerEmpty')}</p>
            ) : (
              <ul className="staff-ledger">
                {ledger.map((entry) => (
                  <li key={entry.id} className="staff-ledger-row">
                    <span className={entry.delta > 0 ? 'staff-delta-plus' : 'staff-delta-minus'}>
                      {entry.delta > 0 ? '+' : ''}
                      {formatNumber(entry.delta)}
                    </span>
                    <span className="staff-ledger-kind">{entry.kind}</span>
                    <span className="muted staff-ledger-note">{entry.note ?? ''}</span>
                    <time className="muted" dateTime={entry.created_at}>
                      {new Date(entry.created_at).toLocaleDateString(locale)}
                    </time>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}
