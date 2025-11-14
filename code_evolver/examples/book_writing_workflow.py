#!/usr/bin/env python3
"""
Book Writing Workflow Example

Demonstrates hierarchical evolution with multiple specialized LLMs:
- Planner: High-level book planning
- Plotter: Story arc and plot development
- Writer: Chapter writing
- Editor: Content editing and refinement
- Researcher: Fact-checking and research

Uses RAG at each level and stores progress in SQLite.
"""
import sys
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from overseer_llm import OverseerLlm, ExecutionPlan
from evaluator_llm import EvaluatorLlm, FitnessEvaluation
from hierarchical_evolver import HierarchicalEvolver, SharedPlanContext
from rag_integrated_tools import RAGIntegratedTools
from rag_memory import RAGMemory, ArtifactType
from tools_manager import ToolsManager, Tool, ToolType
from ollama_client import OllamaClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class BookStorageManager:
    """Manages SQLite storage for book writing workflow."""

    def __init__(self, db_path: str = "./book_project.db"):
        """
        Initialize storage manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()

        # Books table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                book_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                genre TEXT,
                target_words INTEGER,
                created_at TEXT,
                updated_at TEXT,
                status TEXT,
                metadata TEXT
            )
        ''')

        # Chapters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                chapter_id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL,
                chapter_number INTEGER,
                title TEXT,
                content TEXT,
                word_count INTEGER,
                status TEXT,
                quality_score REAL,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (book_id) REFERENCES books(book_id)
            )
        ''')

        # Outlines table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS outlines (
                outline_id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL,
                content TEXT,
                version INTEGER,
                quality_score REAL,
                created_at TEXT,
                FOREIGN KEY (book_id) REFERENCES books(book_id)
            )
        ''')

        # Research notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS research_notes (
                note_id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL,
                topic TEXT,
                content TEXT,
                source TEXT,
                created_at TEXT,
                FOREIGN KEY (book_id) REFERENCES books(book_id)
            )
        ''')

        self.conn.commit()
        logger.info(f"✓ Initialized database: {self.db_path}")

    def create_book(
        self,
        book_id: str,
        title: str,
        genre: str = "fiction",
        target_words: int = 50000,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create a new book project."""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO books (book_id, title, genre, target_words, created_at, updated_at, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            book_id,
            title,
            genre,
            target_words,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
            "planning",
            json.dumps(metadata or {})
        ))

        self.conn.commit()
        logger.info(f"✓ Created book project: {book_id}")

    def save_outline(
        self,
        book_id: str,
        outline_content: str,
        version: int = 1,
        quality_score: float = 0.0
    ) -> str:
        """Save book outline."""
        outline_id = f"{book_id}_outline_v{version}"
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO outlines (outline_id, book_id, content, version, quality_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            outline_id,
            book_id,
            outline_content,
            version,
            quality_score,
            datetime.utcnow().isoformat()
        ))

        self.conn.commit()
        logger.info(f"✓ Saved outline: {outline_id}")
        return outline_id

    def save_chapter(
        self,
        book_id: str,
        chapter_number: int,
        title: str,
        content: str,
        quality_score: float = 0.0
    ) -> str:
        """Save chapter content."""
        chapter_id = f"{book_id}_ch{chapter_number:02d}"
        word_count = len(content.split())
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO chapters
            (chapter_id, book_id, chapter_number, title, content, word_count, status, quality_score, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chapter_id,
            book_id,
            chapter_number,
            title,
            content,
            word_count,
            "draft",
            quality_score,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))

        self.conn.commit()
        logger.info(f"✓ Saved chapter {chapter_number}: {word_count} words")
        return chapter_id

    def get_book_progress(self, book_id: str) -> Dict[str, Any]:
        """Get book writing progress."""
        cursor = self.conn.cursor()

        # Get book info
        cursor.execute('SELECT * FROM books WHERE book_id = ?', (book_id,))
        book = cursor.execute.fetchone()

        # Get chapter count and word count
        cursor.execute('''
            SELECT COUNT(*) as chapter_count, SUM(word_count) as total_words
            FROM chapters WHERE book_id = ?
        ''', (book_id,))
        stats = cursor.fetchone()

        return {
            "book_id": book_id,
            "title": book["title"] if book else "Unknown",
            "chapters": stats["chapter_count"] if stats else 0,
            "total_words": stats["total_words"] if stats and stats["total_words"] else 0,
            "target_words": book["target_words"] if book else 0
        }

    def close(self):
        """Close database connection."""
        self.conn.close()


class BookWritingWorkflow:
    """
    Complete book writing workflow using hierarchical evolution.

    Workflow levels:
    1. WORKFLOW: Complete book creation
    2. NODEPLAN: Chapter/outline creation plans
    3. FUNCTION: Individual writing/editing functions
    """

    def __init__(self, project_dir: str = "./book_project"):
        """
        Initialize book writing workflow.

        Args:
            project_dir: Directory for project files
        """
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.client = OllamaClient()
        self.rag_memory = RAGMemory(memory_path=str(self.project_dir / "rag_memory"))
        self.tools_manager = ToolsManager(
            tools_path=str(self.project_dir / "tools"),
            ollama_client=self.client
        )

        # Initialize specialized LLMs
        self._register_specialized_llms()

        # Initialize evolution system
        self.overseer = OverseerLlm(rag_memory=self.rag_memory, model="llama3")
        self.evaluator = EvaluatorLlm(model="llama3")
        self.evolver = HierarchicalEvolver(
            overseer=self.overseer,
            evaluator=self.evaluator,
            rag_memory=self.rag_memory
        )

        self.rag_tools = RAGIntegratedTools(
            rag_memory=self.rag_memory,
            tools_manager=self.tools_manager,
            ollama_client=self.client
        )

        # Storage
        self.storage = BookStorageManager(str(self.project_dir / "book_project.db"))

        logger.info("✓ Book Writing Workflow initialized")

    def _register_specialized_llms(self):
        """Register specialized LLM tools for book writing."""

        # Planner LLM
        self.tools_manager.register_llm(
            tool_id="planner",
            name="Book Planner",
            description="Creates high-level book plans, outlines, and story structures",
            model_name="llama3",
            system_prompt="""You are an expert book planner. Your role is to:
1. Develop comprehensive book outlines
2. Define story arcs and narrative structures
3. Plan chapter sequences and pacing
4. Ensure coherent story flow

Be strategic, creative, and organized.""",
            tags=["planning", "structure", "book"]
        )

        # Plotter LLM
        self.tools_manager.register_llm(
            tool_id="plotter",
            name="Story Plotter",
            description="Develops plot details, story arcs, and dramatic tension",
            model_name="llama3",
            system_prompt="""You are an expert story plotter. Your role is to:
1. Develop compelling plot points
2. Create dramatic tension and conflict
3. Design character arcs
4. Ensure satisfying story progression

Be creative and emotionally engaging.""",
            tags=["plot", "story", "drama"]
        )

        # Writer LLM
        self.tools_manager.register_llm(
            tool_id="writer",
            name="Chapter Writer",
            description="Writes engaging chapter content with good prose",
            model_name="llama3",
            system_prompt="""You are an expert fiction writer. Your role is to:
1. Write engaging, vivid prose
2. Develop characters through dialogue and action
3. Create immersive scenes
4. Maintain consistent voice and style

Be creative, descriptive, and engaging.""",
            tags=["writing", "prose", "creative"]
        )

        # Editor LLM
        self.tools_manager.register_llm(
            tool_id="editor",
            name="Content Editor",
            description="Edits and refines content for quality and coherence",
            model_name="llama3",
            system_prompt="""You are an expert content editor. Your role is to:
1. Improve prose quality and clarity
2. Fix grammar, spelling, and style issues
3. Ensure consistency in voice and tone
4. Enhance readability and flow

Be thorough, constructive, and quality-focused.""",
            tags=["editing", "quality", "refinement"]
        )

        # Researcher LLM
        self.tools_manager.register_llm(
            tool_id="researcher",
            name="Research Assistant",
            description="Conducts research and fact-checking",
            model_name="llama3",
            system_prompt="""You are an expert research assistant. Your role is to:
1. Gather relevant information on topics
2. Verify facts and details
3. Provide context and background
4. Suggest authentic details

Be thorough, accurate, and informative.""",
            tags=["research", "facts", "accuracy"]
        )

        logger.info("✓ Registered 5 specialized LLMs")

    def create_book_outline(
        self,
        book_id: str,
        title: str,
        genre: str,
        synopsis: str,
        target_chapters: int = 20
    ) -> str:
        """
        Create book outline using Planner LLM.

        Args:
            book_id: Book identifier
            title: Book title
            genre: Genre (sci-fi, fantasy, mystery, etc.)
            synopsis: Brief synopsis
            target_chapters: Number of chapters

        Returns:
            Outline ID
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Creating Book Outline: {title}")
        logger.info(f"{'='*60}")

        # Create book project in database
        self.storage.create_book(
            book_id=book_id,
            title=title,
            genre=genre,
            metadata={"synopsis": synopsis, "target_chapters": target_chapters}
        )

        # Use Planner LLM to create outline
        planner_prompt = f"""Create a detailed book outline for:

Title: {title}
Genre: {genre}
Target Chapters: {target_chapters}

Synopsis:
{synopsis}

Create a JSON outline with:
1. Overall story arc
2. Chapter-by-chapter breakdown with:
   - Chapter number
   - Chapter title
   - Key events
   - Character development
   - Plot progression

Respond in JSON format:
{{
  "story_arc": "Three act structure description...",
  "chapters": [
    {{"number": 1, "title": "...", "summary": "...", "key_events": [...]}},
    ...
  ]
}}
"""

        outline_response = self.tools_manager.invoke_llm_tool(
            tool_id="planner",
            prompt=planner_prompt,
            temperature=0.8
        )

        # Save to database
        outline_id = self.storage.save_outline(
            book_id=book_id,
            outline_content=outline_response,
            version=1,
            quality_score=0.0  # Will be evaluated
        )

        # Save to RAG for future reference
        self.rag_memory.store_artifact(
            artifact_id=outline_id,
            artifact_type=ArtifactType.PLAN,
            name=f"Outline: {title}",
            description=f"Book outline for {genre} novel",
            content=outline_response,
            tags=["outline", genre, "book"],
            metadata={"book_id": book_id, "title": title}
        )

        logger.info(f"✓ Created outline: {outline_id}")
        return outline_id

    def write_chapter(
        self,
        book_id: str,
        chapter_number: int,
        chapter_title: str,
        chapter_summary: str,
        previous_context: str = ""
    ) -> str:
        """
        Write a chapter using hierarchical evolution.

        This demonstrates the complete flow:
        1. Search RAG for similar chapters (RAG at nodeplan level)
        2. Create execution plan with Overseer
        3. Execute with Writer LLM
        4. Evaluate with Evaluator
        5. Evolve if needed

        Args:
            book_id: Book identifier
            chapter_number: Chapter number
            chapter_title: Chapter title
            chapter_summary: What should happen in this chapter
            previous_context: Summary of previous chapters

        Returns:
            Chapter ID
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Writing Chapter {chapter_number}: {chapter_title}")
        logger.info(f"{'='*60}")

        # STEP 1: Search RAG for similar chapters
        logger.info("\n[STEP 1] Searching RAG for similar chapters...")
        similar_chapters = self.rag_tools.find_solution_at_level(
            level="nodeplan",
            task_description=f"{chapter_title}: {chapter_summary}",
            top_k=3,
            min_similarity=0.6
        )

        if similar_chapters:
            logger.info(f"Found {len(similar_chapters)} similar chapter(s):")
            for artifact, similarity in similar_chapters:
                logger.info(f"  - {artifact.name} (similarity: {similarity:.2f})")

        # STEP 2: Get tools for overseer
        logger.info("\n[STEP 2] Retrieving tools from RAG...")
        tools = self.rag_tools.get_tools_for_overseer(
            task_description=f"Write chapter: {chapter_summary}",
            level="nodeplan",
            max_tools=5
        )

        logger.info(f"Retrieved {len(tools)} relevant tools")

        # STEP 3: Create execution plan
        logger.info("\n[STEP 3] Creating execution plan with Overseer...")

        task_description = f"""Write Chapter {chapter_number}: {chapter_title}

Summary: {chapter_summary}

Previous Context: {previous_context if previous_context else "This is the first chapter"}

Requirements:
- Engaging prose
- Character development
- Scene description
- Dialogue
- 2000-3000 words
"""

        node_id = f"{book_id}_ch{chapter_number:02d}_writer"

        # Execute with hierarchical evolver
        plan, execution_result, evaluation = self.evolver.execute_with_plan(
            task_description=task_description,
            node_id=node_id,
            depth=1,  # Chapter is depth 1 (book is depth 0)
            parent_node_id=book_id,
            constraints={
                "quality_target": 0.8,
                "speed_target_ms": 30000  # 30 seconds
            }
        )

        logger.info(f"\n[STEP 4] Execution complete:")
        logger.info(f"  Quality: {evaluation.overall_score:.2f}")
        logger.info(f"  Verdict: {evaluation.verdict}")

        # For demonstration, use Writer LLM to actually write
        logger.info("\n[STEP 5] Writing chapter content with Writer LLM...")

        writer_prompt = f"""Write Chapter {chapter_number}: {chapter_title}

{chapter_summary}

Previous Context:
{previous_context if previous_context else "This is the opening chapter."}

Write an engaging chapter of 2000-3000 words with:
- Vivid descriptions
- Compelling dialogue
- Character development
- Scene progression

Write in an engaging, literary style."""

        chapter_content = self.tools_manager.invoke_llm_tool(
            tool_id="writer",
            prompt=writer_prompt,
            temperature=0.9
        )

        # STEP 6: Evaluate chapter quality
        logger.info("\n[STEP 6] Evaluating chapter quality...")

        chapter_evaluation = self.evaluator.evaluate_fitness(
            node_id=node_id,
            task_description=task_description,
            execution_result={
                "stdout": json.dumps({"chapter": chapter_content}),
                "stderr": "",
                "metrics": {
                    "exit_code": 0,
                    "latency_ms": 25000,
                    "memory_mb_peak": 128,
                    "success": True
                }
            },
            quality_targets={"quality": 0.8}
        )

        logger.info(f"  Chapter Quality: {chapter_evaluation.overall_score:.2f}")

        # STEP 7: Save chapter
        logger.info("\n[STEP 7] Saving chapter...")

        chapter_id = self.storage.save_chapter(
            book_id=book_id,
            chapter_number=chapter_number,
            title=chapter_title,
            content=chapter_content,
            quality_score=chapter_evaluation.overall_score
        )

        # STEP 8: Save to RAG for future learning
        logger.info("\n[STEP 8] Saving to RAG for future learning...")

        artifact_id = self.rag_tools.optimize_and_save(
            code=chapter_content,  # In this case, "code" is the chapter text
            task_description=f"{chapter_title}: {chapter_summary}",
            level="nodeplan",
            quality_score=chapter_evaluation.overall_score
        )

        logger.info(f"\n✓ Chapter {chapter_number} complete!")
        logger.info(f"  Chapter ID: {chapter_id}")
        logger.info(f"  Quality: {chapter_evaluation.overall_score:.2f}")
        logger.info(f"  Word Count: {len(chapter_content.split())}")

        return chapter_id

    def edit_chapter(
        self,
        book_id: str,
        chapter_number: int
    ) -> str:
        """
        Edit an existing chapter using Editor LLM.

        Args:
            book_id: Book identifier
            chapter_number: Chapter to edit

        Returns:
            Updated chapter ID
        """
        logger.info(f"\nEditing Chapter {chapter_number}...")

        # Get chapter from database
        cursor = self.storage.conn.cursor()
        cursor.execute('''
            SELECT * FROM chapters
            WHERE book_id = ? AND chapter_number = ?
        ''', (book_id, chapter_number))

        chapter = cursor.fetchone()

        if not chapter:
            logger.error(f"Chapter {chapter_number} not found")
            return ""

        # Use Editor LLM
        editor_prompt = f"""Edit and improve this chapter:

Title: {chapter['title']}

Current Content:
{chapter['content']}

Improve:
1. Prose quality and flow
2. Grammar and style
3. Dialogue naturalness
4. Scene descriptions
5. Pacing

Return the edited chapter."""

        edited_content = self.tools_manager.invoke_llm_tool(
            tool_id="editor",
            prompt=editor_prompt,
            temperature=0.7
        )

        # Save edited version
        chapter_id = self.storage.save_chapter(
            book_id=book_id,
            chapter_number=chapter_number,
            title=chapter['title'],
            content=edited_content,
            quality_score=0.0  # Could re-evaluate
        )

        logger.info(f"✓ Chapter {chapter_number} edited")
        return chapter_id

    def get_progress(self, book_id: str):
        """Get and display book writing progress."""
        progress = self.storage.get_book_progress(book_id)

        logger.info(f"\n{'='*60}")
        logger.info(f"Book Progress: {progress['title']}")
        logger.info(f"{'='*60}")
        logger.info(f"Chapters Written: {progress['chapters']}")
        logger.info(f"Total Words: {progress['total_words']:,}")
        logger.info(f"Target Words: {progress['target_words']:,}")
        logger.info(f"Progress: {(progress['total_words'] / progress['target_words'] * 100):.1f}%")

    def close(self):
        """Close workflow and cleanup."""
        self.storage.close()


def main():
    """Run book writing workflow example."""
    logger.info("\n" + "="*80)
    logger.info("BOOK WRITING WORKFLOW - HIERARCHICAL EVOLUTION EXAMPLE")
    logger.info("="*80)

    # Initialize workflow
    workflow = BookWritingWorkflow(project_dir="./book_project_example")

    try:
        # Create a book
        book_id = "scifi_novel_001"

        # Create outline
        outline_id = workflow.create_book_outline(
            book_id=book_id,
            title="The Quantum Paradox",
            genre="science fiction",
            synopsis="A physicist discovers a way to communicate with parallel universes, but each message changes the past in unexpected ways. She must navigate the consequences while preventing a catastrophic timeline collapse.",
            target_chapters=15
        )

        logger.info(f"\n✓ Outline created: {outline_id}")

        # Write first two chapters
        logger.info("\n" + "="*60)
        logger.info("Writing Chapters...")
        logger.info("="*60)

        # Chapter 1
        ch1_id = workflow.write_chapter(
            book_id=book_id,
            chapter_number=1,
            chapter_title="The Discovery",
            chapter_summary="Dr. Sarah Chen makes a breakthrough in quantum entanglement research, discovering signals from a parallel universe. She receives her first message - a warning."
        )

        # Chapter 2
        ch2_id = workflow.write_chapter(
            book_id=book_id,
            chapter_number=2,
            chapter_title="The First Message",
            chapter_summary="Sarah decodes the message and realizes it's from a version of herself in another timeline. The message warns of an impending disaster.",
            previous_context="Sarah discovered quantum communication with parallel universes and received a mysterious warning."
        )

        # Show progress
        workflow.get_progress(book_id)

        # Demonstrate editing
        logger.info("\n" + "="*60)
        logger.info("Editing Chapter 1...")
        logger.info("="*60)

        workflow.edit_chapter(book_id, 1)

        logger.info("\n" + "="*80)
        logger.info("✓ Book Writing Workflow Example Complete!")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

    finally:
        workflow.close()


if __name__ == "__main__":
    main()
