# Import necessary libraries
import streamlit as st
from langchain_community.vectorstores import Pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from pinecone import Pinecone, ServerlessSpec
import os
from pymongo import MongoClient
from groq import Groq
from dotenv import load_dotenv

# Load API key for Groq from environment variables and initialize the groq client
GROQ_API_KEY = os.environ.get('GROQ_AP_KEY')
groq_client = Groq(api_key=GROQ_API_KEY)

# Load environment variables
load_dotenv()

# Database connection
uri = os.getenv("MONGO_URI")  # Fetch MongoDB URI from environment variables
client = MongoClient(uri)  # Create a MongoDB client instance
db = client['project']  # Connect to the 'project' database
collection = db['user']  # Access the 'user' collection in the database


# Pinecone setup
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY")) # Initialize Pinecone client with API key
index_name = "capstone" # Name of the Pinecone index
index = pc.Index(index_name) # Get the index object

# OpenAI embeddings object for text embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Create a Pinecone Vector Store
vector_store = PineconeVectorStore(index=index, embedding=embeddings)

# Function to handle inference using GPT models
def inference_with_gpt(history,relevant_docs,query,model_name):
    combined_input = f"""
    You are an AI designed to answer questions strictly and exclusively based on the provided context and conversation history.
 
    Do not use external knowledge or assumptions to answer questions.
    Do not perform mathematical calculations or estimations under any circumstances.
    Do not provide generic answers or information that is not explicitly supported by the provided documents.
    If no context or relevant documents are available, respond with: "No relevant information found."
 
 
    ### Conversation History:
    {history if history else "No prior conversation history available."}
 
    ### Relevant Documents:
    {relevant_docs if relevant_docs else "No relevant documents found."}
 
    ### User Query:
    {query}
 
   Guidelines for Answer:
    Provide the Final Answer concisely and only if it is explicitly supported by the context or relevant documents.
    Avoid step-by-step reasoning, generic statements, or assumptions. Respond only to what is explicitly addressed in the provided documents.
    If the query requires calculations or mathematical operations, respond with: "Mathematical operations are not allowed."
    If no relevant information exists in the documents or conversation history, respond with: "No relevant information found."
    Include an Explanation that highlights how the answer was derived exclusively from the relevant documents or context, or why no information was found.
    """

    
    from langchain_openai import ChatOpenAI
    if model_name == "Gpt-3.5":
        model = ChatOpenAI(model="gpt-3.5-turbo")
        result = model.predict(combined_input)
        return result

    elif model_name == "Gpt-4o":
        model = ChatOpenAI(model="gpt-4o")
        result = model.predict(combined_input)
        return result
    
# Function to handle inference using Groq model
def inference_with_groq(history,relevant_docs,query):
    full_context = f"""
    You are an AI designed to answer questions strictly and exclusively based on the provided context and conversation history.
 
    Do not use external knowledge or assumptions to answer questions.
    Do not perform mathematical calculations or estimations under any circumstances.
    Do not provide generic answers or information that is not explicitly supported by the provided documents.
    If no context or relevant documents are available, respond with: "No relevant information found."
 
 
    ### Conversation History:
    {history if history else "No prior conversation history available."}
 
    ### Relevant Documents:
    {relevant_docs if relevant_docs else "No relevant documents found."}
 
    ### User Query:
    {query}
 
   Guidelines for Answer:
    Provide the Final Answer concisely and only if it is explicitly supported by the context or relevant documents.
    Avoid step-by-step reasoning, generic statements, or assumptions. Respond only to what is explicitly addressed in the provided documents.
    If the query requires calculations or mathematical operations, respond with: "Mathematical operations are not allowed."
    If no relevant information exists in the documents or conversation history, respond with: "No relevant information found."
    Include an Explanation that highlights how the answer was derived exclusively from the relevant documents or context, or why no information was found.
    """

    # Call the Groq API to generate a response
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": full_context,
            }
        ],
        model="llama-3.3-70b-versatile",
        stream=False,
    )
    return chat_completion.choices[0].message.content

# Function to handle the chat page
def chat_page(model_name: str):
    st.title("Financial ChatBot")

    # Initialize or retrieve user chat history
    if "user" in st.session_state:
        username = st.session_state["user"] # logged-in user's name
        user_data = collection.find_one({"username": username})
        if user_data:
            st.session_state["history"] = user_data.get("msgs", []) # Load history from database
        else:
            st.session_state["history"] = []  # Initializing history if not found

    # user queries
    query = st.text_input("Enter your Query", key="query_input")
    ask_button = st.button("Ask")
    if ask_button:
        if query:
            # Retrieve relevant documents from Pinecone vector store
            retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
            relevant_docs = retriever.invoke(query)

            # Combine conversation history and relevant documents into text format
            history_as_text = "\n\n".join(
                [f"User: {hist['query']}\nAI: {hist['response']}" for hist in st.session_state["history"]]
            )
            relevant_docs_text = "\n\n".join([doc.page_content for doc in relevant_docs])
            
            # Generate a response using the selected model
            if model_name == "Groq":
                result = inference_with_groq(history_as_text, relevant_docs_text, query)
            elif model_name == "Gpt-3.5":
                result = inference_with_gpt(history_as_text, relevant_docs_text, query,model_name)
            elif model_name == "Gpt-4o":
                result = inference_with_gpt(history_as_text,relevant_docs_text,query,model_name)
            
            # Display the answer
            st.write("**Answer:**")
            st.write(result)

            # Save the query and response in session history
            st.session_state["history"].insert(0, {"query": query, "response": result}) 
            if "user" in st.session_state:
                collection.update_one(
                    {"username": username},
                    {"$set": {"msgs": st.session_state["history"]}}
                )
        else:
            st.warning("Please enter a query before clicking 'Ask'.")
    
    # Display chat history
    st.subheader("Chat History")
    if st.session_state["history"]:
        for entry in st.session_state["history"]:
            st.markdown(f"**Query:** {entry['query']}")
            st.markdown(f"**Response:** {entry['response']}")
            st.markdown("---")
    else:
        st.write("No chat history available.")


if __name__ == "__main__":
    chat_page()

  
    
