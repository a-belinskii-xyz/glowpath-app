import { useState, type ReactNode } from 'react'

import type { IconCrop, SearchTagPublic } from '../../types/marketplace'
import { ImageCropModal } from '../ImageCropModal'
import { StaffIconFields, type IconDraft } from './StaffIconFields'

export type IconImage = {
  image: HTMLImageElement
  objectUrl: string
  fileName: string
}

type StaffIconDialogProps = {
  source: IconImage
  initialDraft: IconDraft
  initialCrop?: IconCrop | null
  title: string
  hint?: string
  searchTags: SearchTagPublic[]
  busy: boolean
  onSave: (draft: IconDraft, crop: IconCrop) => void
  onCancel: () => void
  /** Secondary action next to Cancel (skip a file, show the whole image). */
  secondaryLabel?: string
  onSecondary?: (draft: IconDraft) => void
  /** Extra controls under the fields (cover, replace file, delete). */
  footer?: ReactNode
}

/** Crop frame plus icon details in one dialog, like the icon editors users see. */
export function StaffIconDialog({
  source,
  initialDraft,
  initialCrop,
  title,
  hint,
  searchTags,
  busy,
  onSave,
  onCancel,
  secondaryLabel,
  onSecondary,
  footer,
}: StaffIconDialogProps) {
  const [draft, setDraft] = useState(initialDraft)

  return (
    <ImageCropModal
      image={source.image}
      imageUrl={source.objectUrl}
      fileName={source.fileName}
      initialRegion={initialCrop}
      isSaving={busy}
      title={title}
      hint={hint}
      onCancel={onCancel}
      onSaveRegion={(region) => onSave(draft, region)}
      resetLabel={secondaryLabel}
      onReset={onSecondary ? () => onSecondary(draft) : undefined}
    >
      <StaffIconFields draft={draft} searchTags={searchTags} onChange={setDraft} />
      {footer}
    </ImageCropModal>
  )
}
