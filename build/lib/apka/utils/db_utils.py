"""Pomôcky a informácie špecifické pre dialekty databáz."""

# Informácie špecifické pre dialekty databáz
INFO_O_DIALEKTE = {
    "sqlite": {
        "poznamky": """
        - Používajte SQLite funkcie pre dátum/čas (strftime, datetime)
        - Pre aktuálny dátum použite 'date("now")'
        - Pre dátumovú aritmetiku použite funkcie strftime
        - Dátumy sú uložené ako TEXT v ISO formáte (YYYY-MM-DD HH:MM:SS)
        """,
        "priklady": """
        - Dáta za posledný mesiac:
            WHERE created_at >= date('now', 'start of month', '-1 month')
            AND created_at < date('now', 'start of month')
        """,
    },
    "postgresql": {
        "poznamky": """
        - Používajte PostgreSQL funkcie pre dátum/čas (date_trunc, interval)
        - Pre aktuálny dátum použite CURRENT_DATE
        - Pre dátumovú aritmetiku použite interval
        - Dátumy sú uložené v natívnom timestamp formáte
        """,
        "priklady": """
        - Dáta za posledný mesiac:
            WHERE created_at >= date_trunc('month', current_date - interval '1 month')
            AND created_at < date_trunc('month', current_date)
        """,
    },
  
}
