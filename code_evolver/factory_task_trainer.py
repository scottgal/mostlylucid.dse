#!/usr/bin/env python3
"""
Factory Task Trainer - Sector-based realistic workflow task generation.

Generates realistic workflow tasks for different industry sectors using LLM.
Supports continuous training with random variations across multiple sectors.
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


class SectorTaskGenerator:
    """Generate realistic sector-based workflow tasks using LLM."""

    # Industry sectors with descriptions and typical workflows
    SECTORS = {
        'manufacturing': {
            'description': 'Manufacturing and production facilities',
            'examples': 'quality control workflows, production scheduling, inventory management, equipment monitoring'
        },
        'healthcare': {
            'description': 'Healthcare and medical facilities',
            'examples': 'patient data processing, appointment scheduling, compliance reporting, medical billing'
        },
        'finance': {
            'description': 'Financial services and banking',
            'examples': 'transaction processing, fraud detection, regulatory compliance, risk assessment'
        },
        'retail': {
            'description': 'Retail and e-commerce',
            'examples': 'order processing, inventory tracking, customer service automation, price optimization'
        },
        'logistics': {
            'description': 'Logistics and supply chain',
            'examples': 'shipment tracking, route optimization, warehouse management, delivery scheduling'
        },
        'education': {
            'description': 'Educational institutions',
            'examples': 'student enrollment, grade processing, attendance tracking, course scheduling'
        },
        'energy': {
            'description': 'Energy and utilities',
            'examples': 'meter reading automation, outage detection, billing cycles, resource allocation'
        },
        'telecom': {
            'description': 'Telecommunications',
            'examples': 'network monitoring, customer provisioning, billing integration, incident management'
        },
        'government': {
            'description': 'Government and public sector',
            'examples': 'permit processing, compliance checking, citizen services automation, data reporting'
        },
        'general': {
            'description': 'General business operations',
            'examples': 'document processing, email automation, data entry, report generation, task scheduling'
        }
    }

    def __init__(self, sector: Optional[str] = None):
        """
        Initialize sector task generator.

        Args:
            sector: Industry sector (None for random selection across all sectors)
        """
        self.sector = sector
        self.variation_count = 0

        # Initialize Ollama client
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from src.ollama_client import OllamaClient
            from src.config_manager import ConfigManager

            config = ConfigManager()
            self.client = OllamaClient(config_manager=config)
            logger.info("Initialized Ollama client for task generation")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            self.client = None

    def generate_realistic_task(self) -> str:
        """Generate a realistic workflow task using LLM."""
        self.variation_count += 1

        # If no LLM available, use fallback templates
        if not self.client:
            return self._generate_fallback_task()

        # Select sector (random if not specified)
        sector = self.sector if self.sector else random.choice(list(self.SECTORS.keys()))
        sector_info = self.SECTORS[sector]

        # Generate task using LLM
        prompt = f"""Generate ONE realistic workflow automation task for the {sector} sector.

Sector: {sector_info['description']}
Typical workflows: {sector_info['examples']}

Requirements:
- Task should be something that workflow automation tools commonly handle
- Be specific and practical (include realistic data/parameters)
- Keep it to 1-2 sentences maximum
- Use real-world terminology from the sector
- Make it actionable and concrete

Generate ONE task now (just the task description, no explanation):"""

        try:
            response = self.client.generate(
                model="gemma3:1b",  # Fast 1B class model
                prompt=prompt,
                max_tokens=150,
                temperature=0.9  # High creativity for variety
            )

            # Clean up response
            task = response.strip()

            # Remove any preamble/explanation
            if '\n' in task:
                lines = [line.strip() for line in task.split('\n') if line.strip()]
                # Take first substantial line
                task = lines[0] if lines else task

            logger.debug(f"Generated {sector} task: {task}")
            return task

        except Exception as e:
            logger.warning(f"LLM generation failed: {e}, using fallback")
            return self._generate_fallback_task()

    def _generate_fallback_task(self) -> str:
        """Generate fallback task using templates when LLM unavailable."""
        sector = self.sector if self.sector else random.choice(list(self.SECTORS.keys()))

        # Fallback templates per sector
        templates = {
            'manufacturing': [
                "Process quality control data and flag items with defect rate above {threshold}%",
                "Schedule production runs for {quantity} units across {lines} production lines",
                "Monitor equipment utilization and alert when downtime exceeds {minutes} minutes",
            ],
            'healthcare': [
                "Process patient admission forms and update electronic health records",
                "Schedule follow-up appointments for patients discharged in last {days} days",
                "Generate compliance reports for {department} department monthly metrics",
            ],
            'finance': [
                "Review transactions over ${amount} for potential fraud indicators",
                "Generate quarterly risk assessment report for portfolio {portfolio_id}",
                "Process loan applications and calculate approval recommendations",
            ],
            'retail': [
                "Process online orders and generate picking lists for warehouse",
                "Update inventory levels when stock falls below {threshold} units",
                "Generate daily sales reports by product category and region",
            ],
            'logistics': [
                "Optimize delivery routes for {vehicles} vehicles covering {zones} zones",
                "Track shipment status and notify customers of delays over {hours} hours",
                "Process warehouse receiving documents and update inventory system",
            ],
            'education': [
                "Process student grade submissions and calculate GPA updates",
                "Generate attendance reports for courses with absences over {threshold}%",
                "Schedule exam rooms based on enrollment and capacity constraints",
            ],
            'energy': [
                "Process meter readings and flag consumption spikes over {threshold}%",
                "Generate outage reports by region and duration for the last {days} days",
                "Schedule maintenance visits for meters due for inspection",
            ],
            'telecom': [
                "Monitor network nodes and alert on packet loss exceeding {threshold}%",
                "Process service activation requests and provision customer accounts",
                "Generate billing reconciliation reports for the last billing cycle",
            ],
            'government': [
                "Process permit applications and route to appropriate departments",
                "Generate compliance reports for regulatory submissions due this quarter",
                "Schedule inspections for facilities requiring annual review",
            ],
            'general': [
                "Process incoming emails and categorize by priority and department",
                "Generate weekly status reports from project tracking data",
                "Schedule recurring tasks for the next {weeks} weeks",
            ]
        }

        template = random.choice(templates.get(sector, templates['general']))

        # Fill in random parameters
        params = {
            'threshold': random.randint(5, 20),
            'quantity': random.randint(100, 10000),
            'lines': random.randint(2, 8),
            'minutes': random.randint(15, 120),
            'days': random.randint(7, 30),
            'department': random.choice(['Surgery', 'Emergency', 'Pediatrics', 'Radiology']),
            'amount': random.randint(1000, 100000),
            'portfolio_id': f"P{random.randint(1000, 9999)}",
            'vehicles': random.randint(5, 50),
            'zones': random.randint(3, 15),
            'hours': random.randint(2, 48),
            'weeks': random.randint(1, 12),
        }

        try:
            return template.format(**params)
        except (KeyError, ValueError):
            return template


class TrainingStatistics:
    """Track training session statistics."""

    def __init__(self):
        self.tasks_attempted = 0
        self.tasks_successful = 0
        self.tasks_failed = 0
        self.total_duration = 0.0
        self.start_time = time.time()
        self.task_times = []
        self.sectors_used = {}  # Track sector distribution

    def record_success(self, duration: float, sector: Optional[str] = None):
        """Record successful task."""
        self.tasks_attempted += 1
        self.tasks_successful += 1
        self.total_duration += duration
        self.task_times.append(duration)
        if sector:
            self.sectors_used[sector] = self.sectors_used.get(sector, 0) + 1

    def record_failure(self, duration: float, sector: Optional[str] = None):
        """Record failed task."""
        self.tasks_attempted += 1
        self.tasks_failed += 1
        self.total_duration += duration
        self.task_times.append(duration)
        if sector:
            self.sectors_used[sector] = self.sectors_used.get(sector, 0) + 1

    def get_summary(self) -> str:
        """Get statistics summary."""
        elapsed = time.time() - self.start_time
        avg_time = sum(self.task_times) / len(self.task_times) if self.task_times else 0
        success_rate = (self.tasks_successful / self.tasks_attempted * 100) if self.tasks_attempted > 0 else 0

        # Sector distribution
        sector_summary = "\n".join([
            f"║  {sector:15s}: {count:4d} tasks"
            for sector, count in sorted(self.sectors_used.items(), key=lambda x: -x[1])
        ])

        return f"""
╔══════════════════════════════════════════════════════════════╗
║                   TRAINING SESSION SUMMARY                   ║
╠══════════════════════════════════════════════════════════════╣
║  Total Tasks:      {self.tasks_attempted:6d}                                ║
║  Successful:       {self.tasks_successful:6d} ({success_rate:5.1f}%)                      ║
║  Failed:           {self.tasks_failed:6d}                                ║
║  Session Duration: {elapsed:6.1f}s                              ║
║  Total Exec Time:  {self.total_duration:6.1f}s                              ║
║  Avg Task Time:    {avg_time:6.2f}s                              ║
║  Tasks/Minute:     {self.tasks_attempted / (elapsed / 60) if elapsed > 0 else 0:6.1f}                              ║
╠══════════════════════════════════════════════════════════════╣
║  Sector Distribution:                                        ║
{sector_summary if sector_summary else "║  (no sector data)"}
╚══════════════════════════════════════════════════════════════╝
"""


class FactoryTaskTrainer:
    """Main trainer that executes random sector-based task variations."""

    def __init__(self, sector: Optional[str] = None, max_tasks: Optional[int] = None,
                 continuous: bool = True):
        """
        Initialize trainer.

        Args:
            sector: Industry sector for tasks (None for random across all sectors)
            max_tasks: Maximum number of tasks to run (None for unlimited)
            continuous: If True, run indefinitely (only Ctrl+C stops)
        """
        self.generator = SectorTaskGenerator(sector)
        self.statistics = TrainingStatistics()
        self.keyboard = KeyboardMonitor()
        self.max_tasks = max_tasks
        self.continuous = continuous
        self.sector = sector

    def run_training_loop(self):
        """Run continuous training loop until key pressed or Ctrl+C."""
        logger.info("="*60)
        logger.info("SECTOR-BASED TASK TRAINER")
        logger.info("="*60)

        if self.sector:
            sector_info = SectorTaskGenerator.SECTORS.get(self.sector, {})
            logger.info(f"Sector: {self.sector}")
            logger.info(f"Description: {sector_info.get('description', 'N/A')}")
        else:
            logger.info("Mode: Random tasks across all sectors")
            logger.info(f"Available sectors: {', '.join(SectorTaskGenerator.SECTORS.keys())}")

        # Log mode
        if self.continuous:
            logger.info("Mode: CONTINUOUS (only Ctrl+C will stop)")
        else:
            logger.info("Mode: Interactive (press any key or Ctrl+C to stop)")

        logger.info("="*60)

        # Start keyboard monitor only if not in continuous mode
        if not self.continuous:
            self.keyboard.start()

        try:
            while True:
                # In non-continuous mode, check if keyboard stop was requested
                if not self.continuous and self.keyboard.stop_requested:
                    logger.info("\nStopping due to keyboard interrupt...")
                    break

                # Check if max tasks reached
                if self.max_tasks and self.statistics.tasks_attempted >= self.max_tasks:
                    logger.info(f"\nReached max tasks limit: {self.max_tasks}")
                    break

                # Generate task
                task = self.generator.generate_realistic_task()
                current_sector = self.sector if self.sector else "random"

                # Execute task
                logger.info(f"\n[Task #{self.statistics.tasks_attempted + 1}] [{current_sector}] {task}")

                start_time = time.time()
                success = self._execute_task(task)
                duration = time.time() - start_time

                # Record statistics
                if success:
                    self.statistics.record_success(duration, current_sector)
                    logger.info(f"✓ Success ({duration:.2f}s)")
                else:
                    self.statistics.record_failure(duration, current_sector)
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
        Execute a task through the DSE system.

        Args:
            task: Task prompt to execute

        Returns:
            True if successful, False otherwise
        """
        try:
            # Execute via chat_cli integration
            sys.path.insert(0, str(Path(__file__).parent))

            from chat_cli import ChatCLI

            # Create CLI instance
            cli = ChatCLI()

            # Execute the task
            success = cli.handle_generate(task)

            if success:
                logger.debug(f"Task completed successfully")
            else:
                logger.debug(f"Task failed to complete")

            return success

        except Exception as e:
            logger.error(f"Task execution error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Sector-Based Task Trainer - Generate realistic workflow tasks for different industries. '
                    'By default, runs indefinitely until Ctrl+C is pressed.'
    )
    parser.add_argument(
        '--sector',
        type=str,
        default=None,
        choices=list(SectorTaskGenerator.SECTORS.keys()),
        help='Industry sector for task generation (default: random across all sectors)'
    )
    parser.add_argument(
        '--max-tasks',
        type=int,
        default=None,
        help='Maximum number of tasks to run (default: unlimited)'
    )
    parser.add_argument(
        '--list-sectors',
        action='store_true',
        help='List available sectors and exit'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        default=True,
        help='Run in continuous mode - only Ctrl+C stops (default: True)'
    )
    parser.add_argument(
        '--interactive',
        dest='continuous',
        action='store_false',
        help='Run in interactive mode - any key press or Ctrl+C stops'
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

    # List sectors and exit
    if args.list_sectors:
        print("\nAvailable Sectors:")
        print("=" * 70)
        for sector, info in sorted(SectorTaskGenerator.SECTORS.items()):
            print(f"\n{sector.upper()}")
            print(f"  Description: {info['description']}")
            print(f"  Typical workflows: {info['examples']}")
        print("\n" + "=" * 70)
        return

    # Create and run trainer
    trainer = FactoryTaskTrainer(
        sector=args.sector,
        max_tasks=args.max_tasks,
        continuous=args.continuous,
    )
    trainer.run_training_loop()


if __name__ == "__main__":
    main()
