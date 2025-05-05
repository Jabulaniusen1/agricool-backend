FROM python:3.9-slim

# Set working directory
WORKDIR /ImpactDashboard

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements.txt /ImpactDashboard/
RUN pip install --upgrade pip && \
  pip install --no-cache-dir -r requirements.txt

# Copy project
COPY DataSlicer.py /ImpactDashboard/
COPY main.py /ImpactDashboard/
COPY queries_data.json /ImpactDashboard/
COPY tests/test_app.py /ImpactDashboard/
COPY fastAPI /ImpactDashboard/fastAPI

COPY utils.py /ImpactDashboard/
COPY create_view.py /ImpactDashboard/
COPY views/ /ImpactDashboard/views/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]
