export type OnboardingOption = {
  key: string
  label: string
}

export type OnboardingQuestion = {
  block_id: string
  title: string
  selection: string
  max_selections: number
  options: OnboardingOption[]
}

export type OnboardingCatalog = {
  questions: OnboardingQuestion[]
}

export type OnboardingSuggestionTag = {
  slug: string
  label: string
  color: string
  icon: string
}

export type OnboardingSuggestionTagGroup = {
  slug: string
  label: string
  pack_id: string
  tags: OnboardingSuggestionTag[]
}

export type OnboardingSuggestionTemplate = {
  slug: string
  label: string
  pack_id: string
  body: string
}

export type OnboardingSuggestions = {
  tag_groups: OnboardingSuggestionTagGroup[]
  note_templates: OnboardingSuggestionTemplate[]
}

export type OnboardingCompleteRequest = {
  skip?: boolean
  option_keys?: string[]
  tag_group_slugs?: string[]
  note_template_slugs?: string[]
  email_reminders?: boolean
}
