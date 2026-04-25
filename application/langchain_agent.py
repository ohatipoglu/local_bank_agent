"""
LangChain/LangGraph banking agent with Ollama integration.
Provides ReAct-style reasoning with banking tool calling.
"""

import os
import re
import sqlite3

import emoji
import httpx
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from application.prompts import get_dynamic_prompt
from application.tools_registry import BankToolsRegistry, reset_customer_id, set_customer_id
from core.exceptions import AgentInitializationError
from core.logger import get_correlated_logger
from domain.interfaces import IAccountService

# SQLite-backed persistent memory — survives application restarts.
# Falls back to in-memory MemorySaver if package is not installed.
try:
    from langgraph.checkpoint.sqlite import SqliteSaver as _SqliteSaver
    _SQLITE_AVAILABLE = True
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver as _SqliteSaver  # type: ignore[assignment]
    _SQLITE_AVAILABLE = False

_AGENT_MEMORY_DB = os.getenv("AGENT_MEMORY_DB_PATH", "./agent_memory.db")


def _build_memory():
    """Create a persistent SqliteSaver (or MemorySaver fallback)."""
    if _SQLITE_AVAILABLE:
        conn = sqlite3.connect(_AGENT_MEMORY_DB, check_same_thread=False)
        return _SqliteSaver(conn)
    return _SqliteSaver()


class LoguruCallbackHandler(BaseCallbackHandler):
    """
    Custom LangChain callback handler that logs LLM/tool interactions
    via Loguru with structured context.
    """

    def __init__(self, logger):
        self.log = logger

    def on_chat_model_start(self, serialized, messages, **kwargs):
        formatted_messages = []
        for msg_list in messages:
            for msg in msg_list:
                formatted_messages.append(f"[{msg.type.upper()}]: {msg.content}")
        self.log.debug("[OLLAMA İSTEK BAŞLADI] -> \n" + "\n".join(formatted_messages))

    def on_llm_end(self, response, **kwargs):
        try:
            generated_text = response.generations[0][0].text
            self.log.debug(f"[OLLAMA YANIT TAMAMLANDI] <- \n{generated_text}")
        except Exception:
            self.log.debug(f"[OLLAMA YANIT TAMAMLANDI] <- {response}")

    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get("name", "Bilinmeyen Tool")
        self.log.debug(
            f"[ARAÇ (TOOL) ÇAĞRILIYOR] -> {tool_name} | Parametreler: {input_str}"
        )

    def on_tool_end(self, output, **kwargs):
        self.log.debug(f"[ARAÇ (TOOL) SONUCU] <- \n{output}")


class LangChainBankAgent:
    """
    AI banking agent using LangGraph ReAct pattern with tool calling.

    Processes natural language requests and invokes banking tools
    (balance inquiry, credit card debt, EFT, Havale) as needed.

    Features:
    - Dynamic strictness level (1-5) for behavioral control
    - Session-based conversation memory (SQLite-backed)
    - Emoji/markdown sanitization for TTS compatibility
    - Structured logging with correlation IDs
    - customer_id passed via ContextVar (not system prompt) to prevent injection
    """

    # Compiled regex for response sanitization (performance optimization)
    _EMOJI_PATTERN = re.compile(r"[:;=]-?[)(DPOp]")
    _MARKDOWN_PATTERNS = [
        (re.compile(r"#+\s*"), ""),              # Headers
        (re.compile(r"\*\*(.*?)\*\*"), r"\1"),   # Bold **
        (re.compile(r"\*(.*?)\*"), r"\1"),        # Italic *
        (re.compile(r"__(.*?)__"), r"\1"),        # Bold __
        (re.compile(r"_(.*?)_"), r"\1"),          # Italic _
        (re.compile(r"^\s*[-*+><]\s+", re.MULTILINE), ""),  # List items
    ]

    def __init__(
        self,
        account_service: IAccountService,
        model_name: str,
        logger=None,
        max_tokens: int = 1536,
        agent_timeout_seconds: int = 1800,
    ):
        self.log = logger or get_correlated_logger()
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.agent_executor = None
        self.tools = []

        self.log.info(f"LangGraph Agent başlatılıyor. Model: {model_name}")

        try:
            # 1. Register banking tools
            registry = BankToolsRegistry(account_service)
            self.tools = registry.get_tools()
            self.log.info(f"Sisteme {len(self.tools)} adet bankacılık aracı yüklendi.")

            # 2. Configure LLM with Ollama
            # Timeout is kept high intentionally — local model (Intel ARC iGPU) takes 6-9 min.
            callback = LoguruCallbackHandler(self.log)
            timeout = httpx.Timeout(float(agent_timeout_seconds), connect=60.0)

            self.llm = ChatOllama(
                model=model_name,
                temperature=0.1,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                callbacks=[callback],
                client_kwargs={"timeout": timeout},
                num_predict=max_tokens,
            )
            self.log.info("ChatOllama yüklendi. Tool Calling aktif.")

            # 3. Create LangGraph agent with persistent SQLite memory
            self.memory = _build_memory()
            memory_type = "SqliteSaver" if _SQLITE_AVAILABLE else "MemorySaver (fallback)"
            self.log.info(f"Konuşma hafızası: {memory_type} — {_AGENT_MEMORY_DB}")

            self.agent_executor = create_react_agent(
                self.llm,
                tools=self.tools,
                checkpointer=self.memory,
            )
            self.log.info("Agent Executor başarıyla oluşturuldu.")

        except Exception as e:
            raise AgentInitializationError(
                f"LangChain Agent oluşturulamadı: {e}"
            ) from e

    def handle_turn(
        self,
        user_text: str,
        strictness_level: int = 3,
        session_id: str = None,
        customer_id: str = None,
    ) -> str:
        """
        Process a single conversation turn.

        customer_id is injected via ContextVar (not the system prompt) to prevent
        prompt injection attacks. Each thread/task gets an isolated context copy.

        Args:
            user_text: User's input text
            strictness_level: Behavioral control level (1-5)
            session_id: Unique session identifier (required)
            customer_id: Verified customer ID — set into ContextVar, not the prompt

        Returns:
            Agent's response text
        """
        if not session_id:
            self.log.error("Session ID belirtilmedi!")
            return "Görüşme oturumu başlatılamadı, lütfen tekrar bağlanın."

        self.log.info(
            f"LangChain Agent Girdisi: {user_text} | "
            f"Seviye: {strictness_level} | "
            f"Customer: {customer_id or 'doğrulanmamış'}"
        )

        # Inject customer_id into ContextVar (isolated per thread — no prompt injection risk)
        token = None
        if customer_id:
            token = set_customer_id(customer_id)

        try:
            dynamic_prompt = get_dynamic_prompt(strictness_level)

            messages = [
                SystemMessage(content=dynamic_prompt),
                HumanMessage(content=user_text),
            ]
            inputs = {"messages": messages}
            config = {"configurable": {"thread_id": session_id}}

            final_response = "Sizi tam olarak anlayamadım, tekrar edebilir misiniz?"

            try:
                response = self.agent_executor.invoke(inputs, config=config)
                if isinstance(response, dict) and "messages" in response:
                    for msg in reversed(response["messages"]):
                        if msg.type == "ai" and getattr(msg, "content", "").strip():
                            final_response = msg.content
                            break
            except Exception as invoke_err:
                self.log.warning(
                    f"Invoke sırasında hata, stream deneniyor: {invoke_err}"
                )
                for chunk in self.agent_executor.stream(
                    inputs, stream_mode="values", config=config
                ):
                    if "messages" in chunk:
                        last_message = chunk["messages"][-1]
                        if (
                            last_message.type == "ai"
                            and hasattr(last_message, "content")
                            and isinstance(last_message.content, str)
                            and last_message.content.strip()
                        ):
                            final_response = last_message.content

            final_response = self._sanitize_response(final_response)

            self.log.info(
                f"LangChain Yanıtı (Seviye {strictness_level}): {final_response}"
            )
            return final_response

        except Exception as e:
            self.log.error(f"LangChain İşlem Hatası: {e}")
            return "Sistemde geçici bir hata oluştu, lütfen daha sonra tekrar deneyin."

        finally:
            # Restore previous ContextVar state to keep threads clean
            if token is not None:
                reset_customer_id(token)

    @classmethod
    def _sanitize_response(cls, text: str) -> str:
        """Remove emojis, markdown, and formatting for TTS compatibility."""
        text = cls._EMOJI_PATTERN.sub("", text)
        text = emoji.replace_emoji(text, replace="")
        for pattern, replacement in cls._MARKDOWN_PATTERNS:
            text = pattern.sub(replacement, text)
        text = " ".join(text.split())
        return text
