# Use Python slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /bot

# Install system dependencies
ENV TZ=America/New_York
RUN apt-get update && apt-get install -y tzdata \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make startup script executable
RUN chmod +x startup.sh

# Set the startup script
ENTRYPOINT ["python3", "bot.py"]