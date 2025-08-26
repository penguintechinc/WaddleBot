# WaddleBot MinIO S3-Compatible Storage Setup

This document describes how to set up and use MinIO S3-compatible object storage for WaddleBot image management and CDN functionality.

## Quick Start (Development)

### 1. Start the Development Environment

```bash
# Start all services including MinIO
docker-compose -f docker-compose.minio.yml up -d

# Check service status
docker-compose -f docker-compose.minio.yml ps
```

### 2. Access Services

- **WaddleBot Portal**: http://localhost:8000
- **MinIO Console**: http://localhost:9001
- **MinIO API**: http://localhost:9000
- **Direct Image Access**: http://localhost/images/

**MinIO Credentials**:
- Username: `waddlebot`
- Password: `waddlebot123`

### 3. Test Image Upload

1. Log into the portal at http://localhost:8000
2. Navigate to **Images** from the menu
3. Upload a test image
4. Verify it appears in MinIO console and is accessible via URL

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WaddleBot     │    │      Nginx      │    │     MinIO       │
│    Portal       │◄──►│   Proxy/CDN     │◄──►│   S3 Storage    │
│                 │    │                 │    │                 │
│ - Image Upload  │    │ - Static Serve  │    │ - Object Store  │
│ - Gallery       │    │ - Caching       │    │ - Public Access │
│ - Management    │    │ - CORS          │    │ - Versioning    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────►│   PostgreSQL    │◄─────────────┘
                        │   Database      │
                        │                 │
                        │ - Image Meta    │
                        │ - User Data     │
                        │ - Communities   │
                        └─────────────────┘
```

## Storage Structure

MinIO organizes images in a hierarchical structure:

```
waddlebot-assets/
├── images/
│   ├── avatar/
│   │   ├── user_123/
│   │   │   ├── 20240101_120000_abc123.jpg
│   │   │   ├── 20240101_120000_abc123_small.jpg
│   │   │   ├── 20240101_120000_abc123_medium.jpg
│   │   │   └── 20240101_120000_abc123_large.jpg
│   │   └── user_456/
│   ├── community_icon/
│   │   ├── community_1/
│   │   └── community_2/
│   └── general/
│       ├── user_123/
│       └── user_456/
└── static/
    ├── css/
    ├── js/
    └── fonts/
```

## Configuration

### Environment Variables

**Portal Configuration**:
```bash
# Enable S3 storage
S3_STORAGE_ENABLED=true
S3_BUCKET_NAME=waddlebot-assets
S3_REGION=us-east-1

# MinIO Configuration (for local development)
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=waddlebot
S3_SECRET_ACCESS_KEY=waddlebot123

# Public URLs
S3_PUBLIC_BASE_URL=http://localhost:9000/waddlebot-assets
S3_CDN_BASE_URL=http://localhost/images

# Image Settings
S3_MAX_FILE_SIZE=10485760          # 10MB
S3_ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,webp,svg
S3_IMAGE_QUALITY=85                # JPEG quality
S3_GENERATE_THUMBNAILS=true        # Generate thumbnail sizes
```

**Production Configuration**:
```bash
# AWS S3 Configuration
S3_STORAGE_ENABLED=true
S3_BUCKET_NAME=waddlebot-prod-assets
S3_REGION=us-west-2
# S3_ENDPOINT_URL=""  # Leave empty for AWS S3
S3_ACCESS_KEY_ID=your_aws_access_key
S3_SECRET_ACCESS_KEY=your_aws_secret_key

# CloudFront CDN
S3_PUBLIC_BASE_URL=https://s3.us-west-2.amazonaws.com/waddlebot-prod-assets
S3_CDN_BASE_URL=https://cdn.waddlebot.com
```

## Features

### Image Upload and Processing

1. **Multi-Format Support**: JPEG, PNG, GIF, WebP, SVG
2. **Automatic Optimization**: Quality compression and format conversion
3. **Thumbnail Generation**: Multiple sizes (64x64, 128x128, 256x256, 512x512)
4. **Deduplication**: SHA256 hash-based duplicate detection
5. **Validation**: File size, format, and dimensions checking

### CDN and Caching

1. **nginx Proxy**: Static file serving with caching headers
2. **Browser Caching**: 1-year cache for images
3. **CORS Support**: Cross-origin access for web applications
4. **Gzip Compression**: Automatic compression for text assets

### Security and Access Control

1. **Public Read Access**: Images are publicly accessible via CDN URLs
2. **Upload Authentication**: Only authenticated users can upload
3. **Ownership Validation**: Users can only delete their own images
4. **Community Permissions**: Community owners can manage community images

## API Endpoints

### Image Management
- `GET /images` - Image gallery and management interface
- `POST /images/upload` - Upload new image
- `DELETE /images/delete/<path>` - Delete image (with ownership check)
- `GET /images/info/<path>` - Get image metadata

### CDN Serving
- `GET /cdn/images/<path>` - Serve image (fallback for local storage)
- `GET /images/*` - Direct nginx proxy to MinIO (via nginx config)

### Admin/API
- `POST /api/images/presigned-upload` - Generate presigned upload URL
- `GET /api/images/storage-status` - Get storage service health status

## Development Workflow

### 1. Local Development Setup

```bash
# Clone repository
git clone <repo-url>
cd WaddleBot

# Start services
docker-compose -f docker-compose.minio.yml up -d

# Check logs
docker-compose -f docker-compose.minio.yml logs -f portal
```

### 2. Testing Image Upload

```bash
# Upload via curl (requires authentication token)
curl -X POST http://localhost:8000/images/upload \
  -H "Authorization: Bearer <token>" \
  -F "image_file=@test.jpg" \
  -F "image_type=avatar"

# Check MinIO console
open http://localhost:9001
```

### 3. Direct MinIO Access

```bash
# Install MinIO client
brew install minio/stable/mc  # macOS
# or download from: https://min.io/download#/linux

# Configure client
mc alias set local http://localhost:9000 waddlebot waddlebot123

# List buckets and objects
mc ls local
mc ls local/waddlebot-assets/images/

# Upload file directly
mc cp test.jpg local/waddlebot-assets/images/test/
```

## Production Deployment

### AWS S3 Setup

1. **Create S3 Bucket**:
```bash
aws s3 mb s3://waddlebot-prod-assets --region us-west-2
```

2. **Set Bucket Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::waddlebot-prod-assets/images/*"
    }
  ]
}
```

3. **Create IAM User**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::waddlebot-prod-assets",
        "arn:aws:s3:::waddlebot-prod-assets/*"
      ]
    }
  ]
}
```

4. **Setup CloudFront CDN**:
   - Origin: S3 bucket
   - Behaviors: Cache images for 1 year
   - Custom domain: cdn.waddlebot.com

### Other S3-Compatible Services

**DigitalOcean Spaces**:
```bash
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
S3_REGION=nyc3
S3_BUCKET_NAME=waddlebot-assets
```

**Wasabi**:
```bash
S3_ENDPOINT_URL=https://s3.wasabisys.com
S3_REGION=us-east-1
S3_BUCKET_NAME=waddlebot-assets
```

**Backblaze B2**:
```bash
S3_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
S3_REGION=us-west-000
S3_BUCKET_NAME=waddlebot-assets
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check storage service health
curl http://localhost:8000/api/images/storage-status

# Check MinIO health
curl http://localhost:9000/minio/health/live
```

### Logs and Debugging

```bash
# Portal logs
docker-compose logs -f portal

# MinIO logs
docker-compose logs -f minio

# Storage service debug info
docker-compose exec portal python -c "
from services.s3_storage_service import S3StorageService
storage = S3StorageService()
print(storage.get_health_status())
"
```

### Backup and Migration

```bash
# Backup MinIO data
mc mirror local/waddlebot-assets /backup/minio-data/

# Sync to production S3
mc mirror local/waddlebot-assets s3-prod/waddlebot-prod-assets/

# Database backup (image metadata)
docker-compose exec postgres pg_dump -U waddlebot waddlebot > backup.sql
```

## Troubleshooting

### Common Issues

**1. Storage service not connecting**:
- Check MinIO container is running: `docker-compose ps minio`
- Verify credentials and endpoint URL
- Check network connectivity between containers

**2. Images not displaying**:
- Verify bucket public read policy
- Check CORS configuration in nginx
- Confirm CDN URL configuration

**3. Upload failures**:
- Check file size limits
- Verify allowed file extensions
- Review portal logs for detailed errors

**4. Performance issues**:
- Enable nginx caching
- Use CDN for production
- Optimize image sizes and formats

### Debug Commands

```bash
# Test MinIO connectivity
docker-compose exec portal python -c "
import boto3
client = boto3.client('s3', 
    endpoint_url='http://minio:9000',
    aws_access_key_id='waddlebot',
    aws_secret_access_key='waddlebot123'
)
print(client.list_buckets())
"

# Check storage service status
docker-compose exec portal curl http://localhost:8000/api/images/storage-status

# Verify bucket contents
mc ls -r local/waddlebot-assets/
```

## Best Practices

1. **Security**:
   - Use strong access keys in production
   - Implement proper IAM policies
   - Enable bucket versioning for data protection
   - Monitor access logs

2. **Performance**:
   - Use CDN for global distribution
   - Implement proper caching headers
   - Optimize image sizes and formats
   - Use WebP format when possible

3. **Cost Optimization**:
   - Implement lifecycle policies
   - Use appropriate storage classes
   - Monitor storage costs
   - Clean up unused images

4. **Backup and Recovery**:
   - Regular data backups
   - Cross-region replication
   - Database backup for metadata
   - Test recovery procedures

This setup provides a robust, scalable image storage and CDN solution for WaddleBot that works seamlessly in both development and production environments.