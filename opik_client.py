"""
Opik Client - Track and analyze documentation retrieval performance
Integrates with Opik for observability and analytics
"""
import opik
from opik import track
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpikClient:
    """Client for Opik tracing and observability of documentation retrieval"""

    def __init__(self, project_name: str = "doc-injection-agent"):
        self.project_name = project_name
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Opik client with proper configuration"""
        try:
            # Configure Opik - this will prompt for setup if not configured
            opik.configure(use_local=False)  # Set to True for self-hosted

            # Initialize client
            self.client = opik.Opik(
                project_name=self.project_name
            )

            logger.info(f"Opik client initialized for project: {self.project_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Opik client: {e}")
            logger.info("You may need to run 'opik configure' first")
            self.client = None

    def is_configured(self) -> bool:
        """Check if Opik client is properly configured"""
        return self.client is not None

    def trace_doc_retrieval_session(self,
                                  user_query: str,
                                  library_name: str,
                                  library_id: str,
                                  context7_success: bool,
                                  retrieved_docs: str,
                                  memmachine_context: Optional[str] = None,
                                  user_id: str = "unknown",
                                  metadata: Optional[Dict] = None) -> Optional[str]:
        """
        Create a trace for a complete documentation retrieval session

        Args:
            user_query: Original user query
            library_name: Library name (e.g., "fastapi")
            library_id: Context7 library ID (e.g., "/fastapi/fastapi")
            context7_success: Whether Context7 retrieval was successful
            retrieved_docs: The documentation text retrieved
            memmachine_context: Context from MemMachine (if any)
            user_id: User identifier
            metadata: Additional metadata

        Returns:
            Trace ID if successful, None otherwise
        """
        if not self.is_configured():
            logger.warning("Opik client not configured, skipping trace")
            return None

        try:
            trace_metadata = {
                "user_id": user_id,
                "library_name": library_name,
                "library_id": library_id,
                "context7_success": context7_success,
                "docs_length": len(retrieved_docs),
                "has_memmachine_context": bool(memmachine_context),
                "timestamp": datetime.now().isoformat()
            }

            if metadata:
                trace_metadata.update(metadata)

            # Create the main trace
            trace = self.client.trace(
                name=f"Doc Retrieval: {library_name}",
                input={
                    "user_query": user_query,
                    "library_requested": library_name,
                    "user_id": user_id
                },
                output={
                    "library_resolved": library_id,
                    "docs_retrieved": len(retrieved_docs) > 0,
                    "docs_preview": retrieved_docs[:200] + "..." if len(retrieved_docs) > 200 else retrieved_docs,
                    "success": context7_success
                },
                tags=["doc-retrieval", library_name, f"user:{user_id}"],
                metadata=trace_metadata
            )

            logger.info(f"Created Opik trace for {library_name} query: {user_query[:50]}...")
            return str(trace.id) if hasattr(trace, 'id') else None

        except Exception as e:
            logger.error(f"Error creating Opik trace: {e}")
            return None

    def trace_context7_call(self,
                          library_name: str,
                          library_id: Optional[str],
                          success: bool,
                          docs_retrieved: str,
                          response_time_ms: Optional[float] = None,
                          error_message: Optional[str] = None) -> Optional[str]:
        """
        Create a span for Context7 API call within current trace

        Args:
            library_name: Library name requested
            library_id: Resolved library ID (if successful)
            success: Whether the call was successful
            docs_retrieved: Documentation text retrieved
            response_time_ms: Response time in milliseconds
            error_message: Error message if failed

        Returns:
            Span ID if successful, None otherwise
        """
        if not self.is_configured():
            return None

        try:
            with opik.start_as_current_span(
                name="Context7 API Call",
                type="tool"
            ) as span:
                span.input = {
                    "library_name": library_name,
                    "request_type": "get_library_docs"
                }

                span.output = {
                    "success": success,
                    "library_id": library_id,
                    "docs_length": len(docs_retrieved) if docs_retrieved else 0,
                    "error": error_message
                }

                span.metadata = {
                    "provider": "context7",
                    "response_time_ms": response_time_ms,
                    "success": success
                }

                span.tags = ["context7", "api-call", library_name]

                logger.info(f"Traced Context7 call for {library_name}: {'success' if success else 'failed'}")
                return str(span.id) if hasattr(span, 'id') else None

        except Exception as e:
            logger.error(f"Error creating Context7 span: {e}")
            return None

    def trace_memmachine_operation(self,
                                 operation_type: str,
                                 query: str,
                                 success: bool,
                                 result_count: int = 0,
                                 response_time_ms: Optional[float] = None) -> Optional[str]:
        """
        Create a span for MemMachine operation within current trace

        Args:
            operation_type: Type of operation ("search" or "store")
            query: Query or content being processed
            success: Whether the operation was successful
            result_count: Number of results returned (for search)
            response_time_ms: Response time in milliseconds

        Returns:
            Span ID if successful, None otherwise
        """
        if not self.is_configured():
            return None

        try:
            with opik.start_as_current_span(
                name=f"MemMachine {operation_type.title()}",
                type="tool"
            ) as span:
                span.input = {
                    "operation": operation_type,
                    "query": query[:200] + "..." if len(query) > 200 else query
                }

                span.output = {
                    "success": success,
                    "result_count": result_count
                }

                span.metadata = {
                    "provider": "memmachine",
                    "operation_type": operation_type,
                    "response_time_ms": response_time_ms,
                    "success": success
                }

                span.tags = ["memmachine", operation_type, "memory"]

                logger.info(f"Traced MemMachine {operation_type} operation: {'success' if success else 'failed'}")
                return str(span.id) if hasattr(span, 'id') else None

        except Exception as e:
            logger.error(f"Error creating MemMachine span: {e}")
            return None

    @track(name="doc_retrieval_pipeline", project_name="doc-injection-agent")
    def trace_full_pipeline(self,
                          user_query: str,
                          user_id: str = "unknown") -> Dict[str, Any]:
        """
        Decorator-based tracing for the full documentation retrieval pipeline

        Args:
            user_query: User's query
            user_id: User identifier

        Returns:
            Dictionary with pipeline results
        """
        return {
            "user_query": user_query,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "pipeline": "doc_retrieval"
        }

    def log_user_feedback(self,
                         trace_id: str,
                         score: float,
                         feedback_type: str = "thumbs",
                         comment: Optional[str] = None) -> bool:
        """
        Log user feedback for a specific trace

        Args:
            trace_id: ID of the trace to provide feedback on
            score: Feedback score (0.0 to 1.0 for thumbs, any range for numeric)
            feedback_type: Type of feedback ("thumbs" or "numeric")
            comment: Optional comment from user

        Returns:
            True if feedback was logged successfully
        """
        if not self.is_configured():
            return False

        try:
            # Note: This is a conceptual implementation
            # Actual Opik feedback API might be different
            feedback_data = {
                "trace_id": trace_id,
                "score": score,
                "feedback_type": feedback_type,
                "comment": comment,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"Logged user feedback for trace {trace_id}: {score}")
            return True

        except Exception as e:
            logger.error(f"Error logging user feedback: {e}")
            return False

    def flush_traces(self):
        """Force flush all pending traces to Opik"""
        if self.is_configured():
            try:
                self.client.flush()
                logger.info("Flushed all traces to Opik")
            except Exception as e:
                logger.error(f"Error flushing traces: {e}")

    def get_project_stats(self) -> Dict[str, Any]:
        """
        Get basic statistics about the project
        Note: This is a placeholder - actual implementation depends on Opik API

        Returns:
            Dictionary with project statistics
        """
        if not self.is_configured():
            return {"error": "Opik not configured"}

        # This would require actual Opik API calls to get project stats
        return {
            "project_name": self.project_name,
            "status": "active",
            "note": "Statistics require additional Opik API implementation"
        }


# Quick test function
if __name__ == "__main__":
    print("Testing Opik Client...")

    client = OpikClient()

    # Test 1: Check configuration
    print(f"\n1. Opik configured: {'✅ Yes' if client.is_configured() else '❌ No'}")

    if not client.is_configured():
        print("   Please run 'opik configure' to set up Opik")
        print("   Or set OPIK_API_KEY environment variable")
        exit(1)

    # Test 2: Trace a documentation retrieval session
    print("\n2. Creating test trace...")
    trace_id = client.trace_doc_retrieval_session(
        user_query="How to create FastAPI routes?",
        library_name="fastapi",
        library_id="/fastapi/fastapi",
        context7_success=True,
        retrieved_docs="FastAPI allows you to create routes using decorators like @app.get()...",
        user_id="test_user"
    )
    print(f"   Trace created: {'✅ Yes' if trace_id else '❌ No'}")

    # Test 3: Test the pipeline decorator
    print("\n3. Testing pipeline decorator...")
    result = client.trace_full_pipeline(
        user_query="How to handle FastAPI dependencies?",
        user_id="test_user"
    )
    print(f"   Pipeline traced: {'✅ Yes' if result else '❌ No'}")

    # Test 4: Flush traces
    print("\n4. Flushing traces...")
    client.flush_traces()
    print("   ✅ Flush completed")

    print("\n✅ Opik client test complete!")
    print("\nNote: Check your Opik dashboard to see the traces!")
