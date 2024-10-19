import pytest
import json
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from mock_ocr.views import ocr_endpoint
from mock_ocr.views import extract
from ninja.errors import HttpError


# Test the /ocr endpoint
@pytest.mark.django_db
@patch("mock_ocr.views.r")
@patch("mock_ocr.views.process_ocr_task")
def test_ocr_endpoint(mock_celery, mock_redis):
    # Mock the Redis rate-limiting logic
    mock_redis.exists.return_value = False

    # Set up the request object
    factory = RequestFactory()
    request = factory.post("/ocr", {"signed_url": "https://dummyurl.com/document.pdf"})
    request.META["REMOTE_ADDR"] = "127.0.0.1"

    # Call the OCR endpoint
    response = ocr_endpoint(request, signed_url="https://dummyurl.com/document.pdf")

    # Verify that the Celery task was called
    mock_celery.delay.assert_called_once_with("https://dummyurl.com/document.pdf", 0)

    # Assert the correct response
    assert response == {
        "message": "OCR task submitted successfully. It will be processed asynchronously."
    }


# Test rate limit exceeded
@pytest.mark.django_db
@patch(
    "mock_ocr.views.check_rate_limit"
)  # Make sure to patch this if it's in a different module
@patch("mock_ocr.views.r")  # Mock Redis
def test_ocr_rate_limit_exceeded(mock_redis, mock_check_rate_limit):
    # Mock the Redis to simulate rate limit exceeded
    mock_redis.exists.return_value = True
    mock_redis.hgetall.return_value = {
        b"count": b"5",
        b"last_request_time": b"1609459200",
    }

    # Mock check_rate_limit to return False
    mock_check_rate_limit.return_value = False

    factory = RequestFactory()
    request = factory.post("/ocr", {"signed_url": "https://dummyurl.com/document.pdf"})
    request.META["REMOTE_ADDR"] = "127.0.0.1"

    with pytest.raises(HttpError) as excinfo:
        ocr_endpoint(request, signed_url="https://dummyurl.com/document.pdf")

    # Verify the rate limit error
    assert excinfo.value.status_code == 429
    assert str(excinfo.value) == "Rate limit exceeded. Please try again later."


# Test the /extract endpoint
@pytest.mark.django_db
@patch("mock_ocr.views.r")
@patch("mock_ocr.views.openai.Embedding.create")
@patch("mock_ocr.views.index.query")
def test_extract_endpoint(mock_pinecone, mock_openai, mock_redis):
    # Mock Redis cache behavior
    mock_redis.get.return_value = None  # No cache found

    # Mock OpenAI embedding generation
    mock_openai.return_value = {
        "data": [{"embedding": [0.1, 0.2, 0.3]}]  # Dummy embedding
    }

    # Mock Pinecone query response
    mock_pinecone.return_value = {
        "matches": [
            {
                "id": "document_dummy",
                "score": 0.82453531,
                "metadata": {"file_id": "document_dummy"},
            }
        ]
    }

    # Create a mock request
    factory = RequestFactory()
    request = factory.post("/extract", {"query": "abcd", "file_id": "document_dummy"})

    # Call the extract endpoint
    response = extract(request, query="abcd", file_id="document_dummy")

    # Verify OpenAI embedding was generated
    mock_openai.assert_called_once_with(input="abcd", model="text-embedding-ada-002")

    # Verify Pinecone was queried
    mock_pinecone.assert_called_once_with(
        vector=[0.1, 0.2, 0.3],  # The embedding returned by OpenAI
        filter={"file_id": "document_dummy"},
        top_k=5,
        include_metadata=True,
        namespace="ocr",
    )

    # Assert the response contains the expected result
    assert response == {
        "message": "Vector search completed.",
        "results": [
            {
                "metadata": {"file_id": "document_dummy"},
                "score": 0.82453531,
                "id": "document_dummy",
            }
        ],
    }


# Test for cached results
@pytest.mark.django_db
@patch("mock_ocr.views.r")
def test_extract_with_cached_results(mock_redis):
    # Mock Redis to simulate cached results
    mock_redis.get.return_value = json.dumps([{"file_id": "document_dummy"}])

    # Create a mock request
    factory = RequestFactory()
    request = factory.post("/extract", {"query": "abcd", "file_id": "document_dummy"})

    # Call the extract endpoint
    response = extract(request, query="abcd", file_id="document_dummy")

    # Verify the cache was used
    mock_redis.get.assert_called_once_with("extract:abcd:document_dummy")

    # Assert the response contains the cached result
    assert response == {
        "message": "Results retrieved from cache.",
        "results": [{"file_id": "document_dummy"}],
    }
