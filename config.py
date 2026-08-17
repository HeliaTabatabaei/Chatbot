# # config.py
# import os
# from dotenv import load_dotenv

# load_dotenv()

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# COLLECTION_NAME = "Adonis_docs"
# VECTOR_SIZE = 3072
# EMBED_MODEL = "text-embedding-3-large"
# LLM_MODEL = "gpt-4.1-mini"

# BATCH_SIZE = 64

# QDRANT_HOST = "qdrant_db"
# QDRANT_PORT = 6333

# JSON_PATH = "data/All_chunks_cleaned_V1.json"
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

COLLECTION_NAME = os.getenv("COLLECTION_NAME")
COLLECTION_NAME_Meta=os.getenv("COLLECTION_NAME_Meta")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE"))
EMBED_MODEL =os.getenv("EMBED_MODEL")
LLM_MODEL = os.getenv("LLM_MODEL")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))

QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")

JSON_PATH = os.getenv("JSON_PATH")
    # ساخت کانکشن استرینگ در پایتون
connection_string=os.getenv("connection_string")
connection_string_Dashboard=os.getenv("connection_string_Dashboard")