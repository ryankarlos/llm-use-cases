import streamlit as st
from botocore.exceptions import ClientError
from llm import Llm
from utils import extract_text_from_file
from streamlit_cognito_auth import CognitoAuthenticator
import os


def logout():
    authenticator.logout()


# --- Streamlit UI ---

st.set_page_config(page_title="Prometheus - Internal AI Assistant", layout="wide")

# Initialize session states
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_content" not in st.session_state:
    st.session_state.file_content = None
if "file_name" not in st.session_state:
    st.session_state.file_name = None
if "file_info" not in st.session_state:
    st.session_state.file_info = None
if "active_document" not in st.session_state:
    st.session_state.active_document = False

# Cognito auth

pool_id = os.environ["POOL_ID"]
app_client_id = os.environ["APP_CLIENT_ID"]
app_client_secret = os.environ["APP_CLIENT_SECRET"]

authenticator = CognitoAuthenticator(
    pool_id=pool_id, app_client_id=app_client_id, app_client_secret=app_client_secret
)

is_logged_in = authenticator.login()
if not is_logged_in:
    st.stop()


# Sidebar for file upload and settings
with st.sidebar:
    st.header(f"Logged in as {authenticator.get_username()}")
    st.button("Logout", "logout_btn", on_click=logout)
    st.title("📄 Document Analysis")

    uploaded_file = st.file_uploader(
        "Upload a document for Prometheus to analyze",
        type=["txt", "pdf", "docx", "csv", "xls", "xlsx"],
    )

    # Document processing section
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            process_btn = st.button("📥 Process Document", use_container_width=True)
        with col2:
            clear_btn = st.button("❌ Clear Document", use_container_width=True)

        if process_btn:
            with st.spinner("Processing document..."):
                extracted_text, file_info = extract_text_from_file(uploaded_file)

                # Store in session state
                st.session_state.file_content = extracted_text
                st.session_state.file_name = uploaded_file.name
                st.session_state.file_info = file_info
                st.session_state.active_document = True

                st.success(f"✅ {file_info['type']} processed successfully!")

        if clear_btn:
            st.session_state.file_content = None
            st.session_state.file_name = None
            st.session_state.file_info = None
            st.session_state.active_document = False
            st.success("Document cleared")
            st.rerun()

    # Document info section
    if st.session_state.active_document:
        st.subheader("Active Document")
        st.info(
            f"📄 **{st.session_state.file_name}**  \n"
            f"Type: {st.session_state.file_info['type']}  \n"
            f"Details: {st.session_state.file_info['details']}"
        )

        # Quick actions for document
        if st.button(
            "🔍 Ask Prometheus to analyze this document", use_container_width=True
        ):
            st.session_state.user_input = f"Please analyze the document '{st.session_state.file_name}' I've uploaded and provide a summary."
            st.rerun()

        # Document preview expander
        with st.expander("👁️ Document Preview"):
            preview_length = min(1000, len(st.session_state.file_content))
            st.text_area(
                "Content Preview",
                st.session_state.file_content[:preview_length]
                + (
                    "..." if len(st.session_state.file_content) > preview_length else ""
                ),
                height=300,
                disabled=True,
            )

    # Document-related suggestions
    if st.session_state.active_document:
        st.subheader("Document Question Suggestions")
        suggestion_cols = st.columns(1)

        # Generate suggestions based on file type
        file_type = st.session_state.file_info["type"]
        suggestions = []

        if "spreadsheet" in file_type.lower():
            suggestions = [
                "What are the main trends in this data?",
                "Summarize this spreadsheet",
                "What columns contain numerical data?",
                "What's the average value in column X?",
            ]
        elif (
            "pdf" in file_type.lower()
            or "word" in file_type.lower()
            or "text" in file_type.lower()
        ):
            suggestions = [
                "Summarize this document",
                "What are the key points?",
                "Extract all dates mentioned",
                "What actions are recommended?",
            ]

        # Display suggestion buttons
        for i, suggestion in enumerate(suggestions):
            if st.button(
                f"❓ {suggestion}", key=f"suggestion_{i}", use_container_width=True
            ):
                st.session_state.user_input = suggestion
                st.rerun()

    # Reset conversation button at bottom of sidebar
    st.divider()
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# Main chat area
st.title("Prometheus - Your Internal AI Assistant 🤖")

# Document status indicator if active
if st.session_state.active_document:
    st.info(f"🔗 Currently working with document: **{st.session_state.file_name}**")

# Display chat history
for msg in st.session_state.chat_history:
    role = msg["role"]
    content = msg["content"][0]["text"]

    # For user messages, check if it's a long document prompt and shorten display
    if (
        role == "user"
        and len(content) > 500
        and "I've uploaded a document named" in content
    ):
        # Extract just the question part
        if "Please analyze this document and address my specific question:" in content:
            display_parts = content.split(
                "Please analyze this document and address my specific question:"
            )
            if len(display_parts) > 1:
                # Show simplified version for document questions
                with st.chat_message(role):
                    st.markdown(
                        f"💬 Asked about document **{st.session_state.file_name}**:"
                    )
                    st.markdown(display_parts[1].strip())
            else:
                # Fallback to normal display with truncation
                with st.chat_message(role):
                    st.markdown(
                        f"💬 {content[:200]}... [Document content hidden] ...{content[-100:]}"
                    )
    else:
        # Normal message display
        with st.chat_message(role):
            st.markdown(content)

# Input box
user_input = st.chat_input("Ask Prometheus a question...")

# Check for input from session state (from suggestion buttons)
if "user_input" in st.session_state and st.session_state.user_input:
    user_input = st.session_state.user_input
    del st.session_state.user_input  # Clear after use

# Process user input
if user_input:
    # Format message based on whether there's an active document
    if st.session_state.active_document and any(
        keyword in user_input.lower()
        for keyword in [
            "document",
            "file",
            "uploaded",
            "spreadsheet",
            "data",
            "pdf",
            "word",
            "excel",
            "csv",
        ]
    ):
        # Format structured document query with content
        document_query = f"""I've uploaded a document named '{st.session_state.file_name}'

Content:
{st.session_state.file_content}

Please analyze this document and address my specific question: {user_input}"""

        # Add user message to history (full version for AI, simplified for UI)
        user_msg = {"role": "user", "content": [{"text": document_query}]}
        st.session_state.chat_history.append(user_msg)

        # Display user message (simplified version)
        with st.chat_message("user"):
            st.markdown(f"💬 Asked about document **{st.session_state.file_name}**:")
            st.markdown(user_input)
    else:
        # Regular user message without document context
        user_msg = {"role": "user", "content": [{"text": user_input}]}
        st.session_state.chat_history.append(user_msg)

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

    # Sanitize message history - MODIFIED TO ONLY INCLUDE LAST 5 MESSAGES
    full_history = [
        msg
        for msg in st.session_state.chat_history
        if msg.get("content") and msg["content"][0].get("text", "").strip() != ""
    ]

    # Get only the last 5 messages for context
    context_messages = full_history[-5:] if len(full_history) > 5 else full_history

    # Stream assistant response
    llm = Llm("eu-west-1")  # adjust your region

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        try:
            with st.spinner("Prometheus is thinking..."):
                stream = llm.stream_response(context_messages)  # Use limited context
                received_chunks = 0

                # Process the streaming response
                for event in stream["stream"]:
                    if "contentBlockDelta" in event:
                        delta = event["contentBlockDelta"]["delta"]["text"]

                        if delta:
                            full_response += delta
                            received_chunks += 1
                            response_placeholder.markdown(full_response + "▌")

                if received_chunks == 0:
                    response_placeholder.error("⚠️ The model didn't return any text.")
                else:
                    response_placeholder.markdown(full_response)

        except ClientError as e:
            response_placeholder.error(
                f"⚠️ Bedrock API error: {e.response['Error']['Message']}"
            )
        except Exception as e:
            response_placeholder.error(f"⚠️ Prometheus encountered an error: {e}")
            full_response = ""

    # Append assistant message only if non-empty
    if full_response.strip():
        assistant_msg = {"role": "assistant", "content": [{"text": full_response}]}
        st.session_state.chat_history.append(assistant_msg)

    # Add metrics display to show how many messages were used for context
    st.sidebar.metric(
        label="Messages in Current Context",
        value=len(context_messages),
        delta=None,
        delta_color="off",
    )
