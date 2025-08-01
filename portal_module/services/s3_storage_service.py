"""
S3-Compatible Storage Service for WaddleBot Portal
Handles image uploads, storage, and CDN-style serving
"""

import boto3
import os
import logging
import mimetypes
import hashlib
import uuid
from typing import Dict, List, Optional, Any, BinaryIO
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, NoCredentialsError
from urllib.parse import urljoin
import tempfile
from PIL import Image
import io

logger = logging.getLogger(__name__)

class S3StorageService:
    """S3-compatible storage service for images and assets"""
    
    def __init__(self):
        """Initialize S3 storage service with configuration"""
        # S3 Configuration
        self.enabled = os.environ.get('S3_STORAGE_ENABLED', 'false').lower() == 'true'
        self.bucket_name = os.environ.get('S3_BUCKET_NAME', 'waddlebot-assets')
        self.region = os.environ.get('S3_REGION', 'us-east-1')
        self.endpoint_url = os.environ.get('S3_ENDPOINT_URL', None)  # For S3-compatible services
        self.access_key = os.environ.get('S3_ACCESS_KEY_ID', '')
        self.secret_key = os.environ.get('S3_SECRET_ACCESS_KEY', '')
        
        # CDN Configuration
        self.cdn_base_url = os.environ.get('S3_CDN_BASE_URL', '')  # CloudFront or custom CDN
        self.public_base_url = os.environ.get('S3_PUBLIC_BASE_URL', '')  # Direct S3 URL
        
        # Upload Settings
        self.max_file_size = int(os.environ.get('S3_MAX_FILE_SIZE', str(10 * 1024 * 1024)))  # 10MB
        self.allowed_extensions = set(os.environ.get('S3_ALLOWED_EXTENSIONS', 'jpg,jpeg,png,gif,webp,svg').split(','))
        self.image_quality = int(os.environ.get('S3_IMAGE_QUALITY', '85'))
        self.generate_thumbnails = os.environ.get('S3_GENERATE_THUMBNAILS', 'true').lower() == 'true'
        
        # Thumbnail sizes
        self.thumbnail_sizes = {
            'small': (64, 64),
            'medium': (128, 128), 
            'large': (256, 256),
            'profile': (512, 512)
        }
        
        # Initialize S3 client
        self.s3_client = None
        self.fallback_storage = os.environ.get('S3_FALLBACK_STORAGE', '/app/static/uploads')
        
        if self.enabled:
            self._initialize_s3_client()
        else:
            logger.info("S3 storage disabled, using local fallback storage")
            os.makedirs(self.fallback_storage, exist_ok=True)
    
    def _initialize_s3_client(self):
        """Initialize S3 client with configuration"""
        try:
            session = boto3.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
            
            # Configure S3 client
            config = {}
            if self.endpoint_url:
                config['endpoint_url'] = self.endpoint_url
            
            self.s3_client = session.client('s3', **config)
            
            # Test connection and create bucket if needed
            self._ensure_bucket_exists()
            
            logger.info(f"S3 storage initialized: bucket={self.bucket_name}, region={self.region}")
            
        except (NoCredentialsError, ClientError) as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.enabled = False
    
    def _ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, create if needed"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.debug(f"S3 bucket '{self.bucket_name}' exists")
            
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                # Bucket doesn't exist, create it
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    
                    # Set public read policy for images
                    self._set_bucket_policy()
                    
                    logger.info(f"Created S3 bucket: {self.bucket_name}")
                    
                except ClientError as create_error:
                    logger.error(f"Failed to create S3 bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error accessing S3 bucket: {e}")
                raise
    
    def _set_bucket_policy(self):
        """Set bucket policy for public read access to images"""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/images/*"
                }
            ]
        }
        
        try:
            self.s3_client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=str(policy).replace("'", '"')
            )
            logger.debug("Set S3 bucket policy for public image access")
        except ClientError as e:
            logger.warning(f"Failed to set bucket policy: {e}")
    
    def _get_file_hash(self, file_data: bytes) -> str:
        """Generate hash for file deduplication"""
        return hashlib.sha256(file_data).hexdigest()[:16]
    
    def _get_file_extension(self, filename: str, content_type: str = None) -> str:
        """Get file extension from filename or content type"""
        if filename and '.' in filename:
            return filename.rsplit('.', 1)[1].lower()
        
        if content_type:
            ext = mimetypes.guess_extension(content_type)
            if ext:
                return ext[1:]  # Remove leading dot
        
        return 'jpg'  # Default extension
    
    def _validate_image(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Validate image file and get metadata"""
        try:
            # Check file size
            if len(file_data) > self.max_file_size:
                return {
                    'valid': False,
                    'error': f'File size ({len(file_data)} bytes) exceeds maximum ({self.max_file_size} bytes)'
                }
            
            # Check file extension
            ext = self._get_file_extension(filename)
            if ext not in self.allowed_extensions:
                return {
                    'valid': False,
                    'error': f'File extension .{ext} not allowed. Allowed: {", ".join(self.allowed_extensions)}'
                }
            
            # Validate image with PIL
            try:
                with Image.open(io.BytesIO(file_data)) as img:
                    img.verify()
                    
                # Get image info (need to reopen after verify)
                with Image.open(io.BytesIO(file_data)) as img:
                    width, height = img.size
                    format_name = img.format.lower() if img.format else ext
                    
                return {
                    'valid': True,
                    'width': width,
                    'height': height,
                    'format': format_name,
                    'size': len(file_data)
                }
                
            except Exception as e:
                return {
                    'valid': False,
                    'error': f'Invalid image file: {str(e)}'
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': f'File validation error: {str(e)}'
            }
    
    def _optimize_image(self, file_data: bytes, max_width: int = None, max_height: int = None) -> bytes:
        """Optimize image size and quality"""
        try:
            with Image.open(io.BytesIO(file_data)) as img:
                # Convert RGBA to RGB if saving as JPEG
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Resize if dimensions specified
                if max_width or max_height:
                    img.thumbnail((max_width or img.width, max_height or img.height), Image.Resampling.LANCZOS)
                
                # Save optimized image
                output = io.BytesIO()
                save_format = 'JPEG'
                save_kwargs = {'quality': self.image_quality, 'optimize': True}
                
                # Keep PNG format for transparency
                if img.mode in ('RGBA', 'LA') or (hasattr(img, 'transparency') and img.transparency is not None):
                    save_format = 'PNG'
                    save_kwargs = {'optimize': True}
                
                img.save(output, format=save_format, **save_kwargs)
                return output.getvalue()
                
        except Exception as e:
            logger.warning(f"Image optimization failed: {e}")
            return file_data  # Return original if optimization fails
    
    def _generate_thumbnails(self, file_data: bytes) -> Dict[str, bytes]:
        """Generate thumbnail images in different sizes"""
        thumbnails = {}
        
        if not self.generate_thumbnails:
            return thumbnails
        
        try:
            for size_name, (width, height) in self.thumbnail_sizes.items():
                thumb_data = self._optimize_image(file_data, width, height)
                thumbnails[size_name] = thumb_data
                
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")
        
        return thumbnails
    
    def upload_image(self, file_data: bytes, filename: str, image_type: str = 'general', 
                    user_id: str = None, community_id: str = None) -> Dict[str, Any]:
        """
        Upload image to S3 storage
        
        Args:
            file_data: Image file data
            filename: Original filename
            image_type: Type of image (avatar, community_icon, banner, general)
            user_id: User ID for user-specific images
            community_id: Community ID for community-specific images
            
        Returns:
            Dict with upload result and URLs
        """
        try:
            # Validate image
            validation = self._validate_image(file_data, filename)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error']
                }
            
            # Generate file hash and key
            file_hash = self._get_file_hash(file_data)
            file_ext = self._get_file_extension(filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            # Build S3 key path
            path_parts = ['images', image_type]
            
            if community_id:
                path_parts.append(f'community_{community_id}')
            elif user_id:
                path_parts.append(f'user_{user_id}')
            
            # Generate unique filename
            unique_filename = f"{timestamp}_{file_hash}.{file_ext}"
            s3_key = '/'.join(path_parts + [unique_filename])
            
            # Optimize main image
            optimized_data = self._optimize_image(file_data)
            
            # Upload main image
            success = self._upload_to_storage(s3_key, optimized_data, f'image/{file_ext}')
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to upload image'
                }
            
            # Generate and upload thumbnails
            thumbnail_urls = {}
            if self.generate_thumbnails:
                thumbnails = self._generate_thumbnails(file_data)
                
                for size_name, thumb_data in thumbnails.items():
                    thumb_key = s3_key.replace(f'.{file_ext}', f'_{size_name}.{file_ext}')
                    thumb_success = self._upload_to_storage(thumb_key, thumb_data, f'image/{file_ext}')
                    
                    if thumb_success:
                        thumbnail_urls[size_name] = self._get_public_url(thumb_key)
            
            # Build response
            main_url = self._get_public_url(s3_key)
            
            return {
                'success': True,
                'url': main_url,
                'cdn_url': self._get_cdn_url(s3_key) if self.cdn_base_url else main_url,
                'thumbnails': thumbnail_urls,
                's3_key': s3_key,
                'metadata': {
                    'filename': filename,
                    'size': len(optimized_data),
                    'width': validation['width'],
                    'height': validation['height'],
                    'format': validation['format'],
                    'uploaded_at': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Image upload failed: {e}")
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }
    
    def _upload_to_storage(self, key: str, data: bytes, content_type: str) -> bool:
        """Upload data to S3 or fallback storage"""
        if self.enabled and self.s3_client:
            return self._upload_to_s3(key, data, content_type)
        else:
            return self._upload_to_local(key, data)
    
    def _upload_to_s3(self, key: str, data: bytes, content_type: str) -> bool:
        """Upload data to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl='public, max-age=31536000',  # 1 year cache
                Metadata={
                    'uploaded-by': 'waddlebot-portal',
                    'upload-timestamp': datetime.utcnow().isoformat()
                }
            )
            
            logger.debug(f"Uploaded to S3: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 upload failed for {key}: {e}")
            return False
    
    def _upload_to_local(self, key: str, data: bytes) -> bool:
        """Upload data to local fallback storage"""
        try:
            local_path = os.path.join(self.fallback_storage, key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                f.write(data)
            
            logger.debug(f"Uploaded to local storage: {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Local upload failed for {key}: {e}")
            return False
    
    def _get_public_url(self, key: str) -> str:
        """Get public URL for image"""
        if self.enabled and self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/{key}"
        elif self.enabled:
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
        else:
            return f"/static/uploads/{key}"
    
    def _get_cdn_url(self, key: str) -> str:
        """Get CDN URL for image"""
        if self.cdn_base_url:
            return f"{self.cdn_base_url.rstrip('/')}/{key}"
        else:
            return self._get_public_url(key)
    
    def delete_image(self, s3_key: str) -> bool:
        """Delete image from storage"""
        try:
            if self.enabled and self.s3_client:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                
                # Delete thumbnails
                if self.generate_thumbnails:
                    for size_name in self.thumbnail_sizes.keys():
                        thumb_key = s3_key.replace('.', f'_{size_name}.')
                        try:
                            self.s3_client.delete_object(Bucket=self.bucket_name, Key=thumb_key)
                        except:
                            pass  # Ignore thumbnail deletion errors
                
                logger.debug(f"Deleted from S3: {s3_key}")
            else:
                # Delete from local storage
                local_path = os.path.join(self.fallback_storage, s3_key)
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logger.debug(f"Deleted from local storage: {local_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete image {s3_key}: {e}")
            return False
    
    def list_images(self, prefix: str = 'images/', limit: int = 100) -> List[Dict[str, Any]]:
        """List images in storage"""
        try:
            if self.enabled and self.s3_client:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    MaxKeys=limit
                )
                
                images = []
                for obj in response.get('Contents', []):
                    images.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'url': self._get_public_url(obj['Key']),
                        'cdn_url': self._get_cdn_url(obj['Key'])
                    })
                
                return images
            else:
                # List local storage
                images = []
                local_prefix = os.path.join(self.fallback_storage, prefix)
                
                if os.path.exists(local_prefix):
                    for root, dirs, files in os.walk(local_prefix):
                        for file in files[:limit]:
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, self.fallback_storage)
                            
                            images.append({
                                'key': rel_path.replace('\\', '/'),
                                'size': os.path.getsize(file_path),
                                'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                                'url': f"/static/uploads/{rel_path.replace('\\', '/')}",
                                'cdn_url': f"/static/uploads/{rel_path.replace('\\', '/')}"
                            })
                
                return images
                
        except Exception as e:
            logger.error(f"Failed to list images: {e}")
            return []
    
    def get_image_info(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """Get image metadata"""
        try:
            if self.enabled and self.s3_client:
                response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                
                return {
                    'key': s3_key,
                    'size': response['ContentLength'],
                    'content_type': response['ContentType'],
                    'last_modified': response['LastModified'].isoformat(),
                    'metadata': response.get('Metadata', {}),
                    'url': self._get_public_url(s3_key),
                    'cdn_url': self._get_cdn_url(s3_key)
                }
            else:
                # Get local file info
                local_path = os.path.join(self.fallback_storage, s3_key)
                if os.path.exists(local_path):
                    stat = os.stat(local_path)
                    content_type = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'
                    
                    return {
                        'key': s3_key,
                        'size': stat.st_size,
                        'content_type': content_type,
                        'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'metadata': {},
                        'url': f"/static/uploads/{s3_key}",
                        'cdn_url': f"/static/uploads/{s3_key}"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get image info for {s3_key}: {e}")
            return None
    
    def generate_presigned_upload_url(self, key: str, content_type: str, expires_in: int = 3600) -> Optional[str]:
        """Generate presigned URL for direct uploads"""
        if not (self.enabled and self.s3_client):
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get storage service health status"""
        status = {
            'enabled': self.enabled,
            'storage_type': 's3' if self.enabled else 'local',
            'bucket_name': self.bucket_name if self.enabled else self.fallback_storage,
            'healthy': False,
            'error': None
        }
        
        try:
            if self.enabled and self.s3_client:
                # Test S3 connection
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                status['healthy'] = True
            else:
                # Check local storage
                status['healthy'] = os.path.exists(self.fallback_storage) and os.access(self.fallback_storage, os.W_OK)
                
        except Exception as e:
            status['error'] = str(e)
        
        return status