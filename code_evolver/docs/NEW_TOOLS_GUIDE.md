# New Tools Guide - Git, GitHub, Ask User, and Explainer

This guide covers the four major tools added to the Code Evolver system:

1. **Git Tool** - Safe and powerful Git operations with authentication
2. **GitHub Tool** - Complete GitHub API integration for PR/issue management
3. **Ask User Tool** - Interactive CLI input with LLM fallback
4. **Explainer Tool** - Fast AI explanations for workflows and stages

## Table of Contents

- [Git Tool](#git-tool)
- [GitHub Tool](#github-tool)
- [Ask User Tool](#ask-user-tool)
- [Explainer Tool](#explainer-tool)
- [Configuration](#configuration)
- [Example Workflows](#example-workflows)

---

## Git Tool

**Type:** Custom Tool
**Location:** `tools/custom/git.yaml`
**Implementation:** `src/git_tool.py`

### Purpose

Provides safe and comprehensive Git integration with authentication from config.yaml.

### Features

- All major Git operations (status, log, diff, clone, push, pull, etc.)
- Authentication via config.yaml (GitHub/GitLab tokens, SSH keys)
- Safety checks for destructive operations
- Parsed output for easy consumption
- Credential injection for HTTPS URLs
- Support for local and remote operations

### Supported Actions

| Action | Description | Safe |
|--------|-------------|------|
| `status` | Show working tree status | ✓ |
| `log` | Show commit logs | ✓ |
| `diff` | Show changes | ✓ |
| `clone` | Clone a repository | ✓ |
| `fetch` | Fetch from remote | ✓ |
| `pull` | Pull from remote | ✓ |
| `push` | Push to remote | ⚠️ |
| `branch` | List/create branches | ✓ |
| `checkout` | Switch branches | ⚠️ |
| `remote` | Manage remotes | ✓ |
| `show` | Show commit details | ✓ |
| `blame` | Show file annotations | ✓ |
| `stash` | Stash changes | ⚠️ |
| `tag` | Manage tags | ✓ |
| `config_get` | Get config value | ✓ |
| `config_set` | Set config value | ⚠️ |

### Usage Example

```python
from node_runtime import call_tool
import json

# Check repository status
result = call_tool("git", json.dumps({
    "action": "status"
}))

data = json.loads(result)
if data['success']:
    print(f"Branch: {data['data']['branch']}")
    print(f"Changes: {len(data['data']['changes'])}")

# View commit history
result = call_tool("git", json.dumps({
    "action": "log",
    "max_count": 5
}))

# Clone repository with authentication
result = call_tool("git", json.dumps({
    "action": "clone",
    "url": "https://github.com/user/repo.git",
    "destination": "./my-repo",
    "use_credentials": true
}))
```

### Test Results

✅ **Status command tested successfully:**
```json
{
  "success": true,
  "data": {
    "branch": "claude/add-git-tool-01GZMgc4JX5zA2L1qQcVjsJU",
    "changes": ["modified:   code_evolver/config.yaml"],
    "clean": false
  }
}
```

---

## GitHub Tool

**Type:** Custom Tool
**Location:** `tools/custom/github.yaml`
**Implementation:** `src/github_tool.py`

### Purpose

Complete GitHub API integration for PR management, issue tracking, and repository operations.

### Features

- Pull Request management (status, list, comments, reviews)
- Issue tracking
- Check merge status
- Repository information
- Authentication from config.yaml
- URL parsing (supports multiple formats)
- Rate limit handling

### Supported Actions

| Action | Description |
|--------|-------------|
| `check_merged` | Check if PR is merged |
| `pr_status` | Get PR details |
| `pr_list` | List pull requests |
| `pr_comments` | Get PR comments |
| `pr_reviews` | Get PR reviews |
| `pr_files` | Get PR changed files |
| `pr_merge_status` | Get merge status |
| `issue_status` | Get issue details |
| `issue_list` | List issues |
| `repo_info` | Get repository info |
| `create_comment` | Add comment to PR/issue |

### Usage Example

```python
from node_runtime import call_tool
import json

# Check if PR is merged (example from requirements)
result = call_tool("github", json.dumps({
    "action": "check_merged",
    "repo_url": "https://github.com/scottgal/mostlylucid.dse/pull/40"
}))

data = json.loads(result)
if data['data']['is_merged']:
    print("PR #40 is merged!")

# Get PR details
result = call_tool("github", json.dumps({
    "action": "pr_status",
    "owner": "scottgal",
    "repo": "mostlylucid.dse",
    "pr_number": 40
}))

# List open PRs
result = call_tool("github", json.dumps({
    "action": "pr_list",
    "repo_url": "scottgal/mostlylucid.dse",
    "state": "open"
}))
```

### Test Results

✅ **PR #40 merge check tested successfully:**
```json
{
  "success": true,
  "data": {
    "pr_number": 40,
    "is_merged": true,
    "merged_at": "2025-11-17T12:43:00Z",
    "merged_by": "scottgal",
    "state": "closed",
    "title": "Build prompt generator with tiered roles"
  }
}
```

---

## Ask User Tool

**Type:** Custom Tool
**Location:** `tools/custom/ask_user.yaml`
**Implementation:** `src/ask_user_tool.py`

### Purpose

Interactive user input for CLI workflows with LLM fallback for non-interactive mode.

### Features

- Interactive CLI prompts when terminal is available
- LLM fallback for non-interactive mode (scheduled tasks, background jobs)
- Multiple question types (text, yes/no, confirm, choice)
- Timeout handling
- Default answers
- Context-aware LLM decisions
- Automatic interactive mode detection

### Question Types

| Type | Description | Example |
|------|-------------|---------|
| `text` | Free-form text input | "What is your email?" |
| `yes_no` | Binary yes/no question | "Proceed with deployment?" |
| `confirm` | Requires specific confirmation | "Type 'DELETE' to confirm" |
| `choice` | Select from predefined options | ["prod", "staging", "dev"] |

### How It Works

**Interactive Mode** (user at terminal):
1. Detects interactive terminal (stdin is TTY)
2. Displays question to user
3. Waits for user input (with timeout)
4. Returns user's answer

**Non-Interactive Mode** (scheduled/background):
1. Detects non-interactive environment
2. If `allow_llm_fallback=true`: Asks overseer LLM to decide
3. If `allow_llm_fallback=false`: Uses default answer
4. Returns decision with `answered_by` field

### Usage Example

```python
from node_runtime import call_tool
import json

# Ask yes/no question
result = call_tool("ask_user", json.dumps({
    "question": "Do you want to proceed with deployment?",
    "question_type": "yes_no",
    "context": "Deploying version 2.0 to production",
    "default_answer": "no"
}))

data = json.loads(result)
if data['answer'] == 'yes':
    deploy_to_production()
else:
    print("Deployment cancelled")

# Multiple choice
result = call_tool("ask_user", json.dumps({
    "question": "Which environment should we deploy to?",
    "question_type": "choice",
    "choices": ["production", "staging", "development"],
    "context": "Feature branch ready for deployment"
}))

environment = json.loads(result)['answer']
deploy_to_environment(environment)

# Get user email (can be stored in RAG for future use)
result = call_tool("ask_user", json.dumps({
    "question": "What is your email address?",
    "question_type": "text",
    "context": "Need email for notifications"
}))

email = json.loads(result)['answer']
# Store in RAG for future use
store_in_rag("user_email", email)
```

### Workflow Pattern: Email Notification

```python
# Example from requirements: "when PR #40 is merged, send an email"

# Get user email from RAG or ask
user_email = get_from_rag("user_email")

if not user_email:
    result = call_tool("ask_user", json.dumps({
        "question": "What is your email address?",
        "question_type": "text"
    }))
    user_email = json.loads(result)['answer']
    store_in_rag("user_email", user_email)

# Check PR status
pr_status = call_tool("github", json.dumps({
    "action": "check_merged",
    "repo_url": "https://github.com/scottgal/mostlylucid.dse/pull/40"
}))

if json.loads(pr_status)['data']['is_merged']:
    send_email(user_email, "PR #40 has been merged!")
```

---

## Explainer Tool

**Type:** LLM Tool
**Location:** `tools/llm/explainer.yaml`
**Model:** Fast 1B-class LLM (gemma3:1b)

### Purpose

Fast AI explainer that generates quick, concise descriptions of what's happening in workflows, tools, and system stages.

### Features

- Ultra-fast (<100ms response using 1B model)
- Concise explanations (1-3 sentences)
- Stage-aware (understands workflow phases)
- Context-sensitive
- Technical but clear language
- Perfect for real-time logging and user feedback

### Supported Stages

| Stage | Focus |
|-------|-------|
| `planning` | What's being designed |
| `execution` | What's running now |
| `testing` | What's being validated |
| `validation` | What's being checked |
| `optimization` | What's being improved |
| `deployment` | What's being released |
| `monitoring` | What's being observed |

### Usage Example

```python
from node_runtime import call_tool
import json

# Explain workflow step
result = call_tool("explainer", json.dumps({
    "query": "What is happening in this step?",
    "context": "Running black_formatter on generated code",
    "stage": "execution"
}))

data = json.loads(result)
print(data['explanation'])
# Output: "Formatting Python code with Black to ensure consistent
#          style and readability across the codebase."

# Explain tool purpose
result = call_tool("explainer", json.dumps({
    "query": "What does the git tool do?",
    "context": "Tool: git, Action: status"
}))

# Explain during tool generation
explanation = call_tool("explainer", json.dumps({
    "query": "What is being generated?",
    "context": f"Tool: {tool_name}, Type: executable",
    "stage": "execution"
}))

print(f"[INFO] {json.loads(explanation)['explanation']}")
```

---

## Configuration

### Setting Up Git/GitHub Authentication

Add to `code_evolver/config.yaml`:

```yaml
git:
  # GitHub configuration
  github:
    username: "${GITHUB_USERNAME}"
    token: "${GITHUB_TOKEN}"

  # GitLab configuration
  gitlab:
    username: "${GITLAB_USERNAME}"
    token: "${GITLAB_TOKEN}"

  # Custom credentials
  credentials:
    - pattern: "github.com"
      username: "${GITHUB_USERNAME}"
      token: "${GITHUB_TOKEN}"
    - pattern: "gitlab.com"
      username: "${GITLAB_USERNAME}"
      token: "${GITLAB_TOKEN}"

  # Tool settings
  tool_settings:
    safe_mode: true
    require_confirmation_for_destructive: true
    max_diff_size_kb: 500
```

### Setting Environment Variables

```bash
# GitHub
export GITHUB_USERNAME="your-username"
export GITHUB_TOKEN="ghp_your_token_here"

# GitLab (optional)
export GITLAB_USERNAME="your-username"
export GITLAB_TOKEN="your_gitlab_token"
```

### Generating GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (Full control of private repositories)
   - `read:org` (Read org and team membership)
4. Copy token and set in environment variable

---

## Example Workflows

### Workflow 1: PR Merge Notification

```python
"""
Workflow: Monitor PR and send email when merged
Usage: "when https://github.com/scottgal/mostlylucid.dse/pull/40 is merged, send an email to me"
"""

from node_runtime import call_tool
import json
import time

# Get user email (ask once, store in RAG)
user_email = get_from_rag("user_email")

if not user_email:
    result = call_tool("ask_user", json.dumps({
        "question": "What email should we send notifications to?",
        "question_type": "text",
        "context": "Setting up PR merge notifications"
    }))
    user_email = json.loads(result)['answer']
    store_in_rag("user_email", user_email)
    print(f"[OK] Will send notifications to: {user_email}")

# Monitor PR status
pr_url = "https://github.com/scottgal/mostlylucid.dse/pull/40"

while True:
    # Check if PR is merged
    result = call_tool("github", json.dumps({
        "action": "check_merged",
        "repo_url": pr_url
    }))

    data = json.loads(result)

    if data['data']['is_merged']:
        # PR is merged! Send notification
        merged_at = data['data']['merged_at']
        merged_by = data['data']['merged_by']
        title = data['data']['title']

        send_email(
            to=user_email,
            subject=f"PR #{data['data']['pr_number']} Merged!",
            body=f"""
            PR has been merged:

            Title: {title}
            Merged by: {merged_by}
            Merged at: {merged_at}
            URL: {pr_url}
            """
        )

        print(f"[✓] Email sent to {user_email}")
        break

    # Not merged yet, wait and check again
    time.sleep(60)  # Check every minute
```

### Workflow 2: Interactive Git Operations

```python
"""
Workflow: Safe git operations with user confirmation
"""

from node_runtime import call_tool
import json

# Check current status
status = call_tool("git", json.dumps({
    "action": "status"
}))

status_data = json.loads(status)
print(f"Current branch: {status_data['data']['branch']}")
print(f"Changes: {len(status_data['data']['changes'])}")

# Ask user if they want to commit
result = call_tool("ask_user", json.dumps({
    "question": "Do you want to commit these changes?",
    "question_type": "yes_no",
    "context": f"Branch: {status_data['data']['branch']}, Changes: {len(status_data['data']['changes'])}",
    "default_answer": "no"
}))

if json.loads(result)['answer'] == 'yes':
    # Ask for commit message
    msg_result = call_tool("ask_user", json.dumps({
        "question": "What should the commit message be?",
        "question_type": "text",
        "context": "Committing changes"
    }))

    commit_message = json.loads(msg_result)['answer']

    # Commit (would use git tool or subprocess)
    print(f"Committing with message: {commit_message}")
```

### Workflow 3: Comprehensive PR Review

```python
"""
Workflow: Get comprehensive PR information with explanations
"""

from node_runtime import call_tool
import json

pr_url = "https://github.com/scottgal/mostlylucid.dse/pull/40"

# Parse URL
result = call_tool("github", json.dumps({
    "action": "pr_status",
    "repo_url": pr_url
}))

pr_data = json.loads(result)['data']

# Get comments
comments_result = call_tool("github", json.dumps({
    "action": "pr_comments",
    "repo_url": pr_url
}))

# Get reviews
reviews_result = call_tool("github", json.dumps({
    "action": "pr_reviews",
    "repo_url": pr_url
}))

# Get files changed
files_result = call_tool("github", json.dumps({
    "action": "pr_files",
    "repo_url": pr_url
}))

# Explain the PR
explanation = call_tool("explainer", json.dumps({
    "query": "What is this PR doing?",
    "context": f"PR #{pr_data['number']}: {pr_data['title']}, {pr_data['changed_files']} files changed",
    "stage": "validation"
}))

print("=== PR Summary ===")
print(f"Title: {pr_data['title']}")
print(f"State: {pr_data['state']}")
print(f"Merged: {pr_data['merged']}")
print(f"Files Changed: {pr_data['changed_files']}")
print(f"Explanation: {json.loads(explanation)['explanation']}")
```

---

## Integration with RAG

All tools integrate seamlessly with the RAG memory system:

### Storing User Preferences

```python
# Ask user once, store in RAG
email = ask_user_for_email()
store_in_rag("user_email", email)

# Use in future workflows
email = get_from_rag("user_email")
```

### Storing Tool Decisions

```python
# Store LLM decisions for analysis
result = call_tool("ask_user", json.dumps({...}))

store_in_rag("deployment_decisions", {
    "environment": result['answer'],
    "decided_by": result['answered_by'],
    "timestamp": datetime.now()
})
```

---

## Safety Features

### Git Tool Safety

- **Safe Mode**: Prevents accidental destructive operations
- **Confirmation Required**: Destructive ops require explicit confirmation
- **Size Limits**: Large diffs are truncated for safety
- **Credential Protection**: Tokens never exposed in output

### GitHub Tool Safety

- **Rate Limiting**: Handles GitHub API rate limits gracefully
- **Authentication**: Secure token-based authentication
- **Read-Only by Default**: Most operations are read-only

### Ask User Tool Safety

- **Timeout**: Prevents infinite waiting (default 60s)
- **Default Answers**: Always have a fallback
- **LLM Toggle**: Can disable LLM for critical operations
- **Answer Source Tracking**: Know who/what made the decision

---

## Troubleshooting

### Git Tool

**Problem:** "No credentials available"
**Solution:** Set `GITHUB_TOKEN` environment variable or configure in `config.yaml`

**Problem:** "Command timed out"
**Solution:** Increase timeout or check network connectivity

### GitHub Tool

**Problem:** "Rate limit exceeded"
**Solution:** Add GitHub token for authentication (5,000 requests/hour)

**Problem:** "Invalid repository URL"
**Solution:** Use format `owner/repo` or `https://github.com/owner/repo`

### Ask User Tool

**Problem:** "No answer available"
**Solution:** Provide a `default_answer` or enable `allow_llm_fallback`

**Problem:** "Timeout"
**Solution:** Increase `timeout_seconds` or use default answer

---

## Next Steps

1. **Set up authentication** in `config.yaml`
2. **Test the tools** with simple commands
3. **Build workflows** using multiple tools together
4. **Integrate with RAG** to remember user preferences
5. **Schedule workflows** for PR monitoring and notifications

For more examples, see the tool YAML files and implementation files.
