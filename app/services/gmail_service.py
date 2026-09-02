import base64
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

    def _extract_body_from_payload(self, payload: Dict[str, Any]) -> str:
        """
        Extract plain text or HTML body from a Gmail message payload.
        """
        body_data = payload.get("body", {}).get("data")
        if body_data:
            try:
                return base64.urlsafe_b64decode(body_data.encode("ascii")).decode("utf-8", errors="replace")
            except Exception:
                pass

        parts = payload.get("parts", [])
        text_plain = ""
        text_html = ""

        def walk_parts(subparts):
            nonlocal text_plain, text_html
            for part in subparts:
                mime = part.get("mimeType", "").lower()
                data = part.get("body", {}).get("data")
                if data:
                    try:
                        decoded = base64.urlsafe_b64decode(data.encode("ascii")).decode("utf-8", errors="replace")
                        if mime == "text/plain" and not text_plain:
                            text_plain = decoded
                        elif mime == "text/html" and not text_html:
                            text_html = decoded
                    except Exception:
                        pass
                if part.get("parts"):
                    walk_parts(part.get("parts"))

        walk_parts(parts)
        return text_plain or text_html or ""

    def _parse_message_data(
        self, data: Dict[str, Any], default_date: str, include_body: bool = False
    ) -> Dict[str, Any]:
        msg_id = data.get("id", "")
        snippet = data.get("snippet", "")
        payload = data.get("payload", {})
        label_ids = data.get("labelIds", [])
        headers_list = payload.get("headers", [])

        subject = "No Subject"
        sender = "Unknown Sender"
        msg_date = default_date

        for h in headers_list:
            name = h.get("name", "").lower()
            if name == "subject":
                subject = h.get("value", "No Subject")
            elif name == "from":
                sender = h.get("value", "Unknown Sender")
            elif name == "date":
                msg_date = h.get("value", default_date)

        result = {
            "id": msg_id,
            "sender": sender,
            "subject": subject,
            "snippet": snippet,
            "date": msg_date,
            "is_unread": "UNREAD" in label_ids,
            "labels": label_ids,
        }

        if include_body:
            extracted_body = self._extract_body_from_payload(payload)
            result["body"] = extracted_body if extracted_body else snippet

        return result

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
                    raw_list.append(self._parse_message_data(detail_resp.json(), today_str))

        return raw_list

    async def fetch_all_messages(
        self, user: User, max_results: int = 25, query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all recent emails from user's Gmail inbox with optional search query.
        """
        access_token = await self.get_access_token(user)
        today_str = date.today().strftime("%Y/%m/%d")

        if access_token:
            params = f"maxResults={min(max_results, 50)}"
            if query:
                params += f"&q={query}"
            messages_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?{params}"

            raw_list = []
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                list_resp = await client.get(messages_url, headers=headers)
                if list_resp.status_code == 200:
                    msg_ids = list_resp.json().get("messages", [])
                    for item in msg_ids[:max_results]:
                        msg_id = item.get("id")
                        detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=full"
                        detail_resp = await client.get(detail_url, headers=headers)
                        if detail_resp.status_code == 200:
                            raw_list.append(self._parse_message_data(detail_resp.json(), today_str))
                    if raw_list:
                        return raw_list

        # Realistic fallback demo emails if disconnected, demo mode, or empty inbox
        demo_emails = [
            {
                "id": "demo-email-1",
                "sender": "Sarah Connor <sarah@cyberdyne.io>",
                "subject": "Urgent: Project Review & Final Specs Submission Today",
                "snippet": "Please submit the final specs and code review for the weekly planner module by 4:00 PM today.",
                "date": date.today().isoformat(),
                "is_unread": True,
                "labels": ["INBOX", "UNREAD", "IMPORTANT"],
            },
            {
                "id": "demo-email-2",
                "sender": "Alex Mercer <alex@acme.org>",
                "subject": "Schedule Sync Meeting for Strategy Discussion",
                "snippet": "Hi, let's schedule a 30 min sync at 2:00 PM today to review customer feedback.",
                "date": date.today().isoformat(),
                "is_unread": True,
                "labels": ["INBOX", "UNREAD"],
            },
            {
                "id": "demo-email-3",
                "sender": "Weekly Digest <newsletter@tech.io>",
                "subject": "Top 10 Tech News This Week",
                "snippet": "Read our weekly digest on latest AI breakthroughs and framework releases...",
                "date": date.today().isoformat(),
                "is_unread": False,
                "labels": ["INBOX"],
            },
            {
                "id": "demo-email-4",
                "sender": "Cloud Provider <billing@cloud.net>",
                "subject": "Monthly Invoice Notification",
                "snippet": "Your monthly invoice #98234 is ready for download. Amount: $0.00.",
                "date": date.today().isoformat(),
                "is_unread": False,
                "labels": ["INBOX"],
            },
            {
                "id": "demo-email-5",
                "sender": "Design Team <design@creative.co>",
                "subject": "Updated Figma Mockups for Mobile Layout",
                "snippet": "Hey team, the responsive mobile mockups for the dashboard and inbox cards have been uploaded.",
                "date": date.today().isoformat(),
                "is_unread": True,
                "labels": ["INBOX", "UNREAD"],
            },
            {
                "id": "demo-email-6",
                "sender": "Security Alerts <noreply@accounts.google.com>",
                "subject": "Security checkup completed successfully",
                "snippet": "No security issues were found on your linked Google account during the regular checkup.",
                "date": date.today().isoformat(),
                "is_unread": False,
                "labels": ["INBOX"],
            },
        ]

        if query:
            q_lower = query.lower()
            demo_emails = [
                e for e in demo_emails
                if q_lower in e["subject"].lower() or q_lower in e["sender"].lower() or q_lower in e["snippet"].lower()
            ]

        return demo_emails

    async def fetch_message_by_id(self, user: User, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single email message with its full body content.
        """
        access_token = await self.get_access_token(user)
        today_str = date.today().strftime("%Y/%m/%d")

        if access_token:
            detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=full"
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                detail_resp = await client.get(detail_url, headers=headers)
                if detail_resp.status_code == 200:
                    return self._parse_message_data(detail_resp.json(), today_str, include_body=True)

        # Realistic bodies for demo messages
        demo_bodies = {
            "demo-email-1": (
                "Hi Team,\n\n"
                "Please make sure to submit the final specifications and your code review for the weekly "
                "planner module by 4:00 PM today. Let me know if you hit any blockers so we can resolve "
                "them immediately.\n\n"
                "Best regards,\nSarah Connor"
            ),
            "demo-email-2": (
                "Hi,\n\n"
                "Let's schedule a 30-minute sync at 2:00 PM today to review customer feedback and roadmap "
                "priorities for the upcoming sprint.\n\n"
                "Looking forward to our chat,\nAlex Mercer"
            ),
            "demo-email-3": (
                "Here is your weekly digest of top tech headlines, AI breakthroughs, and developer tool updates.\n\n"
                "1. Fast inference with Groq LPU\n"
                "2. Full-stack Python & FastAPI patterns\n"
                "3. React performance tips for dashboard apps\n\n"
                "Enjoy reading!\nTech.io Editorial Team"
            ),
            "demo-email-4": (
                "Hello,\n\n"
                "Your monthly cloud hosting invoice #98234 has been generated. Total balance due is $0.00.\n"
                "No further payment action is needed.\n\n"
                "Thank you for choosing Cloud Provider."
            ),
            "demo-email-5": (
                "Hey team,\n\n"
                "The responsive mockups for mobile layout and desktop inbox view are now published on Figma. "
                "Please review the design tokens and component specs, and leave any comments before tomorrow.\n\n"
                "Design Team"
            ),
            "demo-email-6": (
                "A routine security checkup was completed on your linked account. All authentication keys "
                "and permissions are in good standing.\n\n"
                "Google Security Team"
            ),
        }

        demo_emails = await self.fetch_all_messages(user, max_results=50)
        for em in demo_emails:
            if em.get("id") == message_id:
                em_copy = dict(em)
                em_copy["body"] = demo_bodies.get(message_id, em.get("snippet", ""))
                return em_copy

        # If not found in demo list, return basic structured message
        return {
            "id": message_id,
            "sender": "Sender <sender@example.com>",
            "subject": f"Email Details ({message_id})",
            "snippet": "Details for this email message.",
            "body": f"This is the email body for message ID: {message_id}",
            "date": today_str,
            "is_unread": False,
            "labels": ["INBOX"],
        }

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
