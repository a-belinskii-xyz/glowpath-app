import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type ReactNode,
  type RefObject,
} from 'react'

import { useLocale } from '../../context/LocaleContext'
import { hexToOklab } from '../../design/oklab'
import { intlLocale } from '../../i18n/t'
import { buildMonthCalendarCells } from '../../lib/datetime'
import {
  MAX_MOOD,
  MIN_MOOD,
  formatRecapDate,
  weekdayNames,
  type MonthRecapData,
  type RecapDay,
} from '../../lib/monthRecap'
import type { MoodRecapItemPublic } from '../../types/mood'
import type { MoodScoreStylePublic } from '../../types/moodPreferences'
import { GoalIcon } from '../GoalIcon'
import { MoodScoreIcon } from '../MoodScoreIcon'
import { TagIcon } from '../TagIcon'

type ScoreStyle = (score: number) => MoodScoreStylePublic

const MOOD_LEVELS = [5, 4, 3, 2, 1] as const

/** Ink that stays readable on a mood-coloured fill. */
function inkOn(hex: string): string {
  const lab = hexToOklab(hex)
  return lab && lab.L > 0.72 ? '#1e293b' : '#ffffff'
}

function useElementWidth<T extends HTMLElement>(): [RefObject<T>, number] {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const node = ref.current
    if (!node) return
    setWidth(node.clientWidth)
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(node)
    return () => observer.disconnect()
  }, [])
  return [ref, width]
}

type Tip = { x: number; y: number; content: ReactNode } | null

/** Tooltip anchored inside a `position: relative` chart frame. */
function RecapTip({ tip }: { tip: Tip }) {
  if (!tip) return null
  return (
    <div className="recap-tip" role="status" style={{ left: tip.x, top: tip.y }}>
      {tip.content}
    </div>
  )
}

function tipFor(frame: HTMLElement | null, target: HTMLElement, content: ReactNode): Tip {
  if (!frame) return null
  const frameRect = frame.getBoundingClientRect()
  const rect = target.getBoundingClientRect()
  return {
    x: rect.left - frameRect.left + rect.width / 2,
    y: rect.top - frameRect.top,
    content,
  }
}

function DayTipContent({
  day,
  scoreStyle,
  locale,
}: {
  day: RecapDay
  scoreStyle: ScoreStyle
  locale: string
}) {
  const { tp } = useLocale()
  const style = scoreStyle(day.score)
  return (
    <>
      <strong>{formatRecapDate(day.date, locale)}</strong>
      <span className="recap-tip-row">
        <span className="recap-swatch" style={{ background: style.color }} />
        {style.label}
      </span>
      <span className="recap-tip-muted">
        {tp(day.entryCount, {
          one: 'monthSummary.entriesOne',
          few: 'monthSummary.entriesFew',
          many: 'monthSummary.entriesMany',
        })}
      </span>
    </>
  )
}

/* ——— Mood calendar ——— */

export function RecapCalendar({
  data,
  year,
  month,
  scoreStyle,
}: {
  data: MonthRecapData
  year: number
  month: number
  scoreStyle: ScoreStyle
}) {
  const { t, locale } = useLocale()
  const dateLocale = intlLocale(locale)
  const frameRef = useRef<HTMLDivElement>(null)
  const [tip, setTip] = useState<Tip>(null)
  const cells = useMemo(() => buildMonthCalendarCells(year, month), [month, year])
  const byDate = useMemo(() => new Map(data.days.map((day) => [day.date, day])), [data.days])
  const names = useMemo(() => weekdayNames(dateLocale, 'short'), [dateLocale])
  const legendScores = MOOD_LEVELS.filter((score) => data.days.some((day) => day.score === score))
  // Trailing padding weeks carry no information; keep leading pad so columns line up.
  const lastInMonth = cells.map((cell) => cell.inMonth).lastIndexOf(true)
  const visible = cells.slice(0, Math.ceil((lastInMonth + 1) / 7) * 7)

  return (
    <div className="recap-calendar-frame" ref={frameRef} onMouseLeave={() => setTip(null)}>
      <div className="recap-calendar" role="grid" aria-label={t('monthSummary.calendarTitle')}>
        {names.map((name) => (
          <span key={name} className="recap-calendar-weekday" aria-hidden="true">
            {name}
          </span>
        ))}
        {visible.map((cell, index) => {
          if (!cell.inMonth) {
            return <span key={cell.key} className="recap-calendar-cell is-pad" aria-hidden="true" />
          }
          const logged = byDate.get(cell.date)
          const isBest = logged !== undefined && data.bestDay?.date === logged.date
          const color = logged ? scoreStyle(logged.score).color : undefined
          const label = logged
            ? `${formatRecapDate(cell.date, dateLocale)}: ${scoreStyle(logged.score).label}`
            : `${formatRecapDate(cell.date, dateLocale)}: ${t('monthSummary.noEntryDay')}`
          const show = (target: HTMLElement) => {
            if (!logged) return setTip(null)
            setTip(
              tipFor(
                frameRef.current,
                target,
                <DayTipContent day={logged} scoreStyle={scoreStyle} locale={dateLocale} />,
              ),
            )
          }
          return (
            <span
              key={cell.key}
              role="gridcell"
              tabIndex={logged ? 0 : -1}
              aria-label={label}
              className={`recap-calendar-cell${logged ? ' is-logged' : ''}${isBest ? ' is-best' : ''}`}
              style={
                {
                  '--cell-delay': `${index * 18}ms`,
                  ...(color ? { background: color, color: inkOn(color) } : {}),
                } as CSSProperties
              }
              onMouseEnter={(event) => show(event.currentTarget)}
              onFocus={(event) => show(event.currentTarget)}
              onBlur={() => setTip(null)}
            >
              {cell.day}
              {logged && logged.entryCount > 1 ? (
                <span className="recap-calendar-dots" aria-hidden="true">
                  {Array.from({ length: Math.min(3, logged.entryCount) }, (_, dot) => (
                    <i key={dot} />
                  ))}
                </span>
              ) : null}
            </span>
          )
        })}
      </div>
      <RecapTip tip={tip} />
      {legendScores.length > 0 ? (
        <ul className="recap-legend" aria-label={t('monthSummary.legend')}>
          {legendScores.map((score) => {
            const style = scoreStyle(score)
            return (
              <li key={score}>
                <span className="recap-swatch" style={{ background: style.color }} />
                {style.label}
              </li>
            )
          })}
          {data.bestDay ? (
            <li>
              <span className="recap-swatch is-best-key" aria-hidden="true" />
              {t('monthSummary.bestDayKey')}
            </li>
          ) : null}
        </ul>
      ) : null}
    </div>
  )
}

/* ——— Mood flow line ——— */

type Point = { x: number; y: number; day: RecapDay }

/** Monotone cubic path (Fritsch–Carlson): smooth, never overshoots the 1–5 scale. */
function monotonePath(points: Point[]): string {
  if (points.length === 0) return ''
  if (points.length === 1) return `M${points[0].x},${points[0].y}`
  const n = points.length
  const dx = points.slice(1).map((p, i) => p.x - points[i].x)
  const slopes = points.slice(1).map((p, i) => (p.y - points[i].y) / dx[i])
  const tangents = points.map((_, i) => {
    if (i === 0) return slopes[0]
    if (i === n - 1) return slopes[n - 2]
    const a = slopes[i - 1]
    const b = slopes[i]
    return a * b <= 0 ? 0 : (3 * (dx[i - 1] + dx[i])) / ((2 * dx[i] + dx[i - 1]) / a + (dx[i] + 2 * dx[i - 1]) / b)
  })
  let path = `M${points[0].x},${points[0].y}`
  for (let i = 0; i < n - 1; i += 1) {
    const h = dx[i] / 3
    path += `C${points[i].x + h},${points[i].y + tangents[i] * h} ${points[i + 1].x - h},${
      points[i + 1].y - tangents[i + 1] * h
    } ${points[i + 1].x},${points[i + 1].y}`
  }
  return path
}

const FLOW_HEIGHT = 190
const FLOW_PAD = { top: 16, right: 14, bottom: 26, left: 40 }

export function RecapMoodFlow({
  data,
  scoreStyle,
  gradientId,
}: {
  data: MonthRecapData
  scoreStyle: ScoreStyle
  gradientId: string
}) {
  const { t, locale } = useLocale()
  const dateLocale = intlLocale(locale)
  const [frameRef, width] = useElementWidth<HTMLDivElement>()
  const [active, setActive] = useState<number | null>(null)

  const plotW = Math.max(0, width - FLOW_PAD.left - FLOW_PAD.right)
  const plotH = FLOW_HEIGHT - FLOW_PAD.top - FLOW_PAD.bottom
  const x = (day: number) =>
    FLOW_PAD.left + ((day - 1) / Math.max(1, data.daysInMonth - 1)) * plotW
  const y = (mood: number) => FLOW_PAD.top + ((MAX_MOOD - mood) / (MAX_MOOD - MIN_MOOD)) * plotH
  const points: Point[] = data.days.map((day) => ({ x: x(day.day), y: y(day.mood), day }))
  const line = monotonePath(points)
  const baseline = y(MIN_MOOD)
  const area =
    points.length > 1
      ? `${line}L${points[points.length - 1].x},${baseline}L${points[0].x},${baseline}Z`
      : ''
  const ticks = [1, 8, 15, 22, data.daysInMonth].filter(
    (day, index, all) => all.indexOf(day) === index && (day === data.daysInMonth || data.daysInMonth - day > 3),
  )
  const focused = active === null ? null : points[active]

  const nearest = (clientX: number, rect: DOMRect) => {
    const px = clientX - rect.left
    let best = 0
    points.forEach((point, index) => {
      if (Math.abs(point.x - px) < Math.abs(points[best].x - px)) best = index
    })
    return best
  }

  const onKeyDown = (event: KeyboardEvent<SVGSVGElement>) => {
    if (points.length === 0) return
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault()
      const step = event.key === 'ArrowRight' ? 1 : -1
      setActive((current) =>
        Math.min(points.length - 1, Math.max(0, (current ?? (step > 0 ? -1 : points.length)) + step)),
      )
    }
  }

  return (
    <div className="recap-flow-frame" ref={frameRef}>
      {width > 0 ? (
        <>
          <svg
            className="recap-flow"
            width={width}
            height={FLOW_HEIGHT}
            role="img"
            aria-label={t('monthSummary.flowAria')}
            tabIndex={0}
            onKeyDown={onKeyDown}
            onBlur={() => setActive(null)}
            onPointerMove={(event) =>
              points.length > 0 &&
              setActive(nearest(event.clientX, event.currentTarget.getBoundingClientRect()))
            }
            onPointerLeave={() => setActive(null)}
          >
            <defs>
              <linearGradient
                id={gradientId}
                gradientUnits="userSpaceOnUse"
                x1="0"
                x2="0"
                y1={y(MAX_MOOD)}
                y2={y(MIN_MOOD)}
              >
                {MOOD_LEVELS.map((score) => (
                  <stop
                    key={score}
                    offset={`${((MAX_MOOD - score) / (MAX_MOOD - MIN_MOOD)) * 100}%`}
                    stopColor={scoreStyle(score).color}
                  />
                ))}
              </linearGradient>
            </defs>
            {MOOD_LEVELS.map((score) => (
              <line
                key={score}
                className="recap-grid"
                x1={FLOW_PAD.left}
                x2={width - FLOW_PAD.right}
                y1={y(score)}
                y2={y(score)}
              />
            ))}
            {ticks.map((day) => (
              <text key={day} className="recap-axis" x={x(day)} y={FLOW_HEIGHT - 6} textAnchor="middle">
                {day}
              </text>
            ))}
            {area ? <path className="recap-flow-area" d={area} fill={`url(#${gradientId})`} /> : null}
            {points.length > 1 ? (
              <path
                className="recap-flow-line"
                d={line}
                stroke={`url(#${gradientId})`}
                pathLength={1}
              />
            ) : null}
            {focused ? (
              <line
                className="recap-crosshair"
                x1={focused.x}
                x2={focused.x}
                y1={FLOW_PAD.top}
                y2={baseline}
              />
            ) : null}
            {points.map((point, index) => (
              <circle
                key={point.day.date}
                className={`recap-flow-dot${index === active ? ' is-active' : ''}`}
                cx={point.x}
                cy={point.y}
                r={index === active ? 6 : 4.5}
                fill={scoreStyle(point.day.score).color}
                style={{ '--dot-delay': `${400 + index * 30}ms` } as CSSProperties}
              />
            ))}
            {data.bestDay && points.length > 1 ? (
              <text
                className="recap-flow-best"
                x={x(data.bestDay.day)}
                y={Math.max(11, y(data.bestDay.mood) - 12)}
                textAnchor="middle"
              >
                ★
              </text>
            ) : null}
          </svg>
          <div className="recap-flow-icons" aria-hidden="true">
            {MOOD_LEVELS.map((score) => (
              <span key={score} style={{ top: y(score) }}>
                <MoodScoreIcon style={scoreStyle(score)} className="recap-axis-icon" fallbackScore={score} />
              </span>
            ))}
          </div>
          {focused ? (
            <div
              className="recap-tip"
              role="status"
              style={{ left: Math.min(Math.max(focused.x, 70), width - 70), top: focused.y - 8 }}
            >
              <DayTipContent day={focused.day} scoreStyle={scoreStyle} locale={dateLocale} />
            </div>
          ) : null}
        </>
      ) : null}
      <table className="visually-hidden">
        <caption>{t('monthSummary.flowTitle')}</caption>
        <tbody>
          {data.days.map((day) => (
            <tr key={day.date}>
              <th scope="row">{formatRecapDate(day.date, dateLocale)}</th>
              <td>{scoreStyle(day.score).label}</td>
              <td>{day.entryCount}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ——— Mood mix ——— */

export function RecapMoodMix({ data, scoreStyle }: { data: MonthRecapData; scoreStyle: ScoreStyle }) {
  const { locale } = useLocale()
  const percent = new Intl.NumberFormat(intlLocale(locale), { style: 'percent', maximumFractionDigits: 0 })
  return (
    <div className="recap-mix">
      <div className="recap-mix-bar" aria-hidden="true">
        {data.moodMix.map((item, index) => (
          <span
            key={item.score}
            style={
              {
                flexGrow: item.share,
                background: scoreStyle(item.score).color,
                '--seg-delay': `${200 + index * 90}ms`,
              } as CSSProperties
            }
          />
        ))}
      </div>
      <ul className="recap-mix-legend">
        {data.moodMix.map((item) => {
          const style = scoreStyle(item.score)
          return (
            <li key={item.score}>
              <MoodScoreIcon style={style} className="recap-row-icon" fallbackScore={item.score} />
              <span className="recap-mix-label">{style.label}</span>
              <span className="recap-mix-value">
                <strong>{percent.format(item.share)}</strong>
                <span>{item.count}</span>
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/* ——— Weekday rhythm ——— */

export function RecapWeekRhythm({ data, scoreStyle }: { data: MonthRecapData; scoreStyle: ScoreStyle }) {
  const { locale } = useLocale()
  const dateLocale = intlLocale(locale)
  const shortNames = useMemo(() => weekdayNames(dateLocale, 'short'), [dateLocale])
  const moodFormat = new Intl.NumberFormat(dateLocale, { maximumFractionDigits: 1, minimumFractionDigits: 1 })
  return (
    <div className="recap-rhythm">
      {data.weekdays.map((item, index) => {
        const isBest = data.bestWeekday?.weekday === item.weekday
        const height = item.mood === null ? 4 : 12 + ((item.mood - MIN_MOOD) / (MAX_MOOD - MIN_MOOD)) * 88
        const color = item.mood === null ? undefined : scoreStyle(Math.round(item.mood)).color
        const label =
          item.mood === null
            ? `${shortNames[item.weekday]}: —`
            : `${shortNames[item.weekday]}: ${scoreStyle(Math.round(item.mood)).label} (${moodFormat.format(item.mood)})`
        return (
          <div
            key={item.weekday}
            className={`recap-rhythm-col${isBest ? ' is-best' : ''}${item.mood === null ? ' is-empty' : ''}`}
            title={label}
            aria-label={label}
            role="img"
          >
            <span className="recap-rhythm-value">{isBest && item.mood !== null ? moodFormat.format(item.mood) : ''}</span>
            <span className="recap-rhythm-track">
              <span
                className="recap-rhythm-bar"
                style={
                  {
                    height: `${height}%`,
                    background: color,
                    '--bar-delay': `${200 + index * 70}ms`,
                  } as CSSProperties
                }
              />
            </span>
            <span className="recap-rhythm-name">{shortNames[item.weekday]}</span>
          </div>
        )
      })}
    </div>
  )
}

/* ——— Top tags / goals ——— */

export function RecapTopList({ items, kind }: { items: MoodRecapItemPublic[]; kind: 'tag' | 'goal' }) {
  const top = items.slice(0, 5)
  const max = Math.max(1, ...top.map((item) => item.count))
  const [shown, setShown] = useState(false)
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setShown(true))
    return () => window.cancelAnimationFrame(frame)
  }, [])
  return (
    <ol className="recap-top">
      {top.map((item, index) => {
        const iconStyle = { color: item.color, icon_type: item.icon_type, icon: item.icon }
        return (
          <li key={item.id}>
            {kind === 'goal' ? (
              <GoalIcon style={iconStyle} className="recap-row-icon" />
            ) : (
              <TagIcon style={iconStyle} className="recap-row-icon" />
            )}
            <span className="recap-top-label">{item.label}</span>
            <span className="recap-top-count">{item.count}</span>
            <span className="recap-top-track" aria-hidden="true">
              <span
                style={
                  {
                    width: shown ? `${(item.count / max) * 100}%` : '0%',
                    background: item.color,
                    transitionDelay: `${250 + index * 80}ms`,
                  } as CSSProperties
                }
              />
            </span>
          </li>
        )
      })}
    </ol>
  )
}
