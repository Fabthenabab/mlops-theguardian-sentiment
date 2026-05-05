# tabs/block_search_popularity.py
import streamlit as st
import pandas as pd

def get_book_x_popularity(df: pd.DataFrame, limit: int):
    # Initialize filter_popularity if needed
    if 'filter_popularity' not in st.session_state:
        st.session_state.filter_popularity = 1  # Default value
    
    # Slider with increments of 1
    min_popularity = 0
    s_grouped = df.value_counts(['Book-Title', 'Book-Subtitle', 'Book-Author'])
    max_popularity = s_grouped.max()
    
    col0, col1, col2 = st.columns([2, 8, 6])
    with col0:
        st.markdown("**Popularity**")
    
    with col1:
        selected_popularity = st.slider(
            "popularity",
            min_value=min_popularity,
            max_value=max_popularity,
            value=st.session_state.filter_popularity,
            step=1,
            key="slider_popularity",
            label_visibility="collapsed"    # Label invisible
        )
    
    with col2:
        placeholder = st.empty()
    
    # Update session_state
    st.session_state.filter_popularity = selected_popularity
    
    # Preselect values
    # Keep col of interest
    l_col = ['Mean-Rating-X-Book', 'Rating-Count-X-Book', 'Book-Title', 'Book-Subtitle', 'Book-Author', 'ISBN', 'Publisher', 'Description', "Tags-Tokenized", "Image-URL-L"]
    
    df_selected = (
        df
        .loc[df['Rating-Count-X-Book'] >= selected_popularity, l_col]
        .drop_duplicates(subset=['Book-Title', 'Book-Subtitle', 'Book-Author'])
        .sort_values('Rating-Count-X-Book', ascending=False)  # Sort by popularity
    )
    
    sel_size = len(df_selected)
    df_selected = df_selected.head(limit)
    st.session_state.df_sel_popularity = df_selected

    st.session_state.selection_length = len(df_selected)
    plural = ""
    if sel_size > 1:
        plural = "s"
    placeholder.markdown(f"📚 **{sel_size} Book{plural} (reviews ≥ {selected_popularity}) ({limit} firsts)**")
    
