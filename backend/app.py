import warnings

warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

# CRITICAL: Import SSL fix FIRST before any other imports


from config import config
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from rag_system import RAGSystem

# Initialize FastAPI app
app = FastAPI(title="Course Materials RAG System", root_path="")

# Add trusted host middleware for proxy
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Enable CORS with proper settings for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize RAG system
rag_system = RAGSystem(config)


# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for course queries"""

    query: str
    session_id: str | None = None


class SourceItem(BaseModel):
    """Model for a single source with optional link"""

    text: str
    url: str | None = None


class QueryResponse(BaseModel):
    """Response model for course queries"""

    answer: str
    sources: list[SourceItem]
    session_id: str


class CourseStats(BaseModel):
    """Response model for course statistics"""

    total_courses: int
    course_titles: list[str]


# API Endpoints


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

        # Convert sources (list of dicts) to SourceItem objects
        source_items = [
            SourceItem(**src) if isinstance(src, dict) else SourceItem(text=src)
            for src in sources
        ]

        return QueryResponse(answer=answer, sources=source_items, session_id=session_id)
    except Exception as e:
        # Log the full error for debugging
        import traceback

        print("Error in /api/query endpoint:")
        print(f"  Query: {request.query}")
        print(f"  Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
    """Get course analytics and statistics"""
    try:
        analytics = rag_system.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"],
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


@app.on_event("startup")
async def startup_event():
    """Check for existing documents and configuration on startup"""
    print("Checking system configuration...")

    # Validate MAX_RESULTS configuration
    if rag_system.vector_store.max_results == 0:
        print("⚠️  WARNING: MAX_RESULTS is set to 0 - queries will fail!")
        print(
            "⚠️  Please update config.py to set MAX_RESULTS to a positive value (e.g., 5)"
        )
    else:
        print(f"✓ MAX_RESULTS: {rag_system.vector_store.max_results}")

    print("\nChecking for existing documents in vector store...")
    try:
        analytics = rag_system.get_course_analytics()
        print(f"Found {analytics['total_courses']} course(s) in vector store")
        if analytics["total_courses"] == 0:
            print(
                "⚠️  No documents loaded. Run 'uv run python load_documents.py' to load documents"
            )
    except Exception as e:
        print(f"Could not check course analytics: {e}")


# Custom static file handler with no-cache headers for development

from fastapi.responses import FileResponse


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# Serve static files for the frontend
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")
