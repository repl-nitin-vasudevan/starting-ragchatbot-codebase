"""
Shared pytest fixtures for RAG system testing
"""
import pytest
from unittest.mock import Mock, MagicMock
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from typing import List, Dict


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    mock = Mock()
    mock.ANTHROPIC_API_KEY = "test-api-key"
    mock.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    mock.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    mock.CHUNK_SIZE = 800
    mock.CHUNK_OVERLAP = 100
    mock.MAX_RESULTS = 5
    mock.MAX_HISTORY = 2
    mock.CHROMA_PATH = "./test_chroma_db"
    return mock


@pytest.fixture
def mock_rag_system(mock_config):
    """Mock RAG system for testing"""
    rag = MagicMock()
    rag.config = mock_config

    # Mock session manager
    rag.session_manager = MagicMock()
    rag.session_manager.create_session.return_value = "test-session-123"
    rag.session_manager.clear_session.return_value = None

    # Mock vector store
    rag.vector_store = MagicMock()
    rag.vector_store.max_results = 5

    # Default query response
    rag.query.return_value = (
        "This is a test response about Python programming.",
        [
            {"text": "Python is a high-level programming language.", "url": "https://example.com/python"},
            {"text": "Python supports multiple paradigms.", "url": "https://example.com/paradigms"}
        ]
    )

    # Default course analytics
    rag.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": ["Introduction to Python", "Advanced JavaScript", "Data Structures"]
    }

    return rag


@pytest.fixture
def mock_test_data():
    """Shared test data for various test cases"""
    return {
        "query_request": {
            "query": "What is Python?",
            "session_id": "test-session-123"
        },
        "query_response": {
            "answer": "Python is a high-level programming language.",
            "sources": [
                {"text": "Python is versatile.", "url": "https://example.com/python"},
                {"text": "Python is beginner-friendly.", "url": None}
            ],
            "session_id": "test-session-123"
        },
        "course_stats": {
            "total_courses": 3,
            "course_titles": ["Introduction to Python", "Advanced JavaScript", "Data Structures"]
        }
    }


@pytest.fixture
def sample_course_data():
    """Sample course data for testing document processing"""
    return {
        "course_id": "CS101",
        "title": "Introduction to Python",
        "lessons": [
            {
                "lesson_number": 1,
                "title": "Python Basics",
                "content": "Python is a high-level programming language."
            },
            {
                "lesson_number": 2,
                "title": "Variables and Types",
                "content": "Python supports multiple data types."
            }
        ]
    }
