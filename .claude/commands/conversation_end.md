---
description: End the current conversation or a specific conversation by topic
---

You are ending a conversation using the conversation tool.

## Task

End a conversation session, optionally saving metadata for future semantic retrieval.

## Steps

1. Extract the topic from the command arguments (if provided)
   - Command format: `/conversation end <topic>` or `/conversation end`
   - If no topic provided, ends the current active conversation

2. Use the conversation tool to end the conversation:
   ```python
   from code_evolver.src.conversation import ConversationTool

   # Initialize tool
   tool = ConversationTool.create_from_config_file(
       "code_evolver/config.yaml",
       conversation_model="gemma3:1b"
   )

   # End conversation
   result = tool.end_conversation(
       topic="<topic_if_provided>",
       save_metadata=True  # Save for future retrieval
   )

   print(f"Ended conversation: {result['topic']}")
   print(f"Total messages: {result['message_count']}")
   if 'summary' in result:
       print(f"\nSummary:\n{result['summary']}")
   if 'key_points' in result:
       print(f"\nKey Points:")
       for point in result['key_points']:
           print(f"  - {point}")
   ```

3. Display the conversation summary and statistics to the user

## What Happens When You End a Conversation

1. **Summarization**: The entire conversation is summarized using gemma3:1b
2. **Key Points Extraction**: Important points are extracted
3. **Metadata Storage**: Summary and metadata are stored in Qdrant with embeddings
4. **Future Retrieval**: The conversation can be retrieved in future conversations as related context
5. **Collection Cleanup**: The volatile Qdrant collection for this conversation is deleted

## Important Notes

- Metadata is saved by default (`save_metadata=True`)
- The saved metadata enables semantic search in future conversations
- Once ended, the conversation messages are deleted, but metadata persists
- You can end a specific conversation by topic even if it's not the current one

## Example Usage

**End current conversation:**
User: `/conversation end`
Assistant: "Ended conversation about software architecture. Total messages: 12. Summary: [shows summary and key points]"

**End specific conversation:**
User: `/conversation end python debugging`
Assistant: "Ended conversation about python debugging. Total messages: 8. Summary: [shows summary and key points]"
