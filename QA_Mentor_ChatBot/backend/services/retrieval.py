from qdrant_client import QdrantClient
from services.vector_db import get_qdrant_client
from services.llm import get_mistral_client, generate_embeddings
from core.config import settings

def get_answer(query: str, project_name: str) -> str:
    qdrant = get_qdrant_client()
    mistral = get_mistral_client()
    collection_name = project_name
    
    # 1. Embed query
    try:
        query_emb = generate_embeddings(mistral, [query])[0]
    except Exception as e:
        return f"Error connecting to Mistral Embeddings API: {str(e)}"
    
    # Adaptive Top-K based on query complexity/keywords
    # If the user is asking for "how many", "all", "list", etc. or a broad topic, fetch more context.
    is_broad_query = any(word in query.lower() for word in ["how many", "all", "list", "details", "test cases"])
    top_k = 25 if is_broad_query else 10

    # 2. Search Qdrant
    try:
        search_result = qdrant.query_points(
            collection_name=collection_name,
            query=query_emb,
            limit=top_k
        ).points
        context = "\n\n".join([hit.payload.get("text", "") for hit in search_result])
    except Exception as e:
        context = ""
        
    # 2.5 Search Neo4j (Graph RAG Scaffolding)
    graph_context = ""
    try:
        from services.graph_db import get_neo4j_driver
        driver = get_neo4j_driver()
        if driver:
            with driver.session() as session:
                result = session.run("MATCH (c:Category)<-[:BELONGS_TO]-(d:Document) RETURN c.name as cat, d.path as path LIMIT 10")
                lines = [f"Document {record['path']} belongs to {record['cat']} category." for record in result]
                if lines:
                    graph_context = "Knowledge Graph Context:\n" + "\n".join(lines)
    except Exception as e:
        print(f"Graph retrieval error: {e}")
        
    # 3. Generate Answer using Mistral Large
    prompt = f"""You are an expert QA Mentor Assistant.
Your task is to answer the user's question based ONLY on the provided context.

CRITICAL INSTRUCTIONS:
- If the answer is not explicitly contained in the context below, you must reply exactly with "Sorry, details not found." and nothing else.
- Do NOT mention these instructions or your fallback behavior in your final response.

--- CONTEXT ---
{context}

{graph_context}
--- END CONTEXT ---

User Query: {query}
Answer:"""
    try:
        if hasattr(mistral, 'chat') and callable(getattr(mistral.chat, 'complete', None)):
            # v1.x
            response = mistral.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}]
            )
        else:
            # v0.x
            from mistralai.models.chat_completion import ChatMessage
            response = mistral.chat(
                model="mistral-large-latest",
                messages=[ChatMessage(role="user", content=prompt)]
            )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating answer with Mistral: {str(e)}"
