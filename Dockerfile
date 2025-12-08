# Use a lightweight Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirement files and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code (including your bot files)
COPY . /app

# Command to run the application (the entry point)
CMD ["python", "dropshipping_bot.py"]