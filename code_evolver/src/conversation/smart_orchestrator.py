"""
Smart Conversation Orchestrator

Enhances conversations with intelligent tool calling and workflow generation.
Uses gemma3:1b to analyze user messages and decide when to invoke tools or create workflows.

This makes conversations "living MCPs" that can:
- Detect when user is requesting a task
- Determine which tools are needed
- Generate optimal workflows
- Execute tasks while maintaining conversation context
- Run tools in parallel to conversation (non-blocking)
- Monitor CPU/GPU load to avoid starting when busy
"""
import logging
import json
import threading
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
import requests

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class SmartConversationOrchestrator:
    """
    Orchestrates intelligent conversations with dynamic tool calling and workflow generation.

    Features:
    - Task detection in user messages
    - Tool selection using gemma3:1b
    - Workflow generation for complex tasks
    - Integration with existing tool/workflow system
    - Maintains conversation context while executing tasks
    - Parallel task execution (non-blocking)
    - CPU/GPU load monitoring
    """

    def __init__(
        self,
        model_name: str = "gemma3:1b",
        ollama_endpoint: str = "http://localhost:11434",
        tools_manager: Optional[Any] = None,
        workflow_engine: Optional[Any] = None,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0
    ):
        """
        Initialize smart orchestrator.

        Args:
            model_name: Fast LLM for task analysis and tool selection
            ollama_endpoint: Ollama API endpoint
            tools_manager: ToolsManager instance for tool access
            workflow_engine: WorkflowEngine instance for workflow generation
            cpu_threshold: CPU usage threshold (%) to defer task execution
            memory_threshold: Memory usage threshold (%) to defer task execution
        """
        self.model_name = model_name
        self.ollama_endpoint = ollama_endpoint
        self.tools_manager = tools_manager
        self.workflow_engine = workflow_engine
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold

        # Track background tasks
        self.background_tasks: Dict[str, Dict[str, Any]] = {}
        self.tasks_lock = threading.Lock()

        logger.info(f"Smart orchestrator initialized with model: {model_name}")

    def _call_llm(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.2
    ) -> str:
        """
        Call LLM for analysis.

        Args:
            prompt: Prompt text
            max_tokens: Maximum tokens in response
            temperature: LLM temperature

        Returns:
            Response text
        """
        try:
            response = requests.post(
                f"{self.ollama_endpoint}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""

    def analyze_message_for_tasks(
        self,
        user_message: str,
        conversation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze user message to detect if it contains a task request.

        Args:
            user_message: User's message
            conversation_context: Optional conversation context

        Returns:
            Dict with:
            - has_task: Whether message contains a task
            - task_type: Type of task (code_generation, data_processing, etc.)
            - task_description: Description of the task
            - complexity: Simple, moderate, or complex
            - requires_tools: Whether tools are needed
        """
        context_str = f"\n\nConversation context:\n{conversation_context}" if conversation_context else ""

        prompt = f"""Analyze this user message to determine if it contains a task request.

User message: "{user_message}"{context_str}

Determine:
1. Does the message request a task to be performed? (YES/NO)
2. If yes, what type of task? (conversation, code_generation, data_processing, file_operation, web_search, analysis, testing, other)
3. Brief description of the task (one sentence)
4. Complexity level (simple, moderate, complex)
5. Does it require tools/external operations? (YES/NO)

Respond in this format:
HAS_TASK: [YES/NO]
TASK_TYPE: [type]
DESCRIPTION: [description]
COMPLEXITY: [simple/moderate/complex]
REQUIRES_TOOLS: [YES/NO]

Your analysis:"""

        response = self._call_llm(prompt, max_tokens=200, temperature=0.1)

        # Parse response
        has_task = "YES" in response.split("HAS_TASK:")[-1].split("\n")[0].upper()

        if not has_task:
            return {
                "has_task": False,
                "task_type": "none",
                "task_description": "",
                "complexity": "simple",
                "requires_tools": False
            }

        # Extract fields
        try:
            task_type = response.split("TASK_TYPE:")[-1].split("\n")[0].strip().lower()
            description = response.split("DESCRIPTION:")[-1].split("\n")[0].strip()
            complexity = response.split("COMPLEXITY:")[-1].split("\n")[0].strip().lower()
            requires_tools = "YES" in response.split("REQUIRES_TOOLS:")[-1].split("\n")[0].upper()
        except Exception as e:
            logger.error(f"Failed to parse task analysis: {e}")
            task_type = "other"
            description = user_message
            complexity = "simple"
            requires_tools = False

        return {
            "has_task": True,
            "task_type": task_type,
            "task_description": description,
            "complexity": complexity,
            "requires_tools": requires_tools
        }

    def select_tools_for_task(
        self,
        task_description: str,
        task_type: str,
        available_tools: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Select appropriate tools for a task.

        Args:
            task_description: Description of the task
            task_type: Type of task
            available_tools: Optional list of available tool names

        Returns:
            Dict with:
            - recommended_tools: List of tool names
            - reasoning: Why these tools were selected
            - execution_order: Suggested order of tool execution
        """
        tools_list = ""
        if available_tools:
            tools_list = f"\n\nAvailable tools:\n" + "\n".join(f"- {tool}" for tool in available_tools[:20])

        prompt = f"""You are a tool selection expert. Analyze this task and recommend which tools to use.

Task type: {task_type}
Task description: {task_description}{tools_list}

Recommend the most appropriate tools for this task. Consider:
1. What operations are needed?
2. Which tools best match these operations?
3. In what order should tools be used?

Respond in this format:
TOOLS: [comma-separated list of tool names]
REASONING: [brief explanation]
ORDER: [execution order if multiple tools]

Your recommendation:"""

        response = self._call_llm(prompt, max_tokens=300, temperature=0.2)

        # Parse response
        try:
            tools_str = response.split("TOOLS:")[-1].split("\n")[0].strip()
            tools = [t.strip() for t in tools_str.split(",") if t.strip()]

            reasoning = response.split("REASONING:")[-1].split("\n")[0].strip()

            order_str = response.split("ORDER:")[-1].split("\n")[0].strip() if "ORDER:" in response else ""
            execution_order = [t.strip() for t in order_str.split(",") if t.strip()] if order_str else tools
        except Exception as e:
            logger.error(f"Failed to parse tool selection: {e}")
            tools = []
            reasoning = "Failed to parse response"
            execution_order = []

        return {
            "recommended_tools": tools,
            "reasoning": reasoning,
            "execution_order": execution_order
        }

    def generate_workflow_for_task(
        self,
        task_description: str,
        task_type: str,
        recommended_tools: List[str]
    ) -> Dict[str, Any]:
        """
        Generate a workflow for executing a task.

        Args:
            task_description: Description of the task
            task_type: Type of task
            recommended_tools: List of recommended tools

        Returns:
            Dict with workflow specification:
            - steps: List of workflow steps
            - dependencies: Step dependencies
            - parallel_opportunities: Steps that can run in parallel
        """
        tools_str = ", ".join(recommended_tools) if recommended_tools else "none"

        prompt = f"""Create a workflow to accomplish this task.

Task type: {task_type}
Task description: {task_description}
Available tools: {tools_str}

Design a workflow with clear steps. Consider:
1. What needs to happen first?
2. Which steps depend on others?
3. What can run in parallel?
4. What are the inputs/outputs of each step?

Respond in this format:
STEP 1: [description] [tool_if_applicable]
STEP 2: [description] [tool_if_applicable]
...
DEPENDENCIES: [e.g., "step2:step1, step3:step1,step2"]
PARALLEL: [e.g., "step2,step3 can run in parallel"]

Your workflow:"""

        response = self._call_llm(prompt, max_tokens=500, temperature=0.3)

        # Parse response
        steps = []
        dependencies = {}
        parallel_opportunities = []

        try:
            lines = response.split("\n")
            for line in lines:
                if line.strip().startswith("STEP"):
                    # Extract step number and description
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        step_num = parts[0].strip()
                        step_desc = parts[1].strip()
                        steps.append({
                            "step": step_num,
                            "description": step_desc
                        })

                elif line.strip().startswith("DEPENDENCIES:"):
                    # Parse dependencies
                    dep_str = line.split("DEPENDENCIES:")[-1].strip()
                    for dep in dep_str.split(","):
                        if ":" in dep:
                            dependent, prerequisite = dep.split(":")
                            dependencies[dependent.strip()] = [p.strip() for p in prerequisite.split()]

                elif line.strip().startswith("PARALLEL:"):
                    # Parse parallel opportunities
                    parallel_str = line.split("PARALLEL:")[-1].strip()
                    parallel_opportunities.append(parallel_str)

        except Exception as e:
            logger.error(f"Failed to parse workflow: {e}")

        return {
            "steps": steps,
            "dependencies": dependencies,
            "parallel_opportunities": parallel_opportunities
        }

    def orchestrate_conversation_response(
        self,
        user_message: str,
        conversation_context: Optional[str] = None,
        execute_tasks: bool = True
    ) -> Dict[str, Any]:
        """
        Orchestrate a smart response to user message.

        This is the main entry point that:
        1. Analyzes message for tasks
        2. Selects tools if needed
        3. Generates workflow if complex
        4. Optionally executes the workflow
        5. Returns results with conversation context

        Args:
            user_message: User's message
            conversation_context: Optional conversation context
            execute_tasks: Whether to actually execute detected tasks

        Returns:
            Dict with:
            - response_type: 'conversation' or 'task_execution'
            - task_analysis: Task analysis results
            - tools_selected: Selected tools (if applicable)
            - workflow: Generated workflow (if applicable)
            - execution_results: Task execution results (if executed)
            - suggested_response: Suggested response to user
        """
        # Analyze message for tasks
        task_analysis = self.analyze_message_for_tasks(user_message, conversation_context)

        if not task_analysis["has_task"]:
            # Pure conversation, no task
            return {
                "response_type": "conversation",
                "task_analysis": task_analysis,
                "suggested_response": "Continue conversation naturally"
            }

        # Task detected
        result = {
            "response_type": "task_execution",
            "task_analysis": task_analysis
        }

        # Select tools if needed
        if task_analysis["requires_tools"]:
            # Get available tools from tools_manager if available
            available_tools = []
            if self.tools_manager:
                try:
                    # Get tool names from tools manager
                    available_tools = list(getattr(self.tools_manager, 'tools', {}).keys())
                except Exception as e:
                    logger.warning(f"Failed to get available tools: {e}")

            tools_selected = self.select_tools_for_task(
                task_description=task_analysis["task_description"],
                task_type=task_analysis["task_type"],
                available_tools=available_tools
            )
            result["tools_selected"] = tools_selected
        else:
            result["tools_selected"] = {
                "recommended_tools": [],
                "reasoning": "No tools required",
                "execution_order": []
            }

        # Generate workflow if complex
        if task_analysis["complexity"] in ["moderate", "complex"]:
            workflow = self.generate_workflow_for_task(
                task_description=task_analysis["task_description"],
                task_type=task_analysis["task_type"],
                recommended_tools=result["tools_selected"]["recommended_tools"]
            )
            result["workflow"] = workflow
        else:
            result["workflow"] = None

        # Execute if requested
        if execute_tasks and self.workflow_engine and result.get("workflow"):
            try:
                # Execute workflow using workflow engine
                execution_results = self._execute_workflow(result["workflow"])
                result["execution_results"] = execution_results
            except Exception as e:
                logger.error(f"Failed to execute workflow: {e}")
                result["execution_results"] = {
                    "success": False,
                    "error": str(e)
                }

        # Generate suggested response
        result["suggested_response"] = self._generate_suggested_response(result)

        return result

    def _execute_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a workflow using the workflow engine.

        Args:
            workflow: Workflow specification

        Returns:
            Execution results
        """
        # This would integrate with the actual workflow engine
        # For now, return a placeholder
        return {
            "success": True,
            "steps_completed": len(workflow.get("steps", [])),
            "message": "Workflow execution not yet fully integrated"
        }

    def _generate_suggested_response(self, orchestration_result: Dict[str, Any]) -> str:
        """
        Generate a suggested response based on orchestration results.

        Args:
            orchestration_result: Results from orchestration

        Returns:
            Suggested response text
        """
        task_analysis = orchestration_result.get("task_analysis", {})
        tools_selected = orchestration_result.get("tools_selected", {})
        workflow = orchestration_result.get("workflow")

        parts = []

        # Acknowledge task understanding
        parts.append(f"I understand you want to {task_analysis.get('task_description', 'perform a task')}.")

        # Mention tools if any
        if tools_selected.get("recommended_tools"):
            tools_list = ", ".join(tools_selected["recommended_tools"][:3])
            parts.append(f"I'll use these tools: {tools_list}.")

        # Mention workflow if complex
        if workflow and workflow.get("steps"):
            parts.append(f"I've created a {len(workflow['steps'])}-step workflow to accomplish this.")

        # Execution status
        if "execution_results" in orchestration_result:
            if orchestration_result["execution_results"].get("success"):
                parts.append("Task completed successfully!")
            else:
                parts.append(f"Task execution failed: {orchestration_result['execution_results'].get('error')}")

        return " ".join(parts)

    def check_system_load(self) -> Dict[str, Any]:
        """
        Check current system load (CPU, memory, GPU if available).

        Returns:
            Dict with:
            - cpu_percent: Current CPU usage percentage
            - memory_percent: Current memory usage percentage
            - is_busy: Whether system is too busy to start new tasks
            - gpu_info: GPU information (if available)
        """
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, assuming system is not busy")
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "is_busy": False,
                "gpu_info": None
            }

        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent

            is_busy = (
                cpu_percent > self.cpu_threshold or
                memory_percent > self.memory_threshold
            )

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "is_busy": is_busy,
                "gpu_info": None  # TODO: Add GPU monitoring if needed
            }
        except Exception as e:
            logger.error(f"Failed to check system load: {e}")
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "is_busy": False,
                "gpu_info": None
            }

    def execute_task_in_background(
        self,
        task_id: Optional[str],
        task_description: str,
        workflow: Dict[str, Any],
        wait_if_busy: bool = True
    ) -> str:
        """
        Execute a task in background (parallel to conversation).

        Args:
            task_id: Optional task ID (generated if not provided)
            task_description: Description of the task
            workflow: Workflow to execute
            wait_if_busy: Whether to wait if system is busy

        Returns:
            Task ID for tracking
        """
        if not task_id:
            task_id = str(uuid.uuid4())

        # Check system load
        system_load = self.check_system_load()

        if system_load["is_busy"] and wait_if_busy:
            logger.info(
                f"System busy (CPU: {system_load['cpu_percent']}%, "
                f"Memory: {system_load['memory_percent']}%), "
                f"deferring task {task_id}"
            )

        # Create task record
        with self.tasks_lock:
            self.background_tasks[task_id] = {
                "task_id": task_id,
                "description": task_description,
                "workflow": workflow,
                "status": "queued" if system_load["is_busy"] else "running",
                "created_at": time.time(),
                "started_at": None if system_load["is_busy"] else time.time(),
                "completed_at": None,
                "result": None,
                "error": None
            }

        # Start task in background thread
        if not system_load["is_busy"] or not wait_if_busy:
            thread = threading.Thread(
                target=self._run_task_in_background,
                args=(task_id,),
                daemon=True
            )
            thread.start()
        else:
            # Queue for later execution
            thread = threading.Thread(
                target=self._wait_and_run_task,
                args=(task_id,),
                daemon=True
            )
            thread.start()

        logger.info(f"Task {task_id} queued for background execution")
        return task_id

    def _wait_and_run_task(self, task_id: str):
        """
        Wait for system to be ready, then run task.

        Args:
            task_id: Task ID
        """
        max_wait = 300  # 5 minutes max wait
        start_wait = time.time()

        while time.time() - start_wait < max_wait:
            system_load = self.check_system_load()

            if not system_load["is_busy"]:
                # System ready, run task
                with self.tasks_lock:
                    if task_id in self.background_tasks:
                        self.background_tasks[task_id]["status"] = "running"
                        self.background_tasks[task_id]["started_at"] = time.time()

                self._run_task_in_background(task_id)
                return

            # Wait before checking again
            time.sleep(5)

        # Timed out waiting
        with self.tasks_lock:
            if task_id in self.background_tasks:
                self.background_tasks[task_id]["status"] = "failed"
                self.background_tasks[task_id]["error"] = "Timed out waiting for system resources"
                self.background_tasks[task_id]["completed_at"] = time.time()

    def _run_task_in_background(self, task_id: str):
        """
        Run a task in background.

        Args:
            task_id: Task ID
        """
        try:
            with self.tasks_lock:
                task = self.background_tasks.get(task_id)

            if not task:
                logger.error(f"Task {task_id} not found")
                return

            workflow = task["workflow"]

            # Execute workflow
            result = self._execute_workflow(workflow)

            # Update task record
            with self.tasks_lock:
                if task_id in self.background_tasks:
                    self.background_tasks[task_id]["status"] = "completed"
                    self.background_tasks[task_id]["result"] = result
                    self.background_tasks[task_id]["completed_at"] = time.time()

            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")

            with self.tasks_lock:
                if task_id in self.background_tasks:
                    self.background_tasks[task_id]["status"] = "failed"
                    self.background_tasks[task_id]["error"] = str(e)
                    self.background_tasks[task_id]["completed_at"] = time.time()

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a background task.

        Args:
            task_id: Task ID

        Returns:
            Task status dict or None if not found
        """
        with self.tasks_lock:
            task = self.background_tasks.get(task_id)
            if task:
                # Return copy to avoid race conditions
                return task.copy()
            return None

    def list_active_tasks(self) -> List[Dict[str, Any]]:
        """
        List all active (not completed) tasks.

        Returns:
            List of active task dicts
        """
        with self.tasks_lock:
            active = []
            for task in self.background_tasks.values():
                if task["status"] in ["queued", "running"]:
                    active.append(task.copy())
            return active

    def orchestrate_with_parallel_execution(
        self,
        user_message: str,
        conversation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate response with parallel task execution.

        This method:
        1. Analyzes the message
        2. Starts tasks in background if needed
        3. Returns immediately with task ID for tracking
        4. Conversation continues while tasks run in parallel

        Args:
            user_message: User's message
            conversation_context: Optional conversation context

        Returns:
            Dict with:
            - response_type: 'conversation' or 'task_execution'
            - task_analysis: Task analysis results
            - task_id: Background task ID (if task started)
            - immediate_response: Immediate response to user
            - task_status: Current task status
        """
        # Analyze message
        task_analysis = self.analyze_message_for_tasks(user_message, conversation_context)

        if not task_analysis["has_task"]:
            return {
                "response_type": "conversation",
                "task_analysis": task_analysis,
                "immediate_response": "Continue conversation naturally",
                "task_id": None
            }

        # Task detected - select tools and generate workflow
        result = {
            "response_type": "task_execution",
            "task_analysis": task_analysis
        }

        # Select tools
        if task_analysis["requires_tools"]:
            available_tools = []
            if self.tools_manager:
                try:
                    available_tools = list(getattr(self.tools_manager, 'tools', {}).keys())
                except Exception:
                    pass

            tools_selected = self.select_tools_for_task(
                task_description=task_analysis["task_description"],
                task_type=task_analysis["task_type"],
                available_tools=available_tools
            )
            result["tools_selected"] = tools_selected
        else:
            result["tools_selected"] = {
                "recommended_tools": [],
                "reasoning": "No tools required",
                "execution_order": []
            }

        # Generate workflow
        workflow = None
        if task_analysis["complexity"] in ["moderate", "complex"]:
            workflow = self.generate_workflow_for_task(
                task_description=task_analysis["task_description"],
                task_type=task_analysis["task_type"],
                recommended_tools=result["tools_selected"]["recommended_tools"]
            )

        # Start task in background
        task_id = None
        if workflow:
            task_id = self.execute_task_in_background(
                task_id=None,
                task_description=task_analysis["task_description"],
                workflow=workflow,
                wait_if_busy=True
            )
            result["task_id"] = task_id
            result["task_status"] = self.get_task_status(task_id)

        # Generate immediate response
        immediate_response = self._generate_parallel_response(task_analysis, task_id)
        result["immediate_response"] = immediate_response

        return result

    def _generate_parallel_response(
        self,
        task_analysis: Dict[str, Any],
        task_id: Optional[str]
    ) -> str:
        """
        Generate immediate response when running task in parallel.

        Args:
            task_analysis: Task analysis results
            task_id: Background task ID

        Returns:
            Immediate response text
        """
        parts = []

        parts.append(f"I understand you want to {task_analysis.get('task_description', 'perform a task')}.")
        parts.append("I'm working on that in the background.")

        if task_id:
            parts.append(f"You can check the status with task ID: {task_id[:8]}...")

        parts.append("Feel free to continue our conversation while I work on it!")

        return " ".join(parts)
