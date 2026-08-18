import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

function BaseIcon(props: IconProps) {
  return <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" {...props} />
}

export function EditIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M4 20h4.5L19.2 9.3a1.5 1.5 0 0 0 0-2.12L16.82 4.8a1.5 1.5 0 0 0-2.12 0L4 15.5V20z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path
        d="M13.5 6.5l4 4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function DeleteIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M5 7h14M10 11v6M14 11v6M9 7l1-2h4l1 2M7 7l1 12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2l1-12"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </BaseIcon>
  )
}

export function DragHandleIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <circle cx="9" cy="7" r="1.2" fill="currentColor" />
      <circle cx="15" cy="7" r="1.2" fill="currentColor" />
      <circle cx="9" cy="12" r="1.2" fill="currentColor" />
      <circle cx="15" cy="12" r="1.2" fill="currentColor" />
      <circle cx="9" cy="17" r="1.2" fill="currentColor" />
      <circle cx="15" cy="17" r="1.2" fill="currentColor" />
    </BaseIcon>
  )
}

export function ChevronLeftIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M14.5 6.5 9 12l5.5 5.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </BaseIcon>
  )
}

export function ChevronRightIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M9.5 6.5 15 12l-5.5 5.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </BaseIcon>
  )
}

export function ArrowUpIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M12 19V5M6.5 10.5 12 5l5.5 5.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </BaseIcon>
  )
}

export function ArrowDownIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M12 5v14M6.5 13.5 12 19l5.5-5.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </BaseIcon>
  )
}

export function PhotoIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M4.5 6.5h15a1.5 1.5 0 0 1 1.5 1.5v10a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18V8a1.5 1.5 0 0 1 1.5-1.5z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <circle
        cx="9"
        cy="11"
        r="1.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M3.8 17.2 8.4 13l2.8 2.4 3.2-3.6 5.8 5.4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </BaseIcon>
  )
}

export function AudioIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M12 4v16M8 8v8M16 8v8M4 10.5v3M20 10.5v3"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function NavEntriesIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <rect
        x="4.5"
        y="4.5"
        width="15"
        height="15"
        rx="3.25"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M8 9.25h8M8 12.5h8M8 15.75h5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function NavGoalsIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <circle
        cx="12"
        cy="12"
        r="7.25"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <circle
        cx="12"
        cy="12"
        r="3.25"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <circle cx="12" cy="12" r="1.05" fill="currentColor" />
    </BaseIcon>
  )
}

export function NavTagsIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M4.75 12.4 12.35 4.8A1.7 1.7 0 0 1 13.55 4.3h4.7A1.45 1.45 0 0 1 19.7 5.75v4.7a1.7 1.7 0 0 1-.5 1.2L11.6 19.25a1.55 1.55 0 0 1-2.2 0L4.75 14.6a1.55 1.55 0 0 1 0-2.2z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <circle cx="16.05" cy="7.95" r="1.05" fill="currentColor" />
    </BaseIcon>
  )
}

export function NavMoreIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <circle cx="6.5" cy="12" r="1.45" fill="currentColor" />
      <circle cx="12" cy="12" r="1.45" fill="currentColor" />
      <circle cx="17.5" cy="12" r="1.45" fill="currentColor" />
    </BaseIcon>
  )
}
