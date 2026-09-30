from pydantic import BaseModel


class AccountDeleteRequest(BaseModel):
    # Explicit flag so a stray DELETE without a body never wipes an account.
    confirm: bool = False


class AccountExportTelegramResponse(BaseModel):
    parts: int
