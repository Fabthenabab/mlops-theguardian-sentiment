# tabs/block_search_multi_criteria.py
import streamlit as st
import pandas as pd

from utils.books import get_one_book_by_ISBN, get_books_by_title_words, render_book_full
from utils.books import display_books

@st.fragment
def get_book_x_multi_criteria(df: pd.DataFrame):
    
    # Select Book by isbn
    # ==========================================
    col0, col1 = st.columns([1, 5])
    with col0:
        st.markdown("Search by isbn")
    with col1:
        isbn = st.text_input(
            "Enter ISBN",
            label_visibility="collapsed"    # Label invisible
        )
    
    df_book = get_one_book_by_ISBN(df, isbn)
    df_book_placeholder = st.empty()
    
    df_book_placeholder = render_book_full(df_book)
    
    # Select Book by Title
    # ==========================================
    col2, col3 = st.columns([1, 5])
    with col2:
        st.markdown("Search title words")
    with col3:
        title_words = st.text_input(
            "Enter title words",
            label_visibility="collapsed"    # Label invisible
        )

    if not title_words or not title_words.strip():
        st.info("👆 Enter words to search for books")
        return

    st.markdown(f"title_words: {title_words}")
    df_books = get_books_by_title_words(df, title_words)
    display_books(df_books)