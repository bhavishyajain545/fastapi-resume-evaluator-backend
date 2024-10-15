import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
import os
import openai
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from PyPDF2 import PdfReader  # Add this to handle PDFs
import textract  # Handles DOCX and other formats

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Set up OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in environment variables!")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Add CORS middleware to allow requests from React frontend (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fastapi-resume-evaluator-frontend-achbixs71.vercel.app"],  # Update this with your actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Function to extract text from different file types
def extract_text_from_file(file: UploadFile):
    if file.content_type == "application/pdf":
        # Handle PDF files
        reader = PdfReader(file.file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    elif file.content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
        # Handle DOCX or DOC files using textract
        return textract.process(file.file).decode('utf-8')
    else:
        # For text files or unknown formats, just read as text
        return file.file.read().decode('utf-8')

# Function to analyze resume content using OpenAI API
def analyze_resume_with_openai(resume_text: str):
    try:
        logger.info("Sending request to OpenAI API for analysis")
        
        # Updated method for chat-based completion
        response = openai.completions.create(
            model="gpt-3.5-turbo",  # Chat-based model
            messages=[
                {"role": "system", "content": "You are an assistant who evaluates resumes."},
                {"role": "user", "content": f"Evaluate this resume and provide feedback on the skills, industry-standard keywords, and job matching:\n{resume_text}"}
            ],
            max_tokens=500
        )
        return response["choices"][0]["message"]["content"]
        
    except Exception as e:
        logger.error(f"Error with OpenAI API: {e}")
        raise HTTPException(status_code=500, detail="Error analyzing resume with OpenAI API")

# Route to handle resume uploads and feedback using OpenAI API
@app.post("/upload_resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        logger.info("Received resume file upload")
        resume_text = extract_text_from_file(file)
        
        if not resume_text.strip():
            return {"feedback": "The uploaded resume is empty or unreadable. Please upload a valid resume file."}
        
        logger.info("Analyzing resume with OpenAI API")
        feedback = analyze_resume_with_openai(resume_text)
        logger.info("Analysis complete, sending feedback to frontend")
        return {"feedback": feedback}
    except Exception as e:
        logger.error(f"Error processing resume: {e}")
        raise HTTPException(status_code=500, detail="Error processing resume")

# Root route for health check or simple info (optional)
@app.get("/")
def read_root():
    return {"message": "Welcome to the AI-powered Resume Evaluator!"}
