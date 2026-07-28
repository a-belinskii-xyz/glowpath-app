import { type ReactNode } from 'react'

import { IconButton } from './IconButton'
import { ChevronLeftIcon, ChevronRightIcon } from './icons'

type MonthControlProps = {
  label: string
  previousLabel: string
  nextLabel: string
  onPrevious: () => void
  onNext: () => void
  trailing?: ReactNode
}

export function MonthControl({
  label,
  previousLabel,
  nextLabel,
  onPrevious,
  onNext,
  trailing,
}: MonthControlProps) {
  return (
    <div className="month-control">
      <div className="month-control-main">
        <IconButton label={previousLabel} size="sm" onClick={onPrevious}>
          <ChevronLeftIcon />
        </IconButton>
        <h1 className="month-control-title">{label}</h1>
        <IconButton label={nextLabel} size="sm" onClick={onNext}>
          <ChevronRightIcon />
        </IconButton>
      </div>
      {trailing ? <div className="month-control-trailing">{trailing}</div> : null}
    </div>
  )
}
