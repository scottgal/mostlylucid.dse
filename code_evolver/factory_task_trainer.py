#!/usr/bin/env python3
"""
Factory Task Trainer - Continuous training with random task variations.

Generates random variations of a base prompt and executes them through the
DSE system continuously until a key is pressed.
"""
import argparse
import json
import logging
import random
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Platform-specific keyboard input detection
try:
    import msvcrt
    PLATFORM = 'windows'
except ImportError:
    import select
    PLATFORM = 'unix'


class KeyboardMonitor:
    """Monitor keyboard input in a background thread."""

    def __init__(self):
        self.stop_requested = False
        self.thread = None

    def start(self):
        """Start monitoring for keyboard input."""
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()

    def _monitor(self):
        """Monitor keyboard input (platform-specific)."""
        logger.info("Press any key to stop training... (or Ctrl+C)")

        try:
            if PLATFORM == 'windows':
                while not self.stop_requested:
                    if msvcrt.kbhit():
                        msvcrt.getch()  # Consume the key
                        self.stop_requested = True
                        break
                    time.sleep(0.1)
            else:  # Unix/Linux
                import tty
                import termios

                # Check if stdin is a TTY (not when piped/redirected)
                if not sys.stdin.isatty():
                    logger.warning("Not running in interactive terminal - use Ctrl+C to stop")
                    return

                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setcbreak(sys.stdin.fileno())
                    while not self.stop_requested:
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            sys.stdin.read(1)  # Consume the key
                            self.stop_requested = True
                            break
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except Exception as e:
            logger.warning(f"Keyboard monitoring error: {e}. Use Ctrl+C to stop.")


class FactoryTaskGenerator:
    """Generate random factory task variations."""

    # Default factory task templates by category
    FACTORY_TASKS = {
        'arithmetic': [
            "Calculate total production for {quantity} units at {rate} units/hour over {hours} hours",
            "Compute inventory levels: starting {start} units, produced {produced}, shipped {shipped}",
            "Calculate efficiency: {output} units produced from {input} raw materials (percentage)",
            "Determine labor cost: {workers} workers × {hours} hours × ${wage}/hour",
            "Calculate machine utilization: {runtime} hours used / {available} hours available",
        ],
        'data_processing': [
            "Analyze quality control data: {measurements} and identify outliers beyond {threshold} sigma",
            "Process production metrics from shift report: {data} and generate summary statistics",
            "Filter defective items from batch: {items} where defect_rate > {threshold}%",
            "Aggregate daily production by line: {production_data} and rank by efficiency",
            "Transform sensor readings {readings} to normalized 0-100 scale",
        ],
        'code_generation': [
            "Write a PLC ladder logic function to control conveyor belt with {sensors} sensors",
            "Generate Python script to parse production log format: {format}",
            "Create automation script to monitor {metric} and alert if exceeds {threshold}",
            "Write function to calculate OEE (Overall Equipment Effectiveness) from availability, performance, quality metrics",
            "Generate state machine for assembly line with states: {states}",
        ],
        'translation': [
            "Translate safety warning '{text}' to {language}",
            "Convert product label from English to {languages}: '{label}'",
            "Translate assembly instructions '{instructions}' to Spanish and French",
            "Localize error message '{error}' for {market} market",
            "Translate machine manual section '{section}' to {language} maintaining technical accuracy",
        ],
        'question_answering': [
            "What is the proper lockout/tagout procedure for {equipment}?",
            "Explain the safety requirements for operating {machine}",
            "What are the OSHA regulations for {scenario}?",
            "How should operators respond to {alert_type} alarm?",
            "What is the correct procedure for {maintenance_task}?",
        ],
        'formatting': [
            "Format production report: Date: {date}, Line: {line}, Output: {output}, Efficiency: {efficiency}%",
            "Create shift log entry for {shift} shift on {date} with {events} events",
            "Format inventory table with columns: SKU, Description, Quantity, Location, Status",
            "Generate downtime report showing {equipment}, {duration}, {reason}, {cost}",
            "Create quality control report for batch {batch} with pass/fail counts",
        ],
        'conversion': [
            "Convert {temp}°F to Celsius for oven temperature specification",
            "Convert {pressure} PSI to Bar for hydraulic system",
            "Convert {length} feet to meters for international specifications",
            "Convert {weight} pounds to kilograms for shipping documentation",
            "Convert {speed} RPM to rad/s for motor control calculations",
        ],
        'creative_content': [
            "Write a safety notice about {hazard} for factory floor bulletin board",
            "Create training material introduction for new {equipment} operators",
            "Draft announcement for new {policy} policy implementation",
            "Write incident report summary for {incident_type}",
            "Create motivational message for {milestone} achievement",
        ],
    }

    def __init__(self, base_prompt: Optional[str] = None, multistage_probability: Optional[float] = None):
        """
        Initialize task generator.

        Args:
            base_prompt: Base prompt to generate variations from (None for factory tasks)
        """
        self.base_prompt = base_prompt
        self.variation_count = 0
        # Probability that a generated task will be expressed as a multi-stage workflow
        self.multistage_probability = 0.45 if multistage_probability is None else float(multistage_probability)
        # Clamp to [0.0, 1.0]
        if self.multistage_probability < 0.0:
            self.multistage_probability = 0.0
        if self.multistage_probability > 1.0:
            self.multistage_probability = 1.0

    def generate_variation(self) -> str:
        """Generate a random task variation."""
        self.variation_count += 1

        if self.base_prompt:
            # Generate variation of user's base prompt
            return self._generate_custom_variation()
        else:
            # Generate random factory task
            return self._generate_factory_task()

    def _generate_custom_variation(self) -> str:
        """Generate variation of user's base prompt."""
        variations = [
            self.base_prompt,  # Original
            f"{self.base_prompt} (variation {self.variation_count})",
            f"{self.base_prompt} with random parameters",
            f"Alternative approach: {self.base_prompt}",
            f"{self.base_prompt} using different method",
            f"Optimized version: {self.base_prompt}",
            f"{self.base_prompt} with edge cases",
            f"Enhanced {self.base_prompt}",
        ]

        # Add random parameters
        variation = random.choice(variations)

        # Inject random values
        random_params = {
            'quantity': random.randint(100, 10000),
            'rate': random.randint(10, 500),
            'hours': random.randint(1, 24),
            'threshold': random.randint(1, 10),
            'value': random.uniform(0.1, 100.0),
        }

        try:
            task = variation.format(**random_params)
        except (KeyError, ValueError):
            task = variation

        # Optionally wrap as a multi-stage workflow
        return self._maybe_wrap_with_stages(task, category_hint="custom")

    def _generate_factory_task(self) -> str:
        """Generate a random factory task."""
        # Pick random category
        category = random.choice(list(self.FACTORY_TASKS.keys()))
        template = random.choice(self.FACTORY_TASKS[category])

        # Generate random parameters
        params = self._generate_random_params(template)

        try:
            task = template.format(**params)
            logger.debug(f"Generated {category} task: {task}")
            # Optionally wrap as a multi-stage workflow
            return self._maybe_wrap_with_stages(task, category_hint=category)
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to format template: {e}")
            return template

    def _generate_random_params(self, template: str) -> Dict[str, Any]:
        """Generate random parameters for template."""
        params = {
            # Numeric parameters
            'quantity': random.randint(100, 10000),
            'rate': random.randint(10, 500),
            'hours': random.randint(1, 24),
            'start': random.randint(1000, 5000),
            'produced': random.randint(100, 1000),
            'shipped': random.randint(50, 500),
            'output': random.randint(800, 1200),
            'input': random.randint(1000, 1500),
            'workers': random.randint(5, 50),
            'wage': random.randint(15, 50),
            'runtime': random.randint(160, 720),
            'available': 720,
            'threshold': random.randint(2, 5),
            'temp': random.randint(200, 500),
            'pressure': random.randint(20, 150),
            'length': random.randint(10, 1000),
            'weight': random.randint(100, 5000),
            'speed': random.randint(100, 3000),

            # String parameters
            'sensors': ', '.join([f'sensor_{i}' for i in range(1, random.randint(3, 6))]),
            'measurements': str([round(random.gauss(100, 15), 2) for _ in range(10)]),
            'data': json.dumps({'line_1': random.randint(800, 1200), 'line_2': random.randint(700, 1100)}),
            'items': str([{'id': i, 'defect_rate': round(random.uniform(0, 10), 2)} for i in range(10)]),
            'production_data': json.dumps([{'line': i, 'output': random.randint(500, 1500)} for i in range(1, 5)]),
            'readings': str([random.randint(0, 1023) for _ in range(10)]),
            'format': 'timestamp|line_id|product_id|quantity|status',
            'metric': random.choice(['temperature', 'pressure', 'vibration', 'speed']),
            'states': ', '.join(['idle', 'loading', 'processing', 'unloading', 'error']),
            'text': random.choice(['Danger: High Voltage', 'Caution: Wet Floor', 'Warning: Moving Parts']),
            'language': random.choice(['Spanish', 'French', 'German', 'Chinese', 'Japanese']),
            'languages': 'Spanish and French',
            'label': 'Fragile - Handle with Care',
            'instructions': 'Connect cable A to port B',
            'error': 'System overload detected',
            'market': random.choice(['European', 'Asian', 'Latin American']),
            'section': 'Emergency shutdown procedure',
            'equipment': random.choice(['forklift', 'press machine', 'conveyor system', 'robotic arm']),
            'machine': random.choice(['CNC mill', 'injection molder', 'welding station', 'packaging line']),
            'scenario': random.choice(['confined space entry', 'hot work', 'elevated work', 'chemical handling']),
            'alert_type': random.choice(['temperature', 'pressure', 'emergency stop', 'quality']),
            'maintenance_task': random.choice(['bearing replacement', 'filter change', 'calibration', 'lubrication']),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'line': f'Line {random.randint(1, 5)}',
            'efficiency': random.randint(75, 98),
            'shift': random.choice(['Day', 'Night', 'Swing']),
            'events': random.randint(3, 10),
            'batch': f'BATCH-{random.randint(1000, 9999)}',
            'duration': f'{random.randint(1, 8)} hours',
            'reason': random.choice(['mechanical failure', 'scheduled maintenance', 'material shortage', 'changeover']),
            'cost': f'${random.randint(500, 5000)}',
            'hazard': random.choice(['pinch points', 'chemical spills', 'electrical hazards', 'falling objects']),
            'policy': random.choice(['safety', 'quality', 'environmental', 'attendance']),
            'incident_type': random.choice(['near miss', 'minor injury', 'equipment damage', 'quality issue']),
            'milestone': random.choice(['1 million units', 'zero accidents', 'efficiency target', 'certification']),
        }

        return params

    def _maybe_wrap_with_stages(self, task: str, category_hint: Optional[str] = None) -> str:
        """With some probability, wrap the task as a multi-stage workflow.

        The wrapped format explicitly includes a top note and a 'Stages:' section
        with 2–4 steps, so downstream handlers can execute them sequentially.
        """
        try:
            if random.random() > self.multistage_probability:
                return task

            # Stage templates pool (generic + light category bias)
            generic_stages = [
                "Analyze requirements and clarify constraints",
                "Plan the approach and outline solution",
                "Implement the solution step-by-step",
                "Run quick validation/tests and fix issues",
                "Document results and assumptions",
                "Reflect and propose improvements",
            ]

            category_bias = {
                'arithmetic': ["Set up calculations", "Compute results", "Verify computations"],
                'data_processing': ["Load/parse data", "Transform/clean", "Summarize and report"],
                'code_generation': ["Design API/logic", "Write code", "Run example and test"],
                'translation': ["Assess terminology", "Translate content", "Review accuracy"],
                'question_answering': ["Recall policies", "Draft answer", "Cite sources"],
                'formatting': ["Parse inputs", "Format output", "Validate formatting"],
                'conversion': ["Identify units", "Convert values", "Double-check results"],
                'creative_content': ["Brainstorm ideas", "Draft content", "Polish tone/style"],
                'custom': ["Understand prompt", "Propose approach", "Execute and verify"],
            }

            stages_source = generic_stages + category_bias.get(category_hint or '', [])
            # Ensure uniqueness and random order
            unique = list(dict.fromkeys(stages_source))
            random.shuffle(unique)
            stage_count = random.randint(2, 4)
            chosen = unique[:stage_count]

            # Quality guardrails: ensure a planning-style first step and a verification/documentation last step when possible
            planning_candidates = [s for s in unique if any(k in s.lower() for k in ["analyze", "plan", "design", "assess", "understand", "identify"])]
            ending_candidates = [s for s in unique if any(k in s.lower() for k in ["test", "validate", "verify", "document", "review", "reflect"])]

            if chosen:
                if planning_candidates and not any(chosen[0] is pc for pc in planning_candidates):
                    chosen[0] = planning_candidates[0]
                if ending_candidates:
                    chosen[-1] = ending_candidates[0]

            # Build wrapped prompt
            header = (
                "Note: This workflow may be multi-stage. If a 'Stages:' section is present, "
                "execute the stages sequentially, keeping responses concise per stage and a short final summary."
            )
            wrapped = (
                f"{header}\n\n"
                f"Task: {task}\n\n"
                f"Stages:\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(chosen)])
            )
            return wrapped
        except Exception:
            # On any unforeseen error, return the original task
            return task


class TrainingStatistics:
    """Track training session statistics."""

    def __init__(self):
        self.tasks_attempted = 0
        self.tasks_successful = 0
        self.tasks_failed = 0
        self.total_duration = 0.0
        self.start_time = time.time()
        self.task_times = []
        # Multi-stage accounting
        self.multistage_tasks = 0
        self.single_tasks = 0

    def record_success(self, duration: float, is_multistage: bool = False):
        """Record successful task."""
        self.tasks_attempted += 1
        self.tasks_successful += 1
        self.total_duration += duration
        self.task_times.append(duration)
        if is_multistage:
            self.multistage_tasks += 1
        else:
            self.single_tasks += 1

    def record_failure(self, duration: float, is_multistage: bool = False):
        """Record failed task."""
        self.tasks_attempted += 1
        self.tasks_failed += 1
        self.total_duration += duration
        self.task_times.append(duration)
        if is_multistage:
            self.multistage_tasks += 1
        else:
            self.single_tasks += 1

    def get_summary(self) -> str:
        """Get statistics summary."""
        elapsed = time.time() - self.start_time
        avg_time = sum(self.task_times) / len(self.task_times) if self.task_times else 0
        success_rate = (self.tasks_successful / self.tasks_attempted * 100) if self.tasks_attempted > 0 else 0

        multistage_rate = (self.multistage_tasks / self.tasks_attempted * 100) if self.tasks_attempted > 0 else 0
        return f"""
╔══════════════════════════════════════════════════════════════╗
║                   TRAINING SESSION SUMMARY                   ║
╠══════════════════════════════════════════════════════════════╣
║  Total Tasks:      {self.tasks_attempted:6d}                                ║
║  Successful:       {self.tasks_successful:6d} ({success_rate:5.1f}%)                      ║
║  Failed:           {self.tasks_failed:6d}                                ║
║  Multi-stage:      {self.multistage_tasks:6d} ({multistage_rate:5.1f}%)                      ║
║  Single-stage:     {self.single_tasks:6d}                                ║
║  Session Duration: {elapsed:6.1f}s                              ║
║  Total Exec Time:  {self.total_duration:6.1f}s                              ║
║  Avg Task Time:    {avg_time:6.2f}s                              ║
║  Tasks/Minute:     {self.tasks_attempted / (elapsed / 60):6.1f}                              ║
╚══════════════════════════════════════════════════════════════╝
"""


class FactoryTaskTrainer:
    """Main trainer that executes random task variations."""

    def __init__(self, base_prompt: Optional[str] = None, max_tasks: Optional[int] = None,
                 multistage_probability: Optional[float] = None, seed: Optional[int] = None):
        """
        Initialize trainer.

        Args:
            base_prompt: Base prompt for variations (None for factory tasks)
            max_tasks: Maximum number of tasks to run (None for unlimited)
        """
        # If a seed is provided, set deterministic randomness
        self.seed = seed
        if self.seed is not None:
            try:
                random.seed(self.seed)
                logger.info(f"RNG seed set to {self.seed}")
            except Exception as _:
                logger.warning("Failed to set RNG seed")

        self.generator = FactoryTaskGenerator(base_prompt, multistage_probability=multistage_probability)
        self.statistics = TrainingStatistics()
        self.keyboard = KeyboardMonitor()
        self.max_tasks = max_tasks

    def run_training_loop(self):
        """Run continuous training loop until key pressed."""
        logger.info("="*60)
        logger.info("FACTORY TASK TRAINER")
        logger.info("="*60)

        if self.generator.base_prompt:
            logger.info(f"Base prompt: {self.generator.base_prompt}")
        else:
            logger.info("Mode: Random factory tasks")

        # Inform that some tasks will be multi-stage and use a 'Stages:' section
        logger.info(
            "Note: Some tasks will be multi-stage. When a 'Stages:' section is present, "
            "follow the stages sequentially and provide concise per-stage outputs."
        )

        # Log effective multi-stage probability
        try:
            logger.info(f"Effective multi-stage probability: {self.generator.multistage_probability:.2f}")
        except Exception:
            pass

        logger.info("="*60)

        # Start keyboard monitor
        self.keyboard.start()

        try:
            while not self.keyboard.stop_requested:
                # Check if max tasks reached
                if self.max_tasks and self.statistics.tasks_attempted >= self.max_tasks:
                    logger.info(f"\nReached max tasks limit: {self.max_tasks}")
                    break

                # Generate task variation
                task = self.generator.generate_variation()

                # Execute task
                logger.info(f"\n[Task #{self.statistics.tasks_attempted + 1}] {task}")

                start_time = time.time()
                success = self._execute_task(task)
                duration = time.time() - start_time
                is_multistage = self._is_multistage_task(task)

                # Record statistics
                if success:
                    self.statistics.record_success(duration, is_multistage=is_multistage)
                    logger.info(f"✓ Success ({duration:.2f}s)")
                else:
                    self.statistics.record_failure(duration, is_multistage=is_multistage)
                    logger.info(f"✗ Failed ({duration:.2f}s)")

                # Small delay between tasks
                time.sleep(0.5)

        except KeyboardInterrupt:
            logger.info("\n\nTraining interrupted by Ctrl+C")
        finally:
            # Print summary
            print("\n" + self.statistics.get_summary())

    def _execute_task(self, task: str) -> bool:
        """
        Execute a task through the DSE system with full RAG and tool registration.

        Args:
            task: Task prompt to execute

        Returns:
            True if successful, False otherwise
        """
        try:
            # Execute via chat_cli integration
            import sys
            sys.path.insert(0, str(Path(__file__).parent / 'code_evolver'))

            from chat_cli import ChatCLI

            # Create CLI instance (will initialize all components including RAG)
            cli = ChatCLI()

            # Generate node_id from task
            import hashlib
            task_hash = hashlib.sha256(task.encode()).hexdigest()[:8]
            node_id = f"train_{int(time.time() * 1000)}_{task_hash}"

            # Execute the task using handle_generate (which handles RAG, tests, and tool registration)
            success = cli.handle_generate(task)

            if success:
                logger.debug(f"Task completed successfully, node registered as tool")
            else:
                logger.debug(f"Task failed to complete")

            return success

        except Exception as e:
            logger.error(f"Task execution error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    @staticmethod
    def _is_multistage_task(task: str) -> bool:
        """Heuristic to detect multi-stage wrapped tasks."""
        try:
            return "\nStages:\n" in task or task.strip().startswith("Note: This workflow may be multi-stage.")
        except Exception:
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Factory Task Trainer - Continuous training with random task variations'
    )
    parser.add_argument(
        '--prompt',
        type=str,
        default=None,
        help='Base prompt to generate variations from (default: use factory tasks)'
    )
    parser.add_argument(
        '--max-tasks',
        type=int,
        default=None,
        help='Maximum number of tasks to run (default: unlimited)'
    )
    parser.add_argument(
        '--multistage-prob',
        type=float,
        default=None,
        help='Probability [0.0-1.0] that a task is wrapped as a multi-stage workflow'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Set RNG seed for deterministic task generation'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Determine multistage probability from CLI or environment
    multistage_prob = args.multistage_prob
    if multistage_prob is None:
        import os
        env_val = os.environ.get('FACTORY_MULTISTAGE_PROB')
        if env_val is not None:
            try:
                multistage_prob = float(env_val)
            except ValueError:
                logger.warning(f"Invalid FACTORY_MULTISTAGE_PROB '{env_val}', falling back to default")
                multistage_prob = None

    # Create and run trainer
    trainer = FactoryTaskTrainer(
        base_prompt=args.prompt,
        max_tasks=args.max_tasks,
        multistage_probability=multistage_prob,
        seed=args.seed,
    )
    trainer.run_training_loop()


if __name__ == "__main__":
    main()
