#!/bin/bash
echo "===== Connection tests at $(date) ====="

# Create schema if needed
python create_schema.py

# Check S3 artifact store connectivity
python -c "
import boto3, os
bucket = os.environ['ARTIFACT_ROOT'].replace('s3://', '').split('/')[0]
boto3.client('s3').head_bucket(Bucket=bucket)
print(f'S3 OK — bucket {bucket} reachable')
" || echo "WARNING: S3 artifact store unreachable"

echo "===== MLFlow version ====="
mlflow --version

echo "===== MLFlow db upgrade ====="
mlflow db upgrade "$BACKEND_STORE_URI"

exec mlflow server \
    --backend-store-uri "$BACKEND_STORE_URI" \
    --artifacts-destination "$ARTIFACT_ROOT" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --disable-security-middleware