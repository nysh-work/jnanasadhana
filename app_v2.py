import streamlit as st
import streamlit.components.v1 as components
from google.generativeai.generative_models import GenerativeModel
from google.generativeai.client import configure
import os
import PyPDF2
import io
import pyperclip
import json
import hashlib
from datetime import datetime, timedelta
import base64  # Add this for image handling
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from PIL import Image  # Add this for image processing
from dotenv import load_dotenv
import re  # Add regex support for parsing options
import time  # Import for timer functionality
import random  # Add random module for generating focus tips
import shutil
import tempfile
from Crypto.Cipher import AES  # Import PyCryptodome for PDF decryption

# Load environment variables
load_dotenv()
# Gemini API Call
def setup_google_api():
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        st.error("Google API key not found. Please set it as an environment variable.")
        return None
    configure(api_key=GEMINI_API_KEY)
    return GenerativeModel("gemini-2.0-flash-exp-image-generation")
# Extract text from PDF
def extract_text_from_pdf(pdf_file):
    """
    Extract text from a PDF file with improved error handling and fallback methods.
    
    Args:
        pdf_file: The uploaded PDF file object
        
    Returns:
        str: Extracted text from the PDF or error message
    """
    try:
        # Create a BytesIO object to handle the file buffer
        pdf_bytes = io.BytesIO(pdf_file.getvalue())
        
        # First attempt: Use PyPDF2
        try:
            reader = PyPDF2.PdfReader(pdf_bytes)
            
            # Check if PDF is encrypted
            if reader.is_encrypted:
                return "The PDF file is encrypted and cannot be processed. Please upload an unencrypted PDF."
            
            # Try to extract text from first page to catch encryption/permissions issues
            try:
                if len(reader.pages) > 0:
                    first_page = reader.pages[0]
                    first_page_text = first_page.extract_text()
                    if first_page_text is None:
                        # Some encrypted PDFs don't set is_encrypted but still fail on extraction
                        return "The PDF file appears to be encrypted or has restricted permissions. Please upload an unencrypted PDF."
            except Exception as page_e:
                if "decrypt" in str(page_e).lower() or "password" in str(page_e).lower() or "encrypt" in str(page_e).lower():
                    return "The PDF file is encrypted and cannot be processed. Please upload an unencrypted PDF."
            
            # Add progress bar for large documents
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            text_parts = []
            total_pages = len(reader.pages)
            
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    st.warning(f"Warning: Could not extract text from page {i+1}: {str(e)}")
                    continue
                
                # Update progress
                progress = (i + 1) / total_pages
                progress_bar.progress(progress)
                status_text.text(f"Extracting page {i+1}/{total_pages}")
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Clean up the text
            text = "\n\n".join(text_parts)
            text = text.strip()
            
            # Check if text extraction was successful
            if not text:
                st.error(f"No text could be extracted from {pdf_file.name}. The PDF might be scanned or contain only images.")
                return ""
            
            return text
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")
            return ""
    except Exception as e:
        st.error(f"Error processing file {pdf_file.name}: {str(e)}")
        return ""
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass

def extract_text_from_pdf_robust(pdf_file):
    """
    A more robust version of extract_text_from_pdf that tries multiple methods.
    This is especially useful for cloud environments where different methods might work.
    
    Args:
        pdf_file: The uploaded PDF file object
        
    Returns:
        str: Extracted text from the PDF or error message
    """
    # Store original file position
    original_position = pdf_file.tell()
    
    # Create progress indicators
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Method 1: Direct BytesIO approach
    try:
        status_text.text("Extracting text (Method 1)...")
        pdf_file.seek(0)
        pdf_bytes = io.BytesIO(pdf_file.read())
        
        reader = PyPDF2.PdfReader(pdf_bytes)
        if reader.is_encrypted:
            progress_bar.empty()
            status_text.empty()
            return "The PDF file is encrypted and cannot be processed. Please upload an unencrypted PDF."
        
        text_parts = []
        total_pages = len(reader.pages)
        
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(page_text)
            except Exception:
                # Skip pages that can't be processed
                continue
            
            # Update progress
            progress = (i + 1) / (total_pages * 2)  # Split progress between methods
            progress_bar.progress(progress)
            status_text.text(f"Method 1: Page {i+1}/{total_pages}")
        
        combined_text_1 = "\n\n".join(text_parts)
        if combined_text_1 and len(combined_text_1.strip()) > 100:
            # First method worked well enough
            progress_bar.empty()
            status_text.empty()
            return combined_text_1
    
    except Exception as e:
        # Log the error but continue to try other methods
        print(f"Method 1 failed: {str(e)}")
    
    # Method 2: Temporary file approach
    try:
        status_text.text("Extracting text (Method 2)...")
        pdf_file.seek(0)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(pdf_file.read())
            temp_file_path = temp_file.name
        
        text_parts = []
        with open(temp_file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            if reader.is_encrypted:
                os.unlink(temp_file_path)
                progress_bar.empty()
                status_text.empty()
                return "The PDF file is encrypted and cannot be processed. Please upload an unencrypted PDF."
            
            total_pages = len(reader.pages)
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_parts.append(page_text)
                except Exception:
                    # Skip pages that can't be processed
                    continue
                
                # Update progress
                progress = 0.5 + (i + 1) / (total_pages * 2)  # Second half of progress
                progress_bar.progress(progress)
                status_text.text(f"Method 2: Page {i+1}/{total_pages}")
        
        # Clean up
        os.unlink(temp_file_path)
        
        combined_text_2 = "\n\n".join(text_parts)
        if combined_text_2 and len(combined_text_2.strip()) > 100:
            # Second method worked well enough
            progress_bar.empty()
            status_text.empty()
            return combined_text_2
    
    except Exception as e:
        # Log the error but continue
        print(f"Method 2 failed: {str(e)}")
        try:
            os.unlink(temp_file_path)
        except:
            pass
    
    # If we got here, both methods failed or produced insufficient text
    progress_bar.empty()
    status_text.empty()
    
    # Restore original file position
    pdf_file.seek(original_position)
    
    # Try the original method as a last resort
    result = extract_text_from_pdf(pdf_file)
    
    if result and len(result.strip()) > 100:
        return result
    else:
        return "Could not extract sufficient text from this PDF. It may be encrypted, scanned, or contain only images."

def extract_text_from_pdf_with_crypto(pdf_file, password=None):
    """
    Extract text from a PDF file with PyCryptodome support for encrypted PDFs.
    
    Args:
        pdf_file: The uploaded PDF file object
        password: Optional password to try unlocking the PDF
        
    Returns:
        str: Extracted text from the PDF or error message
    """
    # Create progress indicators
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Reset file pointer
        pdf_file.seek(0)
        
        # Create BytesIO object
        pdf_bytes = io.BytesIO(pdf_file.getvalue())
        
        # Create PDF reader
        reader = PyPDF2.PdfReader(pdf_bytes)
        
        # Check if PDF is encrypted
        if reader.is_encrypted:
            if not password:
                # Try with empty password
                try:
                    reader.decrypt('')
                except:
                    # If decryption fails, return error
                    progress_bar.empty()
                    status_text.empty()
                    return "The PDF file is encrypted and requires a password. Please upload an unencrypted version."
            else:
                # Try with provided password
                try:
                    reader.decrypt(password)
                except:
                    progress_bar.empty()
                    status_text.empty()
                    return "The provided password could not decrypt the PDF. Please try with the correct password."
        
        # Extract text from each page
        text_parts = []
        total_pages = len(reader.pages)
        
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(page_text)
            except Exception as e:
                # Skip problematic pages
                print(f"Error extracting page {i+1}: {str(e)}")
                continue
            
            # Update progress
            progress = (i + 1) / total_pages
            progress_bar.progress(progress)
            status_text.text(f"Extracting page {i+1}/{total_pages}")
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Check if we got any text
        if text_parts:
            combined_text = "\n\n".join(text_parts)
            return combined_text
        else:
            return "Could not extract text from the PDF. The document might be scanned or contain only images."
    
    except Exception as e:
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Check for common errors
        error_msg = str(e).lower()
        if "not decrypt" in error_msg or "password" in error_msg or "encrypt" in error_msg:
            return "The PDF file is encrypted and cannot be processed. Please upload an unencrypted PDF."
        else:
            return f"Error processing PDF: {str(e)}. Please try a different file."
# Extract model questions from PDF
def extract_model_questions(pdf_file):
    """Extract model questions from a PDF file to use as examples for AI."""
    try:
        # Create a BytesIO object to handle the file buffer
        pdf_bytes = io.BytesIO(pdf_file.read())
        
        reader = PyPDF2.PdfReader(pdf_bytes)
        total_pages = len(reader.pages)
        
        # Add progress bar for large documents
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
            
            # Update progress
            progress = (i + 1) / total_pages
            progress_bar.progress(progress)
            status_text.text(f"Extracting page {i+1}/{total_pages}")
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        model_questions = "\n".join(text_parts)
        
        # Handle empty PDFs
        if not model_questions.strip():
            return "The PDF appears to be empty or contains non-extractable text."
        return model_questions
    except Exception as e:
        if "password" in str(e).lower() or "decrypt" in str(e).lower():
            st.error("Error: The file appears to be corrupted or password protected.")
        else:
            st.error(f"Error extracting model questions from PDF: {str(e)}")
        return ""
# Generate questions
def generate_questions(summary, question_type, num_questions=10, include_answers=False, model_questions=None):
    model = setup_google_api()
    if not model:
        return ["API configuration failed."]
    
    # Truncate summary if too long for API limits
    max_chars = 30000  # Adjust based on Gemini's token limits
    truncated_summary = summary[:max_chars] if len(summary) > max_chars else summary
    try:
        if question_type == "Mixed":
            # For mixed type, distribute questions evenly among types
            types = ["MCQ", "Short Answer", "Case Based Application", "Numerical Calculation"]
            base_count = num_questions // len(types)
            remainder = num_questions % len(types)
            
            # Distribute questions
            type_counts = {t: base_count for t in types}
            for i in range(remainder):
                type_counts[types[i]] += 1
            
            # Generate questions for each type
            all_questions = []
            for qtype, count in type_counts.items():
                if count > 0:
                    prompt = f"""Generate {count} professionally formatted {qtype} questions based on the following text.
                    
                    Text to analyze:
                    {truncated_summary}
                    
                    Instructions for question creation:
                    1. Create challenging but fair questions that test understanding of key concepts.
                    2. Use clear, concise language and proper formatting.
                    3. Each question should be self-contained and complete.
                    4. Questions should directly relate to the content in the provided text.
                    {"5. For Numerical Calculation questions: ONLY generate these if the content contains numerical data, formulas, or calculations that can be used to create meaningful problems. If the content doesn't support numerical questions, return a message stating 'Cannot generate numerical calculation questions from this content' instead of creating artificial questions." if qtype == "Numerical Calculation" else ""}
                    
                    Format requirements:
                    • Start each question with [{qtype}] on its own line
                    • For MCQ questions:
                      - Begin with "Question: [question text]"
                      - Then "Options:" on a new line
                      - List 4 options as "A) [option text]", "B) [option text]", etc.
                      - Each option on a new line
                      - If answers are included, add "Answer:" section with the correct answer and explanation
                      - Include "Correct Answer: [A/B/C/D]" at the end of the answer section
                    
                    • For Short Answer questions:
                      - Begin with "Question: [question text]"
                      - If answers are included, add "Answer:" section with a detailed model answer
                    
                    • For Case Based Application:
                      - Begin with "Case Scenario: [detailed scenario description]"
                      - Then "Question: [specific questions about the scenario]"
                      - If answers are included, add "Answer:" section with detailed analysis
                    
                    • For Numerical Calculation:
                      - Begin with "Question: [problem statement]"
                      - Include all necessary information for calculation
                      - If answers are included, add "Answer:" section with step-by-step solution
                    
                    {"• Include answers for all questions by adding an 'Answer:' section with detailed explanations." if include_answers else "• Do NOT include answers for any questions."}
                    
                    Example format for MCQ:
                    [MCQ]
                    Question: What is the primary function of X?
                    Options:
                    A) Function 1
                    B) Function 2
                    C) Function 3
                    D) Function 4
                    {"Answer: The primary function of X is Function 2. This is because... [detailed explanation]\nCorrect Answer: B" if include_answers else ""}
                    
                    Example format for Short Answer:
                    [Short Answer]
                    Question: Explain the concept of X and its importance.
                    {"Answer: X is defined as... [detailed explanation]" if include_answers else ""}
                    
                    Do NOT include any introductory text, explanations, or commentary - return ONLY the formatted questions {"with answers" if include_answers else "without answers"}.
                    """
                    
                    response = model.generate_content(prompt)
                    if response:
                        questions_text = response.text.strip()
                        
                        # Split into individual questions - more robust parsing
                        questions = []
                        current_q = ""
                        
                        for line in questions_text.split('\n'):
                            line_stripped = line.strip()
                            # Check if this is the start of a new question
                            if line_stripped.startswith(f"[{qtype}]"):
                                if current_q:  # Save previous question if exists
                                    questions.append(current_q.strip())
                                current_q = line  # Start new question
                            else:
                                # Add to current question
                                current_q += "\n" + line if current_q else line
                        
                        # Don't forget the last question
                        if current_q:
                            questions.append(current_q.strip())
                        
                        all_questions.extend(questions)
            
            return all_questions if all_questions else ["No questions were generated. Please try again."]
            
        else:
            # Original handling for specific question types with improved formatting
            prompt_template = f"""Generate {num_questions} professionally formatted {question_type} questions based on the following text.
            
            Text to analyze:
            {truncated_summary}
            
            Instructions for question creation:
            1. Create challenging but fair questions that test understanding of key concepts.
            2. Use clear, concise language and proper formatting.
            3. Each question should be self-contained and complete.
            4. Questions should directly relate to the content in the provided text.
            {"5. For Numerical Calculation questions: ONLY generate these if the content contains numerical data, formulas, or calculations that can be used to create meaningful problems. If the content doesn't support numerical questions, return a message stating 'Cannot generate numerical calculation questions from this content' instead of creating artificial questions." if question_type == "Numerical Calculation" else ""}
            
            Format requirements:
            • Start each question with [{question_type}] on its own line
            • For MCQ questions:
              - Begin with "Question: [question text]"
              - Then "Options:" on a new line
              - List 4 options as "A) [option text]", "B) [option text]", etc.
              - Each option on a new line
              - If answers are included, add "Answer:" section with the correct answer and explanation
              - Include "Correct Answer: [A/B/C/D]" at the end of the answer section
            
            • For Short Answer questions:
              - Begin with "Question: [question text]"
              - If answers are included, add "Answer:" section with a detailed model answer
            
            • For Case Based Application:
              - Begin with "Case Scenario: [detailed scenario description]"
              - Then "Question: [specific questions about the scenario]"
              - If answers are included, add "Answer:" section with detailed analysis
            
            • For Numerical Calculation:
              - Begin with "Question: [problem statement]"
              - Include all necessary information for calculation
              - If answers are included, add "Answer:" section with step-by-step solution
            
            {"• Include answers for all questions by adding an 'Answer:' section with detailed explanations." if include_answers else "• Do NOT include answers for any questions."}
            
            {"Please also reference the following example questions as a style guide:\n" + model_questions if model_questions else ""}
            
            Do NOT include any introductory text, explanations, or commentary - return ONLY the formatted questions {"with answers" if include_answers else "without answers"}.
            """
            
            response = model.generate_content(prompt_template)
            
            # Process the response to ensure clean formatting
            if response:
                questions_text = response.text.strip()
                
                # Split into individual questions - more robust parsing
                questions = []
                current_q = ""
                
                for line in questions_text.split('\n'):
                    line_stripped = line.strip()
                    # Check if this is the start of a new question
                    if line_stripped.startswith(f"[{question_type}]"):
                        if current_q:  # Save previous question if exists
                            questions.append(current_q.strip())
                        current_q = line  # Start new question
                    else:
                        # Add to current question
                        current_q += "\n" + line if current_q else line
                
                # Don't forget the last question
                if current_q:
                    questions.append(current_q.strip())
                
                return questions if questions else ["No questions were generated. Please try again."]
            else:
                return ["No response from API."]
    except Exception as e:
        return [f"Error generating questions: {str(e)}"]
# Evaluate answer
def evaluate_answer(question, user_answer):
    model = setup_google_api()
    if not model:
        return "API configuration failed."
    try:
        prompt = f"""Evaluate the following answer and provide feedback *strictly* in the specified Markdown-like format. Do NOT include any introductory or concluding sentences, conversational elements, or formatting beyond what is specified.

        Question: {question}
        User Answer: {user_answer}

        ---
        **Feedback:**
        **Correctness:** [Correct/Partially Correct/Incorrect]
        **Explanation:** [Concise feedback on the accuracy of the answer. Focus on *major* errors or omissions. Keep this under 50 words.]
        **Ideal Answer:** [A concise, correct answer that addresses all key aspects of the question. Keep this under 75 words.]
        **Improvement Tips:**
        - Score the answer on a scale of 10 and provide reasons for the score.
        - [Specific suggestion 1]
        - [Specific suggestion 2]
        - [Specific suggestion 3 - Limit to a maximum of 3 suggestions]
        ---
        """

        response = model.generate_content(prompt)
        return response.text if response else "No response from API."
    except Exception as e:
        return f"Error evaluating answer: {str(e)}"
# Generate notes
def generate_notes(summary, note_type="cornell"):
    model = setup_google_api()
    if not model:
        return "API configuration failed."
    
    # Truncate summary if too long for API limits
    max_chars = 30000  # Adjust based on Gemini's token limits
    truncated_summary = summary[:max_chars] if len(summary) > max_chars else summary
    
    try:
        if note_type == "cornell":
            prompt = f"""Generate Cornell Notes from the following summary, strictly adhering to the Markdown-like format below. Do NOT include any introductory or concluding sentences, conversational elements, or formatting beyond what is specified. Ignore the learning outcome section of the notes included.
            Summary Text:
            {truncated_summary}
            
            ---
            ## Cornell Notes
            **Key Questions:** (Generate questions that a reader should be able to answer after reviewing these notes. Ensure these are clear, concise, and directly related to the content and all concepts are covered.)
            [Insert Key Questions Here - One question per line, serially number the questions]

            ---
            | Main Ideas/Key Points | Notes and Details |
            | :-------------------- | :---------------- |
            | [Insert Key Point 1]  | [Insert Detailed Notes for Key Point 1] |
            | [Insert Key Point 2]  | [Insert Detailed Notes for Key Point 2] |
            | ...                   | ...                   |

            ---
            **Summary:** (Provide a summary of the most crucial information from the notes above.)
            [Insert Concise Summary Here in the next line]

            ---
            """

        elif note_type == "concept_map":
            prompt = f"""Create a concept map in text format from the following summary, strictly adhering to the Markdown-like format below. Do NOT include any introductory or concluding sentences, conversational elements, or formatting beyond what is specified.
            Summary Text:
            {truncated_summary}
            
            ---
            # Concept Map Notes
            
            ## Central Concept: [Main Topic]
            
            ### Related Concept 1: [Topic 1]
            - **Connection to Central Concept**: [Explain relationship]
            - **Key Attributes**:
              - [Attribute 1.1]
              - [Attribute 1.2]
            - **Examples**:
              - [Example 1.1]
              - [Example 1.2]
            
            ### Related Concept 2: [Topic 2]
            - **Connection to Central Concept**: [Explain relationship]
            - **Key Attributes**:
              - [Attribute 2.1]
              - [Attribute 2.2]
            - **Examples**:
              - [Example 2.1]
              - [Example 2.2]
            
            ### Connection between [Topic 1] and [Topic 2]:
            - [Explain how these concepts relate to each other]
            
            [Continue with additional related concepts and connections as needed]
            
            ---
            """
        
        response = model.generate_content(prompt)
        return response.text if response else "No response from API."
    except Exception as e:
        return f"Error generating notes: {str(e)}"
# Copy to clipboard
def copy_to_clipboard(text):
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        st.error(f"Error copying to clipboard: {str(e)}")
        return False
# Export study materials
def export_study_materials():
    """Create exportable file with all study materials."""
    if not st.session_state.get("summary", ""):
        st.warning("No content available to export.")
        return None
    
    try:
        # Compile all materials
        export_content = "# AI-Powered Study Materials\n\n"
        export_content += f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        
        # Add original text summary
        export_content += "## Original Document Summary\n\n"
        export_content += st.session_state.get("summary", "No summary available.")
        export_content += "\n\n---\n\n"
        
        # Add Cornell Notes if available
        if st.session_state.get("notes", ""):
            export_content += "# Cornell Notes\n\n"
            export_content += st.session_state.get("notes", "")
            export_content += "\n\n---\n\n"
        
        # Add questions and answers if available
        if st.session_state.get("questions", []):
            export_content += "# Practice Questions and Answers\n\n"
            
            for i, question in enumerate(st.session_state.get("questions", [])):
                export_content += f"## Question {i+1}\n"
                export_content += f"{question.strip()}\n\n"
                
                # Add user's answer if available
                answer_key = f"answer_for_q{i}"
                if answer_key in st.session_state and st.session_state[answer_key]:
                    export_content += "### Your Answer:\n"
                    export_content += f"{st.session_state[answer_key]}\n\n"
                
                # Add evaluation if available
                eval_key = f"eval_{i}"
                if eval_key in st.session_state and st.session_state[eval_key]:
                    export_content += "### Feedback:\n"
                    export_content += f"{st.session_state[eval_key]}\n\n"
                
                export_content += "---\n\n"
        
        # Add flashcards if available
        if st.session_state.get("flashcards", []):
            export_content += "# Flashcards\n\n"
            
            for i, card in enumerate(st.session_state.flashcards):
                export_content += f"## Card {i+1}\n"
                export_content += f"**Front:** {card['front']}\n\n"
                export_content += f"**Back:** {card['back']}\n\n"
                export_content += "---\n\n"
        
        # Add mind map if available
        if st.session_state.get("mind_map"):
            export_content += "# Mind Map\n\n"
            export_content += f"## Central Topic: {st.session_state.mind_map['central_topic']}\n\n"
            
            for branch in st.session_state.mind_map['branches']:
                export_content += f"### {branch['topic']}\n"
                for subtopic in branch['subtopics']:
                    export_content += f"- {subtopic}\n"
                export_content += "\n"
            
            export_content += "---\n\n"
        
        # Add interactive quiz if available
        if st.session_state.get("quiz_data", []):
            export_content += "# Interactive Quiz\n\n"
            
            for i, question in enumerate(st.session_state.get("quiz_data", [])):
                export_content += f"## Quiz Question {i+1}\n"
                export_content += f"**Question:** {question['question']}\n\n"
                
                if question["question_type"] == "multiple_choice":
                    export_content += "**Type:** Multiple Choice\n\n"
                    export_content += "**Options:**\n"
                    for option in question["options"]:
                        if option == question["correct_answer"]:
                            export_content += f"- {option} ✓\n"
                        else:
                            export_content += f"- {option}\n"
                elif question["question_type"] == "true_false":
                    export_content += "**Type:** True/False\n\n"
                    export_content += f"**Correct Answer:** {question['correct_answer']}\n"
                elif question["question_type"] == "short_answer":
                    export_content += "**Type:** Short Answer\n\n"
                    export_content += f"**Correct Answer:** {question['correct_answer']}\n"
                    export_content += "**Keywords:** " + ", ".join(question.get("keywords", [])) + "\n"
                
                export_content += f"\n**Explanation:** {question['explanation']}\n\n"
                
                # Add user's answer if available
                if "quiz_answers" in st.session_state and len(st.session_state.quiz_answers) > i:
                    answer_data = st.session_state.quiz_answers[i]
                    export_content += f"**Your Answer:** {answer_data['user_answer']}\n"
                    export_content += f"**Result:** {'Correct' if answer_data['correct'] else 'Incorrect'}\n\n"
                
                export_content += "---\n\n"
        
        # Create a BytesIO object to store the file
        export_file = io.BytesIO()
        export_file.write(export_content.encode('utf-8'))
        export_file.seek(0)
        
        return export_file
    except Exception as e:
        st.error(f"Error exporting study materials: {str(e)}")
        return None
# Format exam paper
def format_exam_paper(questions):
    """Format questions as an exam paper with clean, consistent formatting"""
    # Count question types
    type_counts = {"MCQ": 0, "Short Answer": 0, "Case Based Application": 0, "Numerical Calculation": 0}
    
    # First pass to count question types
    for question in questions:
        for qtype in type_counts.keys():
            if f"[{qtype}]" in question:
                type_counts[qtype] += 1
                break
    
    # Start building the exam paper
    exam_paper = "# Practice Exam Questions\n\n"
    
    # Add distribution summary
    exam_paper += "## Question Distribution\n"
    total_questions = sum(type_counts.values())
    for qtype, count in type_counts.items():
        if count > 0:
            percentage = (count / total_questions) * 100
            exam_paper += f"- **{qtype}**: {count} question{'s' if count > 1 else ''} ({percentage:.1f}%)\n"
    exam_paper += "\n---\n\n"
    
    # Format each question
    for i, question in enumerate(questions, 1):
        # Clean up question formatting and remove unwanted text
        clean_question = question.strip()
        
        # Determine question type
        current_type = None
        for qtype in type_counts.keys():
            if f"[{qtype}]" in clean_question:
                current_type = qtype
                clean_question = clean_question.replace(f"[{current_type}]", "").strip()
                break
        
        if not current_type:
            current_type = "General Question"
        
        # Add question header with clear numbering and type
        exam_paper += f"## Question {i}\n\n"
        exam_paper += f"**Type: {current_type}**\n\n"
        
        # Parse the question - split into parts
        has_answer = "Answer:" in clean_question
        if has_answer:
            question_part, answer_part = clean_question.split("Answer:", 1)
            question_part = question_part.strip()
            answer_part = answer_part.strip()
        else:
            question_part = clean_question
            answer_part = None
        
        # Format the question based on type
        if current_type == "MCQ":
            # Handle MCQ questions
            if "Options:" in question_part:
                # Split into main question and options
                main_q, options_text = question_part.split("Options:", 1)
                
                # Format the question text
                if main_q.startswith("Question:"):
                    main_q = main_q.replace("Question:", "", 1).strip()
                exam_paper += f"**Question:** {main_q.strip()}\n\n"
                
                # Format options with proper spacing and formatting
                exam_paper += "**Options:**\n\n"
                
                # Check if options are all on one line
                options_text = options_text.strip()
                if " B)" in options_text and not options_text.startswith("B)"):
                    # Options are probably on a single line, let's split them
                    option_matches = re.findall(r'([A-D]\).*?)(?=[A-D]\)|$)', options_text, re.DOTALL)
                    for opt in option_matches:
                        exam_paper += f"{opt.strip()}\n"
                else:
                    # Options are already separated by lines
                    options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
                    for option in options:
                        if option.startswith(('A)', 'B)', 'C)', 'D)')):
                            exam_paper += f"{option}\n"
                
                exam_paper += "\n"
            else:
                # If no "Options:" keyword found, just use the question text as is
                if question_part.startswith("Question:"):
                    question_part = question_part.replace("Question:", "", 1).strip()
                exam_paper += f"**Question:** {question_part}\n\n"
                
        elif current_type == "Case Based Application":
            # Handle Case Based Application questions
            if "Case Scenario:" in question_part and "Question:" in question_part:
                scenario_part, specific_question = question_part.split("Question:", 1)
                scenario_part = scenario_part.replace("Case Scenario:", "", 1).strip()
                
                exam_paper += "**Case Scenario:**\n\n"
                exam_paper += f"{scenario_part}\n\n"
                exam_paper += f"**Question:**\n\n{specific_question.strip()}\n\n"
            elif "Case Scenario:" in question_part:
                scenario_part = question_part.replace("Case Scenario:", "", 1).strip()
                exam_paper += "**Case Scenario:**\n\n"
                exam_paper += f"{scenario_part}\n\n"
            else:
                # Just a regular question without explicit scenario
                if question_part.startswith("Question:"):
                    question_part = question_part.replace("Question:", "", 1).strip()
                exam_paper += f"**Question:** {question_part}\n\n"
                
        elif current_type == "Numerical Calculation":
            # Handle Numerical Calculation questions
            if question_part.startswith("Question:"):
                question_part = question_part.replace("Question:", "", 1).strip()
            exam_paper += f"**Problem:** {question_part}\n\n"
            exam_paper += "*Show all calculations and formulas in your solution.*\n\n"
            
        else:  # Short Answer or any other type
            # Handle Short Answer questions
            if question_part.startswith("Question:"):
                question_part = question_part.replace("Question:", "", 1).strip()
            exam_paper += f"**Question:** {question_part}\n\n"
        
        # Add answer section if available
        if answer_part:
            # Format answer in a collapsible section with improved styling
            exam_paper += "<details>\n"
            exam_paper += "<summary><strong>Model Answer</strong> (Click to expand)</summary>\n\n"
            
            # Format the answer based on question type
            if current_type == "MCQ":
                # Check if there's a "Correct Answer:" section
                if "Correct Answer:" in answer_part:
                    explanation, correct_option = answer_part.split("Correct Answer:", 1)
                    exam_paper += f"**Correct Option:** {correct_option.strip()}\n\n"
                    
                    if explanation.strip():
                        exam_paper += "**Explanation:**\n\n"
                        exam_paper += f"{explanation.strip()}\n\n"
                else:
                    exam_paper += f"{answer_part}\n\n"
                    
            elif current_type == "Numerical Calculation":
                exam_paper += "**Solution:**\n\n"
                exam_paper += f"{answer_part}\n\n"
                
            else:  # Case Based or Short Answer
                exam_paper += f"{answer_part}\n\n"
                
            exam_paper += "</details>\n\n"
        
        # Add clear separation between questions
        exam_paper += "---\n\n"
    
    return exam_paper
# Evaluate handwritten answer
def evaluate_handwritten_answer(question, image_file):
    """Evaluate a handwritten answer from an uploaded image."""
    model = setup_google_api()
    if not model:
        return "API configuration failed."
    
    try:
        # Read the image file
        image_bytes = image_file.getvalue()
        
        # Encode the image as base64 for the API
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create a prompt for the model with the image
        prompt = f"""Analyze the handwritten answer in the image and evaluate it based on the following question:

        Question: {question}

        ---
        **Feedback:**
        **Correctness:** [Correct/Partially Correct/Incorrect]
        **Explanation:** [Concise feedback on the accuracy of the answer. Focus on *major* errors or omissions. Keep this under 50 words.]        **Ideal Answer:** [A concise, correct answer that addresses all key aspects of the question. Keep this under 75 words.]
        **Improvement Tips:**
        - Score the answer on a scale of 10 and provide reasons for the score.
        - [Specific suggestion 1]
        - [Specific suggestion 2]
        - [Specific suggestion 3 - Limit to a maximum of 3 suggestions]
        ---
        """
        
        # Send the prompt and image to the model
        response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_base64}])
        return response.text if response else "No response from API."
    except Exception as e:
        return f"Error evaluating handwritten answer: {str(e)}"
# Generate flashcards
def generate_flashcards(summary):
    """Generate flashcards from the summary text."""
    model = setup_google_api()
    if not model:
        return []
    
    # Truncate summary if too long for API limits
    max_chars = 30000  # Adjust based on Gemini's token limits
    truncated_summary = summary[:max_chars] if len(summary) > max_chars else summary
    
    try:
        prompt = f"""Generate 10-15 flashcards based on the following summary. Each flashcard should have a front (question/term) and back (answer/definition).
        
        Summary Text:
        {truncated_summary}
        
        Format each flashcard as follows:
        
        CARD 1
        Front: [Question or term]
        Back: [Answer or definition]
        
        CARD 2
        Front: [Question or term]
        Back: [Answer or definition]
        
        And so on. Make sure the flashcards cover key concepts, definitions, and important facts from the summary.
        """
        
        response = model.generate_content(prompt)
        
        # Parse the response into flashcards
        flashcards = []
        current_card = {"front": "", "back": ""}
        in_card = False
        
        for line in response.text.split("\n"):
            line = line.strip()
            
            if line.startswith("CARD"):
                # Start a new card
                if current_card["front"] and current_card["back"]:
                    flashcards.append(current_card.copy())
                current_card = {"front": "", "back": ""}
                in_card = True
            elif in_card and line.startswith("Front:"):
                current_card["front"] = line[6:].strip()
            elif in_card and line.startswith("Back:"):
                current_card["back"] = line[5:].strip()
        
        # Add the last card if it exists
        if current_card["front"] and current_card["back"]:
            flashcards.append(current_card.copy())
            
        return flashcards
    except Exception as e:
        st.error(f"Error generating flashcards: {str(e)}")
        return []
# Generate mind map
def generate_mind_map_data(summary):
    """Generate mind map data structure from the summary."""
    model = setup_google_api()
    if not model:
        return None
    
    # Truncate summary if too long for API limits
    max_chars = 30000
    truncated_summary = summary[:max_chars] if len(summary) > max_chars else summary
    
    try:
        prompt = f"""Create a hierarchical mind map structure based on the following text. 
        The mind map should have a central topic and multiple branches with subtopics.
        
        Format the mind map as a JSON structure with the following format:
        {{
            "central_topic": "Main Topic",
            "branches": [
                {{
                    "topic": "Branch 1",
                    "subtopics": ["Subtopic 1.1", "Subtopic 1.2"]
                }},
                {{
                    "topic": "Branch 2",
                    "subtopics": ["Subtopic 2.1", "Subtopic 2.2"]
                }}
            ]
        }}
        
        Text to analyze:
        {truncated_summary}
        
        Only return the JSON structure, nothing else.
        """
        
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        try:
            # Find JSON in the response
            json_text = response.text
            # Clean up any markdown formatting
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
                
            mind_map_data = json.loads(json_text)
            return mind_map_data
        except json.JSONDecodeError as e:
            st.error(f"Error parsing mind map JSON: {str(e)}")
            st.code(response.text)  # Show the raw response for debugging
            return None
            
    except Exception as e:
        st.error(f"Error generating mind map: {str(e)}")
        return None
# Generate mind palace
def generate_mind_palace(summary):
    """Generate a Mind Palace structure from study material using Gemini API."""
    model = setup_google_api()
    if not model:
        return None
    
    # Truncate summary if too long for API limits
    max_chars = 30000
    truncated_summary = summary[:max_chars] if len(summary) > max_chars else summary
    
    try:
        prompt = f"""Create a detailed Mind Palace structure based on the following study material. 
        The Mind Palace should be designed to help memorize and recall the information effectively.
        
        Format the Mind Palace as a JSON structure with the following format:
        {{
            "palace_name": "A descriptive name for the palace",
            "rooms": [
                {{
                    "name": "Room name",
                    "description": "Vivid description of the room's appearance and atmosphere",
                    "memory_anchors": [
                        {{
                            "location": "Specific location in the room",
                            "description": "Detailed description of the location and its appearance",
                            "concept": "The study concept to remember",
                            "details": "Key details about the concept"
                        }}
                    ]
                }}
            ]
        }}
        
        Guidelines for creating the Mind Palace:
        1. Create 3-5 distinct rooms with unique themes
        2. Each room should have 3-5 memory anchors
        3. Use vivid, memorable descriptions
        4. Connect related concepts across rooms
        5. Make locations and associations easy to visualize
        
        Study Material:
        {truncated_summary}
        
        Only return the JSON structure, nothing else.
        """
        
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        try:
            # Find JSON in the response
            json_text = response.text
            # Clean up any markdown formatting
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
                
            mind_palace_data = json.loads(json_text)
            return mind_palace_data
        except json.JSONDecodeError as e:
            st.error(f"Error parsing Mind Palace JSON: {str(e)}")
            st.code(response.text)  # Show the raw response for debugging
            return None
            
    except Exception as e:
        st.error(f"Error generating Mind Palace: {str(e)}")
        return None
# Generate interactive quiz
def generate_interactive_quiz(summary, num_questions=5, difficulty="medium"):
    """Generate an interactive quiz with various question types."""
    model = setup_google_api()
    if not model:
        return None
    
    # Truncate summary if too long for API limits
    max_chars = 30000
    truncated_summary = summary[:max_chars] if len(summary) > max_chars else summary
    
    try:
        prompt = f"""Create an interactive quiz with {num_questions} questions at {difficulty} difficulty level based on this content:
        
        {truncated_summary}
        
        Generate a mix of question types:
        - Multiple choice (4 options)
        - True/False
        - Short answer
        
        Format your response as a JSON array with this structure:
        [
            {{
                "question_type": "multiple_choice",
                "question": "The question text goes here?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Option B",
                "explanation": "Brief explanation of why this is correct"
            }},
            {{
                "question_type": "true_false",
                "question": "Statement that is true or false",
                "correct_answer": true,
                "explanation": "Brief explanation of why this is true/false"
            }},
            {{
                "question_type": "short_answer",
                "question": "Short answer question goes here?",
                "correct_answer": "The correct answer",
                "explanation": "Brief explanation of the answer",
                "keywords": ["keyword1", "keyword2", "keyword3"]
            }}
        ]
        
        Ensure all questions are directly related to the content and are factually accurate.
        Only return the JSON array, nothing else.
        """
        
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        try:
            # Clean up any markdown formatting
            json_text = response.text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
                
            quiz_data = json.loads(json_text)
            return quiz_data
        except json.JSONDecodeError as e:
            st.error(f"Error parsing quiz JSON: {str(e)}")
            st.code(response.text)  # Show the raw response for debugging
            return None
            
    except Exception as e:
        st.error(f"Error generating interactive quiz: {str(e)}")
        return None

def evaluate_quiz_answer_with_gemini(question_data, user_answer):
    """
    Use Gemini API to evaluate quiz answers, particularly useful for short answers.
    
    Args:
        question_data: Dictionary containing question information
        user_answer: The user's submitted answer
        
    Returns:
        Dictionary with evaluation results
    """
    # Check for empty answers to avoid unnecessary API calls
    if not user_answer:
        return {
            "correct": False,
            "explanation": "No answer provided",
            "feedback": "Please provide an answer before submitting",
            "score": 0,
            "missing_concepts": ["All concepts (no answer provided)"],
            "ai_evaluated": True
        }
    
    # Initialize Gemini API
    try:
        model = setup_google_api()
        if not model:
            # Fall back to basic evaluation if API is not available
            st.warning("Gemini API is not available. Using basic evaluation instead.")
            return check_quiz_answer(question_data, user_answer)
        
        # For multiple choice and true/false, we can still use basic checking
        if question_data["question_type"] in ["multiple_choice", "true_false"]:
            return check_quiz_answer(question_data, user_answer)
        
        # For short answers, use Gemini for more intelligent evaluation
        if question_data["question_type"] == "short_answer":
            # Construct prompt for Gemini
            prompt = f"""
            You are an expert educational assessment system. Evaluate this student answer for accuracy.
            
            Question: {question_data["question"]}
            
            Reference correct answer: {question_data["correct_answer"]}
            Key concepts that should be included: {", ".join(question_data["keywords"])}
            
            Student's answer: {user_answer}
            
            Evaluate the answer and respond in this JSON format only:
            {{
                "correct": true or false,
                "score": a number between 0 and 1 representing how correct the answer is,
                "explanation": "Your explanation of why the answer is correct or incorrect",
                "missing_concepts": ["list of concepts the student missed"],
                "feedback": "Constructive feedback for the student"
            }}
            
            Focus on conceptual understanding rather than exact wording. The answer should be considered correct if it demonstrates understanding of the key concepts, even if it doesn't use the exact same words.
            """
            
            # Get evaluation from Gemini with timeout handling
            try:
                response = model.generate_content(prompt, timeout=15)  # 15 second timeout
                
                # Parse the response
                try:
                    json_text = response.text
                    if "```json" in json_text:
                        json_text = json_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in json_text:
                        json_text = json_text.split("```")[1].split("```")[0].strip()
                    
                    evaluation = json.loads(json_text)
                    
                    # Validate required fields
                    if "correct" not in evaluation or "explanation" not in evaluation:
                        raise ValueError("Missing required fields in AI evaluation")
                    
                    # Return the evaluation with standard fields
                    return {
                        "correct": evaluation.get("correct", False),
                        "explanation": evaluation.get("explanation", ""),
                        "feedback": evaluation.get("feedback", ""),
                        "score": evaluation.get("score", 1.0 if evaluation.get("correct", False) else 0.0),
                        "missing_concepts": evaluation.get("missing_concepts", []),
                        "ai_evaluated": True
                    }
                except (json.JSONDecodeError, AttributeError, ValueError) as e:
                    # Fall back to basic evaluation if parsing fails
                    st.warning(f"Error parsing AI evaluation: {str(e)}. Using basic evaluation instead.")
                    return check_quiz_answer(question_data, user_answer)
            except Exception as timeout_err:
                st.warning(f"Timeout or error when calling Gemini API: {str(timeout_err)}. Using basic evaluation instead.")
                return check_quiz_answer(question_data, user_answer)
        
        # For unrecognized question types
        return check_quiz_answer(question_data, user_answer)
    
    except Exception as e:
        st.warning(f"Error using AI for evaluation: {str(e)}. Using basic evaluation instead.")
        # Ensure we always return a valid result
        try:
            return check_quiz_answer(question_data, user_answer)
        except Exception:
            # Last resort error handling
            return {
                "correct": False,
                "explanation": "There was an error evaluating your answer.",
                "feedback": "Please try again or contact support if the issue persists.",
                "score": 0,
                "missing_concepts": [],
                "ai_evaluated": False
            }

def check_quiz_answer(question_data, user_answer):
    """Check if the user's answer is correct based on question type."""
    try:
        if question_data["question_type"] == "multiple_choice":
            return {
                "correct": user_answer == question_data["correct_answer"],
                "explanation": question_data["explanation"],
                "feedback": "Your answer was " + ("correct!" if user_answer == question_data["correct_answer"] else "incorrect."),
                "score": 1.0 if user_answer == question_data["correct_answer"] else 0.0,
                "missing_concepts": [] if user_answer == question_data["correct_answer"] else ["Key concept"],
                "ai_evaluated": False
            }
        elif question_data["question_type"] == "true_false":
            # Convert string "true"/"false" to boolean if needed
            if isinstance(user_answer, str):
                user_bool = user_answer.lower() == "true"
            else:
                user_bool = user_answer
            return {
                "correct": user_bool == question_data["correct_answer"],
                "explanation": question_data["explanation"],
                "feedback": "Your answer was " + ("correct!" if user_bool == question_data["correct_answer"] else "incorrect."),
                "score": 1.0 if user_bool == question_data["correct_answer"] else 0.0,
                "missing_concepts": [] if user_bool == question_data["correct_answer"] else ["Key concept"],
                "ai_evaluated": False
            }
        elif question_data["question_type"] == "short_answer":
            # For short answer, check if keywords are present
            user_answer_lower = user_answer.lower()
            keywords_present = [keyword.lower() in user_answer_lower for keyword in question_data["keywords"]]
            
            # Calculate keyword match percentage
            match_percentage = sum(keywords_present) / len(keywords_present) if keywords_present else 0
            
            # Consider correct if at least 70% of keywords are present
            correct = match_percentage >= 0.7
            
            # Identify missing keywords
            missing_keywords = [
                question_data["keywords"][i] for i in range(len(keywords_present)) 
                if not keywords_present[i]
            ]
            
            return {
                "correct": correct,
                "explanation": question_data["explanation"],
                "feedback": f"You matched {int(match_percentage * 100)}% of the key concepts." +
                           (f" Missing: {', '.join(missing_keywords)}" if missing_keywords else ""),
                "score": match_percentage,
                "missing_concepts": missing_keywords,
                "ai_evaluated": False
            }
        else:
            return {
                "correct": False, 
                "explanation": "Unknown question type",
                "feedback": "This question type cannot be evaluated.",
                "score": 0,
                "missing_concepts": [],
                "ai_evaluated": False
            }
    except Exception as e:
        return {
            "correct": False, 
            "explanation": f"Error checking answer: {str(e)}",
            "feedback": "There was an error evaluating your answer.",
            "score": 0,
            "missing_concepts": [],
            "ai_evaluated": False
        }

# Load question papers from directory
def load_question_papers_from_directory():
    """Load all question papers from the Question Papers directory."""
    question_papers_dir = "Question Papers"
    papers_data = {}
    
    try:
        # Walk through the Question Papers directory
        for root, dirs, files in os.walk(question_papers_dir):
            for file in files:
                if file.endswith('.pdf'):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, question_papers_dir)
                    
                    # Create a readable name from the path
                    paper_name = os.path.splitext(relative_path)[0].replace('\\', '/').replace('_', ' ')
                    
                    # Store the file path
                    papers_data[paper_name] = file_path
        
        return papers_data
    except Exception as e:
        st.error(f"Error loading question papers: {str(e)}")
        return {}
# Get model questions from papers
def get_model_questions_from_papers(selected_papers):
    """Extract questions from selected past papers to use as examples."""
    model_questions = []
    
    try:
        for paper_path in selected_papers:
            with open(paper_path, 'rb') as file:
                paper_text = extract_model_questions(file)
                if paper_text:
                    model_questions.append(paper_text)
        
        return "\n\n".join(model_questions)
    except Exception as e:
        st.error(f"Error extracting questions from papers: {str(e)}")
        return ""
# Rename question papers
def rename_question_papers(rename_pattern):
    """Rename files in the Question Papers directory according to a specified pattern."""
    question_papers_dir = "Question Papers"
    renamed_files = []
    errors = []
    
    try:
        for root, dirs, files in os.walk(question_papers_dir):
            for file in files:
                if file.endswith('.pdf'):
                    old_path = os.path.join(root, file)
                    relative_path = os.path.relpath(old_path, question_papers_dir)
                    
                    # Get directory structure relative to Question Papers
                    dir_structure = os.path.dirname(relative_path)
                    
                    # Apply rename pattern
                    try:
                        # Extract subject and date information if available
                        parts = file.replace('.pdf', '').split('_')
                        
                        if rename_pattern == "subject_term_year":
                            # Expected format: Subject_May/Nov_YYYY.pdf
                            if len(parts) >= 3:
                                subject = parts[0]
                                term = parts[1]
                                year = parts[2]
                                new_name = f"{subject}_{term}_{year}.pdf"
                            else:
                                new_name = file  # Keep original if pattern doesn't match
                                
                        elif rename_pattern == "term_year_subject":
                            # Expected format: May/Nov_YYYY_Subject.pdf
                            if len(parts) >= 3:
                                term = parts[0]
                                year = parts[1]
                                subject = parts[2]
                                new_name = f"{term}_{year}_{subject}.pdf"
                            else:
                                new_name = file
                                
                        elif rename_pattern == "clean_spaces":
                            # Replace spaces with underscores
                            new_name = file.replace(' ', '_')
                            
                        else:
                            new_name = file
                        
                        # Create new path maintaining directory structure
                        new_path = os.path.join(root, new_name)
                        
                        # Rename file if new name is different
                        if new_path != old_path:
                            os.rename(old_path, new_path)
                            renamed_files.append({
                                'old_name': file,
                                'new_name': new_name,
                                'directory': dir_structure
                            })
                            
                    except Exception as e:
                        errors.append(f"Error renaming {file}: {str(e)}")
                        
        return renamed_files, errors
    except Exception as e:
        return [], [f"Error accessing directory: {str(e)}"]
# Generate focus tips
def generate_focus_tips():
    tips = [
        "Find a quiet, distraction-free environment for studying.",
        "Use the Pomodoro Technique: 25 minutes of focused study followed by a 5-minute break.",
        "Put your phone on silent mode or in another room while studying.",
        "Stay hydrated and keep healthy snacks nearby.",
        "Take short breaks to stretch and move around.",
        "Use noise-cancelling headphones or background white noise if needed.",
        "Set specific, achievable goals for each study session.",
        "Review your notes briefly before starting a new study session.",
        "Try studying at different times of day to find your peak productivity hours.",
        "Get enough sleep to ensure your brain can process and retain information."
    ]
    return random.choice(tips)
# Generate journal prompts
def generate_journal_prompts(prompt_type="reflection", content_context=None):
    """
    Generate AI-powered journaling prompts based on the type and optional content context.
    
    Args:
        prompt_type (str): Type of journaling prompt (reflection, gratitude, learning, goals, wellbeing)
        content_context (str, optional): Context from uploaded content to personalize prompts
    
    Returns:
        str: A journaling prompt
    """
    # Base prompts for different categories
    reflection_prompts = [
        "What was the most meaningful moment of my day, and why?",
        "How have I changed in the last year?",
        "What's a recent challenge I handled well, and what did I learn from it?",
        "If I could relive today, what would I do differently?",
        "What limiting beliefs are holding me back right now?"
    ]
    
    gratitude_prompts = [
        "What are three things I'm grateful for today, and why?",
        "Who made my day better today? How can I show appreciation?",
        "What is a small joy I experienced recently that I often overlook?",
        "How has a past challenge led to something good in my life?",
        "What part of my routine am I thankful for?"
    ]
    
    learning_prompts = [
        "What is one new idea I came across today?",
        "What mistake did I make recently, and what did it teach me?",
        "What's a concept I struggled with but now understand better?",
        "How can I apply something I learned today to my personal or professional life?",
        "What book, article, or podcast stood out to me recently, and why?"
    ]
    
    goals_prompts = [
        "What is my top priority this week, and how will I stay focused on it?",
        "Where do I see myself in five years, and what's one step I can take today toward that vision?",
        "What's a goal I've been procrastinating on, and what's stopping me?",
        "How do I define success in my current phase of life?",
        "What's a habit I need to build or break to reach my goals?"
    ]
    
    wellbeing_prompts = [
        "How am I feeling emotionally, and what might be causing it?",
        "What activities truly recharge me, and am I making time for them?",
        "What's something my body or mind is asking for right now?",
        "How do I usually deal with stress, and is it helping or hurting me?",
        "What boundaries do I need to set to protect my mental health?"
    ]
    
    # Select prompt list based on type
    if prompt_type == "reflection":
        prompts = reflection_prompts
    elif prompt_type == "gratitude":
        prompts = gratitude_prompts
    elif prompt_type == "learning":
        prompts = learning_prompts
    elif prompt_type == "goals":
        prompts = goals_prompts
    elif prompt_type == "wellbeing":
        prompts = wellbeing_prompts
    else:
        # Default to reflection
        prompts = reflection_prompts
    
    # If we have content context, use Gemini API to generate a more personalized prompt
    if content_context:
        try:
            # Initialize the Gemini model
            model = setup_google_api()
            if model:
                # Create prompt for Gemini
                prompt = f"""
                Create a thought-provoking journaling prompt related to {prompt_type}. 
                
                The prompt should:
                - Be personal and use "I" or "my" phrasing
                - Ask a specific, meaningful question that encourages deep introspection
                - Be concise (1-2 sentences maximum)
                - Avoid clichés and generic questions
                - Connect to themes in this content if relevant: "{content_context[:300]}..."
                
                Focus on helping the person gain new insights about themselves through writing.
                Return ONLY the prompt itself, with no additional text or explanation.
                """
                
                # Generate response using Gemini
                response = model.generate_content(prompt)
                
                personalized_prompt = response.text.strip()
                if personalized_prompt:
                    return personalized_prompt
        except Exception as e:
            # If API call fails, fall back to pre-written prompts
            print(f"Error generating personalized prompt: {e}")
    
    # Return a random prompt from the selected category
    return random.choice(prompts)
# Save journal entry
def save_journal_entry(entry, prompt, entry_date=None):
    """
    Save a journal entry to a file.
    
    Args:
        entry (str): The journal entry text
        prompt (str): The prompt that was used
        entry_date (datetime, optional): Date of the entry, defaults to current date/time
    
    Returns:
        bool: Success status
    """
    if entry_date is None:
        entry_date = datetime.now()
    
    # Create journals directory if it doesn't exist
    os.makedirs("journals", exist_ok=True)
    
    # Create a filename based on the date
    filename = f"journals/journal_{entry_date.strftime('%Y-%m-%d_%H-%M-%S')}.md"
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Journal Entry - {entry_date.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Prompt\n{prompt}\n\n")
            f.write(f"## Reflection\n{entry}\n")
        return True
    except Exception as e:
        print(f"Error saving journal entry: {e}")
        return False
# Get journal entries
def get_journal_entries():
    """
    Get a list of all saved journal entries.
    
    Returns:
        list: List of dictionaries containing journal entry details
    """
    entries = []
    
    # Check if journals directory exists
    if not os.path.exists("journals"):
        return entries
    
    # Get all markdown files in the journals directory
    journal_files = [f for f in os.listdir("journals") if f.endswith(".md")]
    
    for file in journal_files:
        try:
            with open(os.path.join("journals", file), "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract date from filename
            date_str = file.replace("journal_", "").replace(".md", "")
            date_obj = datetime.strptime(date_str, "%Y-%m-%d_%H-%M-%S")
            
            # Extract prompt and entry from content
            prompt = ""
            entry = ""
            
            prompt_match = re.search(r"## Prompt\n(.*?)\n\n", content, re.DOTALL)
            if prompt_match:
                prompt = prompt_match.group(1)
            
            entry_match = re.search(r"## Reflection\n(.*?)$", content, re.DOTALL)
            if entry_match:
                entry = entry_match.group(1)
            
            entries.append({
                "date": date_obj,
                "prompt": prompt,
                "entry": entry,
                "filename": file
            })
        except Exception as e:
            print(f"Error reading journal entry {file}: {e}")
    
    # Sort entries by date (newest first)
    entries.sort(key=lambda x: x["date"], reverse=True)
    
    return entries
# Delete journal entry
def delete_journal_entry(filename):
    """
    Delete a journal entry file.
    
    Args:
        filename (str): The filename of the journal entry to delete
        
    Returns:
        bool: Success status
    """
    try:
        file_path = os.path.join("journals", filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"Error deleting journal entry: {e}")
        return False
# Save study session
def save_study_session(session_name=None):
    """Save the current study session to a local directory."""
    if not session_name:
        session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create sessions directory if it doesn't exist
    if not os.path.exists("study_sessions"):
        os.makedirs("study_sessions")
    
    # Create session directory
    session_dir = os.path.join("study_sessions", session_name)
    os.makedirs(session_dir, exist_ok=True)
    
    # Save session data
    session_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": st.session_state.get("summary", ""),
        "notes": st.session_state.get("notes", ""),
        "questions": st.session_state.get("questions", []),
        "flashcards": st.session_state.get("flashcards", []),
        "mind_map": st.session_state.get("mind_map", None),
        "mind_palace": st.session_state.get("mind_palace", None),
        "quiz_data": st.session_state.get("quiz_data", []),
        "quiz_answers": st.session_state.get("quiz_answers", []),
        "quiz_score": st.session_state.get("quiz_score", 0),
        "journal_entries": st.session_state.get("journal_entries", []),
        "uploaded_files": st.session_state.get("uploaded_files", []),
        "active_file": st.session_state.get("active_file", None)
    }
    
    # Save session data as JSON
    with open(os.path.join(session_dir, "session_data.json"), "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=4, ensure_ascii=False)
    
    # Save file contents
    file_contents_dir = os.path.join(session_dir, "file_contents")
    os.makedirs(file_contents_dir, exist_ok=True)
    
    for file_name in st.session_state.get("uploaded_files", []):
        if file_name in st.session_state.file_contents:
            with open(os.path.join(file_contents_dir, file_name + ".txt"), "w", encoding="utf-8") as f:
                f.write(st.session_state.file_contents[file_name])
    
    return session_name
# Load study session
def load_study_session(session_name):
    """Load a study session from a local directory."""
    session_dir = os.path.join("study_sessions", session_name)
    if not os.path.exists(session_dir):
        return False
    
    # Load session data
    with open(os.path.join(session_dir, "session_data.json"), "r", encoding="utf-8") as f:
        session_data = json.load(f)
    
    # Restore session state
    for key, value in session_data.items():
        if key != "uploaded_files" and key != "active_file":
            st.session_state[key] = value
    
    # Restore uploaded files
    st.session_state.uploaded_files = session_data.get("uploaded_files", [])
    st.session_state.active_file = session_data.get("active_file", None)
    st.session_state.file_contents = {}
    
    # Load file contents
    file_contents_dir = os.path.join(session_dir, "file_contents")
    if os.path.exists(file_contents_dir):
        for file_name in st.session_state.uploaded_files:
            file_path = os.path.join(file_contents_dir, file_name + ".txt")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    st.session_state.file_contents[file_name] = f.read()
    
    return True
# List study sessions
def list_study_sessions():
    """List all available study sessions."""
    if not os.path.exists("study_sessions"):
        return []
    
    sessions = []
    for session_name in os.listdir("study_sessions"):
        session_dir = os.path.join("study_sessions", session_name)
        if os.path.isdir(session_dir):
            try:
                with open(os.path.join(session_dir, "session_data.json"), "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                    sessions.append({
                        "name": session_name,
                        "timestamp": session_data.get("timestamp", ""),
                        "summary_length": len(session_data.get("summary", "")),
                        "num_questions": len(session_data.get("questions", [])),
                        "num_flashcards": len(session_data.get("flashcards", [])),
                        "has_mind_map": bool(session_data.get("mind_map")),
                        "has_mind_palace": bool(session_data.get("mind_palace")),
                        "quiz_score": session_data.get("quiz_score", 0)
                    })
            except Exception as e:
                print(f"Error loading session {session_name}: {e}")
    
    return sorted(sessions, key=lambda x: x["timestamp"], reverse=True)
# Delete study session
def delete_study_session(session_name):
    """Delete a study session and all its data."""
    session_dir = os.path.join("study_sessions", session_name)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
        return True
    return False
# Save feedback
def save_feedback(feedback_type, feedback_text):
    """Save user feedback to a file."""
    try:
        # Create feedback directory if it doesn't exist
        if not os.path.exists("feedback"):
            os.makedirs("feedback")
        
        # Save feedback to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        feedback_data = {
            "timestamp": datetime.now().isoformat(),
            "type": feedback_type,
            "text": feedback_text,
            "session_info": {
                "has_summary": bool(st.session_state.get("summary", "")),
                "has_notes": bool(st.session_state.get("notes", "")),
                "num_files": len(st.session_state.get("uploaded_files", [])),
                "active_file": st.session_state.get("active_file", None)
            }
        }
        
        with open(os.path.join("feedback", f"feedback_{timestamp}.json"), "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        st.error(f"Error saving feedback: {str(e)}")
        return False
# Main function
def main():
    """Main function to run the Streamlit app."""
    # Set page config
    st.set_page_config(
        page_title="Jñānasādhana",
        page_icon="Logo Updated.png",
        layout="wide",
        initial_sidebar_state="collapsed"  # Sidebar starts collapsed
    )
    
    # Initialize session state variables
    def initialize_session_state():
        """Initialize all session state variables in one place for better organization."""
        if "uploaded_files" not in st.session_state:
            st.session_state.uploaded_files = []
        if "file_contents" not in st.session_state:
            st.session_state.file_contents = {}
        if "active_file" not in st.session_state:
            st.session_state.active_file = None
        if "summary" not in st.session_state:
            st.session_state.summary = ""
        if "notes" not in st.session_state:
            st.session_state.notes = ""
        if "questions" not in st.session_state:
            st.session_state.questions = []
        if "exam_paper" not in st.session_state:
            st.session_state.exam_paper = ""
        if "current_question" not in st.session_state:
            st.session_state.current_question = 0
        if "answer_text" not in st.session_state:
            st.session_state.answer_text = ""
        if "evaluation" not in st.session_state:
            st.session_state.evaluation = ""
        if "flashcards" not in st.session_state:
            st.session_state.flashcards = []
        if "mind_map_data" not in st.session_state:
            st.session_state.mind_map_data = {}
        if "mind_palace" not in st.session_state:
            st.session_state.mind_palace = ""
        if "quiz_data" not in st.session_state:
            st.session_state.quiz_data = []
        if "current_quiz_question" not in st.session_state:
            st.session_state.current_quiz_question = 0
        if "quiz_answers" not in st.session_state:
            st.session_state.quiz_answers = []
        if "quiz_score" not in st.session_state:
            st.session_state.quiz_score = 0
        if "quiz_completed" not in st.session_state:
            st.session_state.quiz_completed = False
        if "use_ai_evaluation" not in st.session_state:
            st.session_state.use_ai_evaluation = True
        if "journal_entries" not in st.session_state:
            st.session_state.journal_entries = []
    
    # Call the initialization function
    initialize_session_state()
    
    # Load custom CSS
    st.markdown(f"""
    <style>
    /* Import Poppins font */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    /* General Styling */
    body {{
        font-family: 'Poppins', sans-serif;
        background-color: #121212;  /* Darker background */
        color: #FFFFFF;  /* White text */
        line-height: 1.6;
    }}
    
    /* Fix for details/summary elements in Streamlit */
    details {{
        background-color: rgba(45, 45, 45, 0.7);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }}
    
    details summary {{
        cursor: pointer;
        padding: 0.75rem;
        border-radius: 5px;
        background-color: rgba(30, 136, 229, 0.2);
        transition: all 0.3s ease;
        font-weight: 500;
        display: flex;
        align-items: center;
    }}
    
    details summary:hover {{
        background-color: rgba(30, 136, 229, 0.3);
    }}
    
    details summary::marker,
    details summary::-webkit-details-marker {{
        color: rgba(30, 136, 229, 0.8);
        margin-right: 0.5rem;
    }}
    
    details[open] summary {{
        margin-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        background-color: rgba(30, 136, 229, 0.25);
    }}
    
    details[open] {{
        padding: 0.75rem 1.25rem 1.25rem 1.25rem;
    }}
    
    details p {{
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
        line-height: 1.6;
    }}
    
    details strong {{
        color: rgba(255, 255, 255, 0.95);
        font-weight: 600;
    }}
    
    .header-container {{
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 1.5rem;
        background: rgba(30, 30, 30, 0.7);  /* Glassmorphism background */
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
        animation: fadeIn 0.5s ease-in-out;
    }}
    .header-container img {{
        width: 120px;
        margin-right: 1rem;
    }}
    .main-header {{
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1E88E5, #5E35B1);  /* Gradient text */
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1.5rem;
        letter-spacing: 0.5px;
        animation: fadeInUp 0.7s ease-out;
    }}
    .section-header {{
        font-size: 1.5rem;
        font-weight: 600;
        background: linear-gradient(90deg, #1E88E5, #64B5F6);  /* Lighter gradient */
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 0.5rem;
        animation: fadeInLeft 0.5s ease-out;
    }}
    .stButton>button {{
        background: linear-gradient(135deg, #1E88E5, #1565C0);  /* Gradient background */
        color: white;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-size: 1rem;
        font-weight: 500;
        border: none;
        box-shadow: 0 4px 15px rgba(21, 101, 192, 0.3);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        z-index: 1;
    }}
    .stButton>button:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(21, 101, 192, 0.4);
    }}
    .stButton>button:active {{
        transform: translateY(1px);
    }}
    .stButton>button::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, #1565C0, #0D47A1);
        z-index: -1;
        transition: opacity 0.3s ease;
        opacity: 0;
    }}
    .stButton>button:hover::before {{
        opacity: 1;
    }}
    .footer {{
        text-align: center;
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.7);
        margin-top: 3rem;
        padding: 1.5rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        background: rgba(30, 30, 30, 0.5);
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
        border-radius: 0 0 16px 16px;
        animation: fadeInUp 0.5s ease-out;
    }}
    .stFileUploader {{
        background: rgba(40, 40, 40, 0.6);  /* Glassmorphism background */
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
        transition: all 0.3s ease;
    }}
    .stFileUploader:hover {{
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }}

    /* Content styling */
    .stTextArea textarea {{
        background: rgba(42, 42, 42, 0.7) !important;
        color: #E0E0E0 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 16px !important;
        font-size: 1rem !important;
        line-height: 1.6 !important;
        backdrop-filter: blur(5px) !important;
        -webkit-backdrop-filter: blur(5px) !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important;
    }}
    .stTextArea textarea:focus {{
        border: 1px solid rgba(30, 136, 229, 0.5) !important;
        box-shadow: 0 4px 20px rgba(30, 136, 229, 0.2) !important;
    }}

    /* Question styling */
    h2, h3 {{
        background: linear-gradient(90deg, #64B5F6, #42A5F5) !important;
        -webkit-background-clip: text !important;
        background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px !important;
    }}
    p {{
        margin-bottom: 1rem !important;
    }}

    /* Tab styling */
    .stTabs [role="tab"] {{
        background: rgba(51, 51, 51, 0.7) !important;
        color: rgba(255, 255, 255, 0.8) !important;
        border-radius: 12px 12px 0 0 !important;
        padding: 0.75rem 1.25rem !important;
        margin-right: 4px !important;
        font-weight: 500 !important;
        backdrop-filter: blur(5px) !important;
        -webkit-backdrop-filter: blur(5px) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-bottom: none !important;
        transition: all 0.3s ease !important;
    }}
    .stTabs [role="tab"][aria-selected="true"] {{
        background: linear-gradient(135deg, #1E88E5, #1565C0) !important;
        color: white !important;
        box-shadow: 0 -4px 10px rgba(21, 101, 192, 0.2) !important;
    }}
    .stTabs [data-baseweb="tab-panel"] {{
        background: rgba(42, 42, 42, 0.7) !important;
        border-radius: 0 12px 12px 12px !important;
        padding: 1.8rem !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1) !important;
    }}

    /* Card styling for flashcards and mind map */
    div[style*="background-color: #e1f5fe"] {{
        background: rgba(42, 42, 42, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border-radius: 16px !important;
        transition: all 0.3s ease !important;
    }}
    div[style*="background-color: #e1f5fe"]:hover {{
        box-shadow: 0 12px 48px rgba(0, 0, 0, 0.25) !important;
        transform: translateY(-5px) !important;
    }}
    div[style*="background-color: #f5f5f5"] {{
        background: rgba(42, 42, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(5px) !important;
        -webkit-backdrop-filter: blur(5px) !important;
    }}
    
    /* Animation keyframes */
    @keyframes fadeIn {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
    }}
    
    @keyframes fadeInUp {{
        from {{ 
            opacity: 0;
            transform: translateY(20px);
        }}
        to {{ 
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    
    @keyframes fadeInLeft {{
        from {{ 
            opacity: 0;
            transform: translateX(-20px);
        }}
        to {{ 
            opacity: 1;
            transform: translateX(0);
        }}
    }}
    
    /* Input field styling */
    .stTextInput input, .stNumberInput input, .stSelectbox, .stMultiselect {{
        background: rgba(42, 42, 42, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 12px !important;
        backdrop-filter: blur(5px) !important;
        -webkit-backdrop-filter: blur(5px) !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important;
    }}
    
    .stTextInput input:focus, .stNumberInput input:focus {{
        border: 1px solid rgba(30, 136, 229, 0.5) !important;
        box-shadow: 0 4px 20px rgba(30, 136, 229, 0.2) !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Header Section
    st.markdown('<div class="main-header">Jñānasādhana</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Bring Your Eagerness to Learn. We Provide All the Tools.</div>', unsafe_allow_html=True)
    st.write("Jñānasādhana is an AI-powered study assistant that helps students and learners extract knowledge from PDF documents, generate study materials, and test their understanding through various interactive tools. Powered by Google's Gemini API, it transforms the way you study by providing intelligent content analysis and generation.")

    # Add a sidebar for configuration
    with st.sidebar:
        st.header("Options")

        # Add session management to sidebar
        st.subheader("💾 Session Management")
        
        # Save current session
        session_name = st.text_input("Enter Session Name", 
                                    key="save_session_input",
                                    placeholder="Required")
        if st.button("Save Session", key="save_session_btn"):
            if not session_name or session_name.strip() == "":
                st.error("Please enter a session name")
            elif save_study_session(session_name):
                st.success("Session saved successfully!")
                st.rerun()
        
        # Load previous sessions
        sessions = list_study_sessions()
        if sessions:
            st.markdown("### Previous Sessions")
            selected_session = st.selectbox(
                "Select a session to load or delete:",
                options=[s["name"] for s in sessions],
                key="session_selector"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load Session", key="load_session_btn"):
                    if load_study_session(selected_session):
                        st.success("Session loaded successfully!")
                        st.rerun()
            with col2:
                if st.button("Delete Session", key="delete_session_btn"):
                    # Add confirmation dialog
                    confirm_delete = st.checkbox(f"Confirm deletion of '{selected_session}'", key="confirm_delete")
                    if confirm_delete:
                        if delete_study_session(selected_session):
                            st.success("Session deleted successfully!")
                            st.rerun()
                    else:
                        st.warning("Please confirm deletion by checking the box above.")
            
            # Display session details
            st.markdown("### Session Details")
            for session in sessions:
                if session["name"] == selected_session:
                    st.markdown(f"""
                        **Date:** {session['timestamp']}  
                        **Summary Length:** {session['summary_length']} characters  
                        **Questions:** {session['num_questions']}  
                        **Flashcards:** {session['num_flashcards']}  
                        **Quiz Score:** {session['quiz_score'] if session['quiz_score'] is not None else 'Not taken'}
                    """)
        else:
            st.info("No previous sessions found. Start by saving your current study session!")
        
        # Session backup info
        st.markdown("---")
        st.markdown("### 📦 Backup Info")
        if os.path.exists("study_sessions"):
            backup_size = sum(os.path.getsize(os.path.join("study_sessions", f)) 
                            for f in os.listdir("study_sessions") 
                            if os.path.isfile(os.path.join("study_sessions", f)))
            st.info(f"Total backup size: {backup_size / 1024 / 1024:.2f} MB")
            st.markdown("""
                Your study sessions are automatically saved in the `study_sessions` directory.
                You can find all your session data there, including:
                - Original documents
                - Generated summaries
                - Flashcards
                - Mind maps
                - Quiz results
                - And more!
            """)
        
        # Add feedback mechanism for testers
        st.markdown("---")
        st.markdown("### 🧪 Testing Feedback")
        with st.expander("Submit Feedback", expanded=False):
            feedback_type = st.selectbox(
                "Feedback Type",
                options=["Bug Report", "Feature Request", "UI/UX Suggestion", "General Feedback"],
                key="feedback_type"
            )
            
            feedback_text = st.text_area(
                "Describe your feedback in detail",
                height=150,
                key="feedback_text",
                help="Please be as specific as possible. Include steps to reproduce for bugs."
            )
            
            severity = st.select_slider(
                "Severity/Importance",
                options=["Low", "Medium", "High", "Critical"],
                value="Medium",
                key="feedback_severity"
            )
            
            if st.button("Submit Feedback", key="submit_feedback"):
                if not feedback_text.strip():
                    st.error("Please enter feedback text before submitting.")
                else:
                    # Create feedback directory if it doesn't exist
                    if not os.path.exists("feedback"):
                        os.makedirs("feedback")
                    
                    # Save feedback to file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    feedback_data = {
                        "timestamp": timestamp,
                        "type": feedback_type,
                        "text": feedback_text,
                        "severity": severity,
                        "session_state": {
                            "has_summary": bool(st.session_state.get("summary", "")),
                            "has_notes": bool(st.session_state.get("notes", "")),
                            "num_files": len(st.session_state.get("uploaded_files", [])),
                            "active_file": st.session_state.get("active_file", None)
                        }
                    }
                    
                    with open(os.path.join("feedback", f"feedback_{timestamp}.json"), "w", encoding="utf-8") as f:
                        json.dump(feedback_data, f, indent=4, ensure_ascii=False)
                    
                    st.success("Thank you for your feedback! It has been saved for review.")
                    # Clear the form
                    st.session_state.feedback_text = ""
        
        st.markdown("---")

    # File upload section
    st.markdown('<div class="section-header">Upload Your Documents</div>', unsafe_allow_html=True)
    
    # File uploader
    uploaded_files = st.file_uploader("Upload PDF files:", 
                                    type=["pdf"],
                                    accept_multiple_files=True,
                                    help="Upload PDF files that are not encrypted or password-protected. Text-based PDFs work best.")
    
    # PDF password input (hidden by default)
    pdf_password = st.text_input(
        "PDF Password (optional)",
        type="password",
        help="Enter password only if your PDF is encrypted and you have the password",
        key="pdf_password"
    )
    
    # Advanced options
    with st.expander("Advanced PDF Options"):
        extraction_method = st.radio(
            "PDF Extraction Method",
            options=["Auto (Recommended)", "Standard PyPDF2", "Robust Multi-method", "With Decryption"],
            index=0,
            help="Select which extraction method to use for PDFs"
        )
    
    # Handle new file uploads
    if uploaded_files:
        for file in uploaded_files:
            file_name = file.name
            if file_name not in [f for f in st.session_state.uploaded_files]:
                with st.spinner(f"Processing {file_name}..."):
                    # Select extraction method based on user choice
                    if extraction_method == "Standard PyPDF2":
                        content = extract_text_from_pdf(file)
                    elif extraction_method == "Robust Multi-method":
                        content = extract_text_from_pdf_robust(file)
                    elif extraction_method == "With Decryption":
                        content = extract_text_from_pdf_with_crypto(file, pdf_password if pdf_password else None)
                    else:
                        # Auto method - try with crypto first, then fallback to robust
                        content = extract_text_from_pdf_with_crypto(file, pdf_password if pdf_password else None)
                        if content and (content.startswith("The PDF file is encrypted") or content.startswith("Could not extract")):
                            content = extract_text_from_pdf_robust(file)
                    
                    # Check if content is an error message
                    if content and "encrypted" in content.lower():
                        st.error(f"""
                        📔 **Encrypted PDF Detected:** {file_name}
                        
                        This PDF is password-protected or encrypted and cannot be processed.
                        
                        **To fix this issue:**
                        1. Open the PDF in a PDF reader (like Adobe Acrobat)
                        2. Enter the password if prompted
                        3. Save a new copy without password protection
                           - In Adobe Acrobat: File → Save As → Reduce Size PDF
                           - In other PDF readers: Look for "Save without encryption" or similar option
                        4. Upload the new unencrypted version
                        """)
                    elif content and (content.startswith("Error") or content.startswith("Failed") or content.startswith("Could not")):
                        st.error(f"Error processing {file_name}: {content}")
                        # Don't add the file to session state if extraction failed
                    else:
                        st.session_state.file_contents[file_name] = content
                        st.session_state.uploaded_files.append(file_name)
                        st.success(f"Successfully processed {file_name}")
                        
                        # Check if content is very short (likely extraction problem)
                        if len(content.strip()) < 100:
                            st.warning(f"""
                            ⚠️ **Limited Content Detected**
                            
                            Only {len(content.strip())} characters were extracted from {file_name}, which is unusually small.
                            
                            This may indicate:
                            - The PDF contains mostly images or scanned content
                            - The PDF has restricted permissions
                            - The text extraction was incomplete
                            
                            Consider using a different PDF with more extractable text.
                            """)
        
        # Display uploaded files
        if st.session_state.uploaded_files:
            st.markdown("### Uploaded Files")
            for idx, file_name in enumerate(st.session_state.uploaded_files):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"📄 {file_name}")
                with col2:
                    if st.button("Set Active", key=f"active_{idx}_{file_name}"):
                        st.session_state.active_file = file_name
                        st.session_state.summary = st.session_state.file_contents[file_name]
                        # Reset other state when a new file is selected
                        st.session_state.notes = ""
                        st.session_state.questions = []
                        st.session_state.exam_paper = ""
                        st.session_state.current_question = 0
                        st.session_state.answer_text = ""
                        st.session_state.evaluation = ""
                        st.rerun()
                with col3:
                    if st.button("Remove", key=f"remove_{idx}_{file_name}"):
                        st.session_state.uploaded_files.remove(file_name)
                        del st.session_state.file_contents[file_name]
                        if st.session_state.active_file == file_name:
                            st.session_state.active_file = None
                            st.session_state.summary = ""
                        st.rerun()
            
            # Add option to combine all files
            if len(st.session_state.uploaded_files) > 1:
                if st.button("Combine All Files for Processing"):
                    combined_content = "\n\n--- NEW DOCUMENT ---\n\n".join([
                        f"Document: {file_name}\n\n{st.session_state.file_contents[file_name]}" 
                        for file_name in st.session_state.uploaded_files
                    ])
                    st.session_state.summary = combined_content
                    st.session_state.active_file = "Combined Documents"
                    # Reset other state when combining files
                    st.session_state.notes = ""
                    st.session_state.questions = []
                    st.session_state.exam_paper = ""
                    st.session_state.current_question = 0
                    st.session_state.answer_text = ""
                    st.session_state.evaluation = ""
                    st.success("All documents combined for processing")
                    st.rerun()
            
            # Show active file
            if st.session_state.active_file:
                st.info(f"Active document: {st.session_state.active_file}")
            else:
                # Set the first file as active if none is selected
                if st.session_state.uploaded_files and not st.session_state.summary:
                    first_file = st.session_state.uploaded_files[0]
                    st.session_state.active_file = first_file
                    st.session_state.summary = st.session_state.file_contents[first_file]
                    st.info(f"Active document: {first_file}")
    
        # Combine content from all files
        combined_content = "\n\n".join([st.session_state.file_contents[file_name] 
                                    for file_name in st.session_state.uploaded_files])
        st.session_state.summary = combined_content
            
        # Reset other state when a new file is uploaded
        st.session_state.notes = ""
        st.session_state.questions = []
        st.session_state.exam_paper = ""
        st.session_state.current_question = 0
        st.session_state.answer_text = ""
        st.session_state.evaluation = ""

    # Debug window to display active content
    if st.session_state.summary and st.checkbox("Show Debug Window (Active Content)", help="Display the current active content being processed by Gemini"):
        with st.expander("Active Content (Markdown Format)", expanded=True):
            st.markdown("### Current Active Content")
            st.markdown("This is the exact content that will be processed by Gemini API:")
            
            # Display content length statistics
            content_length = len(st.session_state.summary)
            st.info(f"Content Length: {content_length} characters | Approximately {content_length // 4} tokens")
            
            # Add download button for the content
            st.download_button(
                "Download Active Content",
                st.session_state.summary,
                file_name="active_content.md",
                mime="text/markdown"
            )
            
            # Display the content in a scrollable area with syntax highlighting
            st.code(st.session_state.summary[:10000], language="markdown")
            
            if len(st.session_state.summary) > 10000:
                st.warning(f"Content truncated for display. Showing first 10,000 of {content_length} characters.")
                if st.button("Show Full Content"):
                    st.code(st.session_state.summary, language="markdown")

    # Tabs for different features
    if st.session_state.summary:
        st.markdown('<div class="section-header">Study Tools</div>', unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["✍️Notes and Practice", "💡Study Aids", "⏰Productivity and Focus"])

        with tab1:
            st.markdown('<div class="section-header">Notes and Practice</div>', unsafe_allow_html=True)
            Note1, Note2, Note3, Note4 = st.tabs(["📚 Generate Notes", "📝 Generate Questions", "✅ Answer & Evaluate", "🎯 Interactive Quiz"])
            with Note1:
                st.markdown('<div class="section-header">Generate Notes</div>', unsafe_allow_html=True)
                # Add note type selector
                note_type = st.selectbox(
                    "Select Note-Taking Method:",
                    options=["Cornell Notes", "Concept Map"],
                    index=0,
                    key="note_type"
                )
            
                # Map the selection to the function parameter
                note_type_map = {
                    "Cornell Notes": "cornell",
                    "Concept Map": "concept_map",
                }
            
                # Add generate notes button
                if st.button("Generate Notes", key="generate_notes_btn"):
                    with st.spinner("Generating notes..."):
                        notes = generate_notes(st.session_state.summary, note_type=note_type_map[note_type])
                        if notes:
                            st.session_state.notes = notes
                            st.success("Notes generated successfully!")
                            st.markdown(notes)
                        else:
                            st.error("Failed to generate notes.")
                
                # Display existing notes if available
                # if st.session_state.get("notes", ""):
                    # st.markdown("### Generated Notes")
                    # st.markdown(st.session_state.notes)
                    
                    # Add download option for notes
                    if st.button("Download Notes", key="download_notes_btn"):
                        st.download_button(
                            label="Download Notes (Markdown)",
                            data=st.session_state.notes,
                            file_name=f"notes_{note_type.lower().replace(' ', '_')}.md",
                            mime="text/markdown"
                        )
            
            with Note2:
                st.markdown('<div class="section-header">Exam Questions</div>', unsafe_allow_html=True)
            
                # Load available question papers
                question_papers = load_question_papers_from_directory()
                
                if question_papers:
                    st.markdown("### Use Past Question Papers")
                    st.write("Select past papers to guide question generation:")
                    
                    # Create a multiselect for choosing papers
                    selected_paper_names = st.multiselect(
                        "Select Question Papers:",
                        options=list(question_papers.keys()),
                        help="Choose papers to use as examples for question generation"
                    )
                    
                    # Get the file paths for selected papers
                    selected_paper_paths = [question_papers[name] for name in selected_paper_names]
                    
                    # Extract model questions from selected papers
                    if selected_paper_paths:
                        with st.spinner("Processing selected papers..."):
                            model_questions_text = get_model_questions_from_papers(selected_paper_paths)
                            if model_questions_text:
                                st.success(f"Successfully loaded questions from {len(selected_paper_names)} papers")
                                with st.expander("View extracted questions"):
                                    st.text_area("Questions from Selected Papers:", 
                                            value=model_questions_text, 
                                            height=200, 
                                            key="selected_papers_questions")
                
                # Optional: Manual upload of additional model questions
                st.markdown("### Optional: Upload Additional Model Questions")
                st.write("Upload additional question papers not in the local directory.")
                model_questions_file = st.file_uploader("Upload model questions (PDF):", 
                                                    type=["pdf"],
                                                    key="model_questions_uploader",
                                                    help="This will help the AI generate questions in your preferred style")
                
                # Combine questions from both sources
                combined_model_questions = ""
                if selected_paper_paths:
                    combined_model_questions += model_questions_text + "\n\n"
                
                if model_questions_file is not None:
                    with st.spinner("Extracting model questions..."):
                        uploaded_questions = extract_model_questions(model_questions_file)
                        if uploaded_questions:
                            combined_model_questions += uploaded_questions
                            st.success("Successfully added questions from uploaded file")
                
                question_type = st.selectbox(
                    "Select Question Type:",
                    options=["Mixed", "MCQ", "Short Answer", "Case Based Application", "Numerical Calculation"],
                    index=0,
                    key="question_type",
                    help="Select 'Mixed' to generate a combination of all question types"
                )

                num_questions = st.number_input(
                    "Number of Questions:",
                    min_value=1,
                    max_value=20,
                    value=5,
                    step=1,
                    key="num_questions"
                )

                include_answers = st.checkbox(
                    "Include Detailed Answers",
                    value=False,
                    key="include_answers"
                )

                if st.button("Generate Exam Questions", key="generate_questions"):
                    with st.spinner("Generating questions..."):
                        st.session_state.questions = generate_questions(
                            st.session_state.summary,
                            question_type,
                            num_questions=num_questions,
                            include_answers=include_answers,
                            model_questions=combined_model_questions if combined_model_questions else None
                        )
                        st.session_state.exam_paper = format_exam_paper(st.session_state.questions)

                if st.session_state.exam_paper:
                    col1, col2 = st.columns([0.9, 0.1])
                    with col1:
                        st.markdown(st.session_state.exam_paper, unsafe_allow_html=True)
                    with col2:
                        if st.button("📋", key="copy_exam", help="Copy to clipboard"):
                            if copy_to_clipboard(st.session_state.exam_paper):
                                st.success("Copied!")

                    st.info("Go to the 'Answer & Evaluate' tab to answer these questions and receive feedback.")

            with Note3:
                st.markdown('<div class="section-header">Answer & Evaluate</div>', unsafe_allow_html=True)
                if not st.session_state.questions:
                    st.warning("Please generate exam questions first in the 'Exam Questions' tab.")
                else:
                    # Question selection
                    question_options = [f"Question {i+1}" for i in range(len(st.session_state.questions))]
                    selected_q = st.selectbox("Select a question to answer:",
                                            options=question_options,
                                            index=st.session_state.current_question,
                                            key="question_select")
                
                    # Update current question index
                    st.session_state.current_question = question_options.index(selected_q)
                
                    # Display selected question
                    q_index = st.session_state.current_question
                    st.markdown(f"### {selected_q}")
                    
                    # Only display the question part, not the answer
                    question_text = st.session_state.questions[q_index]
                    # Check if the question has an answer section and remove it
                    if "Answer:" in question_text:
                        question_only, _ = question_text.split("Answer:", 1)
                        st.markdown(question_only.strip())
                    else:
                        st.markdown(question_text)
                
                    # Add tabs for typed vs handwritten answers
                    answer_tab1, answer_tab2 = st.tabs(["Type Answer", "Upload Handwritten Answer"])
                    
                    with answer_tab1:
                        # Text area for answer (existing code)
                        answer_key = f"answer_for_q{q_index}"
                        
                        # Initialize the answer in session state if it doesn't exist
                        if answer_key not in st.session_state:
                            st.session_state[answer_key] = ""
                        
                        # Get answer from text area
                        st.session_state[answer_key] = st.text_area("Your Answer:",
                                                                    value=st.session_state.get(answer_key, ""),
                                                                    height=200,
                                                                    key=f"textarea_{answer_key}")
                        
                        # Evaluation button
                        if st.button("Evaluate Typed Answer", key=f"eval_btn_{q_index}"):
                            with st.spinner("Evaluating your answer..."):
                                question = st.session_state.questions[q_index]
                                user_answer = st.session_state[answer_key]
                        
                                if not user_answer.strip():
                                    st.error("Please provide an answer before evaluation.")
                                else:
                                    evaluation = evaluate_answer(question, user_answer)
                                    st.session_state[f"eval_{q_index}"] = evaluation
                        
                        with answer_tab2:
                            # File uploader for handwritten answers
                            st.write("Upload a photo of your handwritten answer:")
                            handwritten_file = st.file_uploader("Choose an image file", 
                                                            type=["jpg", "jpeg", "png"], 
                                                            key=f"handwritten_upload_{q_index}")
                            
                            if handwritten_file is not None:
                                # Display the uploaded image
                                image = Image.open(handwritten_file)
                                st.image(image, caption="Uploaded handwritten answer", use_column_width=True)
                                
                                # Store the image path in session state
                                handwritten_key = f"handwritten_for_q{q_index}"
                                st.session_state[handwritten_key] = handwritten_file.name
                                
                                # Evaluation button for handwritten answer
                                if st.button("Evaluate Handwritten Answer", key=f"handwritten_eval_btn_{q_index}"):
                                    with st.spinner("Analyzing handwritten answer..."):
                                        question = st.session_state.questions[q_index]
                                        
                                        # Evaluate the handwritten answer
                                        evaluation = evaluate_handwritten_answer(question, handwritten_file)
                                        st.session_state[f"eval_{q_index}"] = evaluation
                        
                        # Display evaluation if available (for both typed and handwritten)
                        if f"eval_{q_index}" in st.session_state and st.session_state[f"eval_{q_index}"]:
                            st.markdown("### Feedback")
                            st.markdown(st.session_state[f"eval_{q_index}"])

            with Note4:
                st.header("Interactive Quiz")
            
                # Quiz generation options
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    quiz_num_questions = st.number_input("Number of Questions:", min_value=3, max_value=10, value=5, key="quiz_num_questions_input")
                with col2:
                    quiz_difficulty = st.selectbox("Difficulty Level:", ["easy", "medium", "hard"], index=1, key="quiz_difficulty_select")
                with col3:
                    if st.button("Generate Quiz", key="generate_quiz_button"):
                        with st.spinner("Creating interactive quiz..."):
                            quiz_data = generate_interactive_quiz(
                                st.session_state.summary, 
                                num_questions=quiz_num_questions,
                                difficulty=quiz_difficulty
                            )
                            if quiz_data:
                                st.session_state.quiz_data = quiz_data
                                st.session_state.current_quiz_question = 0
                                st.session_state.quiz_answers = []
                                st.session_state.quiz_score = 0
                                st.session_state.quiz_completed = False
                                
                                # Reset all submission flags for questions
                                for key in list(st.session_state.keys()):
                                    if key.startswith("submitted_q"):
                                        del st.session_state[key]
                                
                                st.rerun()
                
                # Advanced quiz options
                with st.expander("Advanced Quiz Options"):
                    use_ai_eval = st.checkbox(
                        "Use Gemini AI for answer evaluation", 
                        value=True,
                        help="Enables more intelligent evaluation of short answer questions using Gemini AI"
                    )
                    
                    # Store the setting in session state
                    if "use_ai_evaluation" not in st.session_state or st.session_state.use_ai_evaluation != use_ai_eval:
                        st.session_state.use_ai_evaluation = use_ai_eval
                    
                    st.markdown("""
                    **With AI Evaluation:**
                    - More intelligent understanding of your answers
                    - Partial credit for partially correct answers
                    - Personalized feedback and explanations
                    - Identifies specific concepts you missed
                    
                    **Without AI Evaluation:**
                    - Faster evaluation (no API call)
                    - Works offline or when API is unavailable
                    - Uses simple keyword matching for short answers
                    """)
                
                # Display quiz if available
                if "quiz_data" in st.session_state and st.session_state.quiz_data:
                    # Initialize quiz state if needed
                    if "current_quiz_question" not in st.session_state:
                        st.session_state.current_quiz_question = 0
                    if "quiz_answers" not in st.session_state:
                        st.session_state.quiz_answers = []
                    if "quiz_score" not in st.session_state:
                        st.session_state.quiz_score = 0
                    if "quiz_completed" not in st.session_state:
                        st.session_state.quiz_completed = False
                    
                    # Quiz progress
                    total_questions = len(st.session_state.quiz_data)
                    current_q = st.session_state.current_quiz_question
                    
                    if not st.session_state.quiz_completed:
                        # Display progress
                        st.progress((current_q) / total_questions)
                        st.write(f"Question {current_q + 1} of {total_questions}")
                        
                        # Get current question data
                        question_data = st.session_state.quiz_data[current_q]
                        
                        # Display question
                        st.subheader(question_data["question"])
                        
                        # Different input methods based on question type
                        user_answer = None
                        if question_data["question_type"] == "multiple_choice":
                            user_answer = st.radio(
                                "Select your answer:",
                                question_data["options"],
                                key=f"mc_q{current_q}"
                            )
                        elif question_data["question_type"] == "true_false":
                            user_answer = st.radio(
                                "Select your answer:",
                                ["True", "False"],
                                key=f"tf_q{current_q}"
                            ) == "True"
                        elif question_data["question_type"] == "short_answer":
                            user_answer = st.text_input(
                                "Your answer:",
                                key=f"sa_q{current_q}"
                            )
                        
                        # Check if this question has been answered already
                        question_answered = f"submitted_q{current_q}" in st.session_state and st.session_state[f"submitted_q{current_q}"]

                        # Submit button (only show if not answered yet)
                        if not question_answered:
                            if st.button("Submit Answer", key=f"submit_q{current_q}"):
                                # Check if AI evaluation is enabled
                                if "use_ai_evaluation" in st.session_state and st.session_state.use_ai_evaluation:
                                    # Use AI evaluation
                                    result = evaluate_quiz_answer_with_gemini(question_data, user_answer)
                                else:
                                    # Use basic evaluation
                                    result = check_quiz_answer(question_data, user_answer)
                                
                                # Ensure quiz_answers is initialized and has enough elements
                                while len(st.session_state.quiz_answers) <= current_q:
                                    st.session_state.quiz_answers.append(None)
                                
                                # Store answer and result
                                st.session_state.quiz_answers[current_q] = {
                                    "question": question_data["question"],
                                    "user_answer": user_answer,
                                    "correct": result["correct"],
                                    "explanation": result["explanation"],
                                    # Add AI evaluation data if available
                                    "ai_evaluated": result.get("ai_evaluated", False),
                                    "feedback": result.get("feedback", ""),
                                    "score": result.get("score", 1.0 if result["correct"] else 0.0),
                                    "missing_concepts": result.get("missing_concepts", [])
                                }
                                
                                # Mark question as answered
                                st.session_state[f"submitted_q{current_q}"] = True
                                st.rerun()
                
                        # Show result if question has been answered
                        if question_answered:
                            # Make sure the index exists in the quiz_answers list
                            if current_q < len(st.session_state.quiz_answers):
                                result = st.session_state.quiz_answers[current_q]
                                if result["correct"]:
                                    st.success("Correct! " + result["explanation"])
                                else:
                                    st.error("Incorrect. " + result["explanation"])
                            
                                # Display additional feedback if AI evaluated
                                if "ai_evaluated" in result and result["ai_evaluated"]:
                                    if "feedback" in result and result["feedback"]:
                                        st.info(f"**Feedback:** {result['feedback']}")
                                    
                                    if "score" in result and "missing_concepts" in result:
                                        score_percent = int(result["score"] * 100)
                                        st.write(f"**Score:** {score_percent}%")
                                        
                                        if result["missing_concepts"]:
                                            st.write("**Concepts to review:**")
                                            for concept in result["missing_concepts"]:
                                                st.write(f"- {concept}")
                            else:
                                # If the answer was marked as submitted but doesn't exist in the answers list
                                st.warning("Answer data not found. Please try submitting again.")
                                # Reset the submission flag to allow resubmission
                                st.session_state[f"submitted_q{current_q}"] = False
                        
                        # Navigation buttons
                        nav_col1, nav_col2 = st.columns([1, 1])
                            
                        with nav_col1:
                            if current_q > 0 and st.button("Previous Question", key=f"prev_q_{current_q}"):
                                st.session_state.current_quiz_question -= 1
                                st.rerun()
                            
                        with nav_col2:
                            # Only show Next/Finish if current question is answered
                            if question_answered:
                                if current_q < total_questions - 1:
                                    if st.button("Next Question", key=f"next_q_{current_q}"):
                                        st.session_state.current_quiz_question += 1
                                        st.rerun()
                                else:
                                    if st.button("Finish Quiz", key=f"finish_q_{current_q}"):
                                        # Calculate final score
                                        correct_answers = sum(1 for a in st.session_state.quiz_answers if a["correct"])
                                        st.session_state.quiz_score = correct_answers
                                        st.session_state.quiz_completed = True
                                        st.rerun()
                    else:
                        # Quiz completed - show results
                        correct_answers = st.session_state.quiz_score
                        score_percent = (correct_answers / total_questions) * 100
                        
                        st.success(f"Quiz completed! Your score: {correct_answers}/{total_questions} ({score_percent:.1f}%)")
                        
                        # Display a chart
                        import matplotlib.pyplot as plt
                        
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.bar(["Correct", "Incorrect"], [correct_answers, total_questions - correct_answers], color=["#1E88E5", "#E53935"])
                        ax.set_ylabel("Number of Questions")
                        ax.set_title("Quiz Results")
                        st.pyplot(fig)
                        
                        # Review answers
                        st.subheader("Review Your Answers")
                        for i, answer_data in enumerate(st.session_state.quiz_answers):
                            with st.expander(f"Question {i+1}: {answer_data['question']}"):
                                st.write(f"**Your answer:** {answer_data['user_answer']}")
                                if answer_data["correct"]:
                                    st.success("Correct!")
                                else:
                                    st.error("Incorrect")
                                st.write(f"**Explanation:** {answer_data['explanation']}")
                                
                                # Display additional AI feedback when available
                                if "ai_evaluated" in answer_data and answer_data["ai_evaluated"]:
                                    if "feedback" in answer_data and answer_data["feedback"]:
                                        st.info(f"**Feedback:** {answer_data['feedback']}")
                                    
                                    if "score" in answer_data:
                                        score_percent = int(answer_data["score"] * 100)
                                        st.progress(answer_data["score"])
                                        st.write(f"**Score:** {score_percent}%")
                                    
                                    if "missing_concepts" in answer_data and answer_data["missing_concepts"]:
                                        st.write("**Concepts to review:**")
                                        for concept in answer_data["missing_concepts"]:
                                            st.write(f"- {concept}")
                        
                        # Reset button
                        if st.button("Take Another Quiz"):
                            # Reset quiz state
                            st.session_state.pop("quiz_data", None)
                            st.session_state.pop("current_quiz_question", None)
                            st.session_state.pop("quiz_answers", None)
                            st.session_state.pop("quiz_score", None)
                            st.session_state.pop("quiz_completed", None)
                            st.rerun()
                else:
                    st.info("Generate a quiz to get started!")

        with tab2:
            st.markdown('<div class="section-header">Study Aids</div>', unsafe_allow_html=True)
            Aid1, Aid2, Aid3 = st.tabs(["🔄 Flashcards", "🔍 Mind Map","🏛️ Memory Palace Generator"])
            # Flashcards Section
            with Aid1:
                st.markdown('<div class="section-header">Flashcards</div>', unsafe_allow_html=True)
                if st.button("Generate Flashcards", key="generate_flashcards"):
                    with st.spinner("Generating flashcards..."):
                        st.session_state.flashcards = generate_flashcards(st.session_state.summary)
                
                if "flashcards" in st.session_state and st.session_state.flashcards:
                    # Display flashcards
                    current_card_idx = st.session_state.get("current_flashcard", 0)
                    
                    # Navigation buttons
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        if st.button("Previous", key="prev_card") and current_card_idx > 0:
                            st.session_state.current_flashcard = current_card_idx - 1
                            st.rerun()
                    with col3:
                        if st.button("Next", key="next_card") and current_card_idx < len(st.session_state.flashcards) - 1:
                            st.session_state.current_flashcard = current_card_idx + 1
                            st.rerun()
                    
                    # Display current card
                    current_card = st.session_state.flashcards[current_card_idx]
                    st.markdown(f"### Card {current_card_idx + 1}/{len(st.session_state.flashcards)}")
                    
                    # Card display with flip functionality
                    if "show_answer" not in st.session_state:
                        st.session_state.show_answer = False
                        
                    st.markdown(f"**Question:** {current_card['front']}")
                    
                    if st.button("Reveal Answer" if not st.session_state.show_answer else "Hide Answer", key="flip_card"):
                        st.session_state.show_answer = not st.session_state.show_answer
                        
                    if st.session_state.show_answer:
                        st.markdown(f"**Answer:** {current_card['back']}")
                    
                    # Add Obsidian export functionality
                    st.markdown("### Export Flashcards")
                    obsidian_format = st.selectbox(
                        "Export format:",
                        options=["Obsidian (Q&A format)", "Obsidian (Basic format)", "Plain text"],
                        key="flashcard_export_format"
                    )
                    
                    if st.button("Download Flashcards", key="download_flashcards"):
                        # Create flashcard content based on selected format
                        if obsidian_format == "Obsidian (Q&A format)":
                            # Format for Spaced Repetition plugin (Question/Answer format)
                            content = "# Jñānasādhana Flashcards\n\n"
                            for i, card in enumerate(st.session_state.flashcards):
                                content += f"{card['front']}?\n"
                                content += "?\n"  # This is the separator in Obsidian Spaced Repetition
                                content += f"{card['back']}\n\n"
                        
                        elif obsidian_format == "Obsidian (Basic format)":
                            # Format for standard Obsidian notes with headers
                            content = "# Jñānasādhana Flashcards\n\n"
                            for i, card in enumerate(st.session_state.flashcards):
                                content += f"## Card {i+1}\n"
                                content += f"**Front:** {card['front']}\n\n"
                                content += f"**Back:** {card['back']}\n\n"
                        
                        else:  # Plain text
                            content = "# Flashcards\n\n"
                            for i, card in enumerate(st.session_state.flashcards):
                                content += f"Card {i+1}\n"
                                content += f"Front: {card['front']}\n"
                                content += f"Back: {card['back']}\n\n"
                        
                        # Provide download button
                        file_extension = ".md" if "Obsidian" in obsidian_format else ".txt"
                        st.download_button(
                            label=f"Download as {file_extension}",
                            data=content,
                            file_name=f"flashcards{file_extension}",
                            mime="text/plain"
                        )
            # Mind Map Section
            with Aid2:
                st.markdown('<div class="section-header">Mind Map</div>', unsafe_allow_html=True)
                if st.button("Generate Mind Map", key="generate_mindmap"):
                    with st.spinner("Generating mind map..."):
                        mind_map_data = generate_mind_map_data(st.session_state.summary)
                        if mind_map_data:
                            st.session_state.mind_map = mind_map_data
                
                if "mind_map" in st.session_state and st.session_state.mind_map:
                    # Display mind map
                    st.markdown("### Mind Map")
                    
                    # Create a simple HTML representation of the mind map
                    mind_map_html = f"""
                    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 10px;">
                        <h2 style="text-align: center; color: #1E88E5;">{st.session_state.mind_map['central_topic']}</h2>
                        <div style="display: flex; flex-wrap: wrap; justify-content: center;">
                    """
                    
                    for branch in st.session_state.mind_map['branches']:
                        mind_map_html += f"""
                        <div style="margin: 10px; padding: 15px; background-color: #e1f5fe; border-radius: 8px; width: 250px;">
                            <h3 style="color: #0277bd;">{branch['topic']}</h3>
                            <ul>
                        """
                        
                        for subtopic in branch['subtopics']:
                            mind_map_html += f"<li>{subtopic}</li>"
                        
                        mind_map_html += """
                            </ul>
                        </div>
                        """
                    
                    mind_map_html += """
                        </div>
                    </div>
                    """
                    
                    st.components.v1.html(mind_map_html, height=875)
                    
                    # Add download options for mind map
                    st.markdown("### Download Mind Map")
                    download_format = st.selectbox(
                        "Select Format:",
                        options=["JSON", "Markdown", "PDF"],
                        key="mind_map_download_format"
                    )
                    
                    if download_format == "JSON":
                        # Convert mind map to JSON for download
                        mind_map_json = json.dumps(st.session_state.mind_map, indent=4)
                        st.download_button(
                            label="Download Mind Map (JSON)",
                            data=mind_map_json,
                            file_name="mind_map.json",
                            mime="application/json"
                        )
                    elif download_format == "Markdown":
                        # Convert mind map to Markdown for download
                        mind_map_md = f"# {st.session_state.mind_map['central_topic']}\n\n"
                        
                        for branch in st.session_state.mind_map['branches']:
                            mind_map_md += f"## {branch['topic']}\n\n"
                            for subtopic in branch['subtopics']:
                                mind_map_md += f"- {subtopic}\n"
                            mind_map_md += "\n"
                        
                        st.download_button(
                            label="Download Mind Map (Markdown)",
                            data=mind_map_md,
                            file_name="mind_map.md",
                            mime="text/markdown"
                        )
                    elif download_format == "PDF":
                        # For PDF, we'll need to generate it using a library like reportlab
                        if st.button("Generate PDF"):
                            with st.spinner("Generating PDF..."):
                                try:
                                    # Import required libraries
                                    from reportlab.lib.pagesizes import letter
                                    from reportlab.lib import colors
                                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListItem, ListFlowable
                                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                                    from io import BytesIO
                                    
                                    # Create a BytesIO object to store the PDF
                                    buffer = BytesIO()
                                    
                                    # Create the PDF document
                                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                                    styles = getSampleStyleSheet()
                                    
                                    # Create custom styles
                                    title_style = ParagraphStyle(
                                        'Title',
                                        parent=styles['Title'],
                                        fontSize=18,
                                        textColor=colors.red
                                    )
                                    heading_style = ParagraphStyle(
                                        'Heading',
                                        parent=styles['Heading2'],
                                        fontSize=14,
                                        textColor=colors.blue
                                    )
                                    
                                    # Build the PDF content
                                    content = []
                                    
                                    # Add title
                                    content.append(Paragraph(st.session_state.mind_map['central_topic'], title_style))
                                    content.append(Spacer(1, 12))
                                    
                                    # Add branches and subtopics
                                    for branch in st.session_state.mind_map['branches']:
                                        content.append(Paragraph(branch['topic'], heading_style))
                                        content.append(Spacer(1, 6))
                                        
                                        # Create bullet points for subtopics
                                        subtopics = [ListItem(Paragraph(subtopic, styles['Normal'])) 
                                                   for subtopic in branch['subtopics']]
                                        content.append(ListFlowable(subtopics))
                                        content.append(Spacer(1, 12))
                                    
                                    # Build the PDF
                                    doc.build(content)
                                    
                                    # Get the PDF data
                                    pdf_data = buffer.getvalue()
                                    
                                    # Provide download button
                                    st.download_button(
                                        label="Download Mind Map (PDF)",
                                        data=pdf_data,
                                        file_name="mind_map.pdf",
                                        mime="application/pdf"
                                    )
                                except Exception as e:
                                    st.error(f"Error generating PDF: {str(e)}")
            # Mind Palace Section
            with Aid3:
                st.markdown('<div class="section-header">Mind Palace</div>', unsafe_allow_html=True)
                st.markdown("""
                    Create a virtual memory palace to help you memorize and recall information effectively.
                    The Mind Palace technique uses spatial memory and vivid imagery to store and retrieve information.
                """)
                
                if st.button("Generate Mind Palace", key="generate_mindpalace"):
                    with st.spinner("Creating your Mind Palace..."):
                        mind_palace_data = generate_mind_palace(st.session_state.summary)
                        if mind_palace_data:
                            st.session_state.mind_palace = mind_palace_data
                            st.success("Mind Palace created successfully!")
                
                # Display the Mind Palace if it exists
                if "mind_palace" in st.session_state and st.session_state.mind_palace:
                    # Display the Mind Palace structure
                    st.markdown(f"### {st.session_state.mind_palace['palace_name']}")
                    
                    # Create tabs for different views
                    tab1, tab2 = st.tabs(["Room View", "Memory Anchors"])
                    
                    with tab1:
                        # Room navigation
                        room_names = [room["name"] for room in st.session_state.mind_palace["rooms"]]
                        selected_room = st.selectbox("Select a Room", room_names)
                        
                        # Display selected room
                        for room in st.session_state.mind_palace["rooms"]:
                            if room["name"] == selected_room:
                                st.markdown(f"**Description:** {room['description']}")
                                
                                # Create columns for memory anchors
                                anchor_cols = st.columns(2)
                                
                                for i, anchor in enumerate(room["memory_anchors"]):
                                    with anchor_cols[i % 2]:
                                        with st.expander(f"📍 {anchor['location']}"):
                                            st.markdown(f"**Concept:** {anchor['concept']}")
                                            st.markdown(f"**Details:** {anchor['details']}")
                                            st.markdown(f"*{anchor['description']}*")
                    
                    with tab2:
                        # Flatten the memory anchors for practice
                        all_anchors = []
                        for room in st.session_state.mind_palace["rooms"]:
                            for anchor in room["memory_anchors"]:
                                anchor_with_room = anchor.copy()
                                anchor_with_room["room"] = room["name"]
                                all_anchors.append(anchor_with_room)
                        
                        # Memory practice mode
                        st.markdown("### Memory Practice Mode")
                        
                        # Make sure we have anchors
                        if all_anchors:
                            # Initialize practice state if needed
                            if "current_anchor" not in st.session_state or not st.session_state.current_anchor:
                                st.session_state.current_anchor = random.choice(all_anchors)
                            
                            # Display practice interface
                            st.markdown(f"**Location:** {st.session_state.current_anchor['room']} - {st.session_state.current_anchor['location']}")
                            
                            # Ask user to recall the concept
                            user_recall = st.text_input("What concept is associated with this location?")
                            
                            if user_recall:
                                if user_recall.lower() in st.session_state.current_anchor['concept'].lower():
                                    st.success(f"Correct! The concept is: {st.session_state.current_anchor['concept']}")
                                    st.markdown(f"**Details:** {st.session_state.current_anchor['details']}")
                                else:
                                    st.error(f"Incorrect. The concept was: {st.session_state.current_anchor['concept']}")
                                
                                if st.button("Next Location"):
                                    st.session_state.current_anchor = random.choice(all_anchors)
                                    st.experimental_rerun()
                        else:
                            st.warning("No memory anchors available. Please generate a Mind Palace with memory anchors.")
                    
                    # Add download options for Mind Palace
                    st.markdown("### Download Mind Palace")
                    
                    # Check if mind palace exists in session state
                    if "mind_palace" not in st.session_state or not st.session_state.mind_palace:
                        st.warning("No Mind Palace data available. Please generate a Mind Palace first.")
                    else:
                        palace_download_format = st.selectbox(
                            "Select Format:",
                            options=["JSON", "Markdown"],
                            key="mind_palace_download_format"
                        )
                        
                        if palace_download_format == "JSON":
                            palace_json = json.dumps(st.session_state.mind_palace, indent=4)
                            st.download_button(
                                label="Download Mind Palace (JSON)",
                                data=palace_json,
                                file_name="mind_palace.json",
                                mime="application/json"
                            )
                        elif palace_download_format == "Markdown":
                            palace_md = f"# {st.session_state.mind_palace['palace_name']}\n\n"
                            
                            for room in st.session_state.mind_palace["rooms"]:
                                palace_md += f"## {room['name']}\n"
                                palace_md += f"{room['description']}\n\n"
                                
                                palace_md += "### Memory Anchors\n"
                                for anchor in room["memory_anchors"]:
                                    palace_md += f"#### 📍 {anchor['location']}\n"
                                    palace_md += f"**Concept:** {anchor['concept']}\n"
                                    palace_md += f"**Details:** {anchor['details']}\n"
                                    palace_md += f"*{anchor['description']}*\n\n"
                            
                            st.download_button(
                                label="Download Mind Palace (Markdown)",
                                data=palace_md,
                                file_name="mind_palace.md",
                                mime="text/markdown"
                            )
                else:
                    st.error("Failed to create Mind Palace.")

        with tab3:
            st.markdown('<div class="section-header">Productivity and Focus</div>', unsafe_allow_html=True)
            Tool1, Tool2 = st.tabs(["⏱️ Focus Timer", "📔 Journal & Reflect"])
            with Tool1:
                st.markdown('<div class="section-header">Focus Timer</div>', unsafe_allow_html=True)
            
                # Initialize timer state
                if "timer_mode" not in st.session_state:
                    st.session_state.timer_mode = "pomodoro"  # Default mode
                if "timer_running" not in st.session_state:
                    st.session_state.timer_running = False
                if "timer_paused" not in st.session_state:
                    st.session_state.timer_paused = False
                if "time_left" not in st.session_state:
                    st.session_state.time_left = 25 * 60  # 25 minutes in seconds
                if "current_mode" not in st.session_state:
                    st.session_state.current_mode = "pomodoro"
                if "completed_pomodoros" not in st.session_state:
                    st.session_state.completed_pomodoros = 0
                
                # Define timer control functions
                def start_timer():
                    st.session_state.timer_running = True
                    st.session_state.timer_paused = False
                
                def pause_timer():
                    st.session_state.timer_paused = True
                
                def resume_timer():
                    st.session_state.timer_paused = False
                
                def reset_timer():
                    if st.session_state.current_mode == "pomodoro":
                        st.session_state.time_left = 25 * 60
                    elif st.session_state.current_mode == "short_break":
                        st.session_state.time_left = 5 * 60
                    else:  # long_break
                        st.session_state.time_left = 15 * 60
                
                def skip_to_next():
                    if st.session_state.current_mode == "pomodoro":
                        st.session_state.completed_pomodoros += 1
                        # After pomodoro, go to break
                        if st.session_state.completed_pomodoros % 4 == 0:
                            st.session_state.current_mode = "long_break"
                            st.session_state.time_left = 15 * 60
                        else:
                            st.session_state.current_mode = "short_break"
                            st.session_state.time_left = 5 * 60
                    else:
                        # After any break, go back to pomodoro
                        st.session_state.current_mode = "pomodoro"
                        st.session_state.time_left = 25 * 60
                
                # Timer settings
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Timer Settings")
                    timer_mode = st.radio(
                        "Select Timer Mode:",
                        options=["Pomodoro", "Short Break", "Long Break"],
                        index=0,
                        key="timer_mode_select",
                        horizontal=True
                    )
                    
                    # Set time based on mode
                    if timer_mode == "Pomodoro" and not st.session_state.timer_running:
                        st.session_state.time_left = 25 * 60  # 25 minutes
                        st.session_state.current_mode = "pomodoro"
                    elif timer_mode == "Short Break" and not st.session_state.timer_running:
                        st.session_state.time_left = 5 * 60  # 5 minutes
                        st.session_state.current_mode = "short_break"
                    elif timer_mode == "Long Break" and not st.session_state.timer_running:
                        st.session_state.time_left = 15 * 60  # 15 minutes
                        st.session_state.current_mode = "long_break"
                    
                    with col2:
                        st.subheader("Focus Tip")
                        st.info(generate_focus_tips())
                
                # Timer display
                mins, secs = divmod(st.session_state.time_left, 60)
                timer_display = f"{mins:02d}:{secs:02d}"
                
                st.markdown(f"""
                <div style="display: flex; justify-content: center; margin: 2rem 0;">
                    <div style="font-size: 5rem; font-weight: bold; color: #1E88E5; text-align: center;">
                        {timer_display}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Timer controls
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if not st.session_state.timer_running:
                        if st.button("Start", key="start_timer"):
                            start_timer()
                    else:
                        if st.session_state.timer_paused:
                            if st.button("Resume", key="resume_timer"):
                                resume_timer()
                        else:
                            if st.button("Pause", key="pause_timer"):
                                pause_timer()
                
                with col2:
                    if st.button("Reset", key="reset_timer"):
                        reset_timer()
                
                with col3:
                    if st.session_state.timer_running:
                        if st.button("Skip", key="skip_timer"):
                            skip_to_next()
                
                with col4:
                    st.metric("Completed Pomodoros", st.session_state.completed_pomodoros)
                
                # Progress bar
                if st.session_state.current_mode == "pomodoro":
                    total_time = 25 * 60
                elif st.session_state.current_mode == "short_break":
                    total_time = 5 * 60
                else:
                    total_time = 15 * 60
                
                progress = 1 - (st.session_state.time_left / total_time)
                st.progress(progress)
                
                # JavaScript for auto-updating timer (placeholder)
                st.markdown("""
                <script>
                    // This is a placeholder for JavaScript that would update the timer
                    // In a real implementation, we would use WebSockets or periodic polling
                </script>
                """, unsafe_allow_html=True)
                
                # Update the timer if running
                if st.session_state.timer_running and not st.session_state.timer_paused:
                    # In a real implementation, we'd handle this with JavaScript or polling
                    # For this demo, we'll update when the user interacts with the page
                    if st.session_state.time_left > 0:
                        st.session_state.time_left -= 1  # Decrease by 1 second on each rerun
                    else:
                        # Timer is complete, move to next mode
                        skip_to_next()
                    
                    # Auto-refresh the page every second while the timer is running
                    st.markdown("""
                    <meta http-equiv="refresh" content="1">
                    """, unsafe_allow_html=True)

            with Tool2:
                st.markdown('<div class="section-header">Journal & Reflect</div>', unsafe_allow_html=True)
                # Initialize journal state
                if "journal_entries" not in st.session_state:
                    st.session_state.journal_entries = get_journal_entries()
                if "current_prompt" not in st.session_state:
                    st.session_state.current_prompt = ""
                if "current_entry" not in st.session_state:
                    st.session_state.current_entry = ""
                if "prompt_type" not in st.session_state:
                    st.session_state.prompt_type = "reflection"
                
                # Journal sidebar with options
                Journal1, Journal2 = st.tabs(["📝Entries", "⚙️Options"])
                
                with Journal2:
                    st.subheader("Journaling Options")
                                                           
                    # View past entries
                    st.subheader("Past Entries")
                    
                    # Refresh entries button
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("Refresh Entries", key="refresh_entries"):
                            st.session_state.journal_entries = get_journal_entries()
                    with col2:
                        # Toggle for viewing all entries
                        if "view_all_entries" not in st.session_state:
                            st.session_state.view_all_entries = False
                        view_all = st.checkbox("View All Entries", value=st.session_state.view_all_entries, key="view_all_entries_checkbox")
                        if view_all != st.session_state.view_all_entries:
                            st.session_state.view_all_entries = view_all
                            st.rerun()
                    
                    # Display past entries
                    if st.session_state.journal_entries:
                        entries_to_display = st.session_state.journal_entries if st.session_state.view_all_entries else st.session_state.journal_entries[:5]
                        for i, entry in enumerate(entries_to_display):
                            with st.expander(f"{entry['date'].strftime('%Y-%m-%d %H:%M')}"):
                                st.markdown(f"**Prompt:** {entry['prompt']}")
                                st.markdown(f"**Reflection:** {entry['entry']}")
                                
                                # Add delete button for each entry
                                delete_col1, delete_col2 = st.columns([1, 1])
                                with delete_col1:
                                    if st.button("Delete Entry", key=f"delete_entry_{i}"):
                                        # Set confirmation state for this entry
                                        st.session_state[f"confirm_delete_{i}"] = True
                                
                                # Show confirmation if needed
                                if st.session_state.get(f"confirm_delete_{i}", False):
                                    with delete_col2:
                                        st.warning("Are you sure?")
                                        confirm_col1, confirm_col2 = st.columns([1, 1])
                                        with confirm_col1:
                                            if st.button("Yes", key=f"confirm_yes_{i}"):
                                                if delete_journal_entry(entry['filename']):
                                                    st.success("Entry deleted successfully!")
                                                    # Refresh the entries list
                                                    st.session_state.journal_entries = get_journal_entries()
                                                    # Reset confirmation state
                                                    st.session_state[f"confirm_delete_{i}"] = False
                                                    st.rerun()
                                                else:
                                                    st.error("Failed to delete entry. Please try again.")
                                        with confirm_col2:
                                            if st.button("No", key=f"confirm_no_{i}"):
                                                # Reset confirmation state
                                                st.session_state[f"confirm_delete_{i}"] = False
                                                st.rerun()
                    else:
                        st.info("No journal entries found. Start journaling to see your entries here.")
                
                with Journal1:
                    st.subheader("Journal Entry")
                    # Prompt type selector
                    prompt_type = st.selectbox(
                        "Select Prompt Type:",
                        options=["Reflection", "Gratitude", "Learning", "Goals", "Wellbeing"],
                        index=0,
                        key="prompt_type_select"
                    )
                    
                    # Map selection to function parameter
                    prompt_type_map = {
                        "Reflection": "reflection",
                        "Gratitude": "gratitude",
                        "Learning": "learning",
                        "Goals": "goals",
                        "Wellbeing": "wellbeing"
                    }
                    
                    st.session_state.prompt_type = prompt_type_map[prompt_type]
                    
                    # Generate new prompt button
                    if st.button("Generate New Prompt", key="generate_prompt"):
                        # Generate a prompt based on the selected type without content context
                        st.session_state.current_prompt = generate_journal_prompts(
                            prompt_type=st.session_state.prompt_type
                        )

                    # Display current prompt
                    if not st.session_state.current_prompt:
                        # Generate a default prompt if none exists (without content context)
                        st.session_state.current_prompt = generate_journal_prompts(
                            prompt_type=st.session_state.prompt_type
                        )
                    
                    st.markdown(f"""
                    <div style="background-color: rgba(30, 136, 229, 0.1); padding: 1rem; border-radius: 8px; border-left: 4px solid #1E88E5; margin-bottom: 1rem;">
                        <p style="font-style: italic; font-size: 1.1rem;">{st.session_state.current_prompt}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Journal entry text area
                    journal_entry = st.text_area(
                        "Your Reflection:",
                        value=st.session_state.current_entry,
                        height=300,
                        key="journal_entry",
                        placeholder="Start typing your thoughts here..."
                    )
                    
                    # Update current entry if changed
                    if journal_entry != st.session_state.current_entry:
                        st.session_state.current_entry = journal_entry
                    
                    # Save entry button
                    if st.button("Save Entry", key="save_entry"):
                        if st.session_state.current_entry.strip():
                            # Save the entry
                            success = save_journal_entry(
                                entry=st.session_state.current_entry,
                                prompt=st.session_state.current_prompt
                            )
                            
                            if success:
                                st.success("Journal entry saved successfully!")
                                # Clear the current entry
                                st.session_state.current_entry = ""
                                # Refresh the entries list
                                st.session_state.journal_entries = get_journal_entries()
                                # Generate a new prompt (without content context)
                                st.session_state.current_prompt = generate_journal_prompts(
                                    prompt_type=st.session_state.prompt_type
                                )
                                # Rerun to update the UI
                                st.rerun()
                            else:
                                st.error("Failed to save journal entry. Please try again.")
                        else:
                            st.warning("Please write something before saving.")
                    
                    # AI insights button
                    if st.session_state.current_entry.strip() and st.button("Get AI Insights", key="ai_insights"):
                        with st.spinner("Analyzing your reflection..."):
                            try:
                                # Initialize the Gemini model
                                model = setup_google_api()
                                if model:
                                    # Create prompt for Gemini
                                    prompt = f"""
                                    Analyze this journal entry thoughtfully and provide 3-5 insightful observations:

                                    PROMPT: {st.session_state.current_prompt}
                                    
                                    ENTRY: {st.session_state.current_entry}
                                    
                                    Your insights should:
                                    - Identify patterns, themes, or underlying emotions in their writing
                                    - Suggest connections they might not have noticed
                                    - Offer a new perspective or reframing of their experience
                                    - Highlight strengths or growth opportunities revealed in their writing
                                    - Be specific to their unique experience, not generic advice
                                    
                                    Format as bullet points, using a warm, supportive tone. Focus on deepening their self-awareness rather than solving problems.
                                    """
                                    
                                    # Generate response using Gemini
                                    response = model.generate_content(prompt)
                                    
                                    insights = response.text.strip()
                                    
                                    # Display the insights
                                    st.markdown("### AI Insights")
                                    st.markdown(f"""
                                    <div style="background-color: rgba(94, 53, 177, 0.1); padding: 1rem; border-radius: 8px; border-left: 4px solid #5E35B1; margin-top: 1rem;">
                                        {insights}
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.error("Could not initialize Gemini API. Please check your API key.")
                            except Exception as e:
                                st.error(f"Error generating insights: {str(e)}")

    else:
        st.info("Please upload a PDF document to get started.")
        
        # Add standalone journaling section when no PDF is uploaded
        st.markdown("---")
        st.markdown('<div class="section-header">📔 Journal & Reflect</div>', unsafe_allow_html=True)
        st.markdown("Use this journaling tool to reflect on your learning journey, regardless of whether you've uploaded a document.")
        
        # Initialize journal state
        if "standalone_journal_entries" not in st.session_state:
            st.session_state.standalone_journal_entries = get_journal_entries()
        if "standalone_current_prompt" not in st.session_state:
            st.session_state.standalone_current_prompt = ""
        if "standalone_current_entry" not in st.session_state:
            st.session_state.standalone_current_entry = ""
        if "standalone_prompt_type" not in st.session_state:
            st.session_state.standalone_prompt_type = "reflection"
        
        # Journal sidebar with options
        tab2, tab1 = st.tabs(["📝Entries", "⚙️Options"])
        
        with tab1:
            st.subheader("Journaling Options")
                       
            # View past entries
            st.subheader("Past Entries")
            
            # Refresh entries button
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Refresh Entries", key="standalone_refresh_entries"):
                    st.session_state.standalone_journal_entries = get_journal_entries()
            with col2:
                # Toggle for viewing all entries
                if "standalone_view_all_entries" not in st.session_state:
                    st.session_state.standalone_view_all_entries = False
                view_all = st.checkbox("View All Entries", value=st.session_state.standalone_view_all_entries, key="standalone_view_all_entries_checkbox")
                if view_all != st.session_state.standalone_view_all_entries:
                    st.session_state.standalone_view_all_entries = view_all
                    st.rerun()
            
            # Display past entries
            if st.session_state.standalone_journal_entries:
                entries_to_display = st.session_state.standalone_journal_entries if st.session_state.standalone_view_all_entries else st.session_state.standalone_journal_entries[:5]
                for i, entry in enumerate(entries_to_display):
                    with st.expander(f"{entry['date'].strftime('%Y-%m-%d %H:%M')}"):
                        st.markdown(f"**Prompt:** {entry['prompt']}")
                        st.markdown(f"**Reflection:** {entry['entry']}")
                        
                        # Add delete button for each entry
                        delete_col1, delete_col2 = st.columns([1, 1])
                        with delete_col1:
                            if st.button("Delete Entry", key=f"standalone_delete_entry_{i}"):
                                # Set confirmation state for this entry
                                st.session_state[f"standalone_confirm_delete_{i}"] = True
                        
                        # Show confirmation if needed
                        if st.session_state.get(f"standalone_confirm_delete_{i}", False):
                            with delete_col2:
                                st.warning("Are you sure?")
                                confirm_col1, confirm_col2 = st.columns([1, 1])
                                with confirm_col1:
                                    if st.button("Yes", key=f"standalone_confirm_yes_{i}"):
                                        if delete_journal_entry(entry['filename']):
                                            st.success("Entry deleted successfully!")
                                            # Refresh the entries list
                                            st.session_state.standalone_journal_entries = get_journal_entries()
                                            # Reset confirmation state
                                            st.session_state[f"standalone_confirm_delete_{i}"] = False
                                            st.rerun()
                                        else:
                                            st.error("Failed to delete entry. Please try again.")
                                    with confirm_col2:
                                        if st.button("No", key=f"standalone_confirm_no_{i}"):
                                            # Reset confirmation state
                                            st.session_state[f"standalone_confirm_delete_{i}"] = False
                                            st.rerun()
            else:
                st.info("No journal entries found. Start journaling to see your entries here.")
        
        with tab2:
            st.subheader("Journal Entry")
            
            # Prompt type selector
            prompt_type = st.selectbox(
                "Select Prompt Type:",
                options=["Reflection", "Gratitude", "Learning", "Goals", "Wellbeing"],
                index=0,
                key="standalone_prompt_type_select"
            )
            
            # Map selection to function parameter
            prompt_type_map = {
                "Reflection": "reflection",
                "Gratitude": "gratitude",
                "Learning": "learning",
                "Goals": "goals",
                "Wellbeing": "wellbeing"
            }
            
            st.session_state.standalone_prompt_type = prompt_type_map[prompt_type]
            
            # Generate new prompt button
            if st.button("Generate New Prompt", key="standalone_generate_prompt"):
                # Generate a prompt based on the selected type without content context
                st.session_state.standalone_current_prompt = generate_journal_prompts(
                    prompt_type=st.session_state.standalone_prompt_type
                )

            # Display current prompt
            if not st.session_state.standalone_current_prompt:
                # Generate a default prompt if none exists (without content context)
                st.session_state.standalone_current_prompt = generate_journal_prompts(
                    prompt_type=st.session_state.standalone_prompt_type
                )
            
            st.markdown(f"""
            <div style="background-color: rgba(30, 136, 229, 0.1); padding: 1rem; border-radius: 8px; border-left: 4px solid #1E88E5; margin-bottom: 1rem;">
                <p style="font-style: italic; font-size: 1.1rem;">{st.session_state.standalone_current_prompt}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Journal entry text area
            journal_entry = st.text_area(
                "Your Reflection:",
                value=st.session_state.standalone_current_entry,
                height=300,
                key="standalone_journal_entry",
                placeholder="Start typing your thoughts here..."
            )
            
            # Update current entry if changed
            if journal_entry != st.session_state.standalone_current_entry:
                st.session_state.standalone_current_entry = journal_entry
            
            # Save entry button
            if st.button("Save Entry", key="standalone_save_entry"):
                if st.session_state.standalone_current_entry.strip():
                    # Save the entry
                    success = save_journal_entry(
                        entry=st.session_state.standalone_current_entry,
                        prompt=st.session_state.standalone_current_prompt
                    )
                    
                    if success:
                        st.success("Journal entry saved successfully!")
                        # Clear the current entry
                        st.session_state.standalone_current_entry = ""
                        # Refresh the entries list
                        st.session_state.standalone_journal_entries = get_journal_entries()
                        # Generate a new prompt (without content context)
                        st.session_state.standalone_current_prompt = generate_journal_prompts(
                            prompt_type=st.session_state.standalone_prompt_type
                        )
                        # Rerun to update the UI
                        st.rerun()
                    else:
                        st.error("Failed to save journal entry. Please try again.")
                else:
                    st.warning("Please write something before saving.")
            
            # AI insights button
            if st.session_state.standalone_current_entry.strip() and st.button("Get AI Insights", key="standalone_ai_insights"):
                with st.spinner("Analyzing your reflection..."):
                    try:
                        # Initialize the Gemini model
                        model = setup_google_api()
                        if model:
                            # Create prompt for Gemini
                            prompt = f"""
                            Analyze this journal entry thoughtfully and provide 3-5 insightful observations:

                            PROMPT: {st.session_state.standalone_current_prompt}
                            
                            ENTRY: {st.session_state.standalone_current_entry}
                            
                            Your insights should:
                            - Identify patterns, themes, or underlying emotions in their writing
                            - Suggest connections they might not have noticed
                            - Offer a new perspective or reframing of their experience
                            - Highlight strengths or growth opportunities revealed in their writing
                            - Be specific to their unique experience, not generic advice
                            
                            Format as bullet points, using a warm, supportive tone. Focus on deepening their self-awareness rather than solving problems.
                            """
                            
                            # Generate response using Gemini
                            response = model.generate_content(prompt)
                            
                            insights = response.text.strip()
                            
                            # Display the insights
                            st.markdown("### AI Insights")
                            st.markdown(f"""
                            <div style="background-color: rgba(94, 53, 177, 0.1); padding: 1rem; border-radius: 8px; border-left: 4px solid #5E35B1; margin-top: 1rem;">
                                {insights}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.error("Could not initialize Gemini API. Please check your API key.")
                    except Exception as e:
                        st.error(f"Error generating insights: {str(e)}")

    # Add footer
    st.markdown("---")
    st.markdown('<div class="footer">Jñānasādhana - Your Companion in the Learning Journey</div>', unsafe_allow_html=True)
    st.markdown('<div class="footer">Created with ❤️ by Anuvakas</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()