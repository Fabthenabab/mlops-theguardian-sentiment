# tabs/block_reco_search_title.py
import streamlit as st
import pandas as pd
import numpy as np

from utils.books import get_one_book_by_ISBN, get_books_by_title_words, render_book_full, display_books
   
from pipeline.core.src.themes import get_similar_books_content_based
from pipeline.core.src.collab import get_similar_books_collaborative


# ============================================
# Recommend by content
# ============================================
def get_reco_x_content_x_book_x_isbn(df: pd.DataFrame, mx: np.ndarray):
    """ 
    Get string input
    parse it to retrieve dataframe
    allow user to select idx
    retrieve one book
    get isbn
    compute recommendations with matrix tfdif_svd passed as an argument
    display best recommended books
    """
    
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
    
    # Vérifier que l'ISBN est fourni
    if not isbn or not isbn.strip():
        st.info("👆 Enter an ISBN to search for a book")
        return
    
    # Récupérer le livre et vérifier qu'il existe
    df_book_x_isbn = get_one_book_by_ISBN(df, isbn)
    
    if df_book_x_isbn is None or df_book_x_isbn.empty:
        st.warning(f"❌ Book with ISBN '{isbn}' not found")
        return
    
    # Display selected book
    # ==========================================   
    st.markdown("---")
    st.markdown("### 📖 Selected Book")
    df_book_placeholder = st.empty()
    #render_book_full(df_book)
    df_book_placeholder = render_book_full(df_book_x_isbn)
    
    # Display selected book and recommendations
    # ==========================================   
    recommendations = get_similar_books_content_based(isbn=isbn, df=df, tfidf_mx=mx)
    
    # Vérifier que recommendations est un DataFrame
    if recommendations is None or not isinstance(recommendations, pd.DataFrame):
        st.error("Unable to generate recommendations")
        return
    
    # No book cover stored in recommendations
    # So we need to associate each book in recommendations
    # With the book in dataset passed in session_state
    # Merge to get all columns back
    df_books_recommended = recommendations.merge(
        df,
        on='ISBN',
        how='left',
        suffixes=('_reco', '')  # When columnns in both dataframes, keep those in df
    )
    #st.dataframe(df_books_recommended)
    display_books(df_books_recommended)


# =====================================================================
# Recommend collaborative by content on readers with similar interests
# =====================================================================
def get_reco_collab_x_book_x_isbn(
    dataset: pd.DataFrame,
    df_uniques_books: pd.DataFrame,
    df_books: pd.DataFrame,
    books_svd: np.ndarray,
    readers_svd: np.ndarray,
    idf_x_score_matrix_readers: pd.DataFrame,
):
    # Reco collab
    """ 
    Get string input
    parse it to retrieve dataframe
    allow user to select idx
    retrieve one book
    get isbn
    compute recommendations with matrix tfdif_svd passed as an argument
    display best recommended books
    """
    
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
    
    # Vérifier que l'ISBN est fourni
    if not isbn or not isbn.strip():
        st.info("👆 Enter an ISBN to search for a book")
        return
    
    # Récupérer le livre et vérifier qu'il existe
    df_book_x_isbn = get_one_book_by_ISBN(df_uniques_books, isbn)
    
    if df_book_x_isbn is None or df_book_x_isbn.empty:
        st.warning(f"❌ Book with ISBN '{isbn}' not found")
        return
    
    # Display selected book
    # ==========================================   
    st.markdown("---")
    st.markdown("### 📖 Selected Book")
    df_book_placeholder = st.empty()
    #render_book_full(df_book)
    df_book_placeholder = render_book_full(df_book_x_isbn)
    
    # Display selected book and recommendations
    # ==========================================   
    df_top_n_books, df_best_candidates = get_similar_books_collaborative(
        df_book_x_title=df_book_x_isbn,
        dataset=dataset,
        df_uniques_books=df_uniques_books,
        df_books=df_books,
        books_svd=books_svd,
        readers_svd=readers_svd,
        idf_x_score_matrix_readers=idf_x_score_matrix_readers
        )
            
    # Si aucun livre ne passe le filtre
    if len(df_best_candidates) == 0:
        st.markdown("No book above quality filter")
        display_books(df_top_n_books)
    else:
        # Sinon afficher les meilleurs candidats livres
        display_books(df_best_candidates)
        
    return True