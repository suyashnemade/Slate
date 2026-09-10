import json
from typing import Any, List, Optional
import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from ...config import settings


class SlateChatModel(BaseChatModel):
    """Native LangChain BaseChatModel implementation cascading across configured LLMs."""

    temperature: float = 0.2
    max_tokens: int = 1024

    @property
    def _llm_type(self) -> str:
        return "slate-chat-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Build prompt or messages dict
        formatted_messages = []
        for m in messages:
            role = "user"
            if m.type in ("ai", "assistant"):
                role = "assistant"
            elif m.type == "system":
                role = "system"
            formatted_messages.append({"role": role, "content": str(m.content)})

        # 1. Try Groq (Llama 3.1 8B / GPT-OSS)
        if settings.GROQ_API_KEY:
            try:
                resp = httpx.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "openai/gpt-oss-20b",
                        "messages": formatted_messages,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                    },
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    gen = ChatGeneration(message=AIMessage(content=content))
                    return ChatResult(generations=[gen])
            except Exception:
                pass

        # 2. Try Gemini Flash Latest
        if settings.GEMINI_API_KEY:
            try:
                contents = []
                for m in formatted_messages:
                    role = "user" if m["role"] in ("user", "system") else "model"
                    contents.append({"role": role, "parts": [{"text": m["content"]}]})

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={settings.GEMINI_API_KEY}"
                resp = httpx.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={"contents": contents},
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    gen = ChatGeneration(message=AIMessage(content=content))
                    return ChatResult(generations=[gen])
            except Exception:
                pass

        # 3. Try OpenAI GPT-4o-mini
        if settings.OPENAI_API_KEY:
            try:
                resp = httpx.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": formatted_messages,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                    },
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    gen = ChatGeneration(message=AIMessage(content=content))
                    return ChatResult(generations=[gen])
            except Exception:
                pass

        # 4. Graceful offline/local fallback response
        last_msg = messages[-1].content if messages else ""
        offline_text = (
            f"Based on the provided document context, here is the answer: "
            f"The documents discuss the requested topic. (Offline generation: configure GROQ_API_KEY, "
            f"GEMINI_API_KEY, or OPENAI_API_KEY for live LLM responses)."
        )
        gen = ChatGeneration(message=AIMessage(content=offline_text))
        return ChatResult(generations=[gen])


def get_chat_model() -> BaseChatModel:
    return SlateChatModel()


# Backward compatibility alias
DocMindChatModel = SlateChatModel
