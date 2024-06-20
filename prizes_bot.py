import asyncio
import logging
import os
import random
import json
import string
import time
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from aiogram.types import FSInputFile
from aiogram.filters import CommandStart
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from settings import crypto
from middlewares import SubChannelCheckPrize, get_need_to_pay_prize, AdminFilter
from src.panels.addons import keyboards, util
from src.panels.addons.config import bot_prize_link, channel_ids, prize_token, admin_ids
from src.panels.addons.states import *
from aiogram import F
import random

admin_filter = AdminFilter(admin_ids)
char_set = string.ascii_letters + string.digits + "!@#$%&*()_+-=[]{}|;:,.<>?/"
REF_REWARD = 5
DATABASE_PLAYERS = 'database/prizes_bot/players.json'

bot = Bot(prize_token)
dp = Dispatcher()

prizes: dict[str, float] = {}
players: dict[str, dict[str, int | str]] = {}

generated_tickets = set()

prize_distribution = {
    1: 20,
    2: 15,
    3: 12,
    4: 10,
    5: 8,
    6: 7,
    7: 6,
    8: 5,
    9: 4,
    10: 3
}


def generate_lottery_ticket(length=10):
    while True:
        ticket = ''.join(random.choices(char_set, k=length))
        if ticket not in generated_tickets:
            generated_tickets.add(ticket)
            return ticket


def save_if_not_exists(event: types.Message | types.CallbackQuery) -> None:
    if not players.get(str(event.from_user.id)):
        pattern = {
            'username': event.from_user.username,
            'namefamily': event.from_user.first_name,
            'ref': 0,
            'balance': 0,
            'not': 0,
            'lottery_balance': 0,
            'lottery_numbers': [],
            'daily_reward_amount': 1,
            'last_requested_for_daily': None,
            'done_task': 'false'
        }
        players[str(event.from_user.id)] = pattern
        return save_all_data()


def calculate_total_lottery_balance() -> int:
    return sum(player.get('lottery_balance', 0) for player in players.values() if isinstance(player, dict))


async def update_database() -> None:
    global prizes
    global players

    with open(DATABASE_PLAYERS, encoding='utf-8') as f:
        players = json.load(f)
        print('players загружены')

    if any(k not in players for k in ('total_balance', 'total_lottery_balance')):
        players['total_balance'] = 0
        players['total_lottery_balance'] = 0

    for v in prizes.values():
        if isinstance(v, float) or isinstance(v, int): return

    prizes = {}

    nums = list(range(1, 10_000 + 1))
    random.shuffle(nums)

    num_tg = random.choice(nums)
    prizes[str(num_tg)] = 0.0007777
    nums.remove(num_tg)

    for n in nums:
        prizes[str(n)] = round(random.uniform(0.5, 1.1), 2)

    players['total_lottery_balance'] = calculate_total_lottery_balance()

    save_all_data()


@dp.message(lambda message: message.text in ('Главное меню', 'Начать'))
async def _main_menu(message: types.Message):
    return await message.answer(
        '⌨ Главное меню:',
        reply_markup=keyboards.prizes_list
    )


@dp.callback_query(lambda query: query.data == 'check_sub')
async def _check_sub(callback_query: types.CallbackQuery) -> types.Message | bool:
    if not await util.is_subscribed(callback_query.from_user.id, bot, channel_ids):
        print('not')
        with suppress(Exception):
            return await bot.edit_message_text(
                chat_id=callback_query.from_user.id,
                message_id=callback_query.message.message_id,
                text=(
                        'Вы до сих пор не подписаны на некоторые каналы.\n\n'
                        'Проверьте данные каналы: ' + ', '.join(channel_ids)
                ),
                reply_markup=keyboards.check_subscribe_list
            )
        return await callback_query.answer('Вы ещё не подписались!', show_alert=True)

    await bot.delete_message(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id
    )

    save_if_not_exists(callback_query)

    need_to_pay = get_need_to_pay_prize().get(callback_query.from_user.id)
    if need_to_pay:
        if players[str(callback_query.from_user.id)].get('already_ref', False):
            await callback_query.answer("⚠ Вы уже активировали чьё-то приглашение!")
        elif not players.get(need_to_pay[0]):
            await callback_query.answer('⚠ Игрока, пригласившего вас, не существует.')
        elif int(need_to_pay[0]) == callback_query.from_user.id:
            await callback_query.answer('⚠ Вы не можете переходить по своей же реферальной ссылке!')
        else:
            await bot.send_message(
                chat_id=need_to_pay[0],
                text=f'👥 У вас новый реферал ID: {callback_query.from_user.id}, ваш бонус {REF_REWARD} 🎟 уже на вашем счету!'
            )
            players[str(callback_query.from_user.id)]['already_ref'] = True
            ref_p = players[need_to_pay[0]]
            ref_p['balance'] += REF_REWARD
            ref_p['ref'] += 1

            save_all_data()

    return await bot.send_message(
        chat_id=callback_query.from_user.id,
        text='Проверка пройдена успешно. Приятного пользования ботом! ✅',
        reply_markup=keyboards.prizes_list
    )


@dp.message(CommandStart())
async def start(message: types.Message) -> None:
    save_if_not_exists(message)

    if len(message.text) > 6:
        ref_id = message.text[7:]
        if players[str(message.chat.id)].get('already_ref', False):
            await message.answer("⚠ Вы уже активировали чьё-то приглашение!")
        elif not players.get(ref_id):
            await message.answer('⚠ Игрока, пригласившего вас, не существует.')
        elif int(ref_id) == message.from_user.id:
            await message.answer('⚠ Вы не можете переходить по своей же реферальной ссылке!')
        else:
            await bot.send_message(
                chat_id=ref_id,
                text=f'👥 У вас новый реферал ID: {message.chat.id}, ваш бонус {REF_REWARD} 🎟 уже на вашем счету!'
            )
            players[str(message.chat.id)]['already_ref'] = True
            ref_p = players[ref_id]
            ref_p['balance'] += REF_REWARD
            ref_p['ref'] += 1

            save_all_data()

    await message.answer(
        f'Приветствую, {message.from_user.first_name}! В этом боте нет возни с заработком 0.0000 NOT. Всё или ничего! Ежедневно проходит '
        'лотерея с 10 призовыми местами и ты можешь обменять свою удачу на NOT уже сегодня! Просто получай ежедневные лотерейные билеты '
        'и меняй их для участия в розыгрыше монет. Вывод выигрыша происходит автоматически через Crypto Bot, поэтому забирай его когда тебе будет удобно! '
        'Так же не забывай ежедневно проверять раздел задания и рейды. Это поможет тебе значительно увеличить шансы на победу на ежедневной основе!'
    )

    await message.answer(
        "⌨ Главное меню:",
        reply_markup=keyboards.prizes_list
    )


@dp.message(lambda message: message.text == '💳 Вывод')
async def _vivod(message: types.Message) -> types.Message:
    if players[str(message.from_user.id)].get('not', 0) < 1:
        return await message.answer('Вывод доступен от баланса 1 и выше! ⛔')

    transfer = crypto.transfer(
        message.from_user.id, 'NOT', str(players[str(message.from_user.id)]['not']),
        '{} {}'.format(
            message.from_user.id,
            datetime.strftime(datetime.now(), '%H-%M-%S-%d.%m')
        )
    )

    if not transfer['ok'] and transfer['error']['name'] == 'USER_NOT_FOUND':
        return await message.answer('Для вывода средств Вам необходимо иметь аккаунт в @CryptoBot ⛔')

    if transfer['ok']:
        players[str(message.from_user.id)]['not'] = 0
        return await message.answer('Средства поступят на Ваш кошелёк в течении минуты. Ожидайте ✅')

    print(transfer['error'])
    return await message.answer('Произошла непредвиденная ошибка. Повторите попытку позже :( 💥')


@dp.message(lambda message: message.text == 'Получить больше 🎟')
async def _referal_system(message: types.Message) -> types.Message:
    up = players[str(message.chat.id)]
    return await message.answer(
        f'''💰 Получайте за каждого приглашенного друга {REF_REWARD} 🎟.

👤 Количество рефералов: {up["ref"]}
🎯 Заработано 🎟: {REF_REWARD * int(up["ref"])}

— Ваша ссылка для приглашения: {bot_prize_link.format(message.from_user.id)}'''
    )


@dp.message(lambda message: message.text == 'Статистика ℹ')
async def _stats(message: types.Message) -> types.Message:
    return await message.answer(
        f"""👤 Всего игроков: {len(players) - 5} чел
💰 Всего заработано: {players.get('total_balance', 'Неизвестно.. ⛔')}
📦 Всего потрачено билетов: {players.get('total_lottery_balance', 'Неизвестно.. ⛔')}
        """
    )


@dp.message(lambda message: message.text == 'Рейды')
async def _lotery(message: types.Message):
    text = players['raides']['text']
    img_path = players['raides']['img']

    img = FSInputFile(img_path)

    await message.answer_photo(photo=img, caption=text)


@dp.message(lambda message: message.text == 'Профиль 🤑')
async def _profile(message: types.Message):
    user = players.get(str(message.from_user.id))
    if not user: return await message.answer('⚡ Произошла ошибка. Попробуйте ввести команду /start')

    return await message.answer(
        f"🏷 Ваш ID: {message.from_user.id}\n\nБаланс билетов: {user.get('balance', 0)} 🎟\n"
        f"NOT: {user.get('not', 0)} \n"
        f"Баланс лотерейных билетов: {user.get('lottery_balance', 0)}\n",
        reply_markup=keyboards.vivod_list
    )


def save_all_data() -> None:
    with open(DATABASE_PLAYERS, 'w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False, indent=4)


async def exchange_tickets(user_id: str, num_tickets: int):
    players[user_id]["lottery_balance"] += num_tickets
    players[user_id]["balance"] -= num_tickets

    players['total_lottery_balance'] += num_tickets
    save_all_data()


@dp.message(lambda message: message.text == 'Лотерея 🎟')
async def lottery_handler(message: types.Message):
    sum = players['bank_balance']
    message1 = (f'Приветствуем тебя в нашей лотерее! Суть лотереи проста – ты можешь обменять свой 1 билет на 1 '
                f'лотерейный билет текущего розыгрыша. Каждый билет = 1 шанс на победу. Каждому обменянному билету '
                f'присваивается порядковый номер и ровно в 20:00 выбираются номера победителей. '
                f'После розыгрыша обменянные билеты сгорают. '
                f'Общий банк: {sum}\n'
                f'Распределение призов:\n'
                f'1-е место: {prize_distribution[1]}% ({sum * prize_distribution[1] / 100} NOT.)\n'
                f'2-е место: {prize_distribution[2]}% ({sum * prize_distribution[2] / 100} NOT)\n'
                f'3-е место: {prize_distribution[3]}% ({sum * prize_distribution[3] / 100} NOT)\n'
                f'4-е место: {prize_distribution[4]}% ({sum * prize_distribution[4] / 100} NOT)\n'
                f'5-е место: {prize_distribution[5]}% ({sum * prize_distribution[5] / 100} NOT.)\n'
                f'6-е место: {prize_distribution[6]}% ({sum * prize_distribution[6] / 100} NOT)\n'
                f'7-е место: {prize_distribution[7]}% ({sum * prize_distribution[7] / 100} NOT)\n'
                f'8-е место: {prize_distribution[8]}% ({sum * prize_distribution[8] / 100} NOT)\n'
                f'9-е место: {prize_distribution[9]}% ({sum * prize_distribution[9] / 100} NOT)\n'
                f'10-е место: {prize_distribution[10]}% ({sum * prize_distribution[10] / 100} NOT)\n')
    await message.answer(message1, reply_markup=keyboards.lot)


@dp.callback_query(lambda query: query.data.startswith('show_tickets'))
async def asks(callback_query: types.CallbackQuery, state: FSMContext):
    user = players.get(str(callback_query.from_user.id))
    lottery_numbers = user.get("lottery_numbers", [])
    lottery_numbers_str = "\n".join(map(str, lottery_numbers))
    if not user: return await callback_query.answer('⚡ Произошла ошибка. Попробуйте ввести команду /start')

    return await callback_query.message.answer(
        f'Ваши лотерейные лоты на сегодняшний розыгрыш: \n {lottery_numbers_str}\n',
    )


@dp.callback_query(lambda query: query.data.startswith('exchange_tickets'))
async def process_exchange_tickets(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(ExchangeTicketsStates.waiting_for_tickets)

    await bot.send_message(callback_query.from_user.id, "Сколько билетов вы хотите обменять?")


@dp.message(ExchangeTicketsStates.waiting_for_tickets)
async def exchange_tickets_message_handler(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)

    try:
        num_tickets = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return await state.clear()

    user_balance = players[user_id]['balance']
    if num_tickets > user_balance:
        await message.answer("У вас недостаточно билетов для обмена.")
        return await state.clear()
    if num_tickets < 0:
        return await message.answer('Введи положительное число')
    await exchange_tickets(user_id, num_tickets)
    for i in range(players[user_id]['lottery_balance']):
        gen_tick = generate_lottery_ticket()
        players[user_id]['lottery_numbers'].append(gen_tick)
    players[user_id]['lottery_balance'] -= num_tickets
    save_all_data()

    await state.clear()
    await message.answer(f"Вы успешно обменяли {num_tickets} билетов.", reply_markup=keyboards.prizes_list)


@dp.message(lambda message: message.text == 'Ежедневные билеты 🎟')
async def _dailyticket(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)

    last_requested = players[user_id]['last_requested_for_daily']

    if last_requested:
        current_time = datetime.now()
        time_since_last_request = current_time - datetime.strptime(last_requested, '%Y-%m-%d %H:%M:%S.%f')

        if time_since_last_request < timedelta(hours=24):
            time_left = timedelta(hours=24) - time_since_last_request
            hours_left = time_left.seconds // 3600
            minutes_left = (time_left.seconds % 3600) // 60
            seconds_left = time_left.seconds % 60
            await message.answer(
                f"Вы уже получили ежедневные билеты. Попробуйте позже через {hours_left} часов {minutes_left} минут {seconds_left} секунд.")
            return

    await message.answer(f'''Каждые 24 часа ты можешь бесплатно получить ежедневные билеты для участия в лотерее!
        Перед получением рекомендуем проверить раздел задания, так как при их выполнении ежедневное количество билетов увеличивается!
        Для получения бонуса нажимай кнопку ниже. Вы получите {players[user_id]['daily_reward_amount']}
    ''', reply_markup=keyboards.daily)
    await state.set_state(DailyTicketsStates.REQUESTED)


@dp.callback_query(lambda query: query.data == 'get_daily_tickets', DailyTicketsStates.REQUESTED)
async def process_get_daily_tickets(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer("Вы получили ежедневные билеты!")
    user_id = str(callback_query.from_user.id)

    if user_id in players:
        players[user_id]['balance'] += players[user_id]['daily_reward_amount']
        current_time = datetime.now()
        players[user_id]['last_requested_for_daily'] = current_time.strftime('%Y-%m-%d %H:%M:%S.%f')

    await state.clear()
    save_all_data()


############################################################################################

@dp.message(lambda message: message.text == '/admin')
async def admin_panel(message: types.Message, state: FSMContext):
    if not admin_filter(message):
        return await message.answer('Доступ запрещен!')
    else:
        return await message.answer('Успешно вошли в админку', reply_markup=keyboards.admin_list)


@dp.message(lambda message: message.text == 'Добавить баланс')
async def _addbalance(message: types.Message, state: FSMContext):
    await message.answer('Введите ID пользователя для добавления баланса.')
    await state.set_state(AddBalance.ID)


@dp.message(AddBalance.ID)
async def process_addbalance(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    await state.update_data(user_id=user_id)
    if players.get(user_id):
        await state.set_state(AddBalance.AMOUNT)
        await message.answer('Введите сумму для добавления на баланс.')

    else:
        await message.answer(f'Пользователь с ID {user_id} не найден ')
        await state.clear()


@dp.message(AddBalance.AMOUNT)
async def process_addbalance_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
    except Exception as e:
        await message.answer('Введите корректное число для добавления на баланс.')
        await state.clear()

    data = await state.get_data()
    user_id = data['user_id']

    players[user_id]['not'] += amount
    save_all_data()

    await state.clear()
    await message.answer(f'Сумма {amount} успешно добавлена на баланс пользователя {user_id}.')


@dp.message(lambda message: message.text == 'Снять баланс')
async def _decreasebalance(message: types.Message, state: FSMContext):
    await message.answer('Введите ID пользователя для списания с баланса.')
    await state.set_state(DEACREASE.ID)


@dp.message(DEACREASE.ID)
async def process_decreasebalance(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    await state.update_data(user_id=user_id)
    if players[user_id]:

        await state.set_state(DEACREASE.AMOUNT)
        await message.answer('Введите сумму для списания с баланса.')
    else:
        await message.answer(f'Пользователь с ID {user_id} не найден ')
        await state.clear()


@dp.message(DEACREASE.AMOUNT)
async def process_decreasebalance_amount(message: types.Message, state: FSMContext):
    global a
    try:
        a = int(message.text)
    except ValueError:
        await message.answer('Введите корректное число для списания с баланса.')
        await state.clear()

    data = await state.get_data()
    user_id = data['user_id']

    players[user_id]['not'] -= a
    save_all_data()

    await state.clear()
    await message.answer(f'Сумма {a} успешно списана с баланса пользователя {user_id}.')


@dp.message(lambda message: message.text == 'Изменить призовой банк в лотерее')
async def _changebnkbalance(message: types.Message, state: FSMContext):
    await message.answer('Ведите сумму банка в NOT')
    await state.set_state(AdminStates.ChangingPrizeBank)


@dp.message(AdminStates.ChangingPrizeBank)
async def process_changing_bank_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        players['bank_balance'] = amount
        await state.clear()
        save_all_data()
        await message.answer('Успешно поменяли призовой бюджет')
    except Exception as e:
        await message.answer(f'Введите правильно значение. Ошибка {e}')
        await state.clear()
        return


@dp.message(lambda message: message.text == 'Удалить каналы из заданий')
async def _delchannel(message: types.Message, state: FSMContext):
    players['task_channels'] = []
    save_all_data()
    await message.answer('Каналы удалены из списка заданий')


@dp.message(lambda message: message.text == 'Добавить канал в задания')
async def _addchannel(message: types.Message, state: FSMContext):
    await message.answer('Введите ссылку на канал/каналы используя такой синтаксис\n'
                         '@channel,@channel2\n'
                         'Если один канал то просто отправьте название с @')
    await state.set_state(AdminStates.AddingTaskChannel)


@dp.message(AdminStates.AddingTaskChannel)
async def process_task_channel(message: types.Message, state: FSMContext):
    channel_names = [channel.strip() for channel in message.text.split(',')]
    id_list = [key for key in players.keys() if key.isdigit()]
    added_channels = []
    for channel_name in channel_names:
        if not channel_name.startswith('@'):
            await message.answer(f"Ошибка: Канал {channel_name} должен начинаться с '@'.")
            await state.clear()

        added_channels.append(channel_name)

    if not added_channels:
        await message.answer("Вы не указали ни одного канала.")
        await state.clear()
        return

    print(added_channels)

    players['task_channels'] += added_channels
    save_all_data()
    await message.answer(f"Добавлены каналы: {', '.join(added_channels)}")
    await state.clear()
    for i in id_list:
        if players[str(i)]['done_task'] == 'true':
            players[str(i)]['done_task'] = 'false'
            save_all_data()


@dp.message(lambda message: message.text == 'Сменить текст раздела рейды')
async def _raides_change_text(message: types.Message, state: FSMContext):
    await message.answer('Введите текст рейда')
    await state.set_state(ModifyRaides.SETTEXT)


@dp.message(ModifyRaides.SETTEXT)
async def _set_raides_text(message: types.Message, state: FSMContext):
    players['raides']['text'] = message.text
    save_all_data()
    await message.answer('Отправьте фото рейда')
    await state.set_state(ModifyRaides.SETIMAGE)


@dp.message(ModifyRaides.SETIMAGE, F.photo)
async def _set_raides_image(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_path = file_info.file_path

    directory = "images"
    if not os.path.exists(directory):
        os.makedirs(directory)

    destination = f"{directory}/{file_path.split('/')[-1]}"
    await bot.download_file(file_path, destination)

    players['raides']['img'] = destination
    await state.clear()
    save_all_data()
    await message.reply("Изображение раздела рейды обновлено.")


def extract_lottery_info(data):
    lottery_data = []
    for user_id, user_info in data.items():
        if user_id not in ["total_balance", "total_lottery_balance", "task_channels", "raides", "bank_balance"]:
            if "lottery_numbers" in user_info:
                lottery_data.append({
                    "username": user_info["username"],
                    "id": user_id,
                    "lottery_numbers": user_info["lottery_numbers"]
                })
    return lottery_data


def get_top_10_lottery_numbers(lottery_numbers):
    if len(lottery_numbers) < 10:
        print("Not enough lottery numbers for top 10")
        return []
    return random.sample(lottery_numbers, 10)


async def send_lottery_ended_message():
    id_list = [key for key in players.keys() if key.isdigit()]
    all_lottery = extract_lottery_info(players)
    top = get_top_10_lottery_numbers(all_lottery)
    if not top:
        return

    total_bank = players["bank_balance"]
    message = f'Лотерея закончилась!\n\nТоп 10:\n'
    for idx, user in enumerate(top):
        place = idx + 1
        percentage = prize_distribution.get(place, 0)
        prize = (total_bank * percentage) / 100
        message += f"- Имя: {user['username']}, ID: {user['id']}, Приз: {prize}\n"
        players[user['id']]['not'] = players.get(user['id'], {}).get('not', 0) + prize
        save_all_data()

    for i in id_list:
        await bot.send_message(chat_id=i, text=message)

    for i in id_list:
        players[str(i)]['lottery_numbers'] = []
        save_all_data()


@dp.message(lambda message: message.text == 'Задания 💵')
async def _tasks(message: types.Message, state: FSMContext):
    await message.answer(
        f'Выполняй задания и получай постоянное увеличение ежедневных билетов. За каждое выполненное задание ты будешь получать на 5 билетов больше ежедневно!'
        f'Сейчас ты получаешь {players[str(message.from_user.id)]["daily_reward_amount"]} билетов ежедневно ',
        reply_markup=keyboards.task)


@dp.callback_query(lambda query: query.data == 'start_task')
async def _check_task2(query: types.CallbackQuery):
    a = query.from_user.id
    if players[str(a)]['done_task'] == 'false':
        task_channels = players.get("task_channels", [])
        await query.message.answer('Подпишитесь на данные каналы ' + ', '.join(task_channels),
                                   reply_markup=keyboards.check_subscribe_list2)
    else:
        await query.message.answer('Вы уже выполнили задание с данным каналом, ждите следующее задание')


########################################################################################################################################################################################################


@dp.callback_query(lambda query: query.data == 'check_sub2')
async def _check_sub(callback_query: types.CallbackQuery) -> types.Message | bool:
    channel_id = players['task_channels']
    uid = callback_query.from_user.id
    print(type(channel_id))
    if not await util.is_subscribed(uid, bot, channel_id):
        print('not')
        with suppress(Exception):
            return await bot.edit_message_text(
                chat_id=callback_query.from_user.id,
                message_id=callback_query.message.message_id,
                text=(
                        'Вы до сих пор не подписаны на некоторые каналы.\n\n'
                        'Проверьте данные каналы: ' + ', '.join(channel_id)
                ),
                reply_markup=keyboards.check_subscribe_list2
            )
        return await callback_query.answer('Вы ещё не подписались!', show_alert=True)

    players[str(uid)]['daily_reward_amount'] += 5
    players[str(uid)]['done_task'] = 'true'
    save_all_data()
    await bot.delete_message(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id
    )
    await callback_query.message.answer(f'Успешно выполнено задание! Теперь ваш ежедневный бонус вырос до {players[str(uid)]["daily_reward_amount"]} ')


##################################################


async def main():
    await update_database()
    scheduler = AsyncIOScheduler()
    scheduler.start()
    scheduler.add_job(send_lottery_ended_message, 'cron', hour=23, minute=00)
    logging.basicConfig(level=logging.INFO)
    dp.message.outer_middleware(SubChannelCheckPrize())
    print('[ PRIZES Бот запущен! ]')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
