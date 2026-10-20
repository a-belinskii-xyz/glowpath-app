/** The food drawer's list mode (GP-49): rows of "what — grams" saved as plain lines of text. */

export type FoodItem = { name: string; grams: string };
export type FoodInputMode = "text" | "list";

const MODE_KEY = "glowpath.foodInputMode";
// "Гречка — 200 г", "rice - 150g", "чай – 250 гр."
const LINE_WITH_GRAMS =
  /^(.*\S)\s*[—–-]\s*(\d{1,4}(?:[.,]\d)?)\s*(?:г|гр|g)?\.?$/i;

export function emptyItem(): FoodItem {
  return { name: "", grams: "" };
}

/** One line of a note: "Гречка — 200 г" gives the name and grams, anything else is just a name. */
export function parseFoodLine(line: string): FoodItem {
  const match = LINE_WITH_GRAMS.exec(line);
  return match
    ? { name: match[1].trim(), grams: match[2] }
    : { name: line, grams: "" };
}

export function formatFoodLine(item: FoodItem, unit: string): string {
  return item.grams
    ? `${item.name.trim()} — ${item.grams} ${unit}`
    : item.name.trim();
}

export function parseFoodItems(text: string): FoodItem[] {
  const items = text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map(parseFoodLine);
  return items.length > 0 ? items : [emptyItem()];
}

export function serializeFoodItems(items: FoodItem[], unit: string): string {
  return items
    .filter((item) => item.name.trim())
    .map((item) => formatFoodLine(item, unit))
    .join("\n");
}

export function readFoodInputMode(): FoodInputMode {
  try {
    return localStorage.getItem(MODE_KEY) === "list" ? "list" : "text";
  } catch {
    return "text";
  }
}

export function saveFoodInputMode(mode: FoodInputMode): void {
  try {
    localStorage.setItem(MODE_KEY, mode);
  } catch {
    // Private mode or blocked storage: the switch just is not remembered.
  }
}
