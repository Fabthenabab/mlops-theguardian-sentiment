import os
#import io
#import sys

# Give access to env variables
from dotenv import load_dotenv
load_dotenv()
#from pathlib import Path

# Connection to S3
import boto3
from botocore.exceptions import ClientError

from io import BytesIO
import pandas as pd

# Logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def check_cnx_to_s3() -> bool:
    """Check connectivity to S3 bucket. Returns True if reachable."""
    logger.debug("function check_cnx_to_s3")
    try:
        bucket = os.environ["AWS_S3_BUCKET"]
        boto3.client("s3").head_bucket(Bucket=bucket)
        logger.info(f"S3 OK — bucket {bucket} reachable")
        return True
    except Exception as e:
        logger.error(f"S3 unreachable: {e}")
        return False

# ===================================
# save_parquet_to_s3
# ===================================
def save_parquet_to_s3(df: pd.DataFrame, s3_key: str) -> bool:
    """
    Serialize a DataFrame as parquet to S3.

    Args:
        df     : DataFrame to serialize
        s3_key : S3 key (path) e.g. "monitor/reference.parquet"

    Returns:
        True if success
    """
    logger.debug("function save_parquet_to_s3")
    try:
        # Configure bucket
        aws_s3_bucket = os.getenv("AWS_S3_BUCKET")
        logger.info(f"⤴️ Serializing object to S3: s3://{aws_s3_bucket}/{s3_key}")

        if not isinstance(df, pd.DataFrame):
            raise ValueError(f"Object must be a DataFrame, got {type(df)}")

        # Create buffer in parquet format
        buffer = BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)

        # Create an S3 client
        s3_client = boto3.client(
            "s3",
            aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name           = os.getenv("AWS_REGION")
        )

        # Put object
        s3_client.put_object(
            Bucket = aws_s3_bucket,
            Key    = s3_key,
            Body   = buffer.getvalue()
        )
        logger.info(f"✅ Parquet saved to s3://{aws_s3_bucket}/{s3_key} ({df.shape[0]} rows)")
        return True
    
    except ClientError as e:
        logger.error(f"Error during serialization to S3: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise


# ===================================
# load_parquet_from_s3
# ===================================
def load_parquet_from_s3(s3_key: str) -> pd.DataFrame:
    """
    Load a parquet file from S3 into a DataFrame.

    Args:
        s3_key : S3 key (path) e.g. "monitor/reference.parquet"

    Returns:
        pd.DataFrame
    """
    logger.debug("function load_parquet_from_s3")
    try:
        # Configure bucket
        aws_s3_bucket = os.getenv("AWS_S3_BUCKET")
        logger.info(f"⤵️ Deserializing the file from S3: s3://{aws_s3_bucket}/{s3_key}")

        # Create an S3 client
        s3_client = boto3.client(
            "s3",
            aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name           = os.getenv("AWS_REGION")
        )

        # Get serialized object from S3
        response = s3_client.get_object(Bucket=aws_s3_bucket, Key=s3_key)
        df = pd.read_parquet(BytesIO(response["Body"].read()))

        logger.info(f"✅ Parquet loaded from s3://{aws_s3_bucket}/{s3_key} ({df.shape[0]} rows)")
        return df
    
    except ClientError as e:
        logger.error(f"Error during deserialization from S3: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

