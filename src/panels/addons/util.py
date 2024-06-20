import random
import time
import re

from .config import channel_ids

from aiogram import Bot


async def is_subscribed(user: int, bot: Bot, channels: list) -> bool:
    for channel_id in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user)
            print(member.status)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            if "user not found" in str(e):
                return False
            else:
                raise
    return True


