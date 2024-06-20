
from settings import bot

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message


from src.panels.addons.keyboards import check_subscribe_list
from src.panels.addons.config import channel_ids, admin_ids


need_to_pay: dict[str, list[int]] = {}
need_to_pay_prize: dict[str, list[int]] = {}


def get_need_to_pay() -> Dict[str, list[int]]:
    return need_to_pay

def get_need_to_pay_prize() -> Dict[str, list[int]]:
    return need_to_pay_prize

class SubChannelCheckPrize(BaseMiddleware):
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
        ) -> Any:
        
        global need_to_pay_prize
        print('[PRIZES] New message from: {} text: {}'.format(event.from_user.username, event.text))
        try:
            
            if event.text and event.text.startswith('/start '):
                need_to_pay_prize[event.from_user.id] = [event.text[7:]]
            
            if not all(
                [
                    (await bot.get_chat_member(chat_id=cid, user_id=event.from_user.id)).status in
                    ("creator", "administrator", "member")
                    for cid in channel_ids
                ]
            ):
                await bot.send_message(
                    chat_id=event.from_user.id,
                    text='Вы не подписаны на некоторые каналы. Подпишитесь для дальнейшего доступа к боту:\n\n' + '— ' + '\n— '.join(channel_ids),
                    reply_markup=check_subscribe_list
                )
                return
        except Exception as e:
            print(e)
            print('[ WARN! ] Необходимо добавить бота в каналы, в которых производится проверка участников!\n' * 5)
        
        await handler(event, data)
        return


class AdminFilter:

    def __init__(self, admin_ids: list[int]):
        self.admin_ids = admin_ids

    def check(self, message: Message) -> bool:
        user_id = message.from_user.id
        print(f'<AdminFilter> Checking user ID: {user_id}')
        return user_id in self.admin_ids

    def __call__(self, message: Message) -> bool:
        return self.check(message)
