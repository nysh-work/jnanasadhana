# Jñānasādhana Study Assistant Architecture

This document outlines the technical architecture of the Jñānasādhana Study Assistant application.

## System Overview

Jñānasādhana is a web-based study assistant application built with Streamlit and powered by Google's Gemini AI. The application helps students extract, analyze, and study content from various sources including PDFs, images, and audio.

## Architecture Diagram
+----------------------------------+
|           User Interface         |
|           (Streamlit)            |
+------------------+---------------+
|
+------------------v---------------+
|        Application Logic         |
|     (Python/Streamlit/Gemini)    |
+------------------+---------------+
|
+--------+---------+--------+------+
|        |                  |      |
v        v                  v      v
+--------+----+  +----------+  +---+------+
| Database    |  | File      |  | External |
| (SQLite)    |  | Storage   |  | APIs     |
+-------------+  +-----------+  +----------+

## Component Descriptions

### 1. User Interface (Streamlit)

The frontend is built using Streamlit, providing a responsive and interactive web interface. Key UI components include:

- Authentication forms (login/register)
- Document upload interface
- Study material generation controls
- Interactive study tools (flashcards, quizzes, etc.)
- Session management interface
- Export functionality

### 2. Application Logic

The core application logic is written in Python and handles:

- User authentication and session management
- Document processing (PDF extraction, OCR, audio transcription)
- AI-powered content generation (questions, notes, flashcards)
- Study tools functionality (quizzes, spaced repetition)
- Data persistence

### 3. Database (SQLite)

The application uses SQLite for data persistence, storing:

- User accounts and authentication data
- Saved study sessions
- Learning progress and statistics
- Application settings

### 4. File Storage

Local file storage is used for:

- Temporary document storage during processing
- Cached study materials for offline use
- Exported study materials

### 5. External APIs

The application integrates with external services:

- Google Gemini API for AI-powered content generation
- (Future) Cloud storage APIs for document sync
- (Future) Third-party learning platform integrations

## Data Flow

1. **Document Processing Flow**
   - User uploads document → Document processed → Text extracted → Content stored in session state
   - AI generates study materials → Materials displayed to user → User can save/export

2. **Authentication Flow**
   - User registers/logs in → Credentials verified → Session authenticated → User-specific data loaded

3. **Study Session Flow**
   - User creates/loads session → Study materials generated/loaded → User interacts with materials → Progress tracked → Session saved

## Technical Considerations

### Security

- Passwords are hashed using SHA-256
- Session data is stored securely
- API keys are managed via environment variables

### Scalability

- Document processing is optimized for large files
- AI requests are batched and cached where possible
- Database queries are optimized for performance

### Extensibility

The architecture is designed to be modular, allowing for:

- New study tool types to be added
- Additional document formats to be supported
- Integration with other learning platforms

## Future Architectural Enhancements

- Migrate to a cloud-based database for better scalability
- Implement a proper backend API service separate from the UI
- Add real-time collaboration features
- Implement progressive web app capabilities for offline use