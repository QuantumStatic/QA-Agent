from unittest.mock import patch, MagicMock
from app.rag.agent import run_agent


def test_run_agent_no_documents():
    """When document_ids is empty, agent skips retrieval loop and generates."""
    with patch("app.rag.agent.get_chroma_collection") as mock_chroma, \
         patch("app.rag.agent._llm") as mock_llm:
        mock_chroma.return_value.query.return_value = {"documents": [[]], "metadatas": [[]]}
        mock_response = MagicMock()
        mock_response.content = "I don't have any documents to answer from."
        mock_llm.return_value.invoke.return_value = mock_response

        result = run_agent(
            message="hello",
            user_id="u1",
            document_ids=[],
            history=[],
        )
        assert "answer" in result
        assert result["sources"] == []
        assert result["iterations_used"] >= 1


def test_run_agent_with_documents():
    """With documents, agent retrieves chunks and generates answer."""
    fake_chunks = {
        "documents": [["Some text from PDF"]],
        "metadatas": [[{"filename": "test.pdf", "page": 1, "document_id": "doc1", "user_id": "u1"}]],
    }
    with patch("app.rag.agent.get_chroma_collection") as mock_chroma, \
         patch("app.rag.agent._llm") as mock_llm:
        mock_chroma.return_value.query.return_value = fake_chunks
        sufficient = MagicMock(); sufficient.content = "YES"
        answer = MagicMock(); answer.content = "Based on test.pdf, the answer is 42."
        mock_llm.return_value.invoke.side_effect = [sufficient, answer]

        result = run_agent(
            message="what is the answer?",
            user_id="u1",
            document_ids=["doc1"],
            history=[],
        )
        assert "42" in result["answer"]
        assert len(result["sources"]) == 1
        assert result["sources"][0]["filename"] == "test.pdf"
