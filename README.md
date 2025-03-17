# Jñānasādhana - AI-Powered Study Assistant

![Jñānasādhana Logo](Logo%20Updated.png)

## Overview

Jñānasādhana is an AI-powered study assistant that helps students and learners extract knowledge from PDF documents, generate study materials, and test their understanding through various interactive tools. Powered by Google's Gemini API, it transforms the way you study by providing intelligent content analysis and generation.

## Features

- **Multiple PDF Support**: Upload and process multiple documents simultaneously
- **Study Notes Generation**: Create structured notes in various formats:
  - Cornell Notes
  - Outline
  - Concept Map
  - Summary
- **Exam Question Generation**: Create practice questions based on your study material
- **Answer & Evaluation**: Test your knowledge and get AI feedback on your answers
- **Flashcards**: Generate and study with digital flashcards
- **Mind Maps**: Visualize connections between concepts
- **Mind Palace**: Create spatial memory associations for better retention
- **Interactive Quizzes**: Test your knowledge with different question types
- **Journal**: Record your learning reflections with AI-generated prompts
- **Focus Timer**: Stay productive with Pomodoro technique integration
- **Export**: Save all your study materials in Markdown or text format
- **Session Management**: Save and load your study sessions
- **Debug Tools**: View and analyze content being processed by the AI

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Gemini API key (from Google AI Studio)
- Internet connection for API access

### Installation

#### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/study-assistant.git
cd study-assistant
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Create a .env file in the root directory and add your Gemini API key:
```plaintext
GEMINI_API_KEY=your_api_key_here
```

### Running the Application

#### Local Development
Start the application using the run script:

```bash
python run.py
```

The application will be available at http://localhost:8501

#### Accessing from Mobile Devices
To access the app from mobile devices on the same network:

1. Find your computer's local IP address:
```bash
# Windows
ipconfig

# macOS/Linux
ifconfig
```

2. Access the app from your mobile device by entering:
```
http://YOUR_LOCAL_IP:8501
```

#### Docker Deployment
You can also run the application using Docker:

```bash
docker build -t study-assistant .
docker run -p 8501:8501 -e GEMINI_API_KEY=your_api_key_here study-assistant
```

## Usage Guide

1. **Upload Documents**: Upload one or more PDF documents containing study material
2. **Select Active Document**: Choose which document to work with or combine all documents
3. **Generate Study Materials**: Use the various tabs to create different types of study aids:
   - Generate structured notes
   - Create practice questions
   - Make flashcards
   - Visualize concepts with mind maps
   - Create a mind palace for spatial memory techniques
   - Test yourself with interactive quizzes
4. **Save Your Work**: Use the session management features to save and load your progress
5. **Export**: Download your study materials in your preferred format

## Data Storage

All data is stored locally:
- Study sessions are saved in the `study_sessions` directory
- Journal entries are stored in the `journals` directory
- User feedback is collected in the `feedback` directory

No data is sent to external servers except for the content sent to the Gemini API for processing.

## Testing & Feedback

During the testing phase, you can provide feedback directly through the application:
1. Use the feedback form in the sidebar
2. Select the type of feedback (bug report, feature request, etc.)
3. Provide detailed information about your experience
4. Submit the feedback, which will be saved locally for review

## Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `PRODUCTION_MODE`: Set to "true" for production deployment (optional)
- `DATABASE_URL`: Database connection string for future authentication (optional)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with Streamlit
- Powered by Google Gemini AI
- PDF processing with PyPDF2
- Visualization with Matplotlib