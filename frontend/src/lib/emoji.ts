/**
 * Exactly one emoji: pictograph (+ VS16 / skin tone), ZWJ sequence, flag,
 * subdivision flag or keycap. Mirrors backend `app/core/emoji.py`.
 */
const SINGLE_EMOJI_RE =
  /^(?:[#*0-9]️?⃣|\p{Regional_Indicator}{2}|\p{Emoji_Modifier}|\p{Extended_Pictographic}️?\p{Emoji_Modifier}?(?:[\u{E0020}-\u{E007E}]+\u{E007F}|(?:‍\p{Extended_Pictographic}️?\p{Emoji_Modifier}?)*))$/u

export function isSingleEmoji(value: string): boolean {
  return SINGLE_EMOJI_RE.test(value.trim())
}
