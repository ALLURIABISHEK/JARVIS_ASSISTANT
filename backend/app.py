from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from config import PINECONE_API_KEY, INDEX_NAME, GROQ_API_KEY

# --- LangChain + Pinecone ---
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone

# --- Groq for LLM ---
from groq import Groq

# --- Setup ---
app = Flask(__name__)
CORS(app)

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize components
pc = Pinecone(api_key=PINECONE_API_KEY)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
groq_client = Groq(api_key=GROQ_API_KEY)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_and_store_file(file_path, filename):
    """Process uploaded file and store in Pinecone"""
    try:
        # Load document based on type
        if filename.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding='utf-8')
        
        docs = loader.load()
        
        # Add metadata
        for doc in docs:
            doc.metadata['source'] = filename
            doc.metadata['upload_type'] = 'user_upload'
        
        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = splitter.split_documents(docs)
        
        # Store in Pinecone
        vectorstore.add_documents(chunks)
        
        return len(chunks)
    
    except Exception as e:
        raise Exception(f"Error processing file: {str(e)}")

def ask_jarvis(question):
    """Query Jarvis with context from Pinecone and response from Groq"""
    try:
        # Retrieve relevant documents from Pinecone
        docs = vectorstore.similarity_search(question, k=5)
        
        if not docs:
            return {
                "answer": "I couldn't find any relevant information in my knowledge base. Try uploading some documents first!",
                "sources": [],
                "chunks_used": 0
            }
        
        # Combine context with sources
        context_parts = []
        sources = set()
        for doc in docs:
            context_parts.append(doc.page_content)
            source = doc.metadata.get('source', 'Unknown')
            sources.add(source)
        
        context = "\n\n".join(context_parts)
        sources_list = list(sources)
        
        # Create prompt with context
        prompt = f"""You are Jarvis, an intelligent AI assistant. Use the context below to answer the question accurately and conversationally.

Context from knowledge base (Sources: {', '.join(sources_list)}):
{context}

Question: {question}

Provide a clear, helpful, and friendly answer based on the context above."""
        
        # Get response from Groq
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are Jarvis, a helpful and knowledgeable AI assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return {
            "answer": response.choices[0].message.content,
            "sources": sources_list,
            "chunks_used": len(docs)
        }
    
    except Exception as e:
        return {"error": str(e)}

@app.route('/')
def home():
    return "🤖 Jarvis API is running!"

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    result = ask_jarvis(question)
    return jsonify(result)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only .txt and .pdf allowed'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process and store in Pinecone
        chunks_created = process_and_store_file(filepath, filename)
        
        return jsonify({
            'success': True,
            'message': f'File "{filename}" uploaded successfully!',
            'filename': filename,
            'chunks_created': chunks_created
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def stats():
    """Get system statistics"""
    try:
        index = pc.Index(INDEX_NAME)
        stats = index.describe_index_stats()
        
        return jsonify({
            'total_vectors': stats.total_vector_count,
            'dimension': stats.dimension,
            'llm_model': 'Llama 3.3 70B (Groq)',
            'vector_db': 'Pinecone',
            'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Jarvis is ready!'})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🤖 JARVIS ASSISTANT WITH FILE UPLOAD")
    print("="*60)
    print(f"📍 API: http://localhost:5000")
    print(f"💬 Chat: POST /api/chat")
    print(f"📤 Upload: POST /api/upload")
    print(f"📊 Stats: GET /api/stats")
    print(f"🧠 LLM: Groq (Llama 3.3 70B)")
    print(f"🗄️  Vector DB: Pinecone")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)