export type Meal = 'morning' | 'day' | 'evening' | 'snack'

export type BodySettings = {
  show_weight: boolean
  show_food: boolean
  /** Blur the weight number on «Моё» until tapped. */
  hide_weight: boolean
  /** Up to three goals the food drawer offers to mark, e.g. "Eat properly". */
  food_goal_ids: string[]
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
