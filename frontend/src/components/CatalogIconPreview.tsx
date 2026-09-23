import { moodGlowFilter } from '../design'
import type { CatalogIconWithPackPublic } from '../types/marketplace'
import { CatalogIconThumb } from './CatalogIconThumb'

type CatalogIconPreviewProps = {
  icons: CatalogIconWithPackPublic[]
  variant: 'single' | 'sample'
}

export function CatalogIconPreview({ icons, variant }: CatalogIconPreviewProps) {
  if (icons.length === 0) {
    return null
  }
  const showLabels = variant === 'single'
  return (
    <ul
      className={`confirm-icon-preview confirm-icon-preview--${variant}`}
      aria-hidden={showLabels ? undefined : true}
    >
      {icons.map((icon) => {
        const glow = icon.suggested_colors[0] ?? '#94a3b8'
        return (
          <li key={icon.id} className="confirm-icon-preview-item">
            <div
              className="confirm-icon-preview-media"
              style={{ filter: moodGlowFilter(glow) }}
            >
              <CatalogIconThumb
                iconId={icon.id}
                label={showLabels ? icon.label : ''}
                glowColor={glow}
              />
            </div>
            {showLabels ? <p className="confirm-icon-preview-label">{icon.label}</p> : null}
          </li>
        )
      })}
    </ul>
  )
}
