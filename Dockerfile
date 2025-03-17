# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/service_account.json"
ENV GEMINI_API_KEY=""
ENV PRODUCTION_MODE="true"
ENV DATABASE_URL=""
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Create necessary directories
RUN mkdir -p /app/study_sessions /app/feedback

# Install system dependencies and Python dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    xclip \
    xvfb \
    xauth \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set permissions for app directories
RUN chmod -R 777 /app/study_sessions /app/feedback

# Define environment variable for Streamlit
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200

# Expose the port the app runs on
EXPOSE 8501

# Run run.py within xvfb-run when the container launches
CMD xvfb-run python run.py --server.address=0.0.0.0 --server.port=${PORT:-8501}