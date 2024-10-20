# api/tasks.py

import openai
import os
import json
import time
import logging
from celery import shared_task
from openai.error import RateLimitError
from pinecone import Pinecone


openai.api_key = os.getenv("OPENAI_API_KEY")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_ocr_task(self, signed_url: str, retries: int):
    """
        Celery task to process OCR, extract text, generate embeddings,
        and upsert them into Pinecone for a given document.

        :param self: Task instance for retrying
        :param signed_url: Signed URL of the PDF document
        :param retries: Number of retry attempts
        :return: JSON containing status or error message
    """
    logger.info(
        f"Starting OCR processing task for signed_url: {signed_url} with retries: {retries}"
    )

    # Simulate the OCR process (retrieve JSON from sample file)
    file_id = signed_url.split("/")[-1].replace(".pdf", "")
    ocr_json_path = os.path.join(os.getcwd(), "sample_ocr", f"{file_id}.json")

    if not os.path.exists(ocr_json_path):
        logger.error(f"OCR file not found for file_id: {file_id}")
        return {"error": "OCR file not found."}

    logger.info(f"OCR file found: {ocr_json_path}")

    try:
        # Read OCR data from the JSON file
        with open(ocr_json_path, "r") as f:
            ocr_data = json.load(f)

        # Extract OCR text
        ocr_text = ocr_data["analyzeResult"]["content"]
        logger.info(f"OCR text extracted for file_id: {file_id}")

        # Make OpenAI API call for embedding
        embedding_response = openai.Embedding.create(
            input=ocr_text, model="text-embedding-ada-002"
        )

        # Handle response
        embeddings = embedding_response["data"][0]["embedding"]
        document_id = f"document_{signed_url.split('/')[-1]}"
        logger.info(f"Generated embeddings for document_id: {document_id}")

        # Upsert the embeddings into the Pinecone index
        index.upsert(
            vectors=[(document_id, embeddings, {"file_id": document_id})],
            namespace="ocr",
        )
        logger.info(
            f"Embeddings upserted into Pinecone index for document_id: {document_id}"
        )

        return {
            "message": "OCR and embedding process completed.",
            "document_id": document_id,
        }

    except RateLimitError:
        logger.warning("Rate limit exceeded. Retrying after a delay...")
        if retries >= 5:
            logger.error("Max retries reached. Aborting task.")
            return {"error": "Max retries reached"}

        retries += 1
        logger.info(f"Retrying... attempt {retries}")
        time.sleep(10)
        return process_ocr_task(self, signed_url, retries)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return {"error": str(e)}
