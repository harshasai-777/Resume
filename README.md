# AI Resume Analyzer

An AI-powered resume analysis and optimization platform built using **Python**, **Streamlit**, **Gemini API (Gemini 1.5 Flash)**, and **Docker**, designed to be containerized and deployed on **Google Cloud Run**.

The platform automates the tedious parts of tailoring resumes for jobs. It parses uploaded resumes, evaluates fit, identifies skill gaps, rewrites weak resume points, and generates personalized interview preparation plans.

---

## 🌟 Features

- **Resume-to-Job Matching**: Scores your compatibility against any job description with a visual matching dashboard.
- **Skill-Gap Analysis**: Extracts required technical and soft skills, cross-checks them with the resume, and maps them in an interactive table showing missing credentials along with a structured bridge plan.
- **Tailored Improvement Suggestions**: Rewrites existing bullet points using impact-driven metrics (STAR/XYZ formulas) and active verbs, with concrete "Before & After" examples.
- **Dynamic Interview Prep Q&A**: Formulates customized behavioral and technical interview questions based on the candidate's specific background and target job description.
- **ATS Keyword Optimizer**: Highlights high-yield keywords extracted directly from the job description to improve Applicant Tracking System parsing rates.
- **Markdown Report Exports**: Generates a unified report file containing all insights for offline review.

---

## 🛠️ Architecture & Tech Stack

- **Frontend & UI**: Streamlit (with custom glassmorphic styling, adaptive light/dark mode UI variables, and custom CSS elements).
- **Core LLM Engine**: Gemini 1.5 Flash API (utilizing `google-generativeai` SDK).
- **PDF Extraction**: `pypdf` parser.
- **Containerization**: Docker (multi-stage equivalent slim container setup).
- **Deployment**: Google Cloud Run (designed to scale down to 0 instances to minimize cost).

---

## 🚀 Local Setup & Installation

### Prerequisites
- Python 3.9 to 3.11 installed.
- A **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/).

### 1. Clone & Navigate to the Project
```bash
cd resume_hrs
```

### 2. Create and Activate Virtual Environment
On Windows:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Open the `.env` file and insert your Gemini API Key:
```env
GEMINI_API_KEY=AIzaSyYourGeminiApiKeyHere
```
*Note: You can also choose to enter the API key directly in the sidebar of the Streamlit web interface.*

### 5. Run the Application
```bash
streamlit run app.py
```
Your default browser will open automatically at `http://localhost:8501`.

---

## 🐳 Running with Docker

You can containerize the application to verify its behavior in an isolated environment.

### 1. Build the Docker Image
```bash
docker build -t ai-resume-analyzer .
```

### 2. Run the Container locally
```bash
docker run -p 8080:8080 --env-file .env ai-resume-analyzer
```
Navigate to `http://localhost:8080` in your web browser.

---

## ☁️ Deploying to Google Cloud Run

This application is ready for immediate deployment on Google Cloud Run. Follow these simple instructions:

### Prerequisites
1. Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install).
2. Create a Google Cloud Project and ensure billing is enabled.
3. Authenticate the CLI:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

### 1. Enable Required Services
Ensure that Cloud Run and Cloud Build APIs are active:
```bash
gcloud services enable run.googleapis.com build.googleapis.com
```

### 2. Deploy Direct from Source code
You can compile and deploy the container directly using standard gcloud source build commands:
```bash
gcloud run deploy ai-resume-analyzer `
    --source . `
    --port 8080 `
    --env-vars GEMINI_API_KEY=YOUR_GEMINI_API_KEY `
    --allow-unauthenticated `
    --region us-central1
```

Once the command finishes running, Google Cloud will provide a public URL (e.g. `https://ai-resume-analyzer-xxxxx-uc.a.run.app`). Open it in your browser!
