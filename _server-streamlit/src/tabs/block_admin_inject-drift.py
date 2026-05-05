# tabs/block_reco_search_title.py
import streamlit as st
import pandas as pd
import numpy as np

from utils.books import get_one_book_by_ISBN, get_books_by_title_words, render_book_full, display_books
   
from pipeline.core.src.themes import get_similar_books_content_based
from pipeline.core.src.collab import get_similar_books_collaborative

# ============================================
# Select one book by click in list
# ============================================
def _capture_event(df: pd.DataFrame, cols: list):
    return st.dataframe(
        df.drop(columns=cols, axis=1),
        on_select="rerun",
        selection_mode="single-row",
        height=220,
        column_config={
            "Book-Title": "Title",
            "Book-Author": "Author",
            "Mean-Rating-X-Book": st.column_config.NumberColumn("Rating", format="⭐ %.2f"),
            "Rating-Count-X-Book": st.column_config.NumberColumn("Reviews", format="%d 📝")
        }
    )


# ============================================
# Recommend by content
# ============================================
def get_reco_x_content_x_book_x_title(df: pd.DataFrame, mx: np.ndarray):
    """ 
    Get string input
    parse it to retrieve dataframe
    allow user to select idx
    retrieve one book
    get isbn
    compute recommendations with matrix tfdif_svd passed as an argument
    display best recommended books
    """
    
    # Select Book by Title
    # ==========================================
    col0, col1 = st.columns([1, 5])
    with col0:
        st.markdown("Search title words")
    with col1:
        title_words = st.text_input(
            "Enter title words",
            label_visibility="collapsed"    # Label invisible
        )

    if not title_words or not title_words.strip():
        st.info("👆 Enter words to search for books")
        return

    df_books = get_books_by_title_words(df, title_words)
    # Keep col of interest
    l_cols_to_keep = ['Mean-Rating-X-Book', 'Rating-Count-X-Book', 'Book-Title', 'Book-Subtitle', 'Book-Author', 'ISBN', 'Publisher', 'Description', "Tags-Tokenized", "Tags-Tokenized-As-Text", "Image-URL-L"]
    df_books = df_books.loc[:, l_cols_to_keep]

    # Define a list of columns to drop before display in dataframe in page
    l_cols = ["Description", "Tags-Tokenized", "Tags-Tokenized-As-Text", "Image-URL-L"]
    event = _capture_event(df_books, l_cols)
    

    # Display selected book and recommendations
    # ==========================================   
    df_book_placeholder = st.empty()
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        df_book = df_books.iloc[[selected_idx]]
        
        st.markdown("---")
        st.markdown("### 📖 Selected Book")
        df_book_placeholder = render_book_full(df_book)
    
        isbn = df_book.get("ISBN").iloc[0]

        recommendations = get_similar_books_content_based(isbn=isbn, df=df, tfidf_mx=mx)
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
def get_reco_collab_x_book_x_title(
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
    
    # Select Book by Title
    # ==========================================
    col0, col1 = st.columns([1, 5])
    with col0:
        st.markdown("Search title words")
    with col1:
        title_words = st.text_input(
            "Enter title words",
            label_visibility="collapsed"    # Label invisible
        )

    if not title_words or not title_words.strip():
        st.info("👆 Enter words to search for books")
        return

    df_books_x_title = get_books_by_title_words(df_uniques_books, title_words)
    # Keep col of interest
    l_cols_to_keep = ['Mean-Rating-X-Book', 'Rating-Count-X-Book', 'Book-Title', 'Book-Subtitle', 'Book-Author', 'ISBN', 'Publisher', 'Description', "Tags-Tokenized", "Tags-Tokenized-As-Text", "Image-URL-L"]
    df_books_x_title = df_books_x_title.loc[:, l_cols_to_keep]

    # Define a list of columns to drop before display in dataframe in page
    l_cols = ["Description", "Tags-Tokenized", "Tags-Tokenized-As-Text", "Image-URL-L"]
    event = _capture_event(df_books_x_title, l_cols)
    
    # Display selected book and recommendations
    # ==========================================   
    df_book_placeholder = st.empty()
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        # Select one book to recommend similar books
        df_book_x_title = df_books_x_title.iloc[[selected_idx]]
        
        st.markdown("---")
        st.markdown("### 📖 Selected Book")
        df_book_placeholder = render_book_full(df_book_x_title)

        df_top_n_books, df_best_candidates = get_similar_books_collaborative(
            df_book_x_title=df_book_x_title,
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