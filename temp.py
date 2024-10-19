# import pinecone
#
# # Initialize Pinecone
# pinecone.init(api_key="3639cd5d-f1d6-453d-a47a-7780aba371a4", environment="us-east-1-aws")

# List all indexes
from pinecone import Pinecone

pc = Pinecone(api_key="")
print(pc.list_indexes())
index = pc.Index("ocr-index") # This will return the correct index names

fetched_vector = index.fetch(ids=["document_dummy_new"], namespace="ocr")  # Use your document ID here
print(f"Fetched Vector: {fetched_vector}")
