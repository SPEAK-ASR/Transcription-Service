# Deployment Guide

## Sinhala ASR Dataset Collection Service Deployment

This guide covers various deployment options for the Sinhala ASR Dataset Collection Service, from local development to production cloud deployment.

---

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Google Cloud Run](#google-cloud-run)
4. [Traditional Server Deployment](#traditional-server-deployment)
5. [Database Setup](#database-setup)
6. [Google Cloud Storage Setup](#google-cloud-storage-setup)
7. [Environment Configuration](#environment-configuration)
8. [Monitoring and Logging](#monitoring-and-logging)

---

## Local Development

### Prerequisites
- Python 3.12 or higher
- PostgreSQL database
- Google Cloud Storage bucket
- Git

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd transcription_service
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the development server:**
   ```bash
   python run_server.py
   ```

The service will be available at http://localhost:8000

---

## Docker Deployment

### Build and Run Locally

1. **Build the Docker image:**
   ```bash
   docker build -t sinhala-asr-service .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name sinhala-asr-service \
     -p 8000:8000 \
     --env-file .env \
     sinhala-asr-service
   ```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/sinhala_asr
      - GCS_BUCKET_NAME=your-bucket-name
    depends_on:
      - db
    volumes:
      - ./static:/app/static
      - ./templates:/app/templates

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=sinhala_asr
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

Run with:
```bash
docker-compose up -d
```

---

## Google Cloud Run

### Prerequisites
- Google Cloud Project with billing enabled
- Google Cloud CLI installed and authenticated
- Docker installed

### Deployment Steps

1. **Build and push to Google Container Registry:**
   ```bash
   # Set project ID
   export PROJECT_ID=your-google-cloud-project-id
   
   # Build and tag image
   docker build -t gcr.io/$PROJECT_ID/sinhala-asr-service .
   
   # Push to registry
   docker push gcr.io/$PROJECT_ID/sinhala-asr-service
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy sinhala-asr-service \
     --image gcr.io/$PROJECT_ID/sinhala-asr-service \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars DATABASE_URL="your-database-url" \
     --set-env-vars GCS_BUCKET_NAME="your-bucket-name" \
     --set-env-vars SERVICE_ACCOUNT_B64="your-service-account-base64" \
     --memory 2Gi \
     --cpu 2 \
     --max-instances 10
   ```

3. **Set up custom domain (optional):**
   ```bash
   gcloud run domain-mappings create \
     --service sinhala-asr-service \
     --domain your-domain.com \
     --region us-central1
   ```

---

## Traditional Server Deployment

### Using systemd (Ubuntu/Debian)

1. **Install system dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3.12 python3.12-venv postgresql-client nginx
   ```

2. **Create deployment directory:**
   ```bash
   sudo mkdir -p /opt/sinhala-asr-service
   sudo chown $USER:$USER /opt/sinhala-asr-service
   ```

3. **Deploy application:**
   ```bash
   cd /opt/sinhala-asr-service
   git clone <repository-url> .
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Create systemd service:**
   ```bash
   sudo nano /etc/systemd/system/sinhala-asr-service.service
   ```

   ```ini
   [Unit]
   Description=Sinhala ASR Dataset Collection Service
   After=network.target

   [Service]
   Type=exec
   User=www-data
   Group=www-data
   WorkingDirectory=/opt/sinhala-asr-service
   Environment=PATH=/opt/sinhala-asr-service/venv/bin
   ExecStart=/opt/sinhala-asr-service/venv/bin/gunicorn \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000 \
     app.main:app
   ExecReload=/bin/kill -HUP $MAINPID
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

5. **Enable and start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable sinhala-asr-service
   sudo systemctl start sinhala-asr-service
   ```

6. **Configure Nginx reverse proxy:**
   ```bash
   sudo nano /etc/nginx/sites-available/sinhala-asr-service
   ```

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /static {
           alias /opt/sinhala-asr-service/static;
           expires 1y;
           add_header Cache-Control "public, immutable";
       }
   }
   ```

   ```bash
   sudo ln -s /etc/nginx/sites-available/sinhala-asr-service /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

---

## Database Setup

### PostgreSQL (Recommended)

1. **Install PostgreSQL:**
   ```bash
   # Ubuntu/Debian
   sudo apt install postgresql postgresql-contrib
   
   # macOS
   brew install postgresql
   ```

2. **Create database and user:**
   ```sql
   sudo -u postgres psql
   
   CREATE DATABASE sinhala_asr_db;
   CREATE USER sinhala_asr_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE sinhala_asr_db TO sinhala_asr_user;
   \q
   ```

3. **Create database tables:**
   The application will automatically create tables on first run. Alternatively, you can create them manually:
   ```sql
   -- Audio table
   CREATE TABLE "Audio" (
       audio_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       audio_filename TEXT NOT NULL UNIQUE,
       google_transcription TEXT,
       transcription_count INTEGER DEFAULT 0,
       leased_until TIMESTAMP WITH TIME ZONE
   );

   -- Transcriptions table
   CREATE TABLE "Transcriptions" (
       trans_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       audio_id UUID REFERENCES "Audio"(audio_id) ON DELETE CASCADE,
       transcription TEXT NOT NULL,
       speaker_gender VARCHAR(20) DEFAULT 'cannot_recognized',
       has_noise BOOLEAN DEFAULT FALSE,
       is_code_mixed BOOLEAN DEFAULT FALSE,
       is_speaker_overlappings_exist BOOLEAN DEFAULT FALSE,
       is_audio_suitable BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   ```

### Supabase (Cloud PostgreSQL)

1. **Create a Supabase project:**
   - Go to https://supabase.com
   - Create a new project
   - Note the database URL from Project Settings > Database

2. **Configure connection:**
   ```bash
   DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres
   ```

---

## Google Cloud Storage Setup

1. **Create a GCS bucket:**
   ```bash
   gsutil mb gs://your-sinhala-asr-bucket
   ```

2. **Set bucket permissions:**
   ```bash
   # Make bucket publicly readable (for signed URLs)
   gsutil iam ch allUsers:objectViewer gs://your-sinhala-asr-bucket
   ```

3. **Create service account:**
   ```bash
   gcloud iam service-accounts create sinhala-asr-service \
     --display-name="Sinhala ASR Service Account"
   
   # Grant Storage Object Viewer permissions
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:sinhala-asr-service@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/storage.objectViewer"
   
   # Create and download key
   gcloud iam service-accounts keys create key.json \
     --iam-account=sinhala-asr-service@PROJECT_ID.iam.gserviceaccount.com
   ```

4. **Convert to base64:**
   ```bash
   # Linux/macOS
   base64 -i key.json
   
   # Windows PowerShell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("key.json"))
   ```

---

## Environment Configuration

### Production Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# Google Cloud Storage
GCS_BUCKET_NAME=your-production-bucket
SERVICE_ACCOUNT_B64=your_base64_encoded_service_account

# Application Settings
DEBUG=false
AUDIO_LEASE_TIMEOUT_MINUTES=30
MAX_TRANSCRIPTIONS_PER_AUDIO=3

# Security (if applicable)
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=["https://yourdomain.com"]
```

### Environment Validation

The application validates required environment variables on startup:
- `DATABASE_URL` - Must be a valid PostgreSQL connection string
- `GCS_BUCKET_NAME` - Must be a valid GCS bucket name

---

## Monitoring and Logging

### Application Logs

The application uses Python's logging module. Configure log levels:

```python
# In production, set to INFO or WARNING
logging.basicConfig(level=logging.INFO)
```

### Health Checks

Set up monitoring for these endpoints:
- `GET /health` - Basic health check
- `GET /` - Root endpoint with service info

### Metrics Collection

Consider implementing metrics collection:
```python
# Example with Prometheus
from prometheus_client import Counter, Histogram

TRANSCRIPTION_COUNTER = Counter('transcriptions_total', 'Total transcriptions')
AUDIO_PROCESSING_TIME = Histogram('audio_processing_seconds', 'Audio processing time')
```

### Docker Health Checks

The Dockerfile includes health checks:
```dockerfile
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1
```

---

## Security Considerations

### Production Checklist

- [ ] Use HTTPS in production
- [ ] Restrict CORS origins
- [ ] Implement rate limiting
- [ ] Use strong database passwords
- [ ] Rotate service account keys regularly
- [ ] Enable database connection encryption
- [ ] Set up proper firewall rules
- [ ] Use environment variables for secrets
- [ ] Enable audit logging
- [ ] Regular security updates

### Example Nginx SSL Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

---

## Troubleshooting

### Common Issues

1. **Database Connection Errors:**
   ```bash
   # Check database connectivity
   psql "postgresql://user:password@host:5432/database" -c "SELECT 1"
   ```

2. **GCS Authentication Issues:**
   ```bash
   # Test service account
   gcloud auth activate-service-account --key-file=key.json
   gsutil ls gs://your-bucket
   ```

3. **Port Already in Use:**
   ```bash
   # Find process using port 8000
   lsof -i :8000
   kill -9 <PID>
   ```

4. **Memory Issues:**
   - Increase Docker memory limits
   - Reduce number of Gunicorn workers
   - Monitor memory usage with `htop` or `docker stats`

### Log Analysis

```bash
# Docker logs
docker logs sinhala-asr-service

# Systemd logs
sudo journalctl -u sinhala-asr-service -f

# Application logs
tail -f /var/log/sinhala-asr-service.log
```

---

## Backup and Recovery

### Database Backup

```bash
# Create backup
pg_dump "postgresql://user:password@host:5432/database" > backup.sql

# Restore backup
psql "postgresql://user:password@host:5432/database" < backup.sql
```

### Automated Backups

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump "$DATABASE_URL" > "/backups/sinhala_asr_$DATE.sql"
find /backups -name "sinhala_asr_*.sql" -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh
```

---

This deployment guide covers the most common deployment scenarios. Choose the method that best fits your infrastructure and requirements.
