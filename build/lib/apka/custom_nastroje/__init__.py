"""Definície a spracovatelia nástrojov."""

# Import preložených nástrojov
from .graf import nakresli_plotly_graf
from .databaza import vykonaj_sql

# Zoznam všetkých nástrojov
nastroje = [
    # TODO: Pridať späť importy a nástroje, ak budú implementované
    # query_stock_price,
    # generate_image,
    # internet_search,
    # draft_linkedin_post,
    # create_python_file,
    # execute_python_file,
    # open_browser,
    # draft_email,
    nakresli_plotly_graf,
    vykonaj_sql,
]

__all__ = ["nastroje"]
