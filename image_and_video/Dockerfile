FROM python:3.11

EXPOSE 8501
WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY app/ .

RUN pip3 install -r requirements.txt

# Create directories for temporary files
RUN mkdir -p /app/temp/images /app/temp/videos /app/temp/music

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]