import streamlit as st
import pandas as pd

def body():
    # ************************************************************************************************************
    # ========================================
    # CACHE SETUP
    # ========================================
    from utils.cache import get_cached_dataset, get_cached_vocab
    dataset = get_cached_dataset()

    # CACHE FOR LOGIN MODULE
    if 'user_id' not in st.session_state:
        user_id = "Guest user"
        st.session_state.user_id = user_id
    else:   # set var from session_state
        user_id = st.session_state.user_id


    st.subheader("**Login**")
    user_ids = ["Guest user"] + list(dataset["User-ID"].unique())

    st.selectbox(
        "Choose a user:", 
        options=user_ids,
        key="temp_user",
        index=user_ids.index(st.session_state.user_id),
        on_change=lambda: setattr(st.session_state, 'user_id', st.session_state.temp_user)
    )
    
    st.write(f"### Welcome, **{st.session_state.user_id}**!")
    
    
