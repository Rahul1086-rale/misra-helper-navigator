# app.py - FastAPI Backend API Server
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import uuid
import tempfile
import json
from pathlib import Path

# Import our Python modules
from misra_chat_client import init_vertex_ai, load_cpp_file, start_chat, send_file_intro, send_misra_violations
from excel_utils import extract_violations_for_file
from numbering import add_line_numbers
from denumbering import remove_line_numbers
from replace import merge_fixed_snippets_into_file
from fixed_response_code_snippet import extract_snippets_from_response, save_snippets_to_json
from diff_utils import create_temp_fixed_denumbered_file, get_file_content, create_diff_data, cleanup_temp_files
from database import db

app = FastAPI(
    title="MISRA Fix Copilot API",
    description="API for fixing MISRA violations in C/C++ code using AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory chat sessions (chat objects can't be easily serialized)
chat_sessions = {}

# Default model settings
default_model_settings = {
    "model_name": "gemini-2.5-pro",
    "temperature": 0.5,
    "top_p": 0.95,
    "max_tokens": 65535,
    "safety_settings": False
}

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'cpp', 'c', 'xlsx', 'xls'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Pydantic models for request/response validation
class LineNumbersRequest(BaseModel):
    projectId: str
    userId: str = "default"

class FirstPromptRequest(BaseModel):
    projectId: str
    userId: str = "default"

class FixViolationsRequest(BaseModel):
    projectId: str
    violations: List[Dict[str, Any]] = []
    userId: str = "default"

class ApplyFixesRequest(BaseModel):
    projectId: str
    userId: str = "default"

class ChatRequest(BaseModel):
    message: str
    projectId: str
    userId: str = "default"  # Add user identification

class ModelSettings(BaseModel):
    model_name: str
    temperature: float
    top_p: float
    max_tokens: int
    safety_settings: bool

class UploadResponse(BaseModel):
    filePath: str
    fileName: str

class ProcessResponse(BaseModel):
    numberedFilePath: str

class GeminiResponse(BaseModel):
    response: str

class FixViolationsResponse(BaseModel):
    response: str
    codeSnippets: List[Dict[str, Any]]

class ApplyFixesResponse(BaseModel):
    fixedFilePath: str

class ChatResponse(BaseModel):
    response: str

class SettingsResponse(BaseModel):
    success: bool
    message: str

class DiffResponse(BaseModel):
    original: str
    fixed: str
    has_changes: bool
    highlight: dict = {}

# Initialize Vertex AI on startup
@app.on_event("startup")
async def startup_event():
    init_vertex_ai()

# Settings endpoints
@app.get("/api/settings", response_model=ModelSettings)
async def get_settings(userId: str = Query("default")):
    """Get user-specific model settings"""
    user_settings = db.get_user_model_settings(userId)
    if user_settings:
        return ModelSettings(**user_settings)
    return ModelSettings(**default_model_settings)

@app.post("/api/settings", response_model=SettingsResponse)
async def save_settings(settings: ModelSettings, userId: str = Query("default")):
    """Save user-specific model settings"""
    try:
        db.save_user_model_settings(userId, settings.dict())
        
        return SettingsResponse(
            success=True,
            message="Settings saved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@app.post("/api/upload/cpp-file", response_model=UploadResponse)
async def upload_cpp_file(
    file: UploadFile = File(...),
    projectId: str = Form(...),
    userId: str = Form("default")
):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        if not allowed_file(file.filename):
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Save uploaded file with user context
        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, f"{userId}_{projectId}_{filename}")
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Initialize user session
        session_data = {
            'cpp_file': file_path,
            'original_filename': filename
        }
        db.save_user_session(userId, projectId, session_data)
        db.save_user_file(userId, projectId, "cpp_file", file_path, filename)
        
        return UploadResponse(
            filePath=file_path,
            fileName=filename
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/misra-report")
async def upload_misra_report(
    file: UploadFile = File(...),
    projectId: str = Form(...),
    targetFile: str = Form(...),
    userId: str = Form("default")
):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        # Save Excel file with user context
        filename = file.filename
        excel_path = os.path.join(UPLOAD_FOLDER, f"{userId}_{projectId}_report_{filename}")
        
        with open(excel_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Extract violations
        violations = extract_violations_for_file(excel_path, targetFile)
        
        # Store in user session
        session_data = db.get_user_session(userId, projectId) or {}
        session_data.update({
            'excel_file': excel_path,
            'violations': violations
        })
        db.save_user_session(userId, projectId, session_data)
        db.save_user_file(userId, projectId, "excel_file", excel_path, filename)
        
        return violations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process/add-line-numbers", response_model=ProcessResponse)
async def process_add_line_numbers(request: LineNumbersRequest):
    try:
        project_id = request.projectId
        user_id = request.userId
        
        session_data = db.get_user_session(user_id, project_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        input_file = session_data['cpp_file']
        
        # Create numbered file with .txt extension and user context
        original_name = Path(session_data['original_filename']).stem
        numbered_filename = f"numbered_{original_name}.txt"
        numbered_path = os.path.join(UPLOAD_FOLDER, f"{user_id}_{project_id}_{numbered_filename}")
        
        add_line_numbers(input_file, numbered_path)
        
        # Update session
        session_data['numbered_file'] = numbered_path
        db.save_user_session(user_id, project_id, session_data)
        db.save_user_file(user_id, project_id, "numbered_file", numbered_path)
        
        return ProcessResponse(numberedFilePath=numbered_path)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/gemini/first-prompt", response_model=GeminiResponse)
async def gemini_first_prompt(request: FirstPromptRequest):
    try:
        project_id = request.projectId
        user_id = request.userId
        
        session_data = db.get_user_session(user_id, project_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        numbered_file = session_data['numbered_file']
        
        # Load numbered file content
        numbered_content = load_cpp_file(numbered_file)
        
        # Get user-specific model settings
        user_settings = db.get_user_model_settings(user_id) or default_model_settings
        
        # Start chat session with user model settings
        chat = start_chat(
            model_name=user_settings['model_name'],
            temperature=user_settings['temperature'],
            top_p=user_settings['top_p'],
            max_tokens=user_settings['max_tokens'],
            safety_settings=user_settings['safety_settings']
        )
        
        # Send first prompt
        response = send_file_intro(chat, numbered_content)
        
        # Check if response is None (blocked by safety filters)
        if response is None:
            raise HTTPException(
                status_code=422, 
                detail="Response was blocked by safety filters. Please try with different content or contact support."
            )
        
        # Store chat session with user context
        chat_sessions[f"{user_id}_{project_id}"] = chat
        db.save_chat_session(user_id, project_id, chat)
        
        return GeminiResponse(response=response)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import logging
import traceback

@app.post("/api/gemini/fix-violations", response_model=FixViolationsResponse)
async def gemini_fix_violations(request: FixViolationsRequest):
    try:
        project_id = request.projectId
        user_id = request.userId
        violations = request.violations
        
        print(f"Processing user_id: {user_id}, project_id: {project_id}")  # Debug
        print(f"Number of violations: {len(violations)}")  # Debug
        
        chat_key = f"{user_id}_{project_id}"
        if chat_key not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        chat = chat_sessions[chat_key]
        
        # Format violations for Gemini
        violations_text = []
        for v in violations:
            violations_text.append(
                f"File: {v['file']}\n"
                f"Path: {v['path']}\n"
                f"Line: {v['line']}\n"
                f"Rule: {v['misra']}\n"
                f"Message: {v['warning']}\n"
            )
        
        violations_str = "\n".join(violations_text)
        print(f"Formatted violations length: {len(violations_str)}")  # Debug
        
        # Send to Gemini
        print("Sending to Gemini...")  # Debug
        response = send_misra_violations(chat, violations_str)
        print(f"Gemini response received: {response is not None}")  # Debug
        
        # Check if response is None (blocked by safety filters)
        if response is None:
            raise HTTPException(
                status_code=422, 
                detail="Response was blocked by safety filters. Please try with different content or contact support."
            )
        
        # Extract code snippets
        print("Extracting snippets...")  # Debug
        code_snippets = extract_snippets_from_response(response)
        print(f"Extracted {len(code_snippets)} snippets")  # Debug
        
        # Save snippets to user session
        session_data = db.get_user_session(user_id, project_id)
        if session_data:
            print("Saving snippets to user session...")  # Debug
            session_data['fixed_snippets'] = code_snippets
            snippet_file = os.path.join(UPLOAD_FOLDER, f"{user_id}_{project_id}_snippets.json")
            save_snippets_to_json(code_snippets, snippet_file)
            session_data['snippet_file'] = snippet_file
            db.save_user_session(user_id, project_id, session_data)
            db.save_user_file(user_id, project_id, "snippet_file", snippet_file)
            print(f"Snippets saved to: {snippet_file}")  # Debug
            
            # Create temporary fixed files for immediate diff view
            try:
                numbered_file = session_data.get('numbered_file')
                if numbered_file:
                    temp_fixed_numbered_path, temp_fixed_denumbered_path = create_temp_fixed_denumbered_file(
                        numbered_file, code_snippets, f"{user_id}_{project_id}", UPLOAD_FOLDER
                    )
                    session_data['temp_fixed_numbered'] = temp_fixed_numbered_path
                    session_data['temp_fixed_denumbered'] = temp_fixed_denumbered_path
                    db.save_user_session(user_id, project_id, session_data)
                    print(f"Created temporary fixed files for user {user_id}, project {project_id}")
            except Exception as e:
                print(f"Error creating temporary fixed files: {str(e)}")
        
        return FixViolationsResponse(
            response=response,
            codeSnippets=[{"code": snippet} for snippet in code_snippets.values()]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Add detailed error logging
        print(f"Error in gemini_fix_violations: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/api/process/apply-fixes", response_model=ApplyFixesResponse)
async def process_apply_fixes(request: ApplyFixesRequest):
    try:
        project_id = request.projectId
        user_id = request.userId
        
        session_data = db.get_user_session(user_id, project_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        numbered_file = session_data['numbered_file']
        fixed_snippets = session_data.get('fixed_snippets', {})
        
        # Apply fixes with user context
        fixed_filename = f"fixed_{session_data['original_filename']}"
        fixed_numbered_path = os.path.join(UPLOAD_FOLDER, f"{user_id}_{project_id}_fixed_numbered_{session_data['original_filename']}")
        
        merge_fixed_snippets_into_file(numbered_file, fixed_snippets, fixed_numbered_path)
        
        # Remove line numbers for final file
        final_fixed_path = os.path.join(UPLOAD_FOLDER, f"{user_id}_{project_id}_{fixed_filename}")
        remove_line_numbers(fixed_numbered_path, final_fixed_path)
        
        # Update session
        session_data['fixed_file'] = final_fixed_path
        db.save_user_session(user_id, project_id, session_data)
        db.save_user_file(user_id, project_id, "fixed_file", final_fixed_path)
        
        return ApplyFixesResponse(fixedFilePath=final_fixed_path)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/fixed-file")
async def download_fixed_file(projectId: str = Query(...), userId: str = Query("default")):
    try:
        session_data = db.get_user_session(userId, projectId)
        if not session_data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        fixed_file = session_data.get('fixed_file')
        
        if not fixed_file or not os.path.exists(fixed_file):
            raise HTTPException(status_code=404, detail="Fixed file not found")
        
        return FileResponse(
            path=fixed_file,
            filename=f"fixed_{session_data['original_filename']}",
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        message = request.message
        project_id = request.projectId
        user_id = request.userId
        
        chat_key = f"{user_id}_{project_id}"
        if chat_key not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        chat_session = chat_sessions[chat_key]
        
        # Send message to Gemini
        response = chat_session.send_message(message)
        
        # Check if response is None or blocked
        if response is None or response.text is None:
            raise HTTPException(
                status_code=422, 
                detail="Response was blocked by safety filters. Please try rephrasing your message."
            )
        
        # Extract code snippets from response and save to user session
        session_data = db.get_user_session(user_id, project_id)
        if session_data:
            print("Extracting snippets from chat response...")  # Debug
            code_snippets = extract_snippets_from_response(response.text)
            print(f"Extracted {len(code_snippets)} snippets from chat")  # Debug
            
            # Save snippets to user session (same as fix-violations endpoint)
            session_data['fixed_snippets'] = code_snippets
            snippet_file = os.path.join(UPLOAD_FOLDER, f"{user_id}_{project_id}_snippets.json")
            save_snippets_to_json(code_snippets, snippet_file)
            session_data['snippet_file'] = snippet_file
            db.save_user_session(user_id, project_id, session_data)
            print(f"Chat snippets saved to: {snippet_file}")  # Debug
            
            # Update temporary fixed file for real-time diff view
            try:
                numbered_file = session_data.get('numbered_file')
                if numbered_file:
                    temp_fixed_numbered_path, temp_fixed_denumbered_path = create_temp_fixed_denumbered_file(
                        numbered_file, code_snippets, f"{user_id}_{project_id}", UPLOAD_FOLDER
                    )
                    session_data['temp_fixed_numbered'] = temp_fixed_numbered_path
                    session_data['temp_fixed_denumbered'] = temp_fixed_denumbered_path
                    db.save_user_session(user_id, project_id, session_data)
                    print(f"Updated temporary fixed files for user {user_id}, project {project_id}")
            except Exception as e:
                print(f"Error updating temporary fixed files: {str(e)}")
        
        return ChatResponse(response=response.text)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session-state")
async def get_session_state():
    # Return empty state for now
    return {}

@app.post("/api/session-state")
async def save_session_state():
    # For now, just return success
    return {"success": True}

# New diff endpoints for Fix View Modal
@app.get("/api/files/numbered/{project_id}")
async def get_numbered_file(project_id: str, userId: str = Query("default")):
    """Get numbered file content"""
    try:
        session_data = db.get_user_session(userId, project_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        numbered_file = session_data.get('numbered_file')
        
        if not numbered_file or not os.path.exists(numbered_file):
            raise HTTPException(status_code=404, detail="Numbered file not found")
        
        content = get_file_content(numbered_file)
        if content is None:
            raise HTTPException(status_code=500, detail="Failed to read numbered file")
        
        return content
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/temp-fixed/{project_id}")
async def get_temp_fixed_file(project_id: str, userId: str = Query("default")):
    """Get temporary fixed file content"""
    try:
        session_data = db.get_user_session(userId, project_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get existing temp fixed file path if it exists
        temp_fixed_numbered_path = session_data.get('temp_fixed_numbered')
        
        if not temp_fixed_numbered_path or not os.path.exists(temp_fixed_numbered_path):
            # If temp file doesn't exist, create it
            fixed_snippets = session_data.get('fixed_snippets', {})
            numbered_file = session_data.get('numbered_file')
            
            if not numbered_file:
                raise HTTPException(status_code=404, detail="Numbered file not found")
            
            temp_fixed_numbered_path, temp_fixed_denumbered_path = create_temp_fixed_denumbered_file(
                numbered_file, fixed_snippets, f"{userId}_{project_id}", UPLOAD_FOLDER
            )
            
            # Store paths in session
            session_data['temp_fixed_numbered'] = temp_fixed_numbered_path
            session_data['temp_fixed_denumbered'] = temp_fixed_denumbered_path
            db.save_user_session(userId, project_id, session_data)
        
        # Return the fixed numbered content (with line numbers for diff view)
        content = get_file_content(temp_fixed_numbered_path)
        if content is None:
            raise HTTPException(status_code=500, detail="Failed to read temporary fixed file")
        
        return content
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/diff/{project_id}", response_model=DiffResponse)
async def get_diff(project_id: str, userId: str = Query("default")):
    """Get diff between original and fixed files"""
    try:
        session_data = db.get_user_session(userId, project_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        original_file = session_data.get('cpp_file')  # Original file
        fixed_snippets = session_data.get('fixed_snippets', {})
        numbered_file = session_data.get('numbered_file')
        
        if not original_file or not numbered_file:
            raise HTTPException(status_code=404, detail="Required files not found")
        
        # Create temporary fixed denumbered file for comparison with original
        temp_fixed_numbered_path, temp_fixed_denumbered_path = create_temp_fixed_denumbered_file(
            numbered_file, fixed_snippets, f"{userId}_{project_id}", UPLOAD_FOLDER
        )
        
        # Create diff data comparing original with fixed denumbered file
        diff_data = create_diff_data(original_file, temp_fixed_denumbered_path, fixed_snippets)
        
        # Store temp paths in session for potential cleanup
        session_data['temp_fixed_numbered'] = temp_fixed_numbered_path
        session_data['temp_fixed_denumbered'] = temp_fixed_denumbered_path
        db.save_user_session(userId, project_id, session_data)
        
        return DiffResponse(**diff_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Root endpoint
@app.get("/")
async def root():
    return {"message": "MISRA Fix Copilot API Server is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)