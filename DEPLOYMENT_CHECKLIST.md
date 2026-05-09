# Vercel Deployment Checklist

Use this checklist to verify your application is ready for Vercel deployment.

## Pre-Deployment Verification

### Code & Configuration ✅

- [x] `app/main.py` contains FastAPI `app` instance
- [x] `pyproject.toml` includes `[tool.vercel]` section with entrypoint
- [x] `build.py` exists and runs without errors
- [x] Vercel configuration is defined in `pyproject.toml` (`vercel.json` is not required for this project)
- [x] `.vercelignore` excludes unnecessary files
- [x] All `__init__.py` files exist in app packages

### Dependencies ✅

- [x] `requirements.txt` is up to date
  ```bash
  pip freeze > requirements.txt
  ```
- [x] All production dependencies are listed
- [x] No development-only packages in requirements.txt
- [x] FastAPI and uvicorn are listed

### Environment Variables ✅

- [ ] `DATABASE_URL` is configured in Vercel
- [ ] `GCS_BUCKET_NAME` is configured in Vercel
- [ ] `.env.example` documents all variables
- [ ] Sensitive values are NOT in code or git
- [ ] Consider required vs optional variables

### Database ✅

- [ ] PostgreSQL database is prepared
- [ ] Connection string is correct (PostgreSQL+asyncpg format)
- [ ] Database accepts connections from Vercel
- [ ] All tables are created/migrated
- [ ] Service account for GCP is ready (if using)

### Application ✅

- [ ] Lifespan events are implemented (startup/shutdown)
- [ ] CORS is configured appropriately
- [ ] All routes are working locally
- [ ] API documentation is accessible
- [ ] Health check endpoint works: `GET /`

### Testing ✅

- [ ] Local development works: `uvicorn app.main:app --reload`
- [ ] All API endpoints respond correctly
- [ ] Database connection works
- [ ] GCS authentication works
- [ ] No `__pycache__` or `.pyc` files are committed

## Deployment Steps

### Step 1: Repository Setup

```bash
# Ensure all files are committed
git add .
git commit -m "Prepare for Vercel deployment"
git push origin main
```

### Step 2: Vercel Project Creation

- [ ] Go to https://vercel.com/new
- [ ] Connect your Git repository
- [ ] Select the project
- [ ] Click "Import"

### Step 3: Configure Environment Variables

- [ ] Add `DATABASE_URL`
- [ ] Add `GCS_BUCKET_NAME`
- [ ] Add `SERVICE_ACCOUNT_B64` (if needed)
- [ ] Add any other required variables from `.env.example`
- [ ] Apply to all environments

### Step 4: Deploy

- [ ] Click "Deploy"
- [ ] Wait for build to complete
- [ ] Monitor build logs for errors
- [ ] Check function logs after deployment

### Step 5: Verify Deployment

- [ ] Test health endpoint: `https://your-project.vercel.app/`
- [ ] Test API endpoints: `https://your-project.vercel.app/api/v1/...`
- [ ] Check Swagger docs: `https://your-project.vercel.app/docs`
- [ ] Monitor logs for errors
- [ ] Test database connectivity
- [ ] Test GCS connectivity

## Common Issues & Solutions

### Build Fails

- ✅ Check `build.py` output in Vercel dashboard
- ✅ Verify Python version is 3.11+
- ✅ Check all dependencies are in `requirements.txt`
- ✅ Look for import errors in app structure

### App Not Starting

- ✅ Verify `entrypoint` in `pyproject.toml` is correct
- ✅ Check `app/main.py` exports `app` instance
- ✅ Look at Function Logs in Vercel dashboard
- ✅ Verify environment variables are set

### Database Connection Errors

- ✅ Verify `DATABASE_URL` format (should use asyncpg)
- ✅ Check database allows connections from Vercel IPs
- ✅ Test connection string locally
- ✅ Ensure database is accessible and running

### GCS/Authentication Errors

- ✅ Verify `GCS_BUCKET_NAME` is correct and accessible
- ✅ Check `SERVICE_ACCOUNT_B64` is valid base64
- ✅ Verify service account has required permissions
- ✅ Test locally with same credentials

### Slow Performance

- ✅ Monitor function invocation time in Vercel dashboard
- ✅ Check database query performance
- ✅ Look for connection pool exhaustion
- ✅ Optimize slow endpoints
- ✅ Consider caching strategies

## Post-Deployment

### Monitoring

- [ ] Set up alerts for errors in Vercel dashboard
- [ ] Monitor function logs regularly
- [ ] Track response times and errors
- [ ] Monitor database connection pool

### Maintenance

- [ ] Keep dependencies updated: `pip list --outdated`
- [ ] Review Vercel deployment logs weekly
- [ ] Test critical endpoints regularly
- [ ] Keep backup of environment variables
- [ ] Document any custom configurations

### Security

- [ ] Review CORS configuration for production
- [ ] Consider adding authentication to admin endpoints
- [ ] Implement rate limiting if needed
- [ ] Regularly rotate service account keys
- [ ] Keep database credentials secure

## Useful Commands

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload

# Test build script
python build.py
```

### Vercel CLI Commands

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy to preview
vercel

# Deploy to production
vercel --prod

# View logs
vercel logs --follow

# Pull environment variables
vercel env pull
```

## Resources

- [Vercel Deployment Guide](./VERCEL_DEPLOYMENT.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Vercel Python Runtime](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- [AsyncPG Documentation](https://magicstack.github.io/asyncpg/)
