"""
API endpoint tests for the RAG system
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional
from unittest.mock import Mock, patch


# Pydantic models (duplicated from app.py to avoid import issues with static files)
class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None


class SourceItem(BaseModel):
    """Model for a single source with optional link"""
    text: str
    url: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[SourceItem]
    session_id: str


class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]


@pytest.fixture
def test_app(mock_rag_system):
    """Create a test FastAPI app without static file mounting"""
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")

    # Add middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Use the mock RAG system
    rag_system = mock_rag_system

    # Define endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            # Create session if not provided
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            # Process query using RAG system
            answer, sources = rag_system.query(request.query, session_id)

            # Convert sources to SourceItem objects
            source_items = [SourceItem(**src) if isinstance(src, dict) else SourceItem(text=src) for src in sources]

            return QueryResponse(
                answer=answer,
                sources=source_items,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        """Clear a conversation session"""
        try:
            rag_system.session_manager.clear_session(session_id)
            return {"status": "success", "message": f"Session {session_id} cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        """Root endpoint for health check"""
        return {"status": "ok", "message": "RAG System API is running"}

    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the FastAPI app"""
    return TestClient(test_app)


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for /api/query endpoint"""

    def test_query_with_session_id(self, client, mock_test_data):
        """Test query endpoint with provided session ID"""
        response = client.post(
            "/api/query",
            json=mock_test_data["query_request"]
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"
        assert isinstance(data["sources"], list)

    def test_query_without_session_id(self, client, mock_rag_system):
        """Test query endpoint without session ID (should create one)"""
        response = client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        # Verify session was created
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_with_empty_query(self, client):
        """Test query endpoint with invalid request (missing query)"""
        response = client.post(
            "/api/query",
            json={"session_id": "test-session"}
        )

        assert response.status_code == 422  # Validation error

    def test_query_response_structure(self, client, mock_rag_system):
        """Test that query response has correct structure"""
        mock_rag_system.query.return_value = (
            "Test answer",
            [
                {"text": "Source 1", "url": "https://example.com/1"},
                {"text": "Source 2", "url": None}
            ]
        )

        response = client.post(
            "/api/query",
            json={"query": "Test query", "session_id": "test-123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Test answer"
        assert len(data["sources"]) == 2
        assert data["sources"][0]["text"] == "Source 1"
        assert data["sources"][0]["url"] == "https://example.com/1"
        assert data["sources"][1]["url"] is None

    def test_query_error_handling(self, client, mock_rag_system):
        """Test query endpoint error handling"""
        mock_rag_system.query.side_effect = Exception("Database error")

        response = client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )

        assert response.status_code == 500
        assert "detail" in response.json()


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for /api/courses endpoint"""

    def test_get_courses_success(self, client, mock_test_data):
        """Test successful retrieval of course statistics"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 3
        assert isinstance(data["course_titles"], list)
        assert len(data["course_titles"]) == 3

    def test_get_courses_structure(self, client):
        """Test that courses response has correct structure"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        for title in data["course_titles"]:
            assert isinstance(title, str)

    def test_get_courses_error_handling(self, client, mock_rag_system):
        """Test courses endpoint error handling"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Vector store error")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "detail" in response.json()


@pytest.mark.api
class TestSessionEndpoint:
    """Tests for /api/session/{session_id} endpoint"""

    def test_clear_session_success(self, client, mock_rag_system):
        """Test successful session clearing"""
        session_id = "test-session-456"
        response = client.delete(f"/api/session/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert session_id in data["message"]
        mock_rag_system.session_manager.clear_session.assert_called_once_with(session_id)

    def test_clear_session_error_handling(self, client, mock_rag_system):
        """Test session clearing error handling"""
        mock_rag_system.session_manager.clear_session.side_effect = Exception("Session not found")

        response = client.delete("/api/session/invalid-session")

        assert response.status_code == 500
        assert "detail" in response.json()


@pytest.mark.api
class TestRootEndpoint:
    """Tests for / root endpoint"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns health check"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data


@pytest.mark.api
class TestRequestValidation:
    """Tests for request validation"""

    def test_query_request_validation_missing_field(self, client):
        """Test that missing required fields return 422"""
        response = client.post("/api/query", json={})
        assert response.status_code == 422

    def test_query_request_validation_wrong_type(self, client):
        """Test that wrong field types return 422"""
        response = client.post("/api/query", json={"query": 123})
        assert response.status_code == 422

    def test_query_request_validation_extra_fields(self, client):
        """Test that extra fields are ignored"""
        response = client.post(
            "/api/query",
            json={
                "query": "What is Python?",
                "extra_field": "should be ignored"
            }
        )
        assert response.status_code == 200


@pytest.mark.api
class TestIntegrationFlow:
    """Integration tests for complete API flows"""

    def test_complete_query_flow(self, client, mock_rag_system):
        """Test complete flow: query -> get courses -> clear session"""
        # Step 1: Make a query (creates session)
        query_response = client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )
        assert query_response.status_code == 200
        session_id = query_response.json()["session_id"]

        # Step 2: Get course stats
        courses_response = client.get("/api/courses")
        assert courses_response.status_code == 200
        assert courses_response.json()["total_courses"] > 0

        # Step 3: Clear the session
        clear_response = client.delete(f"/api/session/{session_id}")
        assert clear_response.status_code == 200
        assert clear_response.json()["status"] == "success"

    def test_multiple_queries_same_session(self, client, mock_rag_system):
        """Test multiple queries with the same session ID"""
        session_id = "test-persistent-session"

        # First query
        response1 = client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": session_id}
        )
        assert response1.status_code == 200

        # Second query with same session
        response2 = client.post(
            "/api/query",
            json={"query": "Tell me more about functions", "session_id": session_id}
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Verify query was called twice
        assert mock_rag_system.query.call_count == 2
