/**
 * Entry share card — draws one mood entry as a 9:16 story image (1080×1920 PNG).
 *
 * Plain Canvas 2D on purpose: DOM-to-image libraries are unreliable in iOS
 * WebViews (Telegram Mini App), and canvas gives the same layout everywhere.
 */

import { buildAmbientGlowColors, moodChipStyle, type ColorScheme } from '../design'
import { hexToOklab, mixOklab, oklabToHex } from '../design/oklab'
import type { MoodEntryGoal, MoodEntryPublic, MoodEntryTag } from '../types/mood'
import type { MoodScoreIconType } from '../types/moodPreferences'
import { getAttachmentObjectUrl } from './attachmentBlobUrl'
import { getCatalogIconObjectUrl } from './catalogIconBlobUrl'
import { formatDayHeading, formatTime, formatWeekday } from './datetime'
import { getGoalIconObjectUrl } from './goalIconBlobUrl'
import { markdownToPlainText } from './markdownPlainText'
import { getBuiltinMoodIconPath } from './moodBuiltinIcons'
import { getMoodIconObjectUrl } from './moodIconBlobUrl'
import { getTagIconObjectUrl } from './tagIconBlobUrl'

export const SHARE_IMAGE_WIDTH = 1080
export const SHARE_IMAGE_HEIGHT = 1920

const W = SHARE_IMAGE_WIDTH
const H = SHARE_IMAGE_HEIGHT
const SIDE = 84
const CARD_PAD = 60
const CARD_RADIUS = 56
const STACK_TOP = 150
const STACK_BOTTOM = H - 250
const HERO_ICON = 260
/** Smaller hero when the card is dense, so the note keeps more lines. */
const HERO_ICON_COMPACT = 180
const PHOTO_MAX = 3
const CHIP_HEIGHT = 76
const CHIP_GAP = 16
const CHIP_MAX_ROWS = 3
const BLOCK_GAP = 44

const SANS =
  'Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, ' +
  '"Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif'
const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'

type Palette = {
  bg: string
  surface: string
  surfaceEdge: string
  text: string
  muted: string
  glowAlpha: number
}

const PALETTES: Record<ColorScheme, Palette> = {
  light: {
    bg: '#eef1f6',
    surface: 'rgba(255, 255, 255, 0.8)',
    surfaceEdge: 'rgba(255, 255, 255, 0.9)',
    text: '#1f2937',
    muted: '#6b7280',
    glowAlpha: 1,
  },
  dark: {
    bg: '#0f1420',
    surface: 'rgba(23, 29, 42, 0.82)',
    surfaceEdge: 'rgba(229, 231, 235, 0.12)',
    text: '#e5e7eb',
    muted: '#9ca3af',
    glowAlpha: 0.55,
  },
}

type IconStyle = { icon_type: MoodScoreIconType; icon: string }
type IconKind = 'mood' | 'tag' | 'goal'
/** Either a decoded image or an emoji / text glyph to draw with fillText. */
type ResolvedIcon = { image: HTMLImageElement } | { glyph: string }

type Chip = {
  label: string
  background: string
  color: string
  icon: ResolvedIcon | null
}

type NoteRun = { text: string; bold: boolean; muted: boolean; gapBefore: boolean }
type NoteLine = { text: string; bold: boolean; muted: boolean; gapBefore: boolean }

export type EntryShareImageInput = {
  entry: MoodEntryPublic
  moodColor: string
  moodIcon: IconStyle
  timeZone: string
  /** BCP 47 locale for dates (e.g. `ru-RU`). */
  dateLocale: string
  scheme: ColorScheme
  brand: string
}

export async function renderEntryShareImage(input: EntryShareImageInput): Promise<Blob> {
  const { entry, moodColor, scheme } = input
  const palette = PALETTES[scheme]

  const photos = entry.attachments
    .filter((attachment) => attachment.kind === 'photo')
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
    .slice(0, PHOTO_MAX)

  const [moodIcon, photoImages, tagChips, goalChips] = await Promise.all([
    resolveIcon(input.moodIcon, 'mood', moodColor),
    Promise.all(
      photos.map((photo) =>
        getAttachmentObjectUrl(entry.id, photo.id)
          .then(loadImage)
          .catch(() => null),
      ),
    ),
    Promise.all(entry.tags.map((tag) => buildChip(tag, 'tag', scheme))),
    Promise.all(entry.goals.map((goal) => buildChip(goal, 'goal', scheme))),
    waitForFonts(),
  ])

  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    throw new Error('Canvas 2D is not available')
  }
  ctx.textBaseline = 'alphabetic'

  const glowColors = [
    moodColor,
    ...entry.tags.map((tag) => tag.color),
    ...entry.goals.map((goal) => goal.color),
  ]
  drawBackground(ctx, palette, glowColors)

  const images = photoImages.filter((image): image is HTMLImageElement => image !== null)
  const chips = [...tagChips, ...goalChips]
  const dateLine = formatDateLine(entry.recorded_at, input.timeZone, input.dateLocale)

  // —— Measure ——
  const cardWidth = W - SIDE * 2
  const innerWidth = cardWidth - CARD_PAD * 2
  const noteRuns = entry.note ? markdownToRuns(entry.note) : []
  const hasNote = noteRuns.length > 0
  const chipRows = layoutChips(ctx, chips, innerWidth)
  const dense = hasNote && (images.length > 0 || chipRows.length > 1)
  const heroIcon = dense ? HERO_ICON_COMPACT : HERO_ICON
  const heroHeight = heroIcon + 56 + 80 + 20 + 44
  const chipsHeight =
    chipRows.length > 0 ? chipRows.length * CHIP_HEIGHT + (chipRows.length - 1) * CHIP_GAP : 0

  const maxCardInner = STACK_BOTTOM - STACK_TOP - heroHeight - BLOCK_GAP - CARD_PAD * 2
  let photosHeight = images.length === 0 ? 0 : photoBlockHeight(images.length, hasNote)
  const fixedBlocks = [photosHeight, chipsHeight].filter((h) => h > 0)
  const gapsWithoutNote = Math.max(0, fixedBlocks.length - 1) * BLOCK_GAP

  let note: NoteLayout | null = null
  if (hasNote) {
    const noteGap = fixedBlocks.length > 0 ? BLOCK_GAP : 0
    let noteBudget = maxCardInner - photosHeight - chipsHeight - gapsWithoutNote - noteGap
    // Text is the point of the card: keep ~7 lines before photos get their full height.
    const minNote = 7 * 55
    if (noteBudget < minNote && photosHeight > 0) {
      const shrinkTo = Math.max(220, photosHeight - (minNote - noteBudget))
      noteBudget += photosHeight - shrinkTo
      photosHeight = shrinkTo
    }
    note = layoutNote(ctx, noteRuns, innerWidth, Math.max(noteBudget, 62))
  }

  const cardBlocks = [note?.height ?? 0, photosHeight, chipsHeight].filter((h) => h > 0)
  const cardInner =
    cardBlocks.reduce((sum, h) => sum + h, 0) + Math.max(0, cardBlocks.length - 1) * BLOCK_GAP
  const cardHeight = cardBlocks.length > 0 ? cardInner + CARD_PAD * 2 : 0
  const stackHeight = heroHeight + (cardHeight > 0 ? BLOCK_GAP + cardHeight : 0)
  const stackTop = STACK_TOP + Math.max(0, (STACK_BOTTOM - STACK_TOP - stackHeight) / 2)

  // —— Hero ——
  let y = stackTop
  drawHeroIcon(ctx, moodIcon, moodColor, W / 2, y + heroIcon / 2, heroIcon)
  y += heroIcon + 56
  ctx.textAlign = 'center'
  ctx.fillStyle = palette.text
  ctx.font = `700 72px ${SANS}`
  ctx.fillText(ellipsize(ctx, entry.score_label, W - SIDE * 2), W / 2, y + 62)
  y += 80 + 20
  ctx.fillStyle = palette.muted
  ctx.font = `500 38px ${SANS}`
  ctx.fillText(ellipsize(ctx, dateLine, W - SIDE * 2), W / 2, y + 36)
  y += 44

  // —— Card ——
  if (cardHeight > 0) {
    y += BLOCK_GAP
    const cardX = SIDE
    ctx.save()
    ctx.shadowColor = scheme === 'dark' ? 'rgba(0, 0, 0, 0.35)' : 'rgba(15, 23, 42, 0.08)'
    ctx.shadowBlur = 60
    ctx.shadowOffsetY = 18
    roundRect(ctx, cardX, y, cardWidth, cardHeight, CARD_RADIUS)
    ctx.fillStyle = palette.surface
    ctx.fill()
    ctx.restore()
    roundRect(ctx, cardX + 1, y + 1, cardWidth - 2, cardHeight - 2, CARD_RADIUS - 1)
    ctx.strokeStyle = palette.surfaceEdge
    ctx.lineWidth = 2
    ctx.stroke()

    let cy = y + CARD_PAD
    const cx = cardX + CARD_PAD
    const blocks: Array<() => number> = []
    if (note) {
      const layout = note
      blocks.push(() => drawNote(ctx, layout, cx, cy, palette))
    }
    if (photosHeight > 0) {
      blocks.push(() => {
        drawPhotos(ctx, images, cx, cy, innerWidth, photosHeight)
        return photosHeight
      })
    }
    if (chipRows.length > 0) {
      blocks.push(() => {
        drawChips(ctx, chipRows, cx, cy)
        return chipsHeight
      })
    }
    blocks.forEach((draw, index) => {
      if (index > 0) {
        cy += BLOCK_GAP
      }
      cy += draw()
    })
  }

  drawWordmark(ctx, input.brand, glowColors, palette, scheme)

  return canvasToPng(canvas)
}

export function shareImageFileName(entry: MoodEntryPublic, timeZone: string): string {
  const day = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(entry.recorded_at))
  return `glowpath-${day}.png`
}

// —— Background & brand ——

function drawBackground(ctx: CanvasRenderingContext2D, palette: Palette, colors: string[]) {
  ctx.fillStyle = palette.bg
  ctx.fillRect(0, 0, W, H)
  const glow = buildAmbientGlowColors(colors)
  const blobs: Array<[number, number, number, string]> = [
    [W * 0.12, H * 0.1, W * 0.95, glow.c1],
    [W * 0.95, H * 0.34, W * 0.85, glow.c2],
    [W * 0.05, H * 0.7, W * 0.9, glow.c3],
    [W * 0.9, H * 0.96, W * 0.9, glow.c4],
  ]
  ctx.save()
  ctx.globalAlpha = palette.glowAlpha
  for (const [x, y, r, color] of blobs) {
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, r)
    gradient.addColorStop(0, color)
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, W, H)
  }
  ctx.restore()
}

function drawWordmark(
  ctx: CanvasRenderingContext2D,
  brand: string,
  colors: string[],
  palette: Palette,
  scheme: ColorScheme,
) {
  const glow = buildAmbientGlowColors(colors)
  const lift = (hex: string) => {
    if (scheme !== 'dark') {
      return hex
    }
    const ink = hexToOklab(hex)
    const white = hexToOklab('#f8fafc')
    return ink && white ? oklabToHex(mixOklab([ink, white], [0.42, 0.58])) : hex
  }
  const y = H - 118
  ctx.save()
  ctx.textAlign = 'center'
  ctx.font = `700 54px ${MONO}`
  const width = ctx.measureText(brand).width
  const gradient = ctx.createLinearGradient(W / 2 - width / 2, 0, W / 2 + width / 2, 0)
  gradient.addColorStop(0, lift(glow.brand1))
  gradient.addColorStop(0.5, lift(glow.brand2))
  gradient.addColorStop(1, lift(glow.brand3))
  ctx.fillStyle = gradient
  ctx.fillText(brand, W / 2, y)
  ctx.restore()
  // Hairline above the wordmark keeps it reading as a signature, not content.
  ctx.save()
  ctx.strokeStyle = palette.muted
  ctx.globalAlpha = 0.35
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(W / 2 - 40, y - 78)
  ctx.lineTo(W / 2 + 40, y - 78)
  ctx.stroke()
  ctx.restore()
}

// —— Hero ——

function drawHeroIcon(
  ctx: CanvasRenderingContext2D,
  icon: ResolvedIcon | null,
  color: string,
  cx: number,
  cy: number,
  size: number,
) {
  ctx.save()
  // shadowBlur (not ctx.filter) — Safari ignores canvas filters.
  ctx.shadowColor = color
  ctx.shadowBlur = 70
  if (icon && 'image' in icon) {
    drawContain(ctx, icon.image, cx - size / 2, cy - size / 2, size, size)
  } else {
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.font = `${Math.round(size * 0.86)}px ${SANS}`
    ctx.fillStyle = color
    ctx.fillText(icon?.glyph ?? '•', cx, cy + size * 0.04)
  }
  ctx.restore()
}

function formatDateLine(iso: string, timeZone: string, locale: string): string {
  const weekday = formatWeekday(iso, timeZone, locale)
  const capitalized = weekday.charAt(0).toLocaleUpperCase(locale) + weekday.slice(1)
  return `${capitalized} · ${formatDayHeading(iso, timeZone, locale)} · ${formatTime(iso, timeZone)}`
}

// —— Note ——

type NoteLayout = {
  lines: NoteLine[]
  fontSize: number
  lineHeight: number
  height: number
}

const NOTE_SIZES = [54, 46, 40] as const

function markdownToRuns(markdown: string): NoteRun[] {
  const runs: NoteRun[] = []
  let pendingGap = false
  let inFence = false
  for (const rawLine of markdown.replace(/\r\n/g, '\n').split('\n')) {
    if (/^\s*```/.test(rawLine)) {
      inFence = !inFence
      continue
    }
    const line = rawLine.trimEnd()
    if (!line.trim()) {
      pendingGap = runs.length > 0
      continue
    }
    if (!inFence && /^\s*([-*_]\s*){3,}$/.test(line)) {
      pendingGap = runs.length > 0
      continue
    }
    let text = line
    let bold = false
    let muted = false
    let prefix = ''
    if (!inFence) {
      const heading = /^#{1,6}\s+(.*)$/.exec(text)
      const task = /^\s*[-*+]\s+\[([ xX])\]\s+(.*)$/.exec(text)
      const bullet = /^\s*[-*+]\s+(.*)$/.exec(text)
      const ordered = /^\s*(\d+)[.)]\s+(.*)$/.exec(text)
      const quote = /^\s*>\s?(.*)$/.exec(text)
      if (heading) {
        text = heading[1]
        bold = true
      } else if (task) {
        prefix = task[1] === ' ' ? '☐ ' : '☑ '
        text = task[2]
      } else if (bullet) {
        prefix = '•  '
        text = bullet[1]
      } else if (ordered) {
        prefix = `${ordered[1]}. `
        text = ordered[2]
      } else if (quote) {
        text = quote[1]
        muted = true
      }
      text = markdownToPlainText(text)
    }
    const trimmed = (prefix + text).trim()
    if (!trimmed) {
      continue
    }
    runs.push({ text: trimmed, bold, muted, gapBefore: pendingGap })
    pendingGap = false
  }
  return runs
}

function noteFont(size: number, bold: boolean): string {
  return `${bold ? 700 : 400} ${size}px ${SANS}`
}

function wrapNote(
  ctx: CanvasRenderingContext2D,
  runs: NoteRun[],
  width: number,
  size: number,
): NoteLine[] {
  const lines: NoteLine[] = []
  for (const run of runs) {
    ctx.font = noteFont(size, run.bold)
    wrapText(ctx, run.text, width).forEach((text, index) => {
      lines.push({
        text,
        bold: run.bold,
        muted: run.muted,
        gapBefore: index === 0 && run.gapBefore,
      })
    })
  }
  return lines
}

function linesHeight(lines: NoteLine[], lineHeight: number): number {
  return lines.reduce(
    (sum, line) => sum + lineHeight + (line.gapBefore ? Math.round(lineHeight * 0.45) : 0),
    0,
  )
}

function layoutNote(
  ctx: CanvasRenderingContext2D,
  runs: NoteRun[],
  width: number,
  maxHeight: number,
): NoteLayout {
  for (const size of NOTE_SIZES) {
    const lineHeight = Math.round(size * 1.38)
    const lines = wrapNote(ctx, runs, width, size)
    const height = linesHeight(lines, lineHeight)
    if (height <= maxHeight) {
      return { lines, fontSize: size, lineHeight, height }
    }
  }
  const size = NOTE_SIZES[NOTE_SIZES.length - 1]
  const lineHeight = Math.round(size * 1.38)
  const all = wrapNote(ctx, runs, width, size)
  const kept: NoteLine[] = []
  for (const line of all) {
    if (linesHeight([...kept, line], lineHeight) > maxHeight) {
      break
    }
    kept.push(line)
  }
  if (kept.length === 0 && all.length > 0) {
    kept.push(all[0])
  }
  if (kept.length < all.length) {
    const last = kept[kept.length - 1]
    ctx.font = noteFont(size, last.bold)
    kept[kept.length - 1] = { ...last, text: ellipsize(ctx, `${last.text}…`, width, true) }
  }
  return { lines: kept, fontSize: size, lineHeight, height: linesHeight(kept, lineHeight) }
}

function drawNote(
  ctx: CanvasRenderingContext2D,
  layout: NoteLayout,
  x: number,
  top: number,
  palette: Palette,
): number {
  ctx.save()
  ctx.textAlign = 'left'
  let y = top
  for (const line of layout.lines) {
    if (line.gapBefore) {
      y += Math.round(layout.lineHeight * 0.45)
    }
    ctx.font = noteFont(layout.fontSize, line.bold)
    ctx.fillStyle = line.muted ? palette.muted : palette.text
    // Baseline sits ~78% down the line box for Latin/Cyrillic system fonts.
    ctx.fillText(line.text, x, y + Math.round(layout.lineHeight * 0.74))
    y += layout.lineHeight
  }
  ctx.restore()
  return layout.height
}

// —— Photos ——

function photoBlockHeight(count: number, hasNote: boolean): number {
  if (count === 1) {
    return hasNote ? 460 : 720
  }
  return hasNote ? 340 : 480
}

function drawPhotos(
  ctx: CanvasRenderingContext2D,
  images: HTMLImageElement[],
  x: number,
  y: number,
  width: number,
  height: number,
) {
  const gap = 18
  const count = images.length
  const cellWidth = (width - gap * (count - 1)) / count
  images.forEach((image, index) => {
    const cellX = x + index * (cellWidth + gap)
    ctx.save()
    roundRect(ctx, cellX, y, cellWidth, height, 34)
    ctx.clip()
    drawCover(ctx, image, cellX, y, cellWidth, height)
    ctx.restore()
  })
}

// —— Chips ——

async function buildChip(
  item: MoodEntryTag | MoodEntryGoal,
  kind: IconKind,
  scheme: ColorScheme,
): Promise<Chip> {
  const style = moodChipStyle(item.color, scheme)
  return {
    label: item.label,
    background: style.background,
    color: style.color,
    icon: await resolveIcon(item, kind, style.color),
  }
}

type ChipPlacement = { chip: Chip; width: number; x: number }

const CHIP_FONT = `600 36px ${SANS}`
const CHIP_ICON = 40
const CHIP_PAD_X = 28
const CHIP_ICON_GAP = 14

function layoutChips(
  ctx: CanvasRenderingContext2D,
  chips: Chip[],
  maxWidth: number,
): ChipPlacement[][] {
  ctx.font = CHIP_FONT
  const widthOf = (chip: Chip) => {
    const labelMax = maxWidth - CHIP_PAD_X * 2 - (chip.icon ? CHIP_ICON + CHIP_ICON_GAP : 0)
    const label = ellipsize(ctx, chip.label, labelMax)
    chip.label = label
    return (
      CHIP_PAD_X * 2 +
      ctx.measureText(label).width +
      (chip.icon ? CHIP_ICON + CHIP_ICON_GAP : 0)
    )
  }
  const rows: ChipPlacement[][] = []
  let row: ChipPlacement[] = []
  let rowWidth = 0
  for (let index = 0; index < chips.length; index += 1) {
    const chip = chips[index]
    const width = widthOf(chip)
    const nextWidth = row.length === 0 ? width : rowWidth + CHIP_GAP + width
    if (row.length > 0 && nextWidth > maxWidth) {
      rows.push(row)
      row = []
      rowWidth = 0
    }
    if (rows.length === CHIP_MAX_ROWS) {
      break
    }
    const x = row.length === 0 ? 0 : rowWidth + CHIP_GAP
    row.push({ chip, width, x })
    rowWidth = x + width
  }
  if (row.length > 0 && rows.length < CHIP_MAX_ROWS) {
    rows.push(row)
  }

  const placedCount = () => rows.reduce((sum, r) => sum + r.length, 0)
  if (chips.length > placedCount() && rows.length > 0) {
    const last = rows[rows.length - 1]
    const more: Chip = {
      label: '',
      background: 'rgba(127, 127, 127, 0.16)',
      color: '#8b93a1',
      icon: null,
    }
    const fitMore = () => {
      more.label = `+${chips.length - placedCount()}`
      const tail = last[last.length - 1]
      const width = widthOf(more)
      return { x: tail.x + tail.width + CHIP_GAP, width }
    }
    let slot = fitMore()
    while (last.length > 1 && slot.x + slot.width > maxWidth) {
      last.pop()
      slot = fitMore()
    }
    last.push({ chip: more, width: slot.width, x: slot.x })
  }
  return rows
}

function drawChips(ctx: CanvasRenderingContext2D, rows: ChipPlacement[][], x: number, y: number) {
  ctx.save()
  ctx.font = CHIP_FONT
  ctx.textAlign = 'left'
  rows.forEach((row, rowIndex) => {
    const top = y + rowIndex * (CHIP_HEIGHT + CHIP_GAP)
    for (const { chip, width, x: offset } of row) {
      const left = x + offset
      roundRect(ctx, left, top, width, CHIP_HEIGHT, CHIP_HEIGHT / 2)
      ctx.fillStyle = chip.background
      ctx.fill()
      let textX = left + CHIP_PAD_X
      if (chip.icon) {
        const iconY = top + (CHIP_HEIGHT - CHIP_ICON) / 2
        if ('image' in chip.icon) {
          drawContain(ctx, chip.icon.image, textX, iconY, CHIP_ICON, CHIP_ICON)
        } else {
          ctx.save()
          ctx.font = `${CHIP_ICON - 6}px ${SANS}`
          ctx.textBaseline = 'middle'
          ctx.fillStyle = chip.color
          ctx.fillText(chip.icon.glyph, textX, top + CHIP_HEIGHT / 2 + 2)
          ctx.restore()
        }
        textX += CHIP_ICON + CHIP_ICON_GAP
      }
      ctx.fillStyle = chip.color
      ctx.textBaseline = 'middle'
      ctx.fillText(chip.label, textX, top + CHIP_HEIGHT / 2 + 2)
    }
  })
  ctx.restore()
}

// —— Icons & images ——

async function resolveIcon(
  style: IconStyle,
  kind: IconKind,
  color: string,
): Promise<ResolvedIcon | null> {
  try {
    if (style.icon_type === 'builtin') {
      return { image: await loadTintedSvg(getBuiltinMoodIconPath(style.icon), color) }
    }
    if (style.icon_type === 'upload') {
      const getUrl =
        kind === 'mood'
          ? getMoodIconObjectUrl
          : kind === 'tag'
            ? getTagIconObjectUrl
            : getGoalIconObjectUrl
      return { image: await loadImage(await getUrl(style.icon)) }
    }
    if (style.icon_type === 'catalog') {
      return { image: await loadImage(await getCatalogIconObjectUrl(style.icon)) }
    }
    return style.icon ? { glyph: style.icon } : null
  } catch {
    return null
  }
}

/** Line built-ins use `currentColor` and get tinted; face built-ins keep their own colors. */
async function loadTintedSvg(path: string, color: string): Promise<HTMLImageElement> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`Icon ${path} failed: ${response.status}`)
  }
  const source = (await response.text())
    .replace(/currentColor/g, color)
    .replace('<svg ', '<svg width="256" height="256" ')
  const url = URL.createObjectURL(new Blob([source], { type: 'image/svg+xml' }))
  try {
    return await loadImage(url)
  } finally {
    URL.revokeObjectURL(url)
  }
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.decoding = 'async'
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error(`Image failed to load: ${src}`))
    image.src = src
  })
}

async function waitForFonts(): Promise<void> {
  try {
    await document.fonts?.ready
  } catch {
    // Font loading API missing — system fonts are fine.
  }
}

function drawContain(
  ctx: CanvasRenderingContext2D,
  image: HTMLImageElement,
  x: number,
  y: number,
  width: number,
  height: number,
) {
  const iw = image.naturalWidth || width
  const ih = image.naturalHeight || height
  const scale = Math.min(width / iw, height / ih)
  const dw = iw * scale
  const dh = ih * scale
  ctx.drawImage(image, x + (width - dw) / 2, y + (height - dh) / 2, dw, dh)
}

function drawCover(
  ctx: CanvasRenderingContext2D,
  image: HTMLImageElement,
  x: number,
  y: number,
  width: number,
  height: number,
) {
  const iw = image.naturalWidth
  const ih = image.naturalHeight
  if (!iw || !ih) {
    return
  }
  const scale = Math.max(width / iw, height / ih)
  const sw = width / scale
  const sh = height / scale
  ctx.drawImage(image, (iw - sw) / 2, (ih - sh) / 2, sw, sh, x, y, width, height)
}

// —— Text helpers ——

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = []
  let line = ''
  for (const token of text.split(/(\s+)/)) {
    if (!token) {
      continue
    }
    const candidate = line + token
    if (ctx.measureText(candidate).width <= maxWidth) {
      line = candidate
      continue
    }
    if (/^\s+$/.test(token)) {
      lines.push(line)
      line = ''
      continue
    }
    if (line.trim()) {
      lines.push(line.trimEnd())
    }
    line = ''
    // A single token wider than the line: break it by grapheme-ish code points.
    for (const char of Array.from(token)) {
      if (ctx.measureText(line + char).width > maxWidth && line) {
        lines.push(line)
        line = ''
      }
      line += char
    }
  }
  if (line.trim()) {
    lines.push(line.trimEnd())
  }
  return lines
}

function ellipsize(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
  forceEllipsis = false,
): string {
  if (!forceEllipsis && ctx.measureText(text).width <= maxWidth) {
    return text
  }
  const chars = Array.from(forceEllipsis ? text.replace(/…$/, '') : text)
  // "радости.…" reads as a typo; drop trailing punctuation before the ellipsis.
  const body = () => chars.join('').replace(/[\s.,;:!?]+$/, '')
  while (chars.length > 0 && ctx.measureText(`${body()}…`).width > maxWidth) {
    chars.pop()
  }
  return `${body()}…`
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) {
  const r = Math.min(radius, width / 2, height / 2)
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + width, y, x + width, y + height, r)
  ctx.arcTo(x + width, y + height, x, y + height, r)
  ctx.arcTo(x, y + height, x, y, r)
  ctx.arcTo(x, y, x + width, y, r)
  ctx.closePath()
}

function canvasToPng(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob)
      } else {
        reject(new Error('Canvas export failed'))
      }
    }, 'image/png')
  })
}
