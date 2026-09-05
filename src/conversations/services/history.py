from assistant.runner import ConversationTurn
from conversations.models import Conversation, MessageRole


def conversation_turns(conversation: Conversation) -> list[ConversationTurn]:
    """Converte o histórico persistido no formato neutro consumido pelo assistente."""
    return [
        ConversationTurn(
            role="user" if message.role == MessageRole.CUSTOMER else "assistant",
            content=message.content,
        )
        for message in conversation.messages.all()
    ]
