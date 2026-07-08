from typing import Any, Dict, List

import httpx

from app.core.logger_config import logger as default_logger


class NotificationService:
    def __init__(self, logger=None):
        self.logger = logger or default_logger

    async def send_push_notification(
        self, tokens: List[str], title: str, body: str, data: Dict[str, Any] = None
    ) -> None:
        if not tokens:
            return

        # Expo only accepts tokens starting with ExponentPushToken
        valid_tokens = [t for t in tokens if t.startswith("ExponentPushToken")]
        if not valid_tokens:
            self.logger.warning("No valid Expo Push Tokens provided for notification.")
            return

        url = "https://exp.host/--/api/v2/push/send"
        payload = []
        for token in valid_tokens:
            msg = {
                "to": token,
                "title": title,
                "body": body,
                "sound": "default",
            }
            if data:
                msg["data"] = data
            payload.append(msg)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    self.logger.info(
                        f"Expo notifications API response: {response.json()}"
                    )
                else:
                    self.logger.error(
                        f"Failed to send notifications. Status: {response.status_code}, Body: {response.text}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Exception while sending push notification to Expo: {e}"
                )
