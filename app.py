import streamlit as st
from google import genai
from PyPDF2 import PdfReader
import os

st.set_page_config(page_title="ATS Resume Checker", page_icon="📄", layout="wide")

api_key = st.secrets.get("GEMINI_API_KEY", None)
if not api_key:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("GEMINI_API_KEY not found.")
    st.stop()

client = genai.Client(api_key=api_key)

def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\\n"
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
    return text

def analyze_resume(resume_text):
    prompt = f"""
You are a professional ATS (Applicant Tracking System) and Resume Reviewer.

Analyze the following resume and provide:
1. ATS Score out of 100
2. Executive Summary
3. Strengths
4. Weaknesses
5. Missing Keywords
6. Formatting Issues
7. Resume Improvement Suggestions
8. Recommended Skills to Add
9. Final Verdict

Resume:
{resume_text}

Return the result in clean markdown format.
ATS Score: XX/100
"""
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt
    )
    return response.text

st.title("📄 ATS Resume Checker")
st.markdown("Upload your resume and receive an ATS score with detailed improvement suggestions.")

uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Reading resume..."):
        resume_text = extract_text_from_pdf(uploaded_file)

    if len(resume_text.strip()) < 100:
        st.warning("Very little text was extracted from the PDF.")
    else:
        st.success("Resume uploaded successfully!")

        if st.button("Analyze Resume"):
            with st.spinner("Analyzing with Gemini Flash..."):
                result = analyze_resume(resume_text)

            st.markdown("## Analysis Report")
            st.markdown(result)
