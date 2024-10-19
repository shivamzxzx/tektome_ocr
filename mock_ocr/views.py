from ninja import NinjaAPI

from auth.jwt_auth import JWTAuth
from mock_ocr.tasks import process_ocr_task
from ninja.errors import HttpError
import time
import os
import openai
from pinecone import Pinecone
import redis
import json

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


api = NinjaAPI(urls_namespace='mock_ocr')

# Redis for rate-limiting and caching
r = redis.StrictRedis.from_url(os.getenv('REDIS_URL'))

# Limit to 5 requests per minute
RATE_LIMIT_THRESHOLD = os.getenv("RATE_LIMIT_THRESHOLD")
RATE_LIMIT_TIME_WINDOW = os.getenv("RATE_LIMIT_TIME_WINDOW")
# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))


# Rate limiting logic
def check_rate_limit(client_ip):
    current_time = int(time.time())

    if r.exists(client_ip):
        request_data = r.hgetall(client_ip)
        request_count = int(request_data[b'count'])
        last_request_time = int(request_data[b'last_request_time'])

        if current_time - last_request_time < int(RATE_LIMIT_TIME_WINDOW):
            if request_count >= int(RATE_LIMIT_THRESHOLD):
                return False
            else:
                r.hincrby(client_ip, 'count', 1)
        else:
            # Reset count and time if the time window has passed
            r.hset(client_ip, 'count', 1)
            r.hset(client_ip, 'last_request_time', current_time)
    else:
        # First request from the client in this time window
        r.hset(client_ip, 'count', 1)
        r.hset(client_ip, 'last_request_time', current_time)

    return True


@api.post("/ocr",  auth=JWTAuth())
def ocr_endpoint(request, signed_url: str):
    # Get the client IP from the META information
    client_ip = request.META.get('REMOTE_ADDR')

    # Check if the client is exceeding the rate limit
    if not check_rate_limit(client_ip):
        raise HttpError(429, "Rate limit exceeded. Please try again later.")

    # Start asynchronous OCR processing
    process_ocr_task.delay(signed_url, 0)

    return {"message": "OCR task submitted successfully. It will be processed asynchronously."}


# Cache results for 10 minutes
def cache_query_results(query_key, results):
    serializable_results = []
    for result in results:
        # Extract only the serializable attributes (e.g., 'id' and 'metadata')
        serializable_results.append({
            "id": result.get("id"),
            "score": result.get("score"),
            "metadata": result.get("metadata")
        })

    r.set(query_key, json.dumps(serializable_results), ex=600)


# Function to retrieve cached results from Redis
def get_cached_results(query_key):
    cached_data = r.get(query_key)
    if cached_data:
        return json.loads(cached_data)
    return None


@api.post("/extract",  auth=JWTAuth())
def extract(request, query: str, file_id: str):
    # Create a unique cache key using the query and file_id
    cache_key = f"extract:{query}:{file_id}"

    # Check if the results for this query are already cached
    cached_results = get_cached_results(cache_key)
    if cached_results:
        logging.info("Results retrieved from cache.")
        return {"message": "Results retrieved from cache.", "results": cached_results}

    # Use OpenAI to generate embeddings for the query
    embedding_response = openai.Embedding.create(
        input=query,
        model="text-embedding-ada-002"
    )
    query_embedding = embedding_response["data"][0]["embedding"]

    logging.info(f"Generated query embedding: {query_embedding}")

    # Perform a vector search on Pinecone using the query embedding and file_id filter
    search_results = index.query(
        vector=query_embedding,
        filter={"file_id": file_id},  # Filter by file ID
        top_k=5,  # Retrieve top 5 matches
        include_metadata=True,
        namespace="ocr"
    )

    logging.info(f"Search results from Pinecone: {search_results}")

    # Extract matching attributes from the Pinecone response
    matching_attributes = []
    if "matches" in search_results and search_results["matches"]:
        for match in search_results["matches"]:
            metadata = match.get("metadata", {})
            serializable_match = {
                "id": match["id"],
                "score": match["score"],
                "metadata": metadata
            }
            matching_attributes.append(serializable_match)
            logging.info(f"Extracted metadata: {serializable_match}")
    else:
        logging.warning("No matches found in search results.")

    # Check if there are any matches to return
    if not matching_attributes:
        return {"message": "No matches found.", "results": []}

    # Cache the results to improve performance for repeated queries
    cache_query_results(cache_key, matching_attributes)

    return {"message": "Vector search completed.", "results": matching_attributes}
