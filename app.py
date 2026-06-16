import streamlit as st
import os
import re
import warnings
# Suppress the Google GenAI SDK deprecation warnings in stdout
warnings.filterwarnings("ignore", category=FutureWarning)
from pypdf import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# App Page Configurations
st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling (Responsive, adaptation to dark/light modes using Streamlit variables)
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Overrides */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Main Layout Accent Colors */
    .stApp {
        background-attachment: fixed;
    }
    
    /* Glassmorphic Container Cards */
    .glass-card {
        background: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.03);
        backdrop-filter: blur(5px);
    }
    
    /* Header Gradient Text */
    .gradient-header {
        background: linear-gradient(90deg, #4f46e5 0%, #9333ea 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 10px;
    }
    
    /* Subtitle Styling */
    .subtitle {
        color: #6b7280;
        font-size: 1.15rem;
        margin-bottom: 30px;
        font-weight: 400;
    }
    
    /* Score Circle Progress Indicator */
    .score-circle-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-right: 30px;
        margin-bottom: 20px;
    }
    
    .score-circle {
        position: relative;
        display: flex;
        justify-content: center;
        align-items: center;
        width: 140px;
        height: 140px;
        border-radius: 50%;
        font-size: 32px;
        font-weight: 800;
        color: var(--text-color);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    
    .score-label {
        font-weight: 600;
        font-size: 0.9rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Sidebar Details styling */
    .sidebar-section {
        background: rgba(128, 128, 128, 0.04);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
    
    /* Custom tags/badges */
    .status-badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }
    
    .status-configured {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    
    .status-missing {
        background-color: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.2);
    }
    
    /* Responsive details */
    @media (max-width: 768px) {
        .score-circle-container {
            margin-right: 0;
            margin-bottom: 25px;
        }
    }
</style>
""", unsafe_allow_html=True)

# Helper function to extract text from PDF
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        st.error(f"Error parsing PDF file: {e}")
        return None

def detect_provider_and_model(api_key):
    api_key = api_key.strip()
    
    # 1. OpenRouter Detection
    if api_key.startswith("sk-or-v1-"):
        try:
            r = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                models = [m["id"] for m in data.get("data", [])]
                for preferred in ["google/gemini-2.5-flash", "google/gemini-2.0-flash", "google/gemini-1.5-flash", "meta-llama/llama-3-8b-instruct:free"]:
                    if preferred in models:
                        return "OpenRouter", preferred
                if models:
                    return "OpenRouter", models[0]
        except Exception:
            pass
        return "OpenRouter", "google/gemini-2.5-flash"
        
    # 2. OpenAI Detection
    if api_key.startswith("sk-proj-") or (api_key.startswith("sk-") and not api_key.startswith("sk-ant-")):
        return "OpenAI", "gpt-4o-mini"
        
    # 3. Anthropic Detection
    if api_key.startswith("sk-ant-"):
        return "Anthropic", "claude-3-5-sonnet-latest"
        
    # 4. Gemini Detection
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        model_names = [m.name.replace("models/", "") for m in models if "generateContent" in m.supported_generation_methods]
        for preferred in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-3.5-flash", "gemini-flash-latest"]:
            if preferred in model_names:
                try:
                    model = genai.GenerativeModel(preferred)
                    model.generate_content("test", generation_config={"max_output_tokens": 1})
                    return "Gemini", preferred
                except Exception:
                    continue
        if model_names:
            return "Gemini", model_names[0]
    except Exception:
        pass
    return "Gemini", "gemini-2.5-flash"

def query_llm(prompt, api_key):
    api_key = api_key.strip()
    if 'detected_key' not in st.session_state or st.session_state.detected_key != api_key:
        provider, model_name = detect_provider_and_model(api_key)
        st.session_state.detected_key = api_key
        st.session_state.detected_provider = provider
        st.session_state.detected_model = model_name
        
    provider = st.session_state.detected_provider
    model_name = st.session_state.detected_model
    
    try:
        if provider == "Gemini":
            genai.configure(api_key=api_key)
            generation_config = {
                "temperature": 0.3,
                "top_p": 0.95,
                "max_output_tokens": 8192,
            }
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config
            )
            response = model.generate_content(prompt)
            return response.text
            
        elif provider == "OpenRouter":
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
            }
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=90)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            else:
                st.error(f"OpenRouter Error {r.status_code}: {r.text}")
                return None
                
        elif provider == "OpenAI":
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
            }
            r = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=90)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            else:
                st.error(f"OpenAI Error {r.status_code}: {r.text}")
                return None
                
        elif provider == "Anthropic":
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
                "temperature": 0.3,
            }
            r = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=90)
            if r.status_code == 200:
                return r.json()["content"][0]["text"]
            else:
                st.error(f"Anthropic Error {r.status_code}: {r.text}")
                return None
    except Exception as e:
        st.error(f"LLM Query Error ({provider} - {model_name}): {e}")
        return None

def get_provider_and_model(api_key):
    api_key = api_key.strip()
    if 'detected_key' not in st.session_state or st.session_state.detected_key != api_key:
        provider, model_name = detect_provider_and_model(api_key)
        st.session_state.detected_key = api_key
        st.session_state.detected_provider = provider
        st.session_state.detected_model = model_name
    return st.session_state.detected_provider, st.session_state.detected_model

# Main Title Section
st.markdown('<div class="gradient-header">AI Resume Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Match resume compatibility, perform skill-gap analyses, and generate personalized interview prep using the Gemini API.</div>', unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/resume.png", width=120)
    st.title("Configuration")
    
    # 1. API Key Check
    env_key = os.getenv("GEMINI_API_KEY")
    api_key_input = st.text_input(
        "Enter API Key",
        value=env_key if env_key else "",
        type="password",
        help="Supports Google AI Studio (Gemini), OpenRouter, OpenAI, and Anthropic keys. Optimal model will be auto-detected."
    )
    
    # Visual validation indicator for API key
    if api_key_input:
        st.markdown('<div class="status-badge status-configured">✓ API Key Configured</div>', unsafe_allow_html=True)
        
        # Trigger auto-detection and display details
        with st.spinner("Detecting API provider..."):
            provider, model_name = get_provider_and_model(api_key_input)
        st.markdown(f"""
        <div style="background-color: rgba(79, 70, 229, 0.1); border: 1px solid rgba(79, 70, 229, 0.2); border-radius: 8px; padding: 12px; margin-top: 10px;">
            <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: #818cf8; font-weight: 700;">Auto-Detected API Details</div>
            <div style="margin-top: 5px; font-size: 0.95rem; font-weight: 600;">Provider: <span style="color: #c084fc;">{provider}</span></div>
            <div style="font-size: 0.9rem; font-weight: 500;">Model: <span style="font-family: monospace; color: #fb7185;">{model_name}</span></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge status-missing">✗ API Key Missing</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 2. Upload Resume
    st.subheader("Upload Resume")
    uploaded_file = st.file_uploader(
        "Upload PDF or TXT Resume",
        type=["pdf", "txt"],
        help="Supports .pdf and .txt format"
    )
    
    resume_text = None
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.pdf'):
            with st.spinner("Extracting text from PDF..."):
                resume_text = extract_text_from_pdf(uploaded_file)
        else:
            resume_text = str(uploaded_file.read(), "utf-8")
        
        if resume_text:
            st.markdown('<div class="status-badge status-configured">✓ Resume Uploaded</div>', unsafe_allow_html=True)
            st.caption(f"Extracted {len(resume_text)} characters")
    
    st.markdown("---")
    st.markdown("""
    <div class="sidebar-section">
        <strong>💡 Deployment Quick-Info</strong><br>
        This container is ready to run on <strong>Google Cloud Run</strong>. Set <code>GEMINI_API_KEY</code> as a Cloud Run environment variable to deploy.
    </div>
    """, unsafe_allow_html=True)

# Main Dashboard Form
col1, col2 = st.columns([1, 1])

# Initialize session state for storing results
if 'analysis_completed' not in st.session_state:
    st.session_state.analysis_completed = False
    st.session_state.match_percentage = 0
    st.session_state.match_summary = ""
    st.session_state.skill_gap = ""
    st.session_state.improvements = ""
    st.session_state.interview_prep = ""

st.markdown("### Job Details")
job_description = st.text_area(
    "Paste the target Job Description (JD) here:",
    height=250,
    placeholder="Paste the job requirements, duties, and qualifications here..."
)

# Start Analysis Button
if st.button("🚀 Analyze Resume & Match Fit", type="primary", use_container_width=True):
    if not api_key_input:
        st.warning("⚠️ Please provide a Gemini API Key in the sidebar.")
    elif not resume_text:
        st.warning("⚠️ Please upload a valid Resume in the sidebar.")
    elif not job_description.strip():
        st.warning("⚠️ Please paste a Job Description to compare against.")
    else:
        # Perform analysis with loading UI
        with st.status("Analyzing resume compatibility...", expanded=True) as status_box:
            st.write("🔄 Parsing resume profiles...")
            
            # Step 1: Match Score & Summary
            st.write("📊 Evaluating Resume-to-Job matching alignment...")
            match_prompt = f"""
            You are an expert ATS (Applicant Tracking System) recruiter. Compare this candidate's resume with the target job description.
            
            Resume:
            {resume_text}
            
            Job Description:
            {job_description}
            
            Format your output strictly as follows:
            Match Percentage: [Insert a single number score from 0 to 100 representing compatibility]
            
            ---
            
            ### Executive Match Summary
            [Provide a detailed paragraph summarizing the fit]
            
            ### Key Strengths & Alignment
            [Provide 3-4 bullet points highlighting the matching experience and competencies]
            """
            
            match_result = query_llm(match_prompt, api_key_input)
            
            if match_result:
                # Extract score
                match_score_match = re.search(r"Match Percentage:\s*(\d+)", match_result)
                if match_score_match:
                    st.session_state.match_percentage = int(match_score_match.group(1))
                    # Remove the score prefix from output for better reading
                    st.session_state.match_summary = re.sub(r"Match Percentage:\s*\d+\s*", "", match_result).strip()
                else:
                    st.session_state.match_percentage = 50
                    st.session_state.match_summary = match_result
            
            # Step 2: Skill Gap Analysis
            st.write("🔍 Identifying technical and soft skill gaps...")
            gap_prompt = f"""
            Identify skill gaps between this candidate's resume and the job description.
            
            Resume:
            {resume_text}
            
            Job Description:
            {job_description}
            
            Output a markdown analysis including:
            1. A clear markdown table comparing critical skills:
               | Skill | Status (Found / Missing / Partial) | Context / Reference from Resume |
            2. Missing Technical Skills & Missing Soft Skills lists.
            3. Recommendations & actionable steps (courses, certifications, specific projects) to bridge these specific gaps.
            """
            st.session_state.skill_gap = query_llm(gap_prompt, api_key_input) or "Failed to run Skill Gap analysis."
            
            # Step 3: Resume Improvement suggestions
            st.write("💡 Drafting personalized resume improvement suggestions...")
            improvement_prompt = f"""
            Review this resume and suggest changes to optimize it for this Job Description. Focus on ATS formatting, active verbs, and keyword alignment.
            
            Resume:
            {resume_text}
            
            Job Description:
            {job_description}
            
            Provide:
            1. **Resume Improvements**: Bulleted tips on formatting, wording, and structure.
            2. **Before & After Examples**: Take 2-3 bullet points or statements from the candidate's actual resume, show them ("Before"), and rewrite them ("After") with improvements. Explain "Why" for each.
            3. **Keyword Optimization**: List of 8-10 high-value keywords from the job description that should be integrated into the resume.
            """
            st.session_state.improvements = query_llm(improvement_prompt, api_key_input) or "Failed to run Resume Improvements."
            
            # Step 4: Interview Preparation Questions
            st.write("💬 Formatting interview questions & response frameworks...")
            interview_prompt = f"""
            Generate interview preparation questions based on this resume and job description.
            
            Resume:
            {resume_text}
            
            Job Description:
            {job_description}
            
            Provide 5 customized interview questions (technical + behavioral) a hiring manager would likely ask this candidate.
            For each question:
            - **Question**: [The question text, referencing the candidate's experience or skill gaps]
            - **Interviewer's Goal**: [What they are looking for]
            - **Answering Strategy**: [A step-by-step guide using the STAR method, suggesting which specific resume details/experience they should cite]
            """
            st.session_state.interview_prep = query_llm(interview_prompt, api_key_input) or "Failed to generate interview prep."


            
            st.session_state.analysis_completed = True
            status_box.update(label="✅ Resume Analysis Completed Successfully!", state="complete", expanded=False)

# Display Results if Analysis is Complete
if st.session_state.analysis_completed:
    st.markdown("---")
    
    # Navigation Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Match Score & Overview", 
        "🔍 Skill-Gap Analysis", 
        "💡 Resume Enhancements", 
        "💬 Interview Prep Q&A"
    ])
    
    with tab1:
        # Match Overview
        col_score, col_details = st.columns([1, 3])
        
        with col_score:
            score = st.session_state.match_percentage
            # Responsive dynamic gradient progress circle using inline css styling
            st.markdown(f"""
            <div class="score-circle-container">
                <div class="score-circle" style="background: radial-gradient(circle, var(--background-color) 60%, transparent 61%), conic-gradient(#8e54e9 {score}%, rgba(128, 128, 128, 0.15) 0);">
                    {score}%
                </div>
                <div class="score-label">Job Match Rate</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Visual text status depending on match score
            if score >= 80:
                st.success("🟢 Excellent Match! Highly competitive candidate.")
            elif score >= 60:
                st.warning("🟡 Good Match. Some skill gaps to address.")
            else:
                st.error("🔴 Low Match. Strong updates required to meet requirements.")
                
        with col_details:
            with st.container(border=True):
                st.markdown(st.session_state.match_summary)
            
    with tab2:
        st.markdown("### Skill-Gap Analysis")
        with st.container(border=True):
            st.markdown(st.session_state.skill_gap)
        
    with tab3:
        st.markdown("### Tailored Resume Improvements")
        with st.container(border=True):
            st.markdown(st.session_state.improvements)
        
    with tab4:
        st.markdown("### Practice Interview Questions")
        with st.container(border=True):
            st.markdown(st.session_state.interview_prep)
        
    # Download Button for the report
    st.markdown("---")
    st.subheader("📥 Export Resume Report")
    
    report_content = f"""# AI Resume Analyzer Report
## Match Rate: {st.session_state.match_percentage}%

{st.session_state.match_summary}

---

## Skill-Gap Analysis
{st.session_state.skill_gap}

---

## Resume Improvements
{st.session_state.improvements}

---

## Interview Prep Q&A
{st.session_state.interview_prep}
"""
    
    st.download_button(
        label="Download Full Report (Markdown)",
        data=report_content,
        file_name="Resume_Analyzer_Report.md",
        mime="text/markdown",
        use_container_width=True
    )
else:
    # Instructions panel when app has not run
    st.markdown("""
    <div class="glass-card">
        <h3>👋 Welcome to the AI Resume Analyzer!</h3>
        <p>To analyze your resume fit against a job requirements profile:</p>
        <ol>
            <li>Input your <strong>Gemini API Key</strong> in the sidebar.</li>
            <li>Upload your resume in <strong>PDF</strong> or <strong>TXT</strong> format.</li>
            <li>Paste the target <strong>Job Description</strong> in the text field above.</li>
            <li>Click <strong>🚀 Analyze Resume & Match Fit</strong>.</li>
        </ol>
        <p>The system will compile custom matches, key strengths, skill gaps, resume improvements, and dynamic interview prep questions for you.</p>
    </div>
    """, unsafe_allow_html=True)
