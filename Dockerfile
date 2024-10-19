# Use the official Python image
FROM python:3.12

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

# Expose the port your app runs on
EXPOSE 8000

# Start the application (replace with your command)
CMD ["gunicorn", "tektome_ocr.wsgi:application", "--bind", "0.0.0.0:8000"]
