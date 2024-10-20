from ninja import NinjaAPI, File
from typing import List

from ninja.errors import HttpError
from ninja.files import UploadedFile
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import boto3

import uuid

from auth.jwt_auth import JWTAuth


api = NinjaAPI(urls_namespace="file_upload")

# Allowed file types
ALLOWED_FILE_TYPES = ["pdf", "tiff", "png", "jpeg", "jpg"]

s3_client = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)


def generate_signed_url(file_name):
    """
    Generates a signed URL for accessing an object in an AWS S3 bucket.

    :param file_name: The name of the file (i.e., the S3 key) for which you want to generate the signed URL.
                      This should match the exact key of the file stored in the specified S3 bucket.
    :return: A signed URL (string) that allows temporary access to the file in S3 for a limited time.
             The URL expires after 1 hour (3600 seconds) and can be used to securely access or download
             the specified file.

    Example return:
    'https://bucket-name.s3.amazonaws.com/your-file-name?AWSAccessKeyId=...&Signature=...&Expires=...'
    """
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": file_name},
        ExpiresIn=3600,  # 1-hour expiration time for the signed URL
    )


# Upload endpoint
@api.post("/upload", auth=JWTAuth())
def upload_file(request, files: List[UploadedFile] = File(...)):
    """
    Handles file uploads and returns signed URLs for the uploaded files.

    :param request: The request object containing authentication and other request-specific data.
    :param files: A list of UploadedFile objects representing the files to be uploaded.
                  These files are validated and processed for uploading to storage (e.g., S3).
    :return: JSON response with a list of signed URLs for the uploaded files.
             If file validation fails, an HTTP 400 error is raised.
             Example response:
             {
                 "uploaded_files": [
                     "https://s3-bucket-url.com/signed-url1",
                     "https://s3-bucket-url.com/signed-url2"
                 ]
             }
    """
    file_urls = []

    for file in files:
        # Get the file extension and validate it
        ext = file.name.split(".")[-1].lower()
        if ext not in ALLOWED_FILE_TYPES:
            raise HttpError(400, f"File type {ext} is not allowed")

        # Create a unique filename to avoid conflicts and ensure sanitization
        unique_filename = str(uuid.uuid4()) + "." + ext

        # Save the file using default Django storage
        file_path = default_storage.save(unique_filename, ContentFile(file.read()))

        # Retrieve signed url from S3
        file_url = generate_signed_url(unique_filename)
        file_urls.append(file_url)

    return {"uploaded_files": file_urls}
