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

# Initialize NinjaAPI
api = NinjaAPI(urls_namespace="file_upload")

# Allowed file types
ALLOWED_FILE_TYPES = ["pdf", "tiff", "png", "jpeg", "jpg"]

s3_client = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)


def generate_signed_url(file_name):
    """
    :param file_name: File name of the file whom you want the signed URL
    :return: Array of Signed URLs
    """
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": file_name},
        ExpiresIn=3600,  # 1-hour expiration time for the signed URL
    )


# Upload endpoint
@api.post("/upload", auth=JWTAuth())
def upload_file(request, files: List[UploadedFile] = File(...)):
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
