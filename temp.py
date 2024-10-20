# import pinecone
#
# List all indexes
from pinecone import Pinecone

pc = Pinecone(api_key="")
print(pc.list_indexes())
index = pc.Index("ocr-index")  # This will return the correct index names

fetched_vector = index.fetch(
    ids=["document_dummy_new"], namespace="ocr"
)  # Use your document ID here
print(f"Fetched Vector: {fetched_vector}")
