import asyncio
import logging
from typing import List, Optional
from uuid import UUID

from llama_index.core.workflow import Workflow, Event, StartEvent, StopEvent, step
from llama_index.llms.openrouter import OpenRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pydocs.config import settings
from pydocs.database import get_db
from pydocs.models import Document, Tag

# Configure logging
logger = logging.getLogger(__name__)


class DocumentTagEvent(Event):
    """Event for document tagging workflow."""

    document_id: UUID
    document_title: str
    document_content: Optional[str] = None


class TagGenerationEvent(Event):
    """Event for tag generation results."""

    document_id: UUID
    suggested_tags: List[str]


class DocumentTaggingWorkflow(Workflow):
    """Workflow for generating document tags using LLM."""

    def __init__(self):
        super().__init__()
        # Initialize OpenRouter LLM
        self.llm = OpenRouter(
            api_key=settings.OPENROUTER_API_KEY,
            model="meta-llama/llama-3.1-8b-instruct:free",  # Using free tier model
        )

    @step
    async def start_tagging(self, ev: StartEvent) -> DocumentTagEvent:
        """Start the document tagging process."""
        document_id = ev.get("document_id")
        document_title = ev.get("document_title")
        document_content = ev.get("document_content")

        logger.info(f"Starting tagging workflow for document {document_id}")

        return DocumentTagEvent(
            document_id=document_id,
            document_title=document_title,
            document_content=document_content,
        )

    @step
    async def generate_tags(self, ev: DocumentTagEvent) -> TagGenerationEvent:
        """Generate tags using OpenRouter LLM."""
        # Get existing tags from database
        existing_tags = await self._get_existing_tags()

        # Create prompt for LLM
        prompt = self._create_tagging_prompt(
            ev.document_title, ev.document_content, existing_tags
        )

        # Generate tags using LLM
        response = await self.llm.acomplete(prompt)
        suggested_tags = self._parse_tags_from_response(str(response))

        logger.info(f"Generated tags for document {ev.document_id}: {suggested_tags}")

        return TagGenerationEvent(
            document_id=ev.document_id, suggested_tags=suggested_tags
        )

    @step
    async def apply_tags(self, ev: TagGenerationEvent) -> StopEvent:
        """Apply generated tags to the document."""
        try:
            # Get database session
            async with get_db() as db:
                # Get the document
                result = await db.execute(
                    select(Document).where(Document.id == ev.document_id)
                )
                document = result.scalar_one_or_none()

                if not document:
                    logger.error(f"Document {ev.document_id} not found")
                    return StopEvent(result="Document not found")

                # Process each suggested tag
                for tag_name in ev.suggested_tags:
                    # Check if tag already exists
                    result = await db.execute(select(Tag).where(Tag.name == tag_name))
                    existing_tag = result.scalar_one_or_none()

                    if existing_tag:
                        # Use existing tag
                        tag = existing_tag
                    else:
                        # Create new tag
                        tag = Tag(name=tag_name)
                        db.add(tag)
                        await db.flush()  # Get the ID without committing

                    # Associate tag with document (avoiding duplicates)
                    if tag not in document.tags:
                        document.tags.append(tag)

                # Commit changes
                await db.commit()
                logger.info(f"Applied tags to document {ev.document_id}")

                return StopEvent(
                    result=f"Successfully applied tags to document {ev.document_id}"
                )
        except Exception as e:
            logger.error(f"Error applying tags to document {ev.document_id}: {str(e)}")
            return StopEvent(result=f"Error applying tags: {str(e)}")

    async def _get_existing_tags(self) -> List[str]:
        """Retrieve existing tags from the database."""
        try:
            async with get_db() as db:
                result = await db.execute(select(Tag.name))
                tags = result.scalars().all()
                return list(tags)
        except Exception as e:
            logger.error(f"Error retrieving existing tags: {str(e)}")
            return []

    def _create_tagging_prompt(
        self, title: str, content: Optional[str], existing_tags: List[str]
    ) -> str:
        """Create a prompt for the LLM to generate tags."""
        existing_tags_str = ", ".join(existing_tags) if existing_tags else "None"

        prompt = f"""
        Based on the document title and content, please suggest relevant tags for categorizing this document.
        
        Document Title: {title}
        
        Document Content: {content[:1000] if content else "No content available"}
        
        Existing tags in the system: {existing_tags_str}
        
        Please provide 3-7 relevant tags that would help categorize this document.
        Prefer using existing tags when appropriate to avoid redundancy.
        Return only the tags as a comma-separated list without any other text.
        
        Example response format: technology,python,web development
        """

        return prompt

    def _parse_tags_from_response(self, response: str) -> List[str]:
        """Parse tags from LLM response."""
        # Clean and split the response
        tags = response.strip().split(",")
        # Remove whitespace and filter out empty tags
        tags = [tag.strip().lower() for tag in tags if tag.strip()]
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        return unique_tags[:7]  # Limit to 7 tags maximum


# Initialize the workflow
document_tagging_workflow = DocumentTaggingWorkflow()


async def trigger_document_tagging(
    document_id: UUID, document_title: str, document_content: Optional[str] = None
):
    """
    Trigger the document tagging workflow.

    Args:
        document_id: The ID of the document to tag
        document_title: The title of the document
        document_content: The content of the document (optional)
    """
    try:
        # Run the workflow
        result = await document_tagging_workflow.run(
            document_id=document_id,
            document_title=document_title,
            document_content=document_content,
        )
        logger.info(f"Document tagging workflow completed: {result}")
    except Exception as e:
        logger.error(f"Error in document tagging workflow: {str(e)}")
