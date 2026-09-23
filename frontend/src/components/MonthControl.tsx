import { type ReactNode } from 'react'

import { IconButton } from './IconButton'
import { ChevronLeftIcon, ChevronRightIcon } from './icons'

type MonthControlProps = {
  label: string
  /** Labels used to reserve width so arrows don't shift between months. */
  sizeLabels: string[]
  previousLabel: string
  nextLabel: string
  onPrevious: () => void
  onNext: () => void
  canGoNext?: boolean
  trailing?: ReactNode
}

export function MonthControl({
  label,
  sizeLabels,
  previousLabel,
  nextLabel,
  onPrevious,
  onNext,
  canGoNext = true,
  trailing,
}: MonthControlProps) {
  return (
    <div className="month-control">
      <div className="month-control-main">
        <IconButton label={previousLabel} size="sm" onClick={onPrevious}>
          <ChevronLeftIcon />
        </IconButton>
        <h1 className="month-control-title">
          <span className="month-control-title-sizer" aria-hidden="true">
            {sizeLabels.map((sizeLabel) => (
              <span key={sizeLabel}>{sizeLabel}</span>
            ))}
          </span>
          <span className="month-control-title-label">{label}</span>
        </h1>
        <IconButton label={nextLabel} size="sm" onClick={onNext} disabled={!canGoNext}>
          <ChevronRightIcon />
        </IconButton>
      </div>
      {trailing ? <div className="month-control-trailing">{trailing}</div> : null}
    </div>
  )
}
