import streamlit as st
from google import genai
import pdfplumber
import docx
import json
from io import BytesIO

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="ATS Resume Checker",
    page_icon="📄",
    layout="wide"
)

# -----------------------------
# GEMINI CONFIG
# -----------------------------
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("Gemini API key not found in Streamlit Secrets.")
    st.stop()

MODEL_NAME = "gemini-2.5-flash"

# -----------------------------
# HELPERS
# -----------------------------
def extract_pdf_text(file):
    text = ""

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text


def extract_docx_text(file):
    document = docx.Document(file)

    text = []

    for para in document.paragraphs:
        text.append(para.text)

    return "\n".join(text)


def get_resume_text(uploaded_file):
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        return extract_pdf_text(uploaded_file)

    elif filename.endswith(".docx"):
        return extract_docx_text(uploaded_file)

    else:
        return ""


# -----------------------------
# GEMINI ANALYSIS
# -----------------------------
def analyze_resume(resume_text, job_description):

    model = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""
You are an expert ATS Resume Reviewer.

Analyze the resume against the provided Job Description.

Return ONLY valid JSON.

JSON format:

{{
  "ats_score": number,
  "keyword_match_score": number,
  "missing_keywords": [],
  "strengths": [],
  "weaknesses": [],
  "improvements": [],
  "section_feedback": {{
      "summary": "",
      "experience": "",
      "education": "",
      "skills": ""
  }},
  "overall_feedback": ""
}}

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}
"""

    response = model.generate_content(prompt)

    text = response.text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "")
        text = text.replace("```", "")

    elif text.startswith("```"):
        text = text.replace("```", "")

    return json.loads(text)


# -----------------------------
# UI
# -----------------------------
st.title("📄 ATS Resume Checker")

st.markdown(
    """
Upload your resume and compare it against a Job Description.
Get ATS Score, Keyword Match, Missing Keywords, and Improvement Suggestions.
"""
)

uploaded_file = st.file_uploader(
    "Upload Resume",
    type=["pdf", "docx"]
)

job_description = st.text_area(
    "Paste Job Description",
    height=250
)

if st.button("Analyze Resume", type="primary"):

    if uploaded_file is None:
        st.warning("Please upload a resume.")
        st.stop()

    if not job_description.strip():
        st.warning("Please enter a job description.")
        st.stop()

    with st.spinner("Analyzing Resume..."):

        try:

            resume_text = get_resume_text(uploaded_file)

            result = analyze_resume(
                resume_text,
                job_description
            )

            st.success("Analysis Completed")

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "ATS Score",
                    f"{result['ats_score']}/100"
                )

            with col2:
                st.metric(
                    "Keyword Match",
                    f"{result['keyword_match_score']}%"
                )

            st.divider()

            st.subheader("Missing Keywords")

            if result["missing_keywords"]:
                for keyword in result["missing_keywords"]:
                    st.write("❌", keyword)
            else:
                st.write("No major keywords missing.")

            st.divider()

            st.subheader("Strengths")

            for item in result["strengths"]:
                st.write("✅", item)

            st.divider()

            st.subheader("Weaknesses")

            for item in result["weaknesses"]:
                st.write("⚠️", item)

            st.divider()

            st.subheader("Improvement Suggestions")

            for item in result["improvements"]:
                st.write("💡", item)

            st.divider()

            st.subheader("Section Feedback")

            sf = result["section_feedback"]

            st.write("### Summary")
            st.write(sf["summary"])

            st.write("### Experience")
            st.write(sf["experience"])

            st.write("### Education")
            st.write(sf["education"])

            st.write("### Skills")
            st.write(sf["skills"])

            st.divider()

            st.subheader("Overall Feedback")
            st.write(result["overall_feedback"])

            st.download_button(
                label="Download Analysis JSON",
                data=json.dumps(
                    result,
                    indent=4
                ),
                file_name="ats_analysis.json",
                mime="application/json"
            )

        except Exception as e:
            st.error(f"Error: {str(e)}")
