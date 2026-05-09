# Vercel Deployment Guide

This document provides comprehensive instructions for deploying the Sinhala ASR Transcription Service to Vercel.

## Prerequisites

- Vercel account (https://vercel.com)
- GitHub, GitLab, or Bitbucket account (for Git integration)
- Vercel CLI installed: `npm install -g vercel` (optional for local development)
- Docker (optional, for local testing)

## Application Overview

The application is a FastAPI service with:

- **Entrypoint**: `app.main:app` (FastAPI instance)
- **Python Version**: 3.11+
- **Runtime**: Python on Vercel with automatic deployment as a single Function
- **Memory**: 1024 MB (configurable)
- **Timeout**: 60 seconds (configurable)

## Step 1: Prepare Your Code

Ensure your repository has the following files:

✅ **Required:**

- `pyproject.toml` - Python project configuration with `[tool.vercel]` section
- `requirements.txt` - Python dependencies
- `app/main.py` - FastAPI application entrypoint
- `build.py` - Build script for Vercel (included)

✅ **Recommended:**

- `.vercelignore` - Files to exclude from deployment
- `vercel.json` - Vercel configuration (included)
- `.env.example` - Environment variable template

## Step 2: Environment Variables Setup

Before deployment, configure the following environment variables in Vercel:

### Required Variables

```
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
GCS_BUCKET_NAME=your-bucket-name
```

### Optional Variables

```
SERVICE_ACCOUNT_B64=base64-encoded-service-account-json
DEBUG=false
ALLOWED_HOSTS=*
```

See `.env.example` for all available configuration options.

## Step 3: Deploy via Git Integration (Recommended)

### Using GitHub

1. Push your code to GitHub
2. Go to https://vercel.com/new
3. Select "Import Git Repository"
4. Authorize and select your repository
5. Import the project
6. Configure environment variables:
   - Click "Environment Variables"
   - Add each required variable
   - Apply to all environments (Production, Preview, Development)
7. Click "Deploy"

### Using GitLab or Bitbucket

Follow the same steps as GitHub using the respective platform authorization.

## Step 4: Deploy via CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy to production
vercel --prod

# Or deploy with environment variables from .env file
vercel env pull
vercel --prod
```

## Step 5: Configure Project Settings (if needed)

After initial deployment, you can customize in Vercel Dashboard:

1. Go to Project Settings > Functions
   - **Memory**: 1024 MB (sufficient for most use cases)
   - **Timeout**: 60 seconds (max for Vercel)
   - **Runtime**: Python 3.11

2. Go to Project Settings > Environment Variables
   - Update values as needed
   - Changes require redeployment

3. Go to Deployments
   - Monitor deployment logs
   - View function invocation metrics

## Step 6: Verify Deployment

### Test Health Check

```bash
curl https://your-project.vercel.app/
# Expected response:
# {
#   "message": "Sinhala ASR Dataset Creation Service",
#   "status": "active",
#   "version": "1.0.0"
# }
```

### Test API Endpoints

```bash
# Get available audio files
curl https://your-project.vercel.app/api/v1/audio

# Check API documentation
https://your-project.vercel.app/docs
```

### View Logs

```bash
# In Vercel Dashboard:
# 1. Select your project
# 2. Click "Deployments"
# 3. Select latest deployment
# 4. Click "Function Logs"

# Or via CLI:
vercel logs --follow
```

## Configuration Details

### pyproject.toml

The `[tool.vercel]` section specifies:

```toml
[tool.vercel]
entrypoint = "app.main:app"

[tool.vercel.scripts]
build = "python build.py"
```

This tells Vercel to:

- Look for FastAPI app named `app` in `app/main.py`
- Run `build.py` during build phase for pre-deployment setup

### vercel.json

Configures:

- **buildCommand**: Custom build process
- **functions**: Function-specific settings (memory, timeout, runtime)
- **headers**: HTTP headers for caching and security
- **rewrites**: Route rewrites to the FastAPI app

### Build Process

The build process (via `build.py`):

1. Validates Python version (3.11+)
2. Checks critical dependencies
3. Validates application configuration
4. Verifies required environment variables

## Limitations

Vercel Functions have the following constraints:

### Size Limits

- **Application Bundle**: Maximum 500MB
- **Unzipped**: Maximum 250MB

Our bundling process removes:

- `__pycache__` directories
- `.pyc` files
- `.vercelignore` listed files

### Runtime Limits

- **Maximum execution time**: 60 seconds
- **Concurrent requests**: Scales with traffic using Fluid compute
- **Memory per function**: 1024 MB (configurable)

### What's NOT Supported

- Long-running background jobs (> 60 seconds)
- WebSocket connections
- Custom protocols (use HTTP/HTTPS only)
- File system writes (except `/tmp`)

### Recommendations

- Keep request processing time < 50 seconds
- Use external services for heavy computation
- Stream large responses
- Implement proper error handling and timeouts

## Troubleshooting

### Build Failures

**Problem**: Build fails with dependency errors

**Solution**:

```bash
# Ensure requirements.txt is up to date
pip freeze > requirements.txt

# Verify local installation works
pip install -r requirements.txt

# Check for circular dependencies
pipdeptree
```

**Problem**: Build fails with import errors

**Solution**:

```bash
# Verify PYTHONPATH includes app directory
# Check that __init__.py files exist in all packages
find app -type d -exec touch {}/__init__.py \;

# Verify app/main.py can be imported locally
python -c "from app.main import app; print(app)"
```

### Runtime Errors

**Problem**: "No module named 'app'"

**Solution**:

- Verify `pyproject.toml` has correct entrypoint: `app.main:app`
- Ensure all `__init__.py` files exist
- Check PYTHONPATH configuration

**Problem**: Database connection timeout

**Solution**:

- Verify `DATABASE_URL` environment variable is set
- Check database accepts connections from Vercel IP range
- Ensure connection string is correct format
- Consider connection pooling for AsyncPG

**Problem**: GCS authentication fails

**Solution**:

- Verify `GCS_BUCKET_NAME` is set and correct
- Check `SERVICE_ACCOUNT_B64` is properly base64 encoded
- Ensure service account has required permissions:
  - `storage.objects.get`
  - `storage.objects.list`

### Environment Variables Not Applied

**Problem**: Environment variables not working after deployment

**Solution**:

1. Verify variables are set in Project Settings
2. Redeploy project: `vercel --prod`
3. Check deployment logs for environment variable values
4. Clear function cache: Deployments > Redeploy

### Performance Issues

**Problem**: API responses are slow (> 5 seconds)

**Solution**:

```bash
# Check function metrics in Vercel Dashboard
# Monitor database query performance
# Optimize database queries (add indexes, etc.)
# Consider caching frequently accessed data
# Use pagination for large result sets
```

## Monitoring and Logging

### Via Vercel Dashboard

1. Project > Deployments > Select deployment
2. Click "Function Logs" to view real-time logs
3. Filter by status (error, warning, log, etc.)

### Via Vercel CLI

```bash
# Follow live logs
vercel logs --follow

# View logs for specific deployment
vercel logs <deployment-id>

# Filter by severity
vercel logs --error
```

### Application Logs

The application uses Python's built-in `logging` module:

- **Startup logs**: GCP auth, database initialization
- **Request logs**: API endpoint access
- **Error logs**: Exceptions and failures
- **Shutdown logs**: Resource cleanup

Configure log level via `DEBUG` environment variable in `app/core/config.py`

## Database Connections

### PostgreSQL on Vercel

For PostgreSQL database, you have options:

1. **Supabase** (Recommended)
   - Hosted PostgreSQL with Vercel integration
   - Free tier available
   - Setup: https://supabase.com

2. **Self-hosted PostgreSQL**
   - Ensure it accepts connections from Vercel IP range
   - May require firewall rules

3. **AWS RDS**
   - Managed PostgreSQL database
   - Configure security groups to allow Vercel

### Connection Configuration

Use this format for `DATABASE_URL`:

```
postgresql+asyncpg://user:password@host:port/database
```

Example with Supabase:

```
postgresql+asyncpg://postgres:password@db.supabase.co:5432/postgres
```

## Security Considerations

### Secrets Management

✅ **Do:**

- Store secrets in Vercel Environment Variables (encrypted)
- Use `.env.example` for non-secret configuration
- Add `.env` to `.gitignore`
- Rotate credentials regularly

❌ **Don't:**

- Commit `.env` files to Git
- Store secrets in code comments
- Expose secrets in error messages
- Use dummy credentials in production

### API Security

- CORS is configured to allow all origins (configurable in app/core/config.py)
- Add authentication middleware as needed
- Validate all user inputs
- Use HTTPS only (automatic with Vercel)
- Implement rate limiting for production

## Cost Estimation

Vercel's free tier includes:

- **Serverless Functions**: 100 GB-hours/month
- **Bandwidth**: 100 GB/month
- **Deployments**: Unlimited
- **Teams**: 1 member

For typical usage:

- 1M requests/month with 100ms processing = ~28 GB-hours
- Should fit comfortably in free tier

See https://vercel.com/pricing for paid tier details.

## Additional Resources

- [Vercel Python Runtime](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/concepts/)
- [AsyncPG Documentation](https://magicstack.github.io/asyncpg/)
- [Google Cloud Storage Python Client](https://cloud.google.com/python/docs/reference/storage/latest)

## Support

For issues or questions:

1. Check Vercel logs in Dashboard
2. Review this deployment guide
3. Check [Vercel Discord Community](https://discord.gg/vercel)
4. Contact Vercel Support
