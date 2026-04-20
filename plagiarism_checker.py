import os
import re
from difflib import SequenceMatcher
from werkzeug.utils import secure_filename
import PyPDF2
import docx
from zipfile import ZipFile
import tempfile

def extract_text_from_file(file_path, file_type):
    """Extract text from various file formats"""
    text_content = ""
    
    try:
        if file_type == 'txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read()
        
        elif file_type == 'pdf':
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text_content += page.extract_text()
        
        elif file_type in ['doc', 'docx']:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        
        elif file_type in ['py', 'java', 'cpp', 'c', 'js', 'html', 'css']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read()
        
        elif file_type == 'zip':
            with tempfile.TemporaryDirectory() as tmpdir:
                with ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                    for root, dirs, files in os.walk(tmpdir):
                        for file in files:
                            if file.endswith(('.txt', '.py', '.java', '.cpp', '.c', '.js', '.html', '.css')):
                                try:
                                    with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                                        text_content += f.read() + "\n"
                                except:
                                    pass
        
        # Clean the text
        text_content = re.sub(r'\s+', ' ', text_content)
        text_content = text_content.strip()
        
    except Exception as e:
        print(f"Error extracting text from {file_type}: {e}")
        text_content = ""
    
    return text_content

def calculate_similarity(text1, text2):
    """Calculate similarity between two texts"""
    if not text1 or not text2:
        return 0
    
    # Use SequenceMatcher for detailed comparison
    similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio() * 100
    return similarity

def check_plagiarism(submission_content, submission_file_path, file_type, assignment_id, db, Submission, current_user_id):
    """Comprehensive plagiarism check against all existing submissions"""
    
    # Extract text from current submission
    current_text = submission_content if submission_content else ""
    
    if submission_file_path and file_type:
        file_text = extract_text_from_file(submission_file_path, file_type)
        current_text += " " + file_text
    
    if not current_text:
        return 0, []
    
    # Get all other submissions for this assignment
    all_submissions = Submission.query.filter(
        Submission.assignment_id == assignment_id,
        Submission.id != None,  # All submissions
        Submission.is_draft == False  # Only final submissions
    ).all()
    
    plagiarism_results = []
    highest_score = 0
    
    for sub in all_submissions:
        # Skip comparing with self if it's an existing submission
        if hasattr(sub, 'student_id') and sub.student_id == current_user_id:
            # Check if this is a resubmission (existing submission)
            continue
        
        other_text = sub.content if sub.content else ""
        
        # Extract text from other submission's file if exists
        if sub.file_path and sub.file_type:
            # Note: In production, you'd want to store extracted text or re-extract
            # For performance, consider storing extracted text in a separate column
            other_file_text = extract_text_from_file(sub.file_path, sub.file_type)
            other_text += " " + other_file_text
        
        if other_text:
            similarity = calculate_similarity(current_text, other_text)
            
            if similarity > 0:
                plagiarism_results.append({
                    'student_name': sub.student.name if hasattr(sub, 'student') else 'Unknown',
                    'student_id': sub.student.matric if hasattr(sub, 'student') else 'Unknown',
                    'similarity': round(similarity, 1),
                    'submission_id': sub.id
                })
                
                if similarity > highest_score:
                    highest_score = similarity
    
    # Sort by similarity (highest first)
    plagiarism_results.sort(key=lambda x: x['similarity'], reverse=True)
    
    return highest_score, plagiarism_results[:10]  # Return top 10 matches