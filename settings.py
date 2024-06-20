
from crypto_pay_api_sdk import Crypto

from aiogram import Bot, Dispatcher
from aiogram.types import LinkPreviewOptions
from aiogram.client.default import DefaultBotProperties

from src.panels.addons.config import token,crypto_token, crypto_token_testnet

bot = Bot(
    token=token,
    default=DefaultBotProperties(link_preview=LinkPreviewOptions(is_disabled=True), parse_mode='HTML')
)
dp = Dispatcher()

crypto = Crypto(
    token=crypto_token_testnet,
    testnet=True
)
