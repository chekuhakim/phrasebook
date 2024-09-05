import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
from transformers import BartTokenizer, BartForConditionalGeneration

# Firebase initialization
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Load the BART model (use st.cache_resource to load it only once)
@st.cache_resource
def load_model():
    path = "KomeijiForce/bart-large-emojilm"
    tokenizer = BartTokenizer.from_pretrained(path)
    generator = BartForConditionalGeneration.from_pretrained(path)
    return tokenizer, generator

tokenizer, generator = load_model()

# Emoji translation function
def translate(sentence, **argv):
    inputs = tokenizer(sentence, return_tensors="pt")
    generated_ids = generator.generate(inputs["input_ids"], **argv)
    decoded = tokenizer.decode(generated_ids[0], skip_special_tokens=True).replace(" ", "")
    return decoded

# Function to generate category emoji
def generate_category_emoji(category):
    return translate(category, num_beams=4, do_sample=True, max_length=10)[:2]

# Authentication functions
def send_login_link(email):
    try:
        action_code_settings = auth.ActionCodeSettings(
            url='https://your-app-url.com',
            handle_code_in_app=True,
            ios_bundle_id='com.example.ios',
            android_package_name='com.example.android',
            android_install_app=True,
            android_minimum_version='12'
        )
        link = auth.generate_sign_in_with_email_link(email, action_code_settings)
        # In a real app, you'd send this link via email. For demo, we'll just display it.
        st.success(f"Login link (in a real app, this would be emailed): {link}")
        return link
    except firebase_admin._auth_utils.ConfigurationNotFoundError:
        st.error("Firebase authentication is not properly configured. Please check your Firebase project settings.")
        return None
    except Exception as e:
        st.error(f"An error occurred while generating the login link: {str(e)}")
        return None

def verify_login(link):
    try:
        signin_info = auth.get_sign_in_with_email_link_info(link)
        if signin_info:
            # Create a custom token
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
            emojis = translate(demo_text, num_beams=4, do_sample=True, max_length=100)
            st.write(f"Generated emojis: {emojis}")
