import os
from config import PINECONE_API_KEY, INDEX_NAME

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

from langchain_community.document_loaders import TextLoader, PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
import glob

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)
existing_indexes = [index.name for index in pc.list_indexes().indexes]

if INDEX_NAME not in existing_indexes:
    print(f"Creating new index: {INDEX_NAME}")
    pc.create_index(
        name=INDEX_NAME,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
else:
    print(f"Index '{INDEX_NAME}' already exists.")

# Load ALL files from directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(BASE_DIR, "../data/notebook_topics/")

print(f"\n📂 Loading files from: {os.path.abspath(data_path)}")

all_docs = []

# Load TXT files
txt_files = glob.glob(os.path.join(data_path, "*.txt"))
print(f"\n📄 Found {len(txt_files)} TXT files:")
for file_path in txt_files:
    print(f"   - {os.path.basename(file_path)}")
    try:
        loader = TextLoader(file_path, encoding='utf-8')
        docs = loader.load()
        # Add source metadata
        for doc in docs:
            doc.metadata['source'] = os.path.basename(file_path)
        all_docs.extend(docs)
        print(f"     ✅ Loaded successfully")
    except Exception as e:
        print(f"     ❌ Error: {e}")

# Load PDF files
pdf_files = glob.glob(os.path.join(data_path, "*.pdf"))
print(f"\n📕 Found {len(pdf_files)} PDF files:")
for file_path in pdf_files:
    print(f"   - {os.path.basename(file_path)}")
    try:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        # Add source metadata
        for doc in docs:
            doc.metadata['source'] = os.path.basename(file_path)
        all_docs.extend(docs)
        print(f"     ✅ Loaded successfully")
    except Exception as e:
        print(f"     ❌ Error: {e}")

if not all_docs:
    print("\n❌ No documents found! Please add .txt or .pdf files to the data folder.")
    exit(1)

print(f"\n📚 Total documents loaded: {len(all_docs)}")

# Split into chunks
print("\n✂️ Splitting documents into chunks...")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, 
    chunk_overlap=200,  # Increased overlap for better context
    separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
)
chunks = splitter.split_documents(all_docs)
print(f"   Created {len(chunks)} chunks")

# Generate embeddings
print("\n🧠 Generating embeddings...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Store in Pinecone
print(f"\n💾 Storing in Pinecone index '{INDEX_NAME}'...")
vectorstore = PineconeVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
    index_name=INDEX_NAME
)

print("\n✅ SUCCESS! All data embedded and stored in Pinecone.")
print(f"   Total chunks indexed: {len(chunks)}")
print(f"   From {len(all_docs)} documents")

# Verify
index = pc.Index(INDEX_NAME)
stats = index.describe_index_stats()
print(f"\n📊 Pinecone Index Stats:")
print(f"   Total vectors: {stats.total_vector_count}")