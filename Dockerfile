FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create .env file if it doesn't exist
RUN touch .env

# Expose port (if needed for webhooks)
EXPOSE 8000

# Run the bot
CMD ["python", "main.py"] 