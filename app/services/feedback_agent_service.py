import json
import os
from typing import Any, Dict, List, Optional

from app.core.logger_config import logger
from app.core.settings import setting
from app.models.habit_quitter import SystemConfig


class FeedbackAgentService:
    def __init__(self):
        self.logger = logger

    async def get_selected_provider(self) -> str:
        """
        Get the currently active LLM provider for the Feedback Agent ('groq' or 'gemini').
        Defaults to groq if available, otherwise gemini, or setting.LLM_PROVIDER.
        """
        try:
            config = await SystemConfig.find_one({"key": "feedback_llm_provider"})
            if config and config.value in ("groq", "gemini"):
                return config.value
        except Exception:
            pass

        groq_key = setting.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
        gemini_key = setting.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")

        if setting.LLM_PROVIDER in ("groq", "gemini"):
            return setting.LLM_PROVIDER
        if groq_key:
            return "groq"
        if gemini_key:
            return "gemini"
        return "groq"

    async def set_selected_provider(self, provider: str) -> str:
        """
        Update the selected LLM provider ('groq' or 'gemini').
        """
        clean_provider = provider.lower().strip()
        if clean_provider not in ("groq", "gemini"):
            clean_provider = "groq"

        try:
            config = await SystemConfig.find_one({"key": "feedback_llm_provider"})
            if not config:
                config = SystemConfig(key="feedback_llm_provider", value=clean_provider)
            else:
                config.value = clean_provider
            await config.save()
        except Exception as e:
            self.logger.warning(f"Could not persist feedback provider config: {e}")

        return clean_provider

    async def get_provider_status(self) -> Dict[str, Any]:
        """
        Get info about active provider and key configurations.
        """
        current = await self.get_selected_provider()
        groq_key = setting.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
        gemini_key = setting.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")

        return {
            "current_provider": current,
            "available_providers": [
                {"id": "groq", "name": "Groq LPU (Ultra Fast)", "configured": bool(groq_key)},
                {"id": "gemini", "name": "Google Gemini (Flash)", "configured": bool(gemini_key)},
            ],
            "groq_configured": bool(groq_key),
            "gemini_configured": bool(gemini_key),
        }

    def _get_llm(self, provider: str):
        """
        Instantiate the requested LLM instance (Gemini or Groq).
        """
        groq_key = setting.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
        gemini_key = setting.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")

        try:
            if provider == "groq" and groq_key:
                from langchain_groq import ChatGroq
                # Use standard groq models
                model_name = setting.GROQ_MODEL_NAME if "llama" in setting.GROQ_MODEL_NAME else "llama-3.3-70b-versatile"
                return ChatGroq(model=model_name, api_key=groq_key, temperature=0.2)

            if provider == "gemini" and gemini_key:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=setting.GEMINI_MODEL_NAME or "gemini-1.5-flash",
                    google_api_key=gemini_key,
                    temperature=0.2,
                )

            # Fallback to whichever is configured
            if groq_key:
                from langchain_groq import ChatGroq
                return ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key, temperature=0.2)
            if gemini_key:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=gemini_key,
                    temperature=0.2,
                )
        except Exception as e:
            self.logger.warning(f"Could not instantiate LLM ({provider}): {e}")
        return None

    def _rule_based_fallback(
        self, feedback_type: str, title: str, content: str, user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Heuristic analyzer when LLM is offline or fails to respond.
        """
        combined = f"{title} {content}".lower()
        name = user_name or "there"

        critical_keywords = [
            "crash", "broken", "bug", "fail", "error", "loss", "freeze",
            "cannot", "can't", "stuck", "exception", "failed", "down",
            "critical", "urgent", "blank", "unauthorized", "login issue"
        ]
        positive_keywords = [
            "love", "awesome", "great", "thank", "good", "amazing",
            "helpful", "best", "perfect", "appreciate", "like", "wonderful", "kudos"
        ]

        is_critical = any(kw in combined for kw in critical_keywords) or feedback_type == "report"
        is_positive = any(kw in combined for kw in positive_keywords) or feedback_type == "appreciation"

        if is_critical:
            sentiment = "critical"
            severity = "critical" if ("crash" in combined or "loss" in combined or "down" in combined) else "high"
            ai_reply = (
                f"Hi {name}, thank you for alerting us. We have received your bug report with high priority. "
                "Our technical admin team has been notified to investigate and resolve this issue as soon as possible."
            )
            ai_suggested_solution = (
                f"Investigate issue related to '{title}'. Check recent logs, frontend console errors, and API endpoints. "
                "Verify user permissions and payload integrity."
            )
            ai_analysis = f"Critical bug or issue reported regarding '{title}'."
        elif is_positive:
            sentiment = "positive"
            severity = "low"
            ai_reply = (
                f"Hi {name}! Thank you so much for your kind words and appreciation! "
                "Feedback like yours truly motivates our team to make Zen Planner the best daily productivity tool. 🧘✨"
            )
            ai_suggested_solution = (
                "Acknowledge the positive feedback with a personal note from the team and highlight this feature in future updates."
            )
            ai_analysis = f"Positive appreciation from user regarding '{title}'."
        else:
            sentiment = "neutral"
            severity = "medium"
            if feedback_type == "suggestion":
                ai_reply = (
                    f"Hi {name}, thank you for your suggestion! We review all feature requests carefully "
                    "as we plan our upcoming Zen Planner releases and product roadmap."
                )
                ai_suggested_solution = (
                    f"Evaluate suggestion '{title}' against product roadmap priorities and technical feasibility."
                )
            else:
                ai_reply = (
                    f"Hi {name}, thank you for reaching out to us. We have logged your request and our admin team "
                    "will review it shortly."
                )
                ai_suggested_solution = f"Review user request '{title}' and reply with helpful guidance."
            ai_analysis = f"User submitted {feedback_type}: '{title}'."

        return {
            "sentiment": sentiment,
            "severity": severity,
            "is_critical": is_critical,
            "ai_analysis": ai_analysis,
            "ai_reply": ai_reply,
            "ai_suggested_solution": ai_suggested_solution,
        }

    async def process_feedback(
        self,
        feedback_type: str,
        title: str,
        content: str,
        user_name: Optional[str] = None,
        preferred_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze user feedback with AI Agent (Gemini or Groq) to determine sentiment,
        urgency, automated response, and admin triage solutions.
        """
        provider = preferred_provider or await self.get_selected_provider()
        llm = self._get_llm(provider)

        if not llm:
            self.logger.info(f"Using rule-based feedback agent fallback (provider: {provider})")
            return self._rule_based_fallback(feedback_type, title, content, user_name)

        name = user_name or "the user"
        prompt = f"""
You are the AI Feedback & Quality Assurance Agent for "Zen Planner", a modern weekly planning and productivity platform.
Analyze the following user feedback submission and generate a structured JSON assessment.

User Name: {name}
Category: {feedback_type}
Subject: {title}
Message: {content}

Tasks:
1. Determine sentiment: "positive" | "neutral" | "negative" | "critical"
2. Determine severity: "critical" | "high" | "medium" | "low"
3. Flag is_critical (boolean): Set to true if this involves broken features, data loss, crashes, authentication failures, blockers, or security concerns.
4. Short ai_analysis (1-2 sentences): A concise summary of the core issue or sentiment.
5. ai_reply: A warm, empathetic, professional response to the user.
   - If positive/appreciation: Give a warm, inspiring thank-you message celebrating their support and productivity.
   - If critical/bug: Give an immediate reassuring acknowledgment that this has been flagged with high priority to our administrators.
   - If suggestion/idea: Express gratitude for helping shape the platform roadmap.
6. ai_suggested_solution: Actionable technical steps, diagnostic advice, or solution guidance for the administrator to resolve or address this item.

Return strictly a valid JSON object without markdown formatting or code blocks:
{{
  "sentiment": "positive" | "neutral" | "negative" | "critical",
  "severity": "critical" | "high" | "medium" | "low",
  "is_critical": true | false,
  "ai_analysis": "Concise summary",
  "ai_reply": "User-facing message",
  "ai_suggested_solution": "Technical guidance for admin"
}}
"""
        try:
            res = await llm.ainvoke(prompt)
            raw = res.content.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]

            parsed = json.loads(raw.strip())
            return {
                "sentiment": parsed.get("sentiment", "neutral"),
                "severity": parsed.get("severity", "medium"),
                "is_critical": bool(parsed.get("is_critical", False)),
                "ai_analysis": parsed.get("ai_analysis", ""),
                "ai_reply": parsed.get("ai_reply", ""),
                "ai_suggested_solution": parsed.get("ai_suggested_solution", ""),
            }
        except Exception as err:
            self.logger.error(f"Error calling LLM for feedback analysis ({provider}): {err}")
            return self._rule_based_fallback(feedback_type, title, content, user_name)
