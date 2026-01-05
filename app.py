import streamlit as st
from datetime import datetime
import google.generativeai as genai
from pymongo import MongoClient

# ----------------------------------
# PAGE CONFIG
# ----------------------------------
st.set_page_config(
    page_title="AI Study Buddy",
    page_icon="🤖",
    layout="wide"
)

# ----------------------------------
# GEMINI CONFIG
# ----------------------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")

# ----------------------------------
# MONGODB CONFIG
# ----------------------------------
client = MongoClient(st.secrets["MONGO_URI"])
db = client["ai_study_buddy"]
chats_collection = db["chats"]
users_collection = db["users"]

# ----------------------------------
# SESSION STATE
# ----------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# ----------------------------------
# LOGIN FUNCTIONS
# ----------------------------------
def signup_user(email, password):
    if users_collection.find_one({"email": email}):
        return False
    users_collection.insert_one({
        "email": email,
        "password": password
    })
    return True

def login_user(email, password):
    return users_collection.find_one({
        "email": email,
        "password": password
    })

# ----------------------------------
# LOGIN / SIGNUP UI
# ----------------------------------
if not st.session_state.logged_in:
    st.title("🔐 Login – AI Study Buddy")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            user = login_user(email, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.success("Login successful ✅")
                st.rerun()
            else:
                st.error("Invalid email or password ❌")

    with tab2:
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_pass")

        if st.button("Sign Up"):
            if signup_user(new_email, new_password):
                st.success("Account created! Please login.")
            else:
                st.error("User already exists")

    st.stop()

# ----------------------------------
# SIDEBAR – CHAT HISTORY
# ----------------------------------
with st.sidebar:
    st.markdown("## 💬 Chat History")

    if st.button("➕ New Chat"):
        chat_id = datetime.now().strftime("%Y%m%d%H%M%S")
        chats_collection.insert_one({
            "_id": chat_id,
            "title": "New Chat",
            "user": st.session_state.user_email,
            "messages": [],
            "created_at": datetime.now()
        })
        st.session_state.current_chat_id = chat_id

    st.markdown("---")

    for chat in chats_collection.find(
        {"user": st.session_state.user_email}
    ).sort("created_at", -1):
        if st.button(chat["title"], key=chat["_id"]):
            st.session_state.current_chat_id = chat["_id"]

    st.markdown("---")
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.user_email = None
        st.session_state.current_chat_id = None
        st.rerun()

# ----------------------------------
# MAIN UI
# ----------------------------------
st.title("🤖 AI Study Buddy – Study Sphere")
st.write(f"Welcome **{st.session_state.user_email}** 👋")

topic = st.text_input("Enter a topic or paste text")

option = st.selectbox(
    "Choose what you want",
    ["Explain", "Summarize", "Quiz", "Flashcards"]
)

# ----------------------------------
# GENERATE BUTTON
# ----------------------------------
if st.button("Generate"):
    if not topic.strip():
        st.warning("Please enter a topic")
    else:
        if st.session_state.current_chat_id is None:
            chat_id = datetime.now().strftime("%Y%m%d%H%M%S")
            chats_collection.insert_one({
                "_id": chat_id,
                "title": topic.title(),
                "user": st.session_state.user_email,
                "messages": [],
                "created_at": datetime.now()
            })
            st.session_state.current_chat_id = chat_id
        else:
            chat_id = st.session_state.current_chat_id

        chat = chats_collection.find_one({"_id": chat_id})
        if chat["title"] == "New Chat":
            chats_collection.update_one(
                {"_id": chat_id},
                {"$set": {"title": topic.title()}}
            )

        chats_collection.update_one(
            {"_id": chat_id},
            {"$push": {"messages": {"role": "user", "content": topic}}}
        )

        with st.spinner("Generating answer..."):
            try:
                prompt = f"{option} the following topic in simple terms:\n\n{topic}"
                response = model.generate_content(prompt)
                ai_response = response.text
            except Exception as e:
                ai_response = f"⚠️ Error: {e}"

        chats_collection.update_one(
            {"_id": chat_id},
            {"$push": {"messages": {"role": "assistant", "content": ai_response}}}
        )

        st.success("Response generated!")

# ----------------------------------
# SHOW CONVERSATION
# ----------------------------------
if st.session_state.current_chat_id:
    st.markdown("### 📜 Conversation")

    chat = chats_collection.find_one(
        {"_id": st.session_state.current_chat_id}
    )

    if chat:
        for msg in chat["messages"]:
            if msg["role"] == "user":
                st.markdown(f"🧑‍🎓 **You:** {msg['content']}")
            else:
                st.markdown(f"🤖 **AI:** {msg['content']}")
