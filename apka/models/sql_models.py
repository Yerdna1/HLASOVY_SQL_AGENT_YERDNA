"""Pydantic modely pre SQL operácie."""

from pydantic import BaseModel, Field

class SQLDotaz(BaseModel):
    """SQL dotaz vygenerovaný z prirodzeného jazyka."""

    dotaz: str = Field(
        ...,
        description="SQL dotaz na vykonanie",
    )
    vysvetlenie: str = Field(
        ...,
        description="Vysvetlenie, čo SQL dotaz robí",
    )
