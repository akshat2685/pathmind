FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# We also need google-generativeai and pydantic which were added later
RUN pip install --no-cache-dir google-generativeai google-cloud-firestore

# Copy backend source
COPY . ./backend

# Expose port
EXPOSE 8080

# Command to run on Cloud Run
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
