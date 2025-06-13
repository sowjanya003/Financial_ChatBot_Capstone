# Import necessary libraries
import streamlit as st
from pymongo import MongoClient
import os
from index import chat_page

# Database connection
uri = os.getenv("MONGO_URI")  # Fetch MongoDB URI from environment variables
client = MongoClient(uri)  # Create a MongoDB client instance
db = client['project']  # Connect to the 'project' database
collection = db['user']  # Access the 'user' collection in the database


# Login Page
def display_login():
    """
    Handles user login:
    1. Displays a login form for username and password input.
    2. Checks credentials against the MongoDB database.
    3. Updates session state on successful login.
    """
    st.title("Login") # login page title

    uname = st.text_input("Username") # Username input
    pwd = st.text_input("Password", type="password") # Password input with masking

    if st.button("Login"):
        user = collection.find_one({"username": uname})  
        if user and user.get("password") == pwd:  # Check if user exists and password matches
            st.success("Login successful!")
            st.session_state["user"] = uname
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("Invalid username or password") # Displaying error message if credentials are incorrect


# Signup Page
def display_signup():
    """
    Handles user signup:
    1. Displays a signup form for username, password, and password confirmation.
    2. Validates input to ensure passwords match and username is unique.
    3. Registers the new user in the MongoDB database and redirects to the login page.
    """
    st.title("Signup") # Signup page title

    uname = st.text_input("Choose a Username")  # Username input
    pwd = st.text_input("Choose a Password", type="password") # Password input
    conf_pwd = st.text_input("Confirm Password", type="password") # Password confirmation 

    if st.button("Signup"):
        if pwd != conf_pwd: # Check if passwords match
            st.error("Passwords do not match")
        elif collection.find_one({"username": uname}):   # Check if username already exists
            st.error("Username already exists")
        else:
            # Insert the new user into the database with an empty message history
            collection.insert_one({"username": uname, "password": pwd, "msgs": []}) 
            st.success("Signup successful! Redirecting to login page...")
            st.session_state["redirect_login"] = True
            st.rerun()

# Main logic
def main():
    """
    Controls app navigation and session state.
    """
    st.sidebar.title("Navigation")

    # Initialize session state variables if they don't already exist
    if "auth" not in st.session_state:
        st.session_state["auth"] = False

    if "redirect_login" in st.session_state and st.session_state["redirect_login"]:
        st.session_state["redirect_login"] = False
        display_login() # Redirect to login page
        return

    if st.session_state["auth"]: # If the user is authenticated
        # Display the logged-in user in the sidebar
        st.sidebar.write(f"Logged in as: {st.session_state['user']}")
        # Add a dropdown menu for model selection
        selected_model = st.sidebar.selectbox("Select Model", ("Groq","GPT-3.5", "GPT-4o"))  # Add model selection
        # Add a logout button 
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()
        # to clear chat history
        if st.sidebar.button("Clear History"):
            username = st.session_state["user"]
            # Clear the user's chat history in the database
            collection.update_one({"username": username}, {"$set": {"msgs": []}})
            st.session_state["history"] = []
            st.success("Chat history cleared!")

        # Load the chat page based on the selected model
        if selected_model == "Groq":
            chat_page("Groq")
        elif selected_model == "GPT-3.5":
            chat_page("Gpt-3.5")
        elif selected_model == "GPT-4o":
            chat_page("Gpt-4o")
        
    else:
        # If the user is not authenticated
        # A dropdown menu for page selection (login or signup)
        page = st.sidebar.selectbox("Choose a page", ["Login", "Signup"])

        if page == "Login":
            display_login()
        elif page == "Signup":
            display_signup()


if __name__ == "__main__":
    main()
