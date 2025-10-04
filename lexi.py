import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import re

st.set_page_config(layout="centered", page_title="LexiRedact")

if 'page' not in st.session_state:
    st.session_state.page = 'upload'
if 'uploaded_file_bytes' not in st.session_state:
    st.session_state.uploaded_file_bytes = None
if 'file_name' not in st.session_state:
    st.session_state.file_name = None
if 'redacted_file_bytes' not in st.session_state:
    st.session_state.redacted_file_bytes = None


def convert_pdf_to_images(pdf_bytes):
    """Converts a PDF file in bytes into a list of PIL Images."""
    images = []
    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            images.append(image)
        pdf_document.close()
    except Exception as e:
        st.error(f"Failed to load and render PDF: {e}")
    return images

def redact_pdf(pdf_bytes, redaction_options):
    """Applies redactions to a PDF based on selected options and returns the redacted PDF bytes."""
    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        aadhaar_pattern = r'\b\d{4}\s\d{4}\s\d{4}\b'
        pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'

        for page in pdf_document:
            if redaction_options['text']:
                for text in redaction_options['text'].split(','):
                    areas = page.search_for(text.strip())
                    for inst in areas:
                        page.add_redact_annot(inst, fill=(0, 0, 0))

            if redaction_options['aadhaar']:
                areas = page.search_for(aadhaar_pattern, quads=True, flags=8)
                for inst in areas:
                    page.add_redact_annot(inst, fill=(0, 0, 0))

            if redaction_options['pan']:
                areas = page.search_for(pan_pattern, quads=True, flags=8)
                for inst in areas:
                     page.add_redact_annot(inst, fill=(0, 0, 0))

            if redaction_options['custom_regex']:
                try:
                    areas = page.search_for(redaction_options['custom_regex'], quads=True, flags=8)
                    for inst in areas:
                        page.add_redact_annot(inst, fill=(0, 0, 0))
                except Exception as e:
                    st.warning(f"Invalid Regex Pattern: {e}")

            page.apply_redactions()

        redacted_bytes = pdf_document.write()
        pdf_document.close()
        return redacted_bytes
    except Exception as e:
        st.error(f"An error occurred during redaction: {e}")
        return None


def upload_page():

    header_cols = st.columns([3, 1])
    with header_cols[0]:
        st.title("LexiRedact")
    with header_cols[1]:
        button_cols = st.columns(2)
        with button_cols[0]:
            if st.button("Login", use_container_width=True):
                st.info("Login functionality would be here.")
        with button_cols[1]:
            if st.button("Signup", use_container_width=True):
                st.info("Signup functionality would be here.")
    st.markdown("---")


    st.subheader("Upload Your Document")
    st.write("Please upload a PDF file that you would like to redact.")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", label_visibility="collapsed")

    if uploaded_file is not None:
        st.success(f"Successfully uploaded: **{uploaded_file.name}**")
        st.session_state.uploaded_file_bytes = uploaded_file.getvalue()
        st.session_state.file_name = uploaded_file.name
    st.markdown("---")

    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button("Cancel / Upload Another", use_container_width=True):
            st.session_state.uploaded_file_bytes = None
            st.session_state.file_name = None
            st.warning("Upload cancelled. You can now upload a new file.")
            st.experimental_rerun()
    with action_cols[1]:
        if st.button("Proceed to Redact", type="primary", use_container_width=True):
            if st.session_state.uploaded_file_bytes:
                st.session_state.page = 'redact'
                st.experimental_rerun()
            else:
                st.error("Please upload a PDF file first before proceeding.")

def redact_page():
    st.title(f"Redacting: {st.session_state.file_name}")
    st.markdown("---")

    if not st.session_state.uploaded_file_bytes:
        st.error("No file found. Please go back and upload a file.")
        if st.button("Back to Upload"):
            st.session_state.page = 'upload'
            st.experimental_rerun()
        return

    pdf_images = convert_pdf_to_images(st.session_state.uploaded_file_bytes)
    if not pdf_images:
        if st.button("Back to Upload"):
            st.session_state.page = 'upload'
            st.experimental_rerun()
        return

    # Layout
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Document Preview")
        if len(pdf_images) > 1:
            page_selection = st.number_input(f"Page (1-{len(pdf_images)})", min_value=1, max_value=len(pdf_images), value=1)
            st.image(pdf_images[page_selection - 1], use_column_width=True)
        else:
            st.image(pdf_images[0], use_column_width=True)
    with col2:
        st.subheader("Redaction Options")
        text_to_redact = st.text_input("Search Text to Redact", placeholder="Enter text, comma-separated...")
        redact_aadhaar = st.checkbox("Redact Aadhaar Numbers")
        redact_pan = st.checkbox("Redact PAN Numbers")
        custom_regex = st.text_area("Redact Custom Patterns (Regex)", placeholder="Enter regex pattern...")
    st.markdown("---")

    # Actions
    final_action_cols = st.columns([1, 1, 2])
    with final_action_cols[0]:
        if st.button("Back to Upload", use_container_width=True):
            st.session_state.page = 'upload'
            st.session_state.uploaded_file_bytes = None
            st.session_state.file_name = None
            st.experimental_rerun()
    with final_action_cols[2]:
        if st.button("Confirm and Redact", type="primary", use_container_width=True):
            options = {
                'text': text_to_redact,
                'aadhaar': redact_aadhaar,
                'pan': redact_pan,
                'custom_regex': custom_regex
            }
            with st.spinner('Redacting document... Please wait.'):
                redacted_pdf = redact_pdf(st.session_state.uploaded_file_bytes, options)
            if redacted_pdf:
                st.session_state.redacted_file_bytes = redacted_pdf
                st.session_state.page = 'download'
                st.experimental_rerun()

def download_page():
    st.title("Redaction Complete")
    st.markdown("---")
    st.success("Your document has been successfully redacted.")
    
    if st.session_state.redacted_file_bytes:
        redacted_filename = f"redacted_{st.session_state.file_name}"
        st.download_button(
            label="Download Redacted PDF",
            data=st.session_state.redacted_file_bytes,
            file_name=redacted_filename,
            mime="application/pdf",
            use_container_width=True
        )
    
    st.markdown("---")
    if st.button("Redact Another Document", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = 'upload' # Ensure page is set back to upload
        st.experimental_rerun()


if st.session_state.page == 'upload':
    upload_page()
elif st.session_state.page == 'redact':
    redact_page()
elif st.session_state.page == 'download':
    download_page()

