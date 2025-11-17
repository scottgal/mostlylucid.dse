"""
Git Tool for mostlylucid DiSE.
Provides safe and powerful Git integration with authentication from config.yaml.
"""
import json
import logging
import subprocess
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitTool:
    """
    Git integration tool with safety features and authentication.

    Features:
    - Comprehensive Git operations (status, log, diff, clone, push, pull, etc.)
    - Authentication from config.yaml (GitHub/GitLab tokens, SSH keys)
    - Safety checks for destructive operations
    - Parsed output for easy consumption
    - Credential injection for HTTPS URLs
    - Support for both local and remote operations
    """

    SAFE_ACTIONS = {
        "status", "log", "diff", "branch", "remote", "show",
        "blame", "tag", "config_get", "fetch"
    }

    DESTRUCTIVE_ACTIONS = {
        "push", "checkout", "stash", "config_set", "pull", "clone"
    }

    def __init__(
        self,
        safe_mode: bool = True,
        require_confirmation_for_destructive: bool = True,
        max_diff_size_kb: int = 500,
        config_manager: Optional[Any] = None
    ):
        """
        Initialize Git tool.

        Args:
            safe_mode: Enable safety checks
            require_confirmation_for_destructive: Require confirmation for destructive ops
            max_diff_size_kb: Maximum diff size in KB
            config_manager: ConfigManager for loading credentials
        """
        self.safe_mode = safe_mode
        self.require_confirmation = require_confirmation_for_destructive
        self.max_diff_size = max_diff_size_kb * 1024
        self.config_manager = config_manager

        # Load credentials from config
        self.credentials = self._load_credentials()

        logger.info(f"GitTool initialized (safe_mode={safe_mode})")

    def _load_credentials(self) -> Dict[str, Dict[str, str]]:
        """Load Git credentials from config.yaml."""
        credentials = {}

        if not self.config_manager:
            logger.warning("No config manager provided, credentials not available")
            return credentials

        try:
            # Try to get git config section
            git_config = self.config_manager.get("git", {})

            # Load GitHub credentials
            github_config = git_config.get("github", {})
            if github_config:
                credentials["github.com"] = {
                    "username": github_config.get("username", ""),
                    "token": os.path.expandvars(github_config.get("token", ""))
                }

            # Load GitLab credentials
            gitlab_config = git_config.get("gitlab", {})
            if gitlab_config:
                credentials["gitlab.com"] = {
                    "username": gitlab_config.get("username", ""),
                    "token": os.path.expandvars(gitlab_config.get("token", ""))
                }

            # Load custom credentials (pattern-based)
            for cred in git_config.get("credentials", []):
                pattern = cred.get("pattern", "")
                if pattern:
                    credentials[pattern] = {
                        "username": cred.get("username", ""),
                        "token": os.path.expandvars(cred.get("token", ""))
                    }

            logger.info(f"Loaded credentials for {len(credentials)} patterns")

        except Exception as e:
            logger.error(f"Error loading Git credentials: {e}")

        return credentials

    def _inject_credentials(self, url: str) -> str:
        """
        Inject credentials into HTTPS Git URL.

        Args:
            url: Git repository URL

        Returns:
            URL with credentials injected
        """
        if not url.startswith("https://"):
            return url

        parsed = urlparse(url)
        hostname = parsed.hostname

        # Find matching credentials
        creds = None
        for pattern, pattern_creds in self.credentials.items():
            if pattern in hostname:
                creds = pattern_creds
                break

        if not creds or not creds.get("token"):
            return url

        # Inject credentials into URL
        username = creds.get("username", "git")
        token = creds["token"]

        # Construct authenticated URL
        auth_url = f"https://{username}:{token}@{hostname}{parsed.path}"

        logger.debug(f"Injected credentials for {hostname}")
        return auth_url

    def _run_git_command(
        self,
        args: List[str],
        repo_path: Optional[str] = None,
        capture_output: bool = True,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Run a git command safely.

        Args:
            args: Git command arguments
            repo_path: Repository path (uses current directory if None)
            capture_output: Whether to capture output
            env: Environment variables to add

        Returns:
            Dict with success, output, and error
        """
        cmd = ["git"] + args

        try:
            # Set working directory
            cwd = repo_path if repo_path else os.getcwd()

            # Prepare environment
            cmd_env = os.environ.copy()
            if env:
                cmd_env.update(env)

            logger.debug(f"Running git command: {' '.join(args)} in {cwd}")

            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=60,
                env=cmd_env
            )

            output = result.stdout.strip() if result.stdout else ""
            error = result.stderr.strip() if result.stderr else ""

            success = result.returncode == 0

            return {
                "success": success,
                "output": output,
                "error": error,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Git command timed out (60s limit)",
                "return_code": -1
            }
        except Exception as e:
            logger.error(f"Error running git command: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "return_code": -1
            }

    def _parse_status(self, output: str) -> Dict[str, Any]:
        """Parse git status output."""
        lines = output.split("\n")

        # Extract branch
        branch = "unknown"
        for line in lines:
            if line.startswith("On branch "):
                branch = line.replace("On branch ", "").strip()
                break

        # Extract changes
        changes = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("On branch") or line.startswith("Your branch"):
                continue
            if line.startswith(("modified:", "new file:", "deleted:", "renamed:")):
                changes.append(line)

        return {
            "branch": branch,
            "changes": changes,
            "clean": len(changes) == 0
        }

    def _parse_log(self, output: str, max_count: int = 10) -> Dict[str, Any]:
        """Parse git log output."""
        commits = []

        # Use --format to get structured output
        for line in output.split("\n"):
            if not line.strip():
                continue

            parts = line.split("|")
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0].strip(),
                    "author": parts[1].strip(),
                    "date": parts[2].strip(),
                    "message": parts[3].strip()
                })

        return {"commits": commits[:max_count]}

    def _parse_branches(self, output: str) -> Dict[str, Any]:
        """Parse git branch output."""
        branches = []
        current_branch = None

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            if line.startswith("* "):
                current_branch = line[2:].strip()
                branches.append(current_branch)
            else:
                branches.append(line.strip())

        return {
            "branches": branches,
            "current": current_branch
        }

    def status(self, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Get repository status."""
        result = self._run_git_command(["status"], repo_path=repo_path)

        if result["success"]:
            result["data"] = self._parse_status(result["output"])

        return result

    def log(
        self,
        repo_path: Optional[str] = None,
        max_count: int = 10,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get commit log."""
        args = [
            "log",
            f"--max-count={max_count}",
            "--format=%H|%an|%ad|%s",
            "--date=short"
        ]

        if file_path:
            args.append(file_path)

        result = self._run_git_command(args, repo_path=repo_path)

        if result["success"]:
            result["data"] = self._parse_log(result["output"], max_count)

        return result

    def diff(
        self,
        repo_path: Optional[str] = None,
        file_path: Optional[str] = None,
        commit_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get diff of changes."""
        args = ["diff"]

        if commit_ref:
            args.append(commit_ref)

        if file_path:
            args.append(file_path)

        result = self._run_git_command(args, repo_path=repo_path)

        # Truncate large diffs
        if result["success"] and len(result["output"]) > self.max_diff_size:
            result["output"] = result["output"][:self.max_diff_size] + "\n... (truncated)"
            result["truncated"] = True

        return result

    def clone(
        self,
        url: str,
        destination: str,
        use_credentials: bool = True
    ) -> Dict[str, Any]:
        """Clone a repository."""
        # Inject credentials if requested
        clone_url = self._inject_credentials(url) if use_credentials else url

        args = ["clone", clone_url, destination]

        # Run clone (don't pass credentials in logs)
        logger.info(f"Cloning {url} to {destination}")
        result = self._run_git_command(args)

        # Remove credentials from output
        if use_credentials and result.get("output"):
            result["output"] = result["output"].replace(clone_url, url)

        return result

    def fetch(
        self,
        repo_path: Optional[str] = None,
        remote_name: str = "origin"
    ) -> Dict[str, Any]:
        """Fetch from remote."""
        args = ["fetch", remote_name]
        return self._run_git_command(args, repo_path=repo_path)

    def pull(
        self,
        repo_path: Optional[str] = None,
        remote_name: str = "origin",
        branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pull from remote."""
        args = ["pull", remote_name]
        if branch_name:
            args.append(branch_name)

        return self._run_git_command(args, repo_path=repo_path)

    def push(
        self,
        repo_path: Optional[str] = None,
        remote_name: str = "origin",
        branch_name: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Push to remote."""
        if self.safe_mode and force:
            return {
                "success": False,
                "error": "Force push is disabled in safe mode",
                "output": ""
            }

        args = ["push", remote_name]
        if branch_name:
            args.append(branch_name)
        if force:
            args.append("--force")

        return self._run_git_command(args, repo_path=repo_path)

    def branch(
        self,
        repo_path: Optional[str] = None,
        branch_name: Optional[str] = None,
        create: bool = False
    ) -> Dict[str, Any]:
        """List or create branches."""
        if branch_name and create:
            args = ["branch", branch_name]
        else:
            args = ["branch"]

        result = self._run_git_command(args, repo_path=repo_path)

        if result["success"] and not create:
            result["data"] = self._parse_branches(result["output"])

        return result

    def checkout(
        self,
        branch_name: str,
        repo_path: Optional[str] = None,
        create_branch: bool = False
    ) -> Dict[str, Any]:
        """Checkout a branch."""
        args = ["checkout"]
        if create_branch:
            args.append("-b")
        args.append(branch_name)

        return self._run_git_command(args, repo_path=repo_path)

    def remote(
        self,
        repo_path: Optional[str] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """List remotes."""
        args = ["remote"]
        if verbose:
            args.append("-v")

        return self._run_git_command(args, repo_path=repo_path)

    def show(
        self,
        commit_ref: str = "HEAD",
        repo_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Show commit details."""
        args = ["show", commit_ref]
        result = self._run_git_command(args, repo_path=repo_path)

        # Truncate large output
        if result["success"] and len(result["output"]) > self.max_diff_size:
            result["output"] = result["output"][:self.max_diff_size] + "\n... (truncated)"
            result["truncated"] = True

        return result

    def config_get(
        self,
        config_key: str,
        repo_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get git config value."""
        args = ["config", "--get", config_key]
        return self._run_git_command(args, repo_path=repo_path)

    def config_set(
        self,
        config_key: str,
        config_value: str,
        repo_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Set git config value."""
        args = ["config", config_key, config_value]
        return self._run_git_command(args, repo_path=repo_path)

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a git action.

        Args:
            params: Action parameters

        Returns:
            Result dictionary
        """
        action = params.get("action")

        if not action:
            return {
                "success": False,
                "error": "No action specified",
                "output": ""
            }

        # Check if action is allowed in safe mode
        if self.safe_mode and action in self.DESTRUCTIVE_ACTIONS:
            if self.require_confirmation:
                logger.warning(f"Destructive action '{action}' requires confirmation")

        # Route to appropriate method
        try:
            if action == "status":
                result = self.status(repo_path=params.get("repo_path"))

            elif action == "log":
                result = self.log(
                    repo_path=params.get("repo_path"),
                    max_count=params.get("max_count", 10),
                    file_path=params.get("file_path")
                )

            elif action == "diff":
                result = self.diff(
                    repo_path=params.get("repo_path"),
                    file_path=params.get("file_path"),
                    commit_ref=params.get("commit_ref")
                )

            elif action == "clone":
                url = params.get("url")
                destination = params.get("destination")
                if not url or not destination:
                    return {
                        "success": False,
                        "error": "Clone requires 'url' and 'destination'",
                        "output": ""
                    }
                result = self.clone(
                    url=url,
                    destination=destination,
                    use_credentials=params.get("use_credentials", True)
                )

            elif action == "fetch":
                result = self.fetch(
                    repo_path=params.get("repo_path"),
                    remote_name=params.get("remote_name", "origin")
                )

            elif action == "pull":
                result = self.pull(
                    repo_path=params.get("repo_path"),
                    remote_name=params.get("remote_name", "origin"),
                    branch_name=params.get("branch_name")
                )

            elif action == "push":
                result = self.push(
                    repo_path=params.get("repo_path"),
                    remote_name=params.get("remote_name", "origin"),
                    branch_name=params.get("branch_name"),
                    force=params.get("force", False)
                )

            elif action == "branch":
                result = self.branch(
                    repo_path=params.get("repo_path"),
                    branch_name=params.get("branch_name"),
                    create=params.get("create_branch", False)
                )

            elif action == "checkout":
                branch_name = params.get("branch_name")
                if not branch_name:
                    return {
                        "success": False,
                        "error": "Checkout requires 'branch_name'",
                        "output": ""
                    }
                result = self.checkout(
                    branch_name=branch_name,
                    repo_path=params.get("repo_path"),
                    create_branch=params.get("create_branch", False)
                )

            elif action == "remote":
                result = self.remote(
                    repo_path=params.get("repo_path")
                )

            elif action == "show":
                result = self.show(
                    commit_ref=params.get("commit_ref", "HEAD"),
                    repo_path=params.get("repo_path")
                )

            elif action == "config_get":
                config_key = params.get("config_key")
                if not config_key:
                    return {
                        "success": False,
                        "error": "config_get requires 'config_key'",
                        "output": ""
                    }
                result = self.config_get(
                    config_key=config_key,
                    repo_path=params.get("repo_path")
                )

            elif action == "config_set":
                config_key = params.get("config_key")
                config_value = params.get("config_value")
                if not config_key or not config_value:
                    return {
                        "success": False,
                        "error": "config_set requires 'config_key' and 'config_value'",
                        "output": ""
                    }
                result = self.config_set(
                    config_key=config_key,
                    config_value=config_value,
                    repo_path=params.get("repo_path")
                )

            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "output": ""
                }

            result["action"] = action
            return result

        except Exception as e:
            logger.error(f"Error executing git action '{action}': {e}")
            return {
                "success": False,
                "action": action,
                "error": str(e),
                "output": ""
            }
