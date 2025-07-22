# 🔥 Start with slim Python
FROM python:3.9-slim

# 📦 Install system dependencies for Plotly 3D
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 📁 Set working directory
WORKDIR /app

# ⬇️ Copy all your app files
COPY . /app

# 📦 Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 🌍 Expose Streamlit default port
EXPOSE 8501

# 🚀 Run your Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
