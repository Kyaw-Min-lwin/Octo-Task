# Use a lightweight Python image
FROM python:3.9-slim

# Set working directory to /app
WORKDIR /app

# Copy requirements first (to cache dependencies)
COPY requirements.txt .

# Install dependencies
# We use --no-cache-dir to keep the image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create a non-root user (Hugging Face security requirement)
# We set the owner of /app to this user so it can write temp files
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

# Expose the magic port 7860
EXPOSE 7860

# Command to run the app
# Binding to 0.0.0.0:7860 is CRITICAL for HF Spaces
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]