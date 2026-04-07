import os
import aiohttp
import json
import logging
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

# Initialize the embedding model globally so it stays in memory
# Using an extreme lightweight model since this runs locally
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    logger.error(f"Could not load SentenceTransformer: {e}")
    model = None

# In-memory store for vector indexes (in production, use Pinecone/Milvus or Mongo Atlas Vector Search)
matter_vectors = {}  # Format: {matter_id: {"chunks": [], "embeddings": []}}

async def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    try:
        if ext == ".pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n\n"
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
    return text

def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list:
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

async def index_document(file_id: str, file_path: str, matter_id: str):
    """Extracts text, chunks it, embeds it, and stores it in the index for the matter."""
    if not model:
        logger.error("Embedding model not loaded. Skipping indexing.")
        return
        
    logger.info(f"Indexing document {file_id} for matter {matter_id}...")
    
    # 1. Extract text
    text = await extract_text(file_path)
    if not text.strip():
        logger.warning(f"No text extracted from {file_id}")
        return
        
    # 2. Chunk text
    chunks = chunk_text(text)
    
    # 3. Create context-aware chunks (attach file ID for tracking)
    chunk_docs = [{"file_id": file_id, "text": chunk} for chunk in chunks]
    
    # 4. Generate embeddings
    texts_to_embed = [c["text"] for c in chunk_docs]
    embeddings = model.encode(texts_to_embed, convert_to_numpy=True)
    
    # 5. Store in vector index
    if matter_id not in matter_vectors:
        matter_vectors[matter_id] = {"chunks": [], "embeddings": np.empty((0, embeddings.shape[1]))}
        
    matter_vectors[matter_id]["chunks"].extend(chunk_docs)
    matter_vectors[matter_id]["embeddings"] = np.vstack([matter_vectors[matter_id]["embeddings"], embeddings])
    
    logger.info(f"Successfully indexed {len(chunks)} chunks for {file_id}")

async def query_documents(matter_id: str, query: str, top_k: int = 3) -> dict:
    """Queries the document index for a matter and uses Groq LLaMA3 to synthesize the answer."""
    if matter_id not in matter_vectors or len(matter_vectors[matter_id]["chunks"]) == 0:
        return {"answer": "No documents indexed for this matter.", "sources": [], "chunks": []}
        
    if not model:
        return {"answer": "Error: Embedding engine offline.", "sources": [], "chunks": []}
        
    logger.info(f"Querying matter {matter_id} for: '{query}'")
    
    # 1. Embed query
    query_embedding = model.encode([query], convert_to_numpy=True)
    
    # 2. Compute cosine similarity
    index_embeddings = matter_vectors[matter_id]["embeddings"]
    
    # Normalize for cosine similarity
    q_norm = np.linalg.norm(query_embedding[0])
    query_norm = query_embedding[0] / q_norm if q_norm != 0 else query_embedding[0]
    
    idx_norms = np.linalg.norm(index_embeddings, axis=1, keepdims=True)
    idx_normalized = np.divide(index_embeddings, idx_norms, out=np.zeros_like(index_embeddings), where=idx_norms!=0)
    
    similarities = np.dot(idx_normalized, query_norm)
    
    # 3. Get top K indices
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    # 4. Retrieve chunks
    relevant_chunks = []
    source_files = set()
    
    for i, idx in enumerate(top_indices):
        score = similarities[idx]
        if score < 0.2:  # very low relevance threshold
            continue
            
        chunk_data = matter_vectors[matter_id]["chunks"][idx]
        relevant_chunks.append({
            "text": chunk_data["text"],
            "file_id": chunk_data["file_id"],
            "score": float(score)
        })
        source_files.add(chunk_data["file_id"])

    if not relevant_chunks:
        return {"answer": "I could not find any relevant information in the uploaded documents to answer this query.", "sources": list(source_files), "chunks": []}

    # 5. Synthesize answer with LLM
    context_text = "\n\n---\n\n".join([f"SOURCE ({c['file_id']}):\n{c['text']}" for c in relevant_chunks])
    
    system_prompt = """You are the Associate Bulk Document Intelligence Engine.
Your job is to answer the user's question based ONLY on the provided document excerpts.
If the excerpts do not contain the answer, say "The provided documents do not contain information to answer this."
Always cite the source document ID when stating a fact."""

    user_prompt = f"USER QUERY: {query}\n\nDOCUMENT EXCERPTS:\n{context_text}\n\nBased on the excerpts above, answer the query."
    
    try:
        async with aiohttp.ClientSession() as session:
            groq_key = os.environ.get("GROQ_KEY", "")
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1
            }
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    answer = data["choices"][0]["message"]["content"]
                else:
                    answer = f"Error generating answer: {await resp.text()}"
    except Exception as e:
        answer = f"Error contacting AI model: {e}"

    return {
        "answer": answer,
        "sources": list(source_files),
        "chunks": relevant_chunks
    }
