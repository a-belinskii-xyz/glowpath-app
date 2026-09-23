import { useCatalogIconBlobUrl } from '../lib/useCatalogIconBlobUrl'

type CatalogIconThumbProps = {
  iconId: string
  label: string
  className?: string
  glowColor?: string | null
}

export function CatalogIconThumb({
  iconId,
  label,
  className,
  glowColor,
}: CatalogIconThumbProps) {
  const url = useCatalogIconBlobUrl(iconId)
  const classes = ['catalog-icon-thumb', className].filter(Boolean).join(' ')

  return (
    <span
      className={classes}
      style={
        glowColor
          ? { ['--catalog-icon-glow' as string]: glowColor }
          : undefined
      }
      aria-hidden={!label ? true : undefined}
    >
      {url ? (
        <img src={url} alt="" loading="lazy" />
      ) : (
        <span className="catalog-icon-thumb-placeholder" />
      )}
    </span>
  )
}
