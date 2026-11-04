# CodeGuard AI — AI-Powered Project Report Generator

CodeGuard AI is a full-stack web application that automates the generation of academic and technical project reports. Users can upload their source code as a ZIP file, provide a sample PDF format, and the application uses Generative AI to write and render a perfectly formatted PDF report.

## Features
- **Project Ingestion:** Analyzes project ZIP files to extract structure, languages, frameworks, and entry points.
- **Format Parsing:** Uses PyMuPDF to extract chapter headings and layout rules from a user-uploaded sample PDF.
- **Generative AI:** Integrates the Groq API (with Ollama fallback) to write context-aware report chapters based on the codebase.
- **Parallel Processing:** Utilizes Python's ThreadPoolExecutor to generate chapters in parallel, reducing AI generation time by 4x.
- **PDF Rendering:** Uses Jinja2 and WeasyPrint to programmatically render HTML/CSS into a paginated PDF with an automated Table of Contents, dynamic page breaks, and image galleries.

## Tech Stack
- **Frontend:** React, TypeScript, Tailwind CSS, Vite
- **Backend:** Python, FastAPI
- **AI Providers:** Groq API (Llama 3), Ollama (Llama 3.1 fallback)
- **Document Processing:** PyMuPDF (fitz), PyPDF, Jinja2, WeasyPrint

## How to Run Locally
1. Clone the repository.
2. Set up the frontend (`npm install`).
3. Set up the backend (`pip install -r requirements.txt`).
4. Add your `GROQ_API_KEY` to a `.env` file.
5. Start the backend (`uvicorn app.main:app --reload`) and frontend (`npm run dev`).
