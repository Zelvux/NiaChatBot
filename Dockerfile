# 1. Lightweight base image
FROM python:3.10-slim

# 2. Environment settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV GIT_PYTHON_REFRESH=quiet

# 3. Minimal system dependencies (optimized)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# 4. Set working directory
WORKDIR /app

# 5. Copy requirements first (for caching)
COPY requirements.txt .

# 6. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy project files
COPY . .

# 8. Start bot
CMD ["python", "Zelvux.py"]
