import streamlit as st
from google import genai
import pdfplumber
import docx
import json
import re

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="ATS Resume Checker",
    page_icon="📄",
    layout="wide"
)

# =========================
# GEMINI CLIENT
# =========================

try:
    client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )
except Exception:
    st.error(
        "Gemini API key not found. Add GEMINI_API_KEY in Streamlit Secrets."
    )
    st.stop()

MODEL_NAME = st.sidebar.selectbox(
    "Select Gemini Model",
    [
        "gemini-3.6-flash",
        "gemini-3.6-pro"
    ]
)

# =========================
# FILE EXTRACTION
# =========================

def extract_pdf_text(uploaded_file):
    text = ""

    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    text += page_text + "\n"

    except Exception as e:
        raise Exception(f"PDF reading failed: {e}")

    return text


def extract_docx_text(uploaded_file):
    try:
        document = docx.Document(uploaded_file)

        paragraphs = []

        for para in document.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)

        return "\n".join(paragraphs)

    except Exception as e:
        raise Exception(f"DOCX reading failed: {e}")


def get_resume_text(uploaded_file):

    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        return extract_pdf_text(uploaded_file)

    elif filename.endswith(".docx"):
        return extract_docx_text(uploaded_file)

    raise Exception("Unsupported file type.")


# =========================
# CLEAN JSON
# =========================

def clean_json_response(text):

    text = text.strip()

    text = re.sub(r"^```json", "", text)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)

    return text.strip()


# =========================
# GEMINI ANALYSIS
# =========================

def analyze_resume(resume_text, job_description):

    prompt = f"""
You are a professional ATS Resume Analyzer.

Analyze the resume against the provided Job Description.

Return ONLY valid JSON.

{{
  "ats_score": 0,
  "keyword_match_score": 0,
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

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    text = response.text

    cleaned = clean_json_response(text)

    try:
        result = json.loads(cleaned)
        return result

    except Exception:
        raise Exception(
            f"Gemini did not return valid JSON.\n\nResponse:\n{cleaned}"
        )


# =========================
# UI
# =========================

st.title("📄 ATS Resume Checker")

st.markdown(
    """
Upload your Resume (PDF/DOCX) and paste a Job Description.

The app will provide:

- ATS Score
- Keyword Match Score
- Missing Keywords
- Strengths
- Weaknesses
- Improvement Suggestions
- Section-by-Section Feedback
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
        st.warning("Please paste a Job Description.")
        st.stop()

    with st.spinner("Analyzing Resume..."):

        try:

            resume_text = get_resume_text(uploaded_file)

            if len(resume_text.strip()) < 50:
                st.error(
                    "Could not extract enough text from the uploaded resume."
                )
                st.stop()

            result = analyze_resume(
                resume_text,
                job_description
            )

            st.success("Analysis Completed")

            # =========================
            # SCORE CARDS
            # =========================

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "ATS Score",
                    f"{result.get('ats_score', 0)}/100"
                )

            with col2:
                st.metric(
                    "Keyword Match",
                    f"{result.get('keyword_match_score', 0)}%"
                )

            st.divider()

            # =========================
            # MISSING KEYWORDS
            # =========================

            st.subheader("Missing Keywords")

            missing = result.get("missing_keywords", [])

            if missing:
                for keyword in missing:
                    st.write(f"❌ {keyword}")
            else:
                st.write("No major keywords missing.")

            st.divider()

            # =========================
            # STRENGTHS
            # =========================

            st.subheader("Strengths")

            for item in result.get("strengths", []):
                st.write(f"✅ {item}")

            st.divider()

            # =========================
            # WEAKNESSES
            # =========================

            st.subheader("Weaknesses")

            for item in result.get("weaknesses", []):
                st.write(f"⚠️ {item}")

            st.divider()

            # =========================
            # IMPROVEMENTS
            # =========================

            st.subheader("Improvement Suggestions")

            for item in result.get("improvements", []):
                st.write(f"💡 {item}")

            st.divider()

            # =========================
            # SECTION FEEDBACK
            # =========================

            st.subheader("Section Feedback")

            section_feedback = result.get(
                "section_feedback",
                {}
            )

            st.markdown("### Summary")
            st.write(
                section_feedback.get(
                    "summary",
                    "No feedback."
                )
            )

            st.markdown("### Experience")
            st.write(
                section_feedback.get(
                    "experience",
                    "No feedback."
                )
            )

            st.markdown("### Education")
            st.write(
                section_feedback.get(
                    "education",
                    "No feedback."
                )
            )

            st.markdown("### Skills")
            st.write(
                section_feedback.get(
                    "skills",
                    "No feedback."
                )
            )

            st.divider()

            # =========================
            # OVERALL FEEDBACK
            # =========================

            st.subheader("Overall Feedback")

            st.write(
                result.get(
                    "overall_feedback",
                    "No feedback generated."
                )
            )

            st.divider()

            st.download_button(
                label="📥 Download Analysis JSON",
                data=json.dumps(
                    result,
                    indent=4
                ),
                file_name="ats_analysis.json",
                mime="application/json"
            )

        except Exception as e:
            st.error(str(e))
