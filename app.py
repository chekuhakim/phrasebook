import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
import random
import emoji
from google.auth.exceptions import RefreshError
import os

# Firebase initialization
if not firebase_admin._apps:
    try:
        # Use os.path.join for better cross-platform compatibility
        cred_path = os.path.join(os.path.dirname(__file__), "firebase-credentials.json")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        st.success("Firebase initialized successfully")
    except Exception as e:
        st.error(f"Firebase initialization error: {str(e)}")
        st.stop()

db = firestore.client()

# Simple emoji generation function
def generate_emojis(text, num_emojis=3):
    all_emojis = list(emoji.EMOJI_DATA.keys())
    return ''.join(random.choices(all_emojis, k=num_emojis))

# Function to generate category emoji
def generate_category_emoji(category):
    return generate_emojis(category, num_emojis=1)

# Authentication functions
def send_login_link(email):
    try:
        action_code_settings = auth.ActionCodeSettings(
            url='https://your-app-name.streamlit.app',  # Update this URL
            handle_code_in_app=True,
            ios_bundle_id='com.example.ios',
            android_package_name='com.example.android',
            android_install_app=True,
            android_minimum_version='12'
        )
        link = auth.generate_sign_in_with_email_link(email, action_code_settings)
        st.success(f"Login link (in a real app, this would be emailed): {link}")
        return link
    except RefreshError as e:
        st.error(f"Authentication error (RefreshError): {str(e)}")
        st.error(f"Error details: {e.args}")
    except auth.AuthError as e:
        st.error(f"Firebase Auth error: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        st.error(f"Error type: {type(e).__name__}")
    return None

def verify_login(link):
    try:
        signin_info = auth.get_sign_in_with_email_link_info(link)
        if signin_info:
            custom_token = auth.create_custom_token(signin_info.user_id)
            return custom_token
    except:
        return None

# Streamlit app
st.title("Emoji Phrasebook")

# Authentication
if 'user_id' not in st.session_state:
    st.header("Login")
    email = st.text_input("Enter your email")
    if st.button("Send Login Link"):
        link = send_login_link(email)
        if link:
            st.session_state.login_link = link
    
    login_link = st.text_input("Enter the login link you received")
    if st.button("Verify Login"):
        custom_token = verify_login(login_link)
        if custom_token:
            st.session_state.user_id = custom_token
            st.success("Login successful!")
            st.experimental_rerun()
        else:
            st.error("Invalid login link")
else:
    st.write(f"Logged in as: {st.session_state.user_id}")
    if st.button("Logout"):
        del st.session_state.user_id
        st.experimental_rerun()

    # Add new category
    new_category = st.text_input("Add new category")
    if st.button("Add Category"):
        if new_category:
            emoji = generate_category_emoji(new_category)
            db.collection('users').document(st.session_state.user_id).collection('categories').add({
                'name': new_category,
                'emoji': emoji
            })
            st.success(f"Category '{new_category}' added with emoji {emoji}")

    # Display categories and phrases
    categories = db.collection('users').document(st.session_state.user_id).collection('categories').stream()

    for category in categories:
        cat_data = category.to_dict()
        with st.expander(f"{cat_data['emoji']} {cat_data['name']}"):
            new_phrase = st.text_input(f"Add new phrase to {cat_data['name']}", key=f"new_phrase_{category.id}")
            if st.button("Add Phrase", key=f"add_phrase_{category.id}"):
                if new_phrase:
                    db.collection('users').document(st.session_state.user_id).collection('categories').document(category.id).collection('phrases').add({
                        'text': new_phrase
                    })
                    st.success(f"Phrase added to {cat_data['name']}")
            
            phrases = db.collection('users').document(st.session_state.user_id).collection('categories').document(category.id).collection('phrases').stream()
            for phrase in phrases:
                st.write(phrase.to_dict()['text'])

    # Emoji generation demo
    st.header("Emoji Generation Demo")
    demo_text = st.text_input("Enter text to generate emojis")
    if st.button("Generate Emojis"):
        if demo_text:
            emojis = generate_emojis(demo_text, num_emojis=5)
            st.write(f"Generated emojis: {emojis}")
