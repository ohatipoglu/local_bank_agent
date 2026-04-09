"""
LangChain/LangGraph banking agent with Ollama integration.
Provides ReAct-style reasoning with banking tool calling.
"""
import re
import emoji
import httpx
from typing import Optional

from domain.interfaces import IAccountService
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from application.prompts import get_dynamic_prompt
from application.tools_registry import BankToolsRegistry
from core.exceptions import AgentError, AgentInitializationError
from core.logger import get_correlated_logger


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
        self.log.debug(
            "[OLLAMA İSTEK BAŞLADI] -> \n" + "\n".join(formatted_messages)
        )

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
    - Session-based conversation memory
    - Emoji/markdown sanitization for TTS compatibility
    - Structured logging with correlation IDs
    """

    # Compiled regex for response sanitization (performance optimization)
    _EMOJI_PATTERN = re.compile(r'[:;=]-?[)(DPOp]')
    _MARKDOWN_PATTERNS = [
        (re.compile(r'#+\s*'), ''),                          # Headers
        (re.compile(r'\*\*(.*?)\*\*'), r'\1'),               # Bold **
        (re.compile(r'\*(.*?)\*'), r'\1'),                   # Italic *
        (re.compile(r'__(.*?)__'), r'\1'),                   # Bold __
        (re.compile(r'_(.*?)_'), r'\1'),                     # Italic _
        (re.compile(r'^\s*[-*+><]\s+', re.MULTILINE), ''),   # List items
    ]

    def __init__(
        self,
        account_service: IAccountService,
        model_name: str,
        logger=None,
        max_tokens: int = 1536,
    ):
        """
        Initialize the banking agent.
        
        Args:
            account_service: Banking service implementation
            model_name: Ollama model name (e.g., "gemma4:26B-32K")
            logger: Loguru logger instance (auto-created if None)
            max_tokens: Maximum response tokens
        """
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
            callback = LoguruCallbackHandler(self.log)
            timeout = httpx.Timeout(1800.0, connect=60.0)

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

            # 3. Create LangGraph agent with memory
            self.memory = MemorySaver()
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
        
        Args:
            user_text: User's input text
            strictness_level: Behavioral control level (1-5)
            session_id: Unique session identifier (required)
            customer_id: Verified customer ID (optional, defaults per tool)
            
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

        try:
            # Build dynamic system prompt
            dynamic_prompt = get_dynamic_prompt(strictness_level)

            # Inject customer context if available
            if customer_id:
                dynamic_prompt += (
                    f"\n\nMüşteri Kimliği: {customer_id}. "
                    f"İşlemlerde bu müşteri kimliğini kullanın."
                )

            messages = [
                SystemMessage(content=dynamic_prompt),
                HumanMessage(content=user_text),
            ]
            inputs = {"messages": messages}
            config = {"configurable": {"thread_id": session_id}}

            final_response = "Sizi tam olarak anlayamadım, tekrar edebilir misiniz?"

            # Execute agent with fallback to streaming on error
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

            # Sanitize response for TTS compatibility
            final_response = self._sanitize_response(final_response)

            self.log.info(
                f"LangChain Yanıtı (Seviye {strictness_level}): {final_response}"
            )
            return final_response

        except Exception as e:
            self.log.error(f"LangChain İşlem Hatası: {e}")
            return "Sistemde geçici bir hata oluştu, lütfen daha sonra tekrar deneyin."

    @classmethod
    def _sanitize_response(cls, text: str) -> str:
        """
        Remove emojis, markdown, and formatting for TTS compatibility.
        
        Args:
            text: Raw agent response
            
        Returns:
            Cleaned plain text
        """
        # 1. Remove text-based emojis
        text = cls._EMOJI_PATTERN.sub('', text)

        # 2. Remove unicode emojis
        text = emoji.replace_emoji(text, replace='')

        # 3. Remove markdown formatting
        for pattern, replacement in cls._MARKDOWN_PATTERNS:
            text = pattern.sub(replacement, text)

        # 4. Normalize whitespace
        text = " ".join(text.split())

        return text
