"""Pydantic modely pre konfiguráciu databázy."""

from typing import Optional
from pydantic import BaseModel, Field

class KonfiguraciaDatabazy(BaseModel):
    """Konfigurácia databázy."""

    dialekt: str = Field(
        ...,
        description="Dialekt databázy (napr. 'postgresql', 'mysql', 'sqlite')",
    )
    pouzivatelske_meno: Optional[str] = Field(
        None,
        description="Používateľské meno databázy",
    )
    heslo: Optional[str] = Field(
        None,
        description="Heslo databázy",
    )
    hostitel: Optional[str] = Field(
        None,
        description="Hostiteľ databázy",
    )
    port: Optional[int] = Field(
        None,
        description="Port databázy",
    )
    databaza: str = Field(
        ...,
        description="Názov databázy",
    )
