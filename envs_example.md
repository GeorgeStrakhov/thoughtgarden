# Combined environment variables (combined.env)

# Django settings
DEBUG=1
SECRET_KEY=verySecretKeyChangeIt
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1] 0.0.0.0

# Database settings
USE_EXTERNAL_DB=False  # True if using an external database, False for local
POSTGRES_DB=garden_db
POSTGRES_USER=garden_user
POSTGRES_PASSWORD=securePassword123
POSTGRES_HOST=db  # Change this to your external DB host if USE_EXTERNAL_DB=True
POSTGRES_PORT=5432  # Usually, 5432 is the default

# S3/DigitalOcean Spaces settings
AWS_ACCESS_KEY_ID=yourDOAccessKey
AWS_SECRET_ACCESS_KEY=yourDOSecretKey
AWS_STORAGE_BUCKET_NAME=yourBucketName
AWS_S3_ENDPOINT_URL=https://yourRegion.digitaloceanspaces.com
AWS_LOCATION=garden_project  # Optional path within your bucket