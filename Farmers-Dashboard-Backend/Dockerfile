FROM python:3.9-slim

# Set working directory
WORKDIR /FarmerDashboard

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements.txt /FarmerDashboard/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY DataSlicer.py /FarmerDashboard/
COPY main.py /FarmerDashboard/
COPY fastAPI /FarmerDashboard/fastAPI

COPY utils.py /FarmerDashboard/
COPY create_view.py /FarmerDashboard/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]
