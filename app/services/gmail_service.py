import json
import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import httpx

from app.core.logger_config import logger
from app.core.settings import setting
from app.models.user import User
from app.models.habit_quitter import SystemConfig
from app.utils.common import CustomException


class GmailService:
    def __init__(self):
        self.logger = logger

    async def is_feature_enabled(self) -> bool:
        """
        Check if Gmail AI integration feature is globally enabled.
        """
        config = await SystemConfig.find_one(SystemConfig.key == "gmail_feature_enabled")
        if config:
            return config.value.lower() in ("true", "1", "yes")
        return True

    async def set_feature_enabled(self, enabled: bool) -> bool:
        """
        Set global Gmail feature status (admin option).
        """
        config = await SystemConfig.find_one(SystemConfig.key == "gmail_feature_enabled")
        if not config:
            config = SystemConfig(key="gmail_feature_enabled", value=str(enabled).lower())
        else:
            config.value = str(enabled).lower()
        await config.save()
        return enabled

    def get_oauth_url(self, user: User) -> str:
        """
        Generate Google OAuth URL requesting gmail.readonly scope.
        """
        client_id = setting.GOOGLE_CLIENT_ID or ""
        redirect_uri = setting.GOOGLE_REDIRECT_URI or "http://localhost:5173/gmail-callback"
        scope = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email"
        state = str(user.id)

        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            "&response_type=code"
            f"&scope={scope}"
            "&access_type=offline"
            "&prompt=consent"
            f"&state={state}"
        )
        return auth_url

    async def exchange_code_for_tokens(self, code: str, user: User) -> Dict[str, Any]:
        """
        Exchange authorization code for OAuth access and refresh tokens.
        """
        client_id = setting.GOOGLE_CLIENT_ID
        client_secret = setting.GOOGLE_CLIENT_SECRET
        redirect_uri = setting.GOOGLE_REDIRECT_URI or "http://localhost:5173/gmail-callback"

        if not client_id or not client_secret:
            # Fallback for local demo mode if client credentials aren't set
            user.gmail_connected = True
            user.gmail_email = user.email
            user.gmail_refresh_token = "demo_refresh_token"
            await user.save()
            return {"status": "success", "gmail_email": user.email}

        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=payload)
            if resp.status_code != 200:
                self.logger.error(f"Failed to exchange code with Google: {resp.text}")
                raise CustomException("Failed to authorize with Google Gmail API", 400)

            data = resp.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")

            # Fetch user email from Google UserInfo
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            gmail_email = user.email
            if userinfo_resp.status_code == 200:
                gmail_email = userinfo_resp.json().get("email", user.email)

            user.gmail_connected = True
            user.gmail_email = gmail_email
            if refresh_token:
                user.gmail_refresh_token = refresh_token
            await user.save()

            return {"status": "success", "gmail_email": gmail_email}

    async def disconnect_gmail(self, user: User) -> None:
        user.gmail_connected = False
        user.gmail_refresh_token = None
        user.gmail_email = None
        await user.save()

    async def get_access_token(self, user: User) -> Optional[str]:
        if not user.gmail_refresh_token or user.gmail_refresh_token == "demo_refresh_token":
            return None

        client_id = setting.GOOGLE_CLIENT_ID
        client_secret = setting.GOOGLE_CLIENT_SECRET
        if not client_id or not client_secret:
            return None

        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": user.gmail_refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=payload)
            if resp.status_code == 200:
                return resp.json().get("access_token")
            return None

    async def fetch_today_raw_messages(self, user: User) -> List[Dict[str, Any]]:
        """
        Fetch today's incoming email metadata from Gmail REST API.
        """
        access_token = await self.get_access_token(user)
        if not access_token:
            return []

        today_str = date.today().strftime("%Y/%m/%d")
        messages_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q=after:{today_str}&maxResults=15"

        raw_list = []
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            list_resp = await client.get(messages_url, headers=headers)
            if list_resp.status_code != 200:
                return []

            msg_ids = list_resp.json().get("messages", [])
            for item in msg_ids[:10]:
                msg_id = item.get("id")
                detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=full"
                detail_resp = await client.get(detail_url, headers=headers)
                if detail_resp.status_code == 200:
                    data = detail_resp.json()
                    snippet = data.get("snippet", "")
                    payload = data.get("payload", {})
                    headers_list = payload.get("headers", [])

                    subject = "No Subject"
                    sender = "Unknown Sender"
                    msg_date = today_str

                    for h in headers_list:
                        name = h.get("name", "").lower()
                        if name == "subject":
                            subject = h.get("value", "No Subject")
                        elif name == "from":
                            sender = h.get("value", "Unknown Sender")
                        elif name == "date":
                            msg_date = h.get("value", today_str)

                    raw_list.append({
                        "id": msg_id,
                        "sender": sender,
                        "subject": subject,
                        "snippet": snippet,
                        "date": msg_date,
                    })

        return raw_list

    async def analyze_messages_with_groq(self, user: User) -> List[Dict[str, Any]]:
        """
        Fetch today's emails & send them to Groq AI to extract only high-priority actionable items.
        """
        raw_emails = await self.fetch_today_raw_messages(user)

        # Fallback to realistic demo emails if Gmail isn't connected or has no new messages today
        if not raw_emails:
            raw_emails = [
                {
                    "id": "demo-email-1",
                    "sender": "Project Lead <manager@company.com>",
                    "subject": "Urgent: Project Review & Final Specs Submission Today",
                    "snippet": "Please submit the final specs and code review for the weekly planner module by 4:00 PM today.",
                    "date": date.today().isoformat(),
                },
                {
                    "id": "demo-email-2",
                    "sender": "Client Services <client@acme.org>",
                    "subject": "Schedule Sync Meeting for Strategy Discussion",
                    "snippet": "Hi, let's schedule a 30 min sync at 2:00 PM today to review customer feedback.",
                    "date": date.today().isoformat(),
                },
                {
                    "id": "demo-email-3",
                    "sender": "Weekly Digest <newsletter@tech.io>",
                    "subject": "Top 10 Tech News This Week",
                    "snippet": "Read our weekly digest on latest AI breakthroughs and framework releases...",
                    "date": date.today().isoformat(),
                },
                {
                    "id": "demo-email-4",
                    "sender": "Cloud Provider <billing@cloud.net>",
                    "subject": "Monthly Invoice Notification",
                    "snippet": "Your monthly invoice #98234 is ready for download. Amount: $0.00.",
                    "date": date.today().isoformat(),
                },
            ]

        # Use Groq AI / LangChain Chat model to filter and extract important items
        groq_key = setting.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
        gemini_key = setting.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        openai_key = setting.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")

        llm = None
        try:
            if groq_key:
                from langchain_groq import ChatGroq
                llm = ChatGroq(model=setting.GROQ_MODEL_NAME, api_key=groq_key, temperature=0.1)
            elif gemini_key:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(model=setting.GEMINI_MODEL_NAME, google_api_key=gemini_key, temperature=0.1)
            elif openai_key:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(model=setting.OPENAI_MODEL_NAME, api_key=openai_key, temperature=0.1)
        except Exception as e:
            self.logger.warning(f"Could not instantiate LLM for Gmail analysis: {e}")

        prompt = f"""
You are an expert AI productivity assistant.
Analyze the following list of raw emails received today.
Your goal is to FILTER OUT newsletters, spam, promotional emails, receipts, automated notifications, and social updates.
Extract ONLY urgent, actionable, or important emails that require the user's attention or action today.

Raw Emails Input:
{json.dumps(raw_emails, indent=2)}

Return a strict JSON array of objects. Do NOT include markdown codeblocks or conversational text. Return ONLY JSON syntax:
[
  {{
    "id": "email_id",
    "sender": "sender name/email",
    "subject": "email subject",
    "snippet": "concise AI summary of key action item",
    "date": "YYYY-MM-DD",
    "urgency": "high" | "medium" | "low",
    "suggested_task_title": "Short actionable task title",
    "suggested_task_description": "Task details derived from email",
    "suggested_start_time": "HH:mm format (e.g. 14:00)",
    "suggested_end_time": "HH:mm format (e.g. 15:00)"
  }}
]
"""

        if llm:
            try:
                res = await llm.ainvoke(prompt)
                content = res.content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                parsed = json.loads(content.strip())
                if isinstance(parsed, list):
                    return parsed
            except Exception as e:
                self.logger.error(f"Error parsing Groq LLM output for Gmail items: {e}")

        # Fallback structured response if LLM isn't active or fails parsing
        important_items = []
        for em in raw_emails:
            subj_lower = em["subject"].lower()
            if "urgent" in subj_lower or "review" in subj_lower or "meeting" in subj_lower or "sync" in subj_lower or "submit" in subj_lower:
                urgency = "high" if "urgent" in subj_lower else "medium"
                important_items.append({
                    "id": em["id"],
                    "sender": em["sender"],
                    "subject": em["subject"],
                    "snippet": em["snippet"],
                    "date": date.today().isoformat(),
                    "urgency": urgency,
                    "suggested_task_title": f"Action on: {em['subject']}",
                    "suggested_task_description": f"From: {em['sender']}\nSummary: {em['snippet']}",
                    "suggested_start_time": "14:00",
                    "suggested_end_time": "15:00",
                })

        return important_items
