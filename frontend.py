import json
import streamlit as st
import requests
import io
from pypdf import PdfReader

st.set_page_config(
    page_title="DocuMind",
    page_icon="D",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000"


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state['token']}"}


def end_session(message):
    st.session_state.clear()
    st.session_state["auth_message"] = message
    st.rerun()


def authed_request(method, url, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update(auth_headers())
    response = requests.request(method, url, headers=headers, **kwargs)
    if response.status_code == 401:
        end_session("Your session expired. Please log in again.")
    return response


def authed_get(url, **kwargs):
    return authed_request("GET", url, **kwargs)


def authed_post(url, **kwargs):
    return authed_request("POST", url, **kwargs)


def authed_delete(url, **kwargs):
    return authed_request("DELETE", url, **kwargs)


def submit_credentials(action, username, password):
    try:
        response = requests.post(
            f"{API_URL}/{action}",
            json={"username": username, "password": password},
            timeout=30
        )
    except requests.exceptions.RequestException as error:
        st.error(f"Could not connect to DocuMind API: {error}")
        return

    if response.status_code == 200:
        st.session_state["token"] = response.json()["token"]
        st.rerun()
    elif response.status_code == 422:
        st.error(
            "Username must be 3-50 characters and "
            "password 8-128 characters."
        )
    else:
        st.error(response.json().get("detail", "Request failed."))


def show_login_screen():
    st.title("DocuMind")
    st.subheader("AI-Powered Document Intelligence")

    message = st.session_state.pop("auth_message", None)
    if message:
        st.warning(message)

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input(
                "Password", type="password", key="login_password"
            )
            submitted = st.form_submit_button("Log in")
        if submitted:
            submit_credentials("login", username, password)

    with register_tab:
        with st.form("register_form"):
            username = st.text_input(
                "Username (3-50 characters)", key="register_username"
            )
            password = st.text_input(
                "Password (8-128 characters)",
                type="password",
                key="register_password"
            )
            submitted = st.form_submit_button("Create account")
        if submitted:
            submit_credentials("register", username, password)


if "token" not in st.session_state:
    show_login_screen()
    st.stop()

if "username" not in st.session_state:
    try:
        me_response = requests.get(
            f"{API_URL}/me", headers=auth_headers(), timeout=30
        )
    except requests.exceptions.RequestException as error:
        st.error(f"Could not connect to DocuMind API: {error}")
        st.stop()
    if me_response.status_code != 200:
        end_session("Your session expired. Please log in again.")
    st.session_state["username"] = me_response.json()["username"]

with st.sidebar:
    st.write(f"Logged in as **{st.session_state['username']}**")
    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()



def build_docx(result):
    from docx import Document

    doc = Document()
    doc.add_heading("DocuMind Analysis Report", level=0)
    doc.add_paragraph(f"Document Type: {result['document_type']}")

    doc.add_heading("Summary", level=1)
    doc.add_paragraph(result["summary"])

    sections = [
        ("Key Information", "key_information"),
        ("Important Dates", "important_dates"),
        ("Amounts", "amounts"),
        ("Missing Information", "missing_information"),
        ("Inconsistencies", "inconsistencies"),
    ]
    for title, field in sections:
        doc.add_heading(title, level=1)
        items = result[field]
        if items:
            for item in items:
                doc.add_paragraph(item, style="List Bullet")
        else:
            doc.add_paragraph("None found.")

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def build_pdf(result):
    from fpdf import FPDF

    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2022": "-", "\u2026": "...",
    }

    def clean(text):
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    def write(text, size=11, bold=False):
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.multi_cell(0, 7, clean(text), new_x="LMARGIN", new_y="NEXT")

    write("DocuMind Analysis Report", 18, True)
    pdf.ln(3)
    write(f"Document Type: {result['document_type']}")
    pdf.ln(3)

    write("Summary", 14, True)
    write(result["summary"])
    pdf.ln(3)

    sections = [
        ("Key Information", "key_information"),
        ("Important Dates", "important_dates"),
        ("Amounts", "amounts"),
        ("Missing Information", "missing_information"),
        ("Inconsistencies", "inconsistencies"),
    ]
    for title, field in sections:
        write(title, 14, True)
        items = result[field]
        if items:
            for item in items:
                write("- " + item)
        else:
            write("None found.")
        pdf.ln(3)

    return bytes(pdf.output())

def display_analysis(result, key_prefix="new"):
    st.header("Analysis Results")
    st.download_button(
        "Download JSON",
        data=json.dumps(result, indent=2),
        file_name="documind_analysis.json",
        mime="application/json",
        key=f"download_json_{key_prefix}",
        on_click="ignore"
    )
    st.download_button(
        "Download DOCX",
        data=build_docx(result),
        file_name="documind_analysis.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key=f"download_docx_{key_prefix}",
        on_click="ignore"
    )
    st.download_button(
        "Download PDF",
        data=build_pdf(result),
        file_name="documind_analysis.pdf",
        mime="application/pdf",
        key=f"download_pdf_{key_prefix}",
        on_click="ignore"
    )

    st.subheader("Document Overview")
    st.write("Document Type:", result["document_type"])

    st.subheader("Summary")
    st.write(result["summary"])

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Key Information")
        for item in result["key_information"]:
            st.write("- " + item)

        st.subheader("Important Dates")
        for item in result["important_dates"]:
            st.write("- " + item)

        st.subheader("Amounts")
        for item in result["amounts"]:
            st.write("- " + item)

    with col2:
        st.subheader("Missing Information")
        for item in result["missing_information"]:
            st.write("- " + item)

        st.subheader("Inconsistencies")
        for item in result["inconsistencies"]:
            st.write("- " + item)


st.title("DocuMind")
st.subheader("AI-Powered Document Intelligence")

st.write(
    "Upload your documents and let AI extract important "
    "information, summarize content, and identify inconsistencies."
)

st.divider()

st.header("Upload Document")

uploaded_file = st.file_uploader(
    "Choose a document",
    type=["pdf", "docx", "txt"],
    max_upload_size=10
)

if uploaded_file:
    st.success(f"Selected: {uploaded_file.name}")

    with st.expander("Document Information and Preview", expanded=True):
        file_bytes = uploaded_file.getvalue()
        extension = uploaded_file.name.lower().rsplit(".", 1)[-1]

        st.write(f"**Filename:** {uploaded_file.name}")
        st.write(f"**Size:** {len(file_bytes) / 1024:.1f} KB")

        if extension == "pdf":
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                st.write(f"**Pages:** {len(reader.pages)}")
            except Exception:
                st.warning("Could not read PDF details.")
            try:
                st.pdf(file_bytes, height=500)
            except Exception:
                st.info("Visual PDF preview is not available.")
        elif extension == "txt":
            text = file_bytes.decode("utf-8", errors="replace")
            st.write(f"**Characters:** {len(text)}")
            st.text(text[:1000])
        else:
            st.write("Preview is not available for DOCX files.")


    if st.button("Analyze Document", type="primary"):

        with st.spinner("Analyzing your document with AI..."):

            try:
                response = authed_post(
                    f"{API_URL}/analyze",
                    files={
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type
                        )
                    },
                    timeout=180
                )

                if response.status_code == 200:
                    st.success("Analysis completed!")
                    display_analysis(response.json())
                else:
                    st.error(response.json().get(
                        "detail", "Analysis failed."
                    ))

            except requests.exceptions.RequestException as error:
                st.error(f"Could not connect to DocuMind API: {error}")


from datetime import datetime

st.divider()
st.header("Analysis History")


def load_history():
    try:
        response = authed_get(f"{API_URL}/history", timeout=30)
        if response.status_code == 200:
            return response.json()
        st.error("Could not load analysis history.")
    except requests.exceptions.RequestException as error:
        st.error(f"Could not connect to DocuMind API: {error}")
    return []


def delete_record(record_id):
    try:
        response = authed_delete(
            f"{API_URL}/history/{record_id}", timeout=30
        )
        if response.status_code == 200:
            return True
        st.error(response.json().get(
            "detail", "Could not delete analysis."
        ))
    except requests.exceptions.RequestException as error:
        st.error(f"Could not connect to DocuMind API: {error}")
    return False


def format_timestamp(value):
    return value[:19].replace("T", " ") + " UTC"


def record_date(record):
    return datetime.fromisoformat(record["created_at"]).date()


history = load_history()

if not history:
    st.info("No saved analyses yet. Analyze a document to see it here.")
else:
    doc_types = sorted({r["analysis"]["document_type"] for r in history})

    col_search, col_type, col_sort = st.columns([2, 2, 1])
    search_query = col_search.text_input("Search by filename")
    type_filter = col_type.selectbox("Document type", ["All types"] + doc_types)
    sort_order = col_sort.selectbox("Sort by", ["Newest first", "Oldest first"])

    date_range = None
    if st.checkbox("Filter by date"):
        all_dates = [record_date(r) for r in history]
        picked = st.date_input(
            "Date range", value=(min(all_dates), max(all_dates))
        )
        if isinstance(picked, tuple) and len(picked) == 2:
            date_range = picked

    filtered_history = []
    for r in history:
        if search_query.strip().lower() not in r["filename"].lower():
            continue
        if type_filter != "All types" and r["analysis"]["document_type"] != type_filter:
            continue
        if date_range and not (date_range[0] <= record_date(r) <= date_range[1]):
            continue
        filtered_history.append(r)

    if sort_order == "Oldest first":
        filtered_history.reverse()

    st.caption(f"Showing {len(filtered_history)} of {len(history)} analyses")

    if not filtered_history:
        st.info("No analyses match your filters.")

    for record in filtered_history:
        col_name, col_time, col_view, col_delete = st.columns([3, 2, 1, 1])

        col_name.write(record["filename"])
        col_time.write(format_timestamp(record["created_at"]))

        if col_view.button("View", key=f"view_{record['id']}"):
            st.session_state["selected_id"] = record["id"]
            st.session_state.pop("confirm_delete_id", None)

        if col_delete.button("Delete", key=f"delete_{record['id']}"):
            st.session_state["confirm_delete_id"] = record["id"]

    confirm_id = st.session_state.get("confirm_delete_id")
    confirm_record = next(
        (r for r in history if r["id"] == confirm_id), None
    )

    if confirm_record:
        st.warning(
            f"Delete '{confirm_record['filename']}' from "
            f"{format_timestamp(confirm_record['created_at'])}? "
            "This cannot be undone."
        )
        col_yes, col_no, _ = st.columns([1, 1, 4])

        if col_yes.button("Yes, delete", type="primary", key="confirm_yes"):
            if delete_record(confirm_id):
                if st.session_state.get("selected_id") == confirm_id:
                    st.session_state.pop("selected_id", None)
                st.session_state.pop("confirm_delete_id", None)
                st.rerun()

        if col_no.button("Cancel", key="confirm_no"):
            st.session_state.pop("confirm_delete_id", None)
            st.rerun()

    selected_id = st.session_state.get("selected_id")

    if selected_id is not None:
        selected = next(
            (r for r in history if r["id"] == selected_id), None
        )

        if selected:
            st.divider()
            st.subheader(f"Viewing: {selected['filename']}")
            display_analysis(selected["analysis"], key_prefix=f"history_{selected['id']}")

            st.divider()
            st.subheader("Chat with this document")

            chat_key = f"chat_{selected['id']}"
            if chat_key not in st.session_state:
                st.session_state[chat_key] = []

            for message in st.session_state[chat_key]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

            question = st.chat_input(
                "Ask a question about this document",
                key=f"chat_input_{selected['id']}"
            )

            if question:
                st.session_state[chat_key].append(
                    {"role": "user", "content": question}
                )
                with st.chat_message("user"):
                    st.write(question)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            chat_response = authed_post(
                                f"{API_URL}/chat",
                                json={
                                    "analysis_id": selected["id"],
                                    "question": question
                                },
                                timeout=90
                            )
                            if chat_response.status_code == 200:
                                answer = chat_response.json()["answer"]
                            else:
                                answer = chat_response.json().get(
                                    "detail", "Could not answer the question."
                                )
                        except requests.exceptions.RequestException as error:
                            answer = f"Could not connect to DocuMind API: {error}"
                    st.write(answer)

                st.session_state[chat_key].append(
                    {"role": "assistant", "content": answer}
                )


st.divider()
st.header("Compare Documents")
st.write("Upload two documents to find differences and conflicting details.")

col_a, col_b = st.columns(2)
file_a = col_a.file_uploader(
    "Document A", type=["pdf", "docx", "txt"], key="compare_a"
)
file_b = col_b.file_uploader(
    "Document B", type=["pdf", "docx", "txt"], key="compare_b"
)

if file_a and file_b:
    if st.button("Compare Documents", type="primary"):
        with st.spinner("Comparing your documents with AI..."):
            try:
                compare_response = authed_post(
                    f"{API_URL}/compare",
                    files={
                        "file_a": (file_a.name, file_a.getvalue(), file_a.type),
                        "file_b": (file_b.name, file_b.getvalue(), file_b.type),
                    },
                    timeout=180
                )

                if compare_response.status_code == 200:
                    comparison = compare_response.json()

                    st.success("Comparison completed!")
                    st.subheader("Summary")
                    st.write(comparison["summary"])

                    col_sim, col_diff = st.columns(2)

                    with col_sim:
                        st.subheader("Similarities")
                        for item in comparison["similarities"]:
                            st.write("- " + item)

                    with col_diff:
                        st.subheader("Differences")
                        for item in comparison["differences"]:
                            st.write("- " + item)

                    conflicts = [
                        ("Conflicting Dates", "conflicting_dates"),
                        ("Conflicting Amounts", "conflicting_amounts"),
                        ("Other Conflicting Information", "conflicting_information"),
                    ]
                    for title, field in conflicts:
                        if comparison[field]:
                            st.subheader(title)
                            for item in comparison[field]:
                                st.warning(item)
                else:
                    st.error(compare_response.json().get(
                        "detail", "Comparison failed."
                    ))

            except requests.exceptions.RequestException as error:
                st.error(f"Could not connect to DocuMind API: {error}")
elif file_a or file_b:
    st.info("Upload both documents to compare them.")
