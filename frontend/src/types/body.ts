export type Meal = 'morning' | 'day' | 'evening' | 'snack'

export type BodySettings = {
  show_weight: boolean
  show_food: boolean
  /** Blur the weight number on «Моё» until tapped. */
  hide_weight: boolean
  /** Up to three goals the food drawer offers to mark, e.g. "Eat properly". */
  food_goal_ids: string[]
  show_sleep: boolean
  /** Centimetres; only used to show BMI next to the weight. */
  height_cm: number | null
}

export type WeightPoint = {
  day: string
  /** Kilograms, one decimal. */
  value: number
}

export type FoodLog = {
  id: string
  day: string
  meal: Meal | null
  text: string
  created_at: string
}

export type SleepQuality = 'hard' | 'ok' | 'good'

/** One night, stored under the morning it ended on. Times are "HH:MM:SS". */
export type SleepLog = {
  day: string
  bed_time: string
  wake_time: string
  up_time: string | null
  quality: SleepQuality | null
  note: string | null
}
