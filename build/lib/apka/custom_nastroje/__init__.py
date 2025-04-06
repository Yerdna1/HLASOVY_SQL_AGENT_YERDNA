"""Definície a spracovatelia nástrojov."""

# Import preložených nástrojov
from .graf import nakresli_plotly_graf
from .databaza import vykonaj_sql
from .email import draft_email
from .browser import open_browser
from .python_file import  execute_python_file, create_python_file
from .linkedin import draft_linkedin_post
from .image import generate_image
from .stock import query_stock_price
from .search import internet_search

# Zoznam všetkých nástrojov
nastroje = [
    # TODO: Pridať späť importy a nástroje, ak budú implementované
     query_stock_price,
     generate_image,
     internet_search,
     draft_linkedin_post,
     create_python_file,
     execute_python_file,
     open_browser,
     draft_email,
    nakresli_plotly_graf,
    vykonaj_sql,
]

__all__ = ["nastroje"]
