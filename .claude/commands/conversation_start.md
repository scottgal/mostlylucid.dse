---
description: Start a new conversation with multi-chat context memory and semantic search
---

You are starting a new conversation using the conversation tool.

## Task

Start a conversation session with the following capabilities:
- Multi-chat context memory that remembers previous exchanges
- Auto-summarization based on context window size
- Semantic storage in Qdrant for conversation retrieval
- Related conversation context from past conversations
- Performance tracking

## Steps

1. Extract the topic from the command arguments (if provided)
   - Command format: `/conversation start <topic>`
   - Default topic: "general"

2. Use the conversation tool to start the conversation:
   ```python
   from code_evolver.src.conversation import ConversationTool

   # Initialize tool
   tool = ConversationTool.create_from_config_file(
       "code_evolver/config.yaml",
       conversation_model="gemma3:1b"
   )

   # Start conversation
   result = tool.start_conversation(topic="<extracted_topic>")
   print(f"Started conversation: {result['topic']}")
   print(f"Conversation ID: {result['conversation_id']}")
   ```

3. Inform the user that the conversation has started and is ready

4. For subsequent user messages:
   - Add user message to conversation
   - Prepare optimized context
   - Generate response using the prepared context
   - Add assistant response to conversation with performance metrics

## Important Notes

- The conversation will automatically summarize when context window threshold is reached
- Related context from past conversations will be included when relevant
- Performance metrics (response time, etc.) are tracked automatically
- The conversation persists until explicitly ended with `/conversation end`
- Context is optimized for the model being used to ensure fast, accurate responses

## Example Usage

User: `/conversation start software architecture`
Assistant: "Started conversation about software architecture. I'm ready to discuss! The conversation system is tracking our discussion with context-aware memory and will automatically optimize as we chat."
