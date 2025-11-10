import os
from config import PINECONE_API_KEY, INDEX_NAME, GROQ_API_KEY

# --- LangChain + Pinecone ---
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

# --- Groq for LLM ---
from groq import Groq

# --- Setup ---
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

# 1️⃣ Load Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# 2️⃣ Load Embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# 3️⃣ Create Vector Store
vectorstore = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)

# 4️⃣ Initialize Groq Client
groq_client = Groq(api_key=GROQ_API_KEY)

# 5️⃣ Query Function
def ask_jarvis(question):
    """
    Query Jarvis with context from Pinecone and response from Groq
    """
    # Retrieve relevant documents from Pinecone
    docs = vectorstore.similarity_search(question, k=3)
    
    # Combine retrieved context
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Create prompt with context
    prompt = f"""You are Jarvis, an intelligent AI assistant. Use the context below to answer the question accurately and concisely.

Context from knowledge base:
{context}

Question: {question}

Provide a clear and helpful answer based on the context above."""
    
    # Get response from Groq (Llama 3.3 70B - FAST & FREE)
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are Jarvis, a helpful and knowledgeable AI assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content

# 6️⃣ Interactive Chat Loop
print("🤖 Jarvis Assistant is ready! (Type 'exit' or 'quit' to stop)\n")

while True:
    query = input("Ask Jarvis: ")
    
    if query.lower() in ["exit", "quit"]:
        print("👋 Goodbye!")
        break
    
    if not query.strip():
        continue
    
    try:
        print("\n🤖 Jarvis: ", end="", flush=True)
        response = ask_jarvis(query)
        print(response)
        print()  # Extra line for readability
    except Exception as e:
        print(f"❌ Error: {e}")
        print()