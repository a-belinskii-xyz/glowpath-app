from pydantic import BaseModel, Field


class OnboardingOptionPublic(BaseModel):
    key: str
    label: str


class OnboardingQuestionPublic(BaseModel):
    block_id: str
    title: str
    selection: str
    max_selections: int
    options: list[OnboardingOptionPublic]


class OnboardingCatalogResponse(BaseModel):
    questions: list[OnboardingQuestionPublic]


class OnboardingSuggestionTagPublic(BaseModel):
    slug: str
    label: str
    color: str
    icon: str


class OnboardingSuggestionTagGroupPublic(BaseModel):
    slug: str
    label: str
    pack_id: str
    tags: list[OnboardingSuggestionTagPublic]


class OnboardingSuggestionTemplatePublic(BaseModel):
    slug: str
    label: str
    pack_id: str
    body: str


class OnboardingSuggestionsRequest(BaseModel):
    option_keys: list[str] = Field(default_factory=list)


class OnboardingSuggestionsResponse(BaseModel):
    tag_groups: list[OnboardingSuggestionTagGroupPublic]
    note_templates: list[OnboardingSuggestionTemplatePublic]


class OnboardingCompleteRequest(BaseModel):
    skip: bool = False
    option_keys: list[str] = Field(default_factory=list)
    tag_group_slugs: list[str] = Field(default_factory=list)
    note_template_slugs: list[str] = Field(default_factory=list)
    # Opt-in toggle shown to accounts without Telegram: daily reminder by email.
    email_reminders: bool = False
