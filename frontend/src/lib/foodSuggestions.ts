/** Food items from past notes, offered again while writing a new one (GP-59). */

import { parseFoodLine } from "./foodItems";
import type { FoodLog } from "../types/body";

export type FoodSuggestion = {
  name: string;
  /** The grams written the last time, or "" when none were. */
  grams: string;
  /** In how many notes it appeared. */
  count: number;
};

// Longer pieces are sentences ("felt like having something sweet"), not dishes.
const MAX_NAME_LENGTH = 40;

function keyOf(name: string): string {
  return name.toLowerCase().replace(/\s+/g, " ").trim();
}

/** Items from the notes, most frequent first; the latest spelling and grams win. */
export function buildFoodSuggestions(logs: FoodLog[]): FoodSuggestion[] {
  const byKey = new Map<string, FoodSuggestion & { last: number }>();
  const ordered = [...logs].sort((a, b) =>
    a.day === b.day ? a.created_at.localeCompare(b.created_at) : a.day < b.day ? -1 : 1,
  );
  ordered.forEach((log, order) => {
    const seen = new Set<string>();
    for (const line of log.text.split("\n")) {
      const item = parseFoodLine(line.trim());
      // A text note "oatmeal, banana, coffee" is three items.
      const pieces = item.grams ? [item] : item.name.split(/[,;]/).map((name) => ({ name, grams: "" }));
      for (const piece of pieces) {
        const name = piece.name.trim().replace(/[.!]+$/, "");
        const key = keyOf(name);
        if (!key || name.length > MAX_NAME_LENGTH) continue;
        const known = byKey.get(key);
        const display = name.charAt(0).toUpperCase() + name.slice(1);
        if (known) {
          if (!seen.has(key)) known.count += 1;
          known.name = display;
          if (piece.grams) known.grams = piece.grams;
          known.last = order;
        } else {
          byKey.set(key, { name: display, grams: piece.grams, count: 1, last: order });
        }
        seen.add(key);
      }
    }
  });
  return [...byKey.values()]
    .sort((a, b) => b.count - a.count || b.last - a.last)
    .map(({ name, grams, count }) => ({ name, grams, count }));
}

/** Up to ``limit`` items matching what is typed: word starts first, then anywhere in the name. */
export function matchFoodSuggestions(
  suggestions: FoodSuggestion[],
  query: string,
  limit = 5,
): FoodSuggestion[] {
  const typed = keyOf(query);
  if (!typed) return [];
  const starts: FoodSuggestion[] = [];
  const contains: FoodSuggestion[] = [];
  for (const item of suggestions) {
    const key = keyOf(item.name);
    if (key === typed) continue;
    if (key.startsWith(typed) || key.includes(` ${typed}`)) starts.push(item);
    else if (key.includes(typed)) contains.push(item);
  }
  return [...starts, ...contains].slice(0, limit);
}

/** Whether a note being written already has this item, so it is not offered twice. */
export function hasFoodItem(names: string[], suggestion: FoodSuggestion): boolean {
  const key = keyOf(suggestion.name);
  return names.some((name) => keyOf(name) === key);
}
