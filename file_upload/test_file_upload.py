import pytest
from unittest.mock import patch, MagicMock
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.test import RequestFactory
from file_upload.views import upload_file  # Adjust the import based on your project structure


@pytest.mark.django_db
@patch('file_upload.views.default_storage')  # Mock Django's default storage
@patch('file_upload.views.generate_signed_url')  # Mock the generate_signed_url function
def test_upload_file_success(mock_generate_signed_url, mock_default_storage):
    # Mock the signed URL response
    mock_generate_signed_url.return_value = "http://mockurl.com/signed_url"

    # Create a mock file
    mock_file = MagicMock(spec=UploadedFile)
    mock_file.name = "test_image.png"
    mock_file.read.return_value = b"mock file content"

    # Set up the request with the mock file
    factory = RequestFactory()
    request = factory.post('/upload', {'files': [mock_file]})

    # Call the upload_file function
    response = upload_file(request, files=[mock_file])

    # Verify the response
    assert response == {"uploaded_files": ["http://mockurl.com/signed_url"]}


    # Ensure the call was made with ContentFile containing the expected content
    assert mock_default_storage.save.call_count == 1
    saved_file_call = mock_default_storage.save.call_args[0]

    # Compare the content directly
    assert isinstance(saved_file_call[0], str)  # Check that the first argument is a string (the file path)
    assert saved_file_call[1].read() == b"mock file content"  # Check the content


@pytest.mark.django_db
@patch('file_upload.views.default_storage')  # Mock Django's default storage
@patch('file_upload.views.generate_signed_url')  # Mock the generate_signed_url function
def test_upload_multiple_files(mock_generate_signed_url, mock_default_storage):
    # Mock the signed URL response
    mock_generate_signed_url.side_effect = [
        "http://mockurl.com/signed_url1",
        "http://mockurl.com/signed_url2"
    ]

    # Create mock files
    mock_file1 = MagicMock(spec=UploadedFile)
    mock_file1.name = "file1.pdf"
    mock_file1.read.return_value = b"mock file content 1"

    mock_file2 = MagicMock(spec=UploadedFile)
    mock_file2.name = "file2.png"
    mock_file2.read.return_value = b"mock file content 2"

    # Set up the request with the mock files
    factory = RequestFactory()
    request = factory.post('/upload', {'files': [mock_file1, mock_file2]})

    # Call the upload_file function
    response = upload_file(request, files=[mock_file1, mock_file2])

    # Verify the response
    assert response == {
        "uploaded_files": [
            "http://mockurl.com/signed_url1",
            "http://mockurl.com/signed_url2"
        ]
    }

    # Check that each file is saved correctly with ContentFile
    assert mock_default_storage.save.call_count == 2
    calls = mock_default_storage.save.call_args_list

    # Ensure the content is correct for each call by comparing the read output
    assert calls[0][0][1].read() == b"mock file content 1"
    assert calls[1][0][1].read() == b"mock file content 2"
