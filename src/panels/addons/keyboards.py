from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardButton


def reply_builder(
        text: str | list[str],
        sizes: int | list[int] = 2,
        **kwargs
) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    text = [text] if isinstance(text, str) else text
    sizes = [sizes] if isinstance(sizes, int) else sizes

    [
        builder.button(text=txt)
        for txt in text
    ]

    builder.adjust(*sizes)
    return builder.as_markup(resize_keyboard=True, **kwargs)


admin_list = reply_builder(
    ['Добавить баланс', 'Снять баланс', 'Изменить призовой банк в лотерее',
     'Удалить каналы из заданий', 'Добавить канал в задания', 'Сменить текст раздела рейды','Главное меню'],
    [2,2,2,1]
)

prizes_list = reply_builder(
    ['Статистика ℹ', 'Профиль 🤑', 'Лотерея 🎟', 'Рейды', 'Задания 💵', 'Ежедневные билеты 🎟', 'Получить больше 🎟', ],
    [2, 2, 2]
)

vivod_list = reply_builder(
    ['💳 Вывод', 'Главное меню'],
    1
)

check_subscribe_list = InlineKeyboardBuilder(markup=[
    [InlineKeyboardButton(text='✔ Проверить подписку', callback_data='check_sub')]
]).as_markup()

lot = InlineKeyboardBuilder(markup=[
    [InlineKeyboardButton(text="Обменять билеты", callback_data="exchange_tickets")],
    [InlineKeyboardButton(text="Мои билеты", callback_data="show_tickets")]
]).as_markup()

daily = InlineKeyboardBuilder(markup=[
    [InlineKeyboardButton(text="Получить билеты", callback_data="get_daily_tickets")]
]).as_markup()

task = InlineKeyboardBuilder(markup=[
    [InlineKeyboardButton(text="Начать выполнение заданий", callback_data="start_task")]
]).as_markup()

check_subscribe_list2 = InlineKeyboardBuilder(markup=[
    [InlineKeyboardButton(text='✔ Проверить подписку', callback_data='check_sub2')]
]).as_markup()
