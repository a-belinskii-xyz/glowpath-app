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

export function MicIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <rect
        x="9.15"
        y="3.5"
        width="5.7"
        height="10"
        rx="2.85"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M6.5 11.25a5.5 5.5 0 0 0 11 0M12 16.75V20.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
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

export function NavMarketIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M6 8.5h12l-1.1 9.2a2 2 0 0 1-2 1.8H9.1a2 2 0 0 1-2-1.8L6 8.5z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path
        d="M9 8.5V7a3 3 0 0 1 6 0v1.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function NavProfileIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <circle
        cx="12"
        cy="8.25"
        r="3.15"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M5.4 18.6c.85-3.05 3.2-4.6 6.6-4.6s5.75 1.55 6.6 4.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function SearchIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <circle
        cx="11"
        cy="11"
        r="5.75"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M15.6 15.6 19.25 19.25"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function PlusIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M12 5.5v13M5.5 12h13"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function SettingsIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <circle
        cx="12"
        cy="12"
        r="3.05"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M12 4.4v1.7M12 17.9v1.7M4.4 12h1.7M17.9 12h1.7M6.55 6.55l1.2 1.2M16.25 16.25l1.2 1.2M17.45 6.55l-1.2 1.2M7.75 16.25l-1.2 1.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function BellIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M6.2 9.5c0-3.1 2.55-5.7 5.8-5.7s5.8 2.6 5.8 5.7c0 4.05 1.7 5.5 1.7 5.5H4.5S6.2 13.55 6.2 9.5z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path
        d="M9.55 18.15a2.5 2.5 0 0 0 4.9 0"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function PaletteIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M12 4.6a7.4 7.4 0 1 0 .35 14.78h1.4a1.85 1.85 0 0 0 1.62-2.75 1.85 1.85 0 0 1 1.62-2.8H17.1a3.35 3.35 0 0 0 2.85-5.1A7.4 7.4 0 0 0 12 4.6z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <circle cx="9.1" cy="10.1" r="1.05" fill="currentColor" />
      <circle cx="12.15" cy="8.15" r="1.05" fill="currentColor" />
      <circle cx="15.05" cy="10.1" r="1.05" fill="currentColor" />
      <circle cx="10.35" cy="13.35" r="1.05" fill="currentColor" />
    </BaseIcon>
  )
}

export function SoundOnIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M5 10.2v3.6h2.7L12 17.6V6.4L7.7 10.2H5z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path
        d="M15.2 9.1a3.1 3.1 0 0 1 0 5.8M17.6 7.2a6.2 6.2 0 0 1 0 9.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function SoundOffIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M5 10.2v3.6h2.7L12 17.6V6.4L7.7 10.2H5z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path
        d="M15.4 10.2 19 13.8M19 10.2 15.4 13.8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </BaseIcon>
  )
}

export function SparkleIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path
        d="M12 3.4 13.35 9 19 10.2 13.35 11.4 12 17 10.65 11.4 5 10.2 10.65 9z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path
        d="M18.2 15.1 18.85 17.1 20.9 17.7 18.85 18.3 18.2 20.3 17.55 18.3 15.5 17.7 17.55 17.1z"
        fill="currentColor"
      />
    </BaseIcon>
  )
}
