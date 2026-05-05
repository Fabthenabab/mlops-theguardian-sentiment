# tabs/block_search_rating.py
import streamlit as st
import pandas as pd

#@st.fragment
def get_book_x_rating(df: pd.DataFrame, limit: int):
    # Initialize selection_length if needed
    if 'selection_length' not in st.session_state:
        st.session_state.selection_length = len(df.drop_duplicates(subset=['Book-Title', 'Book-Subtitle', 'Book-Author']))  # Default value
    # Initialize filter_rating if needed
    if 'filter_rating' not in st.session_state:
        st.session_state.filter_rating = 4.0  # Default value
    
    # Slider with increments of 0.1
    min_rating = float(df["Mean-Rating-X-Book"].min())
    max_rating = float(df["Mean-Rating-X-Book"].max())

    col0, col1, col2 = st.columns([2, 8, 6])
    with col0:
        st.markdown("**Rating**")
    
    with col1:
        selected_rating = st.slider(
            label="rating",
            min_value=min_rating,
            max_value=max_rating,
            value=st.session_state.filter_rating,
            step=0.1,
            format="%.1f",
            key="slider_rating",
            label_visibility="collapsed"    # Label invisible
            )
    
    with col2:
        placeholder = st.empty()
 
    # Update session_state
    st.session_state.filter_rating = selected_rating
    
    # Preselect values
    # Keep col of interest
    l_col = ['Mean-Rating-X-Book', 'Rating-Count-X-Book', 'Book-Title', 'Book-Subtitle', 'Book-Author', 'ISBN', 'Publisher', 'Description', "Tags-Tokenized", "Image-URL-L"]
    
    df_selected = (
        df[l_col] # Get a copy of interesting columns
        .query(f'`Mean-Rating-X-Book` >= {selected_rating}')  # Filter with selected rating
        .drop_duplicates(subset=['Book-Title', 'Book-Subtitle', 'Book-Author'])
        .sort_values(by='Mean-Rating-X-Book', ascending=False)
    )
    sel_size = len(df_selected)
    df_selected = df_selected.head(limit)
    st.session_state.df_sel_rating = df_selected

    st.session_state.selection_length = len(df_selected)
    plural = ""
    if sel_size > 1:
        plural = "s"
    placeholder.markdown(f"📚 **{sel_size} Book{plural} (rating ≥ {selected_rating}) ({limit} firsts)**")
    



    