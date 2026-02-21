import boto3
from botocore.exceptions import NoCredentialsError
import os

# Configuration — set these in your environment or replace directly
ENDPOINT_URL = "https://78d5629b13f881a076ac38046e5df31e.r2.cloudflarestorage.com"
ACCESS_KEY_ID = "8a9e77c0d1328c86d4e1eb3e1cac5510"
SECRET_ACCESS_KEY = "f265bea8ddcefe13de4224ce6103e3c667327d03ae8221d7a5d36023227b716c"
BUCKET_NAME = "smartlens-images"
CDN_DOMAIN = "https://cdn.theboldlens.com"  # Public domain for serving

# Create R2 client
s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT_URL,
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
    region_name="auto"
)

def upload_to_r2(file_path: str, r2_key: str) -> str:
    """
    Upload a local file to Cloudflare R2 and return its public URL.

    Args:
        file_path: Path to the local file (e.g., "./images/photo.jpg")
        r2_key: Path/key in the R2 bucket (e.g., "uploads/photo.jpg")

    Returns:
        Public URL of the uploaded file
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        s3.upload_file(file_path, BUCKET_NAME, r2_key)
        print(f"✅ Uploaded {file_path} to R2 at {r2_key}")
        return f"{CDN_DOMAIN}/{r2_key}"
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        raise
def upload_content_to_r2(content: str, r2_key: str, content_type: str = 'text/html') -> str:
    """Uploads a string content to R2."""
    try:
        s3.put_object(Bucket=BUCKET_NAME, Key=r2_key, Body=content, ContentType=content_type)
        return f"{CDN_DOMAIN}/{r2_key}"
    except NoCredentialsError:
        print(f"❌ Credentials error: {e}")
        raise
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        raise

# Example usage:
if __name__ == "__main__":
    public_url = upload_to_r2("./images/image.jpg", "uploads/image.jpg")
    print(f"Public URL: {public_url}")
