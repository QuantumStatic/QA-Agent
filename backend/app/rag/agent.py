from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq

from app.config import settings
from app.rag.chroma import get_chroma_collection


class AgentState(TypedDict):
    message: str
    user_id: str
    document_ids: list[str]
    conversation_history: list[dict]
    retrieved_chunks: list[dict]
    query: str
    iterations: int
    answer: str
    sufficient: bool


def _llm():
    return ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0)


def retrieve_chunks(state: AgentState) -> AgentState:
    collection = get_chroma_collection()
    query = state.get("query") or state["message"]
    doc_ids = state["document_ids"]
    if not doc_ids:
        return {**state, "retrieved_chunks": [], "iterations": state["iterations"] + 1}

    if len(doc_ids) == 1:
        where_filter = {"$and": [
            {"document_id": {"$eq": doc_ids[0]}},
            {"user_id": {"$eq": state["user_id"]}},
        ]}
    else:
        where_filter = {"$and": [
            {"document_id": {"$in": doc_ids}},
            {"user_id": {"$eq": state["user_id"]}},
        ]}

    results = collection.query(query_texts=[query], n_results=5, where=where_filter)
    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({
            "text": doc,
            "filename": meta.get("filename"),
            "page": meta.get("page"),
            "document_id": meta.get("document_id"),
        })
    return {**state, "retrieved_chunks": chunks, "iterations": state["iterations"] + 1}


def assess_sufficiency(state: AgentState) -> AgentState:
    if state["iterations"] >= settings.max_iterations or not state["document_ids"]:
        return {**state, "sufficient": True}
    context = "\n".join(c["text"] for c in state["retrieved_chunks"])
    prompt = (
        f"Given this context:\n{context}\n\n"
        f'Can you fully answer: "{state["message"]}"?\n'
        f"Reply with only YES or NO."
    )
    response = _llm().invoke(prompt)
    sufficient = "YES" in response.content.upper()
    return {**state, "sufficient": sufficient}


def refine_query(state: AgentState) -> AgentState:
    prompt = (
        f'Original question: {state["message"]}\n'
        f'Current search query: {state.get("query", state["message"])}\n'
        f"The retrieved context was insufficient. Generate a different, more specific search query.\n"
        f"Reply with only the new query."
    )
    response = _llm().invoke(prompt)
    return {**state, "query": response.content.strip()}


def generate_answer(state: AgentState) -> AgentState:
    context = "\n\n".join(
        f"[{c['filename']} p.{c['page']}]: {c['text']}"
        for c in state["retrieved_chunks"]
    )
    history = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}"
        for m in state["conversation_history"][-6:]
    )
    prompt = (
        f"You are a helpful assistant that answers questions based on the provided documents.\n\n"
        f"Conversation history:\n{history}\n\n"
        f"Retrieved context:\n{context}\n\n"
        f"Answer the question: {state['message']}\n"
        f"Be concise and cite the document filename when relevant."
    )
    response = _llm().invoke(prompt)
    return {**state, "answer": response.content}


def should_continue(state: AgentState) -> str:
    if state["sufficient"] or state["iterations"] >= settings.max_iterations:
        return "generate"
    return "refine"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_chunks)
    graph.add_node("assess", assess_sufficiency)
    graph.add_node("refine", refine_query)
    graph.add_node("generate", generate_answer)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "assess")
    graph.add_conditional_edges("assess", should_continue, {
        "generate": "generate",
        "refine": "refine",
    })
    graph.add_edge("refine", "retrieve")
    graph.add_edge("generate", END)
    return graph.compile()


_graph = build_graph()


def run_agent(message: str, user_id: str, document_ids: list[str], history: list[dict]) -> dict:
    state: AgentState = {
        "message": message,
        "user_id": user_id,
        "document_ids": document_ids,
        "conversation_history": history,
        "retrieved_chunks": [],
        "query": message,
        "iterations": 0,
        "answer": "",
        "sufficient": False,
    }
    result = _graph.invoke(state)
    sources = [{
        "documentId": c["document_id"],
        "filename": c["filename"],
        "page": c["page"],
        "excerpt": c["text"][:200],
    } for c in result["retrieved_chunks"][:3]]
    return {
        "answer": result["answer"],
        "sources": sources,
        "iterations_used": result["iterations"],
    }
