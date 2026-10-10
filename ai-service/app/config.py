import os
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
SOURCE = Path(os.getenv('SOURCE_DATA_DIR', str(ROOT / 'data')))
KB = Path(os.getenv('KNOWLEDGE_BASE_DIR', str(ROOT / 'knowledge_base')))
VERSIONS = Path(os.getenv('UPLOAD_ROOT', str(ROOT / 'data/uploads')))
GENERATED = Path(os.getenv('GENERATED_DIR', str(ROOT / 'data/generated')))
MAX_BYTES = int(os.getenv('UPLOAD_MAX_BYTES', '5242880'))
MAX_ROWS = int(os.getenv('UPLOAD_MAX_ROWS', '50000'))
ANCHOR = '2026-10-10 12:00:00+05:30'
CATEGORIES = ['POS and Payments','Inventory and Replenishment','Pricing and Promotions','Returns and Refunds','Vendor and Supply Chain','Product Quality and Safety','Customer Service','Other or Security']
def missing_ai():
    names = ['GROQ_API_KEY','GROQ_MODEL','EMBEDDING_PROVIDER','EMBEDDING_MODEL','EMBEDDING_BASE_URL','EMBEDDING_API_KEY','PINECONE_API_KEY','PINECONE_INDEX']
    return [n for n in names if not os.getenv(n) or os.getenv(n,'').startswith('REPLACE_')]
