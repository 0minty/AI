from lib import *


async def base():
    async with aiosqlite.connect('base.db') as conn:
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            lang TEXT
        )
        ''')
        await conn.commit()


bot = Bot(token_tg, default=DefaultBotProperties(parse_mode='html'), request_timeout=60)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sticker = 'CAACAgIAAxkBAAENcX5neP0tad22z4LYMZ67O-ARd-jUbwACBQADwDZPE_lqX5qCa011NgQ'
start_text = 'Я AI и могу помочь вам выучить или подтянуть знания в области иностранного языка.\nОтправьте мне вопрос в этот чат или создайте задание на грамматику и я постараюсь помочь вам! '

languages = [
    {"en": "🇺🇸Английский"},
    {"ru": "🇷🇺Русский"},
    {"fr": "🇫🇷Французский"},
    {"tr": "🇹🇷Турецкий"},
    {"de": "🇩🇪Немецкий"},
    {"it": "🇮🇹Итальянский"},
    {"pt": "🇵🇹Португальский"}
]


class FMSuser(StatesGroup):
    mes = State()
    user_gen = State()
    user_check_response = State()
    user_check_response_generate = State()


async def first(user_id):
    async with aiosqlite.connect('base.db') as conn:
        await conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await conn.commit()


@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    async with aiosqlite.connect('base.db') as conn:
        user_id = message.from_user.id
        await first(user_id)
        cursor = await conn.cursor()
        await cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        user_lang = await cursor.fetchone()
        if user_lang[0]:
            kb = [
                [types.InlineKeyboardButton(text='✨Создать задание на грамматику', callback_data='grammar')],
                [types.InlineKeyboardButton(text='🔄Сменить изучаемый язык', callback_data='change_lang')]
            ]
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
            await bot.send_sticker(message.chat.id, sticker=sticker)
            await cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
            user_lang = await cursor.fetchone()
            for lang in languages:
                if user_lang[0] in lang:
                    lang_user = lang[user_lang[0]]
            old_mes = await bot.send_message(message.chat.id,
                                             text=f'{start_text}\n\nСейчас выбран: <b>{lang_user}</b> язык.',
                                             reply_markup=keyboard)
            await state.update_data(mes=old_mes)
        else:
            kb = [[types.InlineKeyboardButton(text=lang[next(iter(lang))], callback_data=f'lang_{next(iter(lang))}')]
                  for lang in languages]
            keyboard_lang = types.InlineKeyboardMarkup(inline_keyboard=kb)

            await bot.send_sticker(message.chat.id, sticker=sticker)
            old_mes = await bot.send_message(message.chat.id, text='Выберите язык который вы хотите изучить',
                                             reply_markup=keyboard_lang)
            await state.update_data(mes=old_mes)


@dp.callback_query(F.data.startswith('lang_'))
async def select_language(callback: types.CallbackQuery, state: FSMContext):
    kb = [
        [types.InlineKeyboardButton(text='В меню', callback_data='back')]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    lang_code = callback.data.split('_')[1]
    user_id = callback.from_user.id
    async with aiosqlite.connect('base.db') as conn:
        await conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang_code, user_id))
        await conn.commit()

    selected_lang = next(lang[lang_code] for lang in languages if lang_code in lang)
    data = await state.get_data()
    old_mes = data.get('mes')
    old_mes = await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=old_mes.message_id,
                                          text=f"Вы выбрали язык: <b>{selected_lang}</b>. Теперь вы можете задавать вопросы или создавать задания на этом языке!",
                                          reply_markup=keyboard)
    await state.update_data(mes=old_mes)
    await callback.answer()


@dp.callback_query(F.data == 'change_lang')
async def change_languages(callback: types.CallbackQuery, state: FSMContext):
    kb = [[types.InlineKeyboardButton(text=lang[next(iter(lang))], callback_data=f'lang_{next(iter(lang))}')]
          for lang in languages]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    data = await state.get_data()
    old_mes = data.get('mes')
    old_mes = await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=old_mes.message_id,
                                          text='Выберите язык который вы хотите изучить',
                                          reply_markup=keyboard)
    await state.update_data(mes=old_mes)
    await callback.answer()


@dp.callback_query(F.data == 'grammar')
async def generate_grammar(callback: types.CallbackQuery, state: FSMContext):
    kb = [
        [types.InlineKeyboardButton(text='💡Проверить задание', callback_data='check_task')],
        [types.InlineKeyboardButton(text='✅Выполнил(а)', callback_data='back')]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    data = await state.get_data()
    old_mes = data.get('mes')
    old_mes = await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=old_mes.message_id,
                                          text='✨Генерирую задание...')
    await state.update_data(mes=old_mes)
    user_id = callback.from_user.id
    async with aiosqlite.connect('base.db') as conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        user_lang = await cursor.fetchone()
        for lang in languages:
            if user_lang[0] in lang:
                lang_user = lang[user_lang[0]]
        response_text = f"Привет! Придумай мне задание на грамматику из 5 пунктов и выдели их жирным шрифтом на {lang_user} языке."

        ai_response = await generate_ai(response_text=response_text)
        await state.update_data(user_check_response=ai_response)
        processed_response = '\n'.join([
            f"<code>{line.lstrip('```').strip()}</code>" if line.strip().startswith('```') else
            f"<b>{line.replace('*', '').strip()}</b>" if '**' in line or '*' in line else
            f"<i>{line.lstrip('#').strip()}</i>" if line.strip().startswith('###') else
            line
            for line in ai_response.split('\n')
        ])
        try:
            old_mes = await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=old_mes.message_id,
                                                  text=processed_response, reply_markup=keyboard)
            await state.update_data(mes=old_mes)
        except Exception as e:
            old_mes = await bot.send_message(chat_id=callback.message.chat.id,
                                             text=processed_response, reply_markup=keyboard)
            await state.update_data(mes=old_mes)
        await callback.answer()


@dp.callback_query(F.data == 'check_task')
async def check_user_task(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    kb = [
        [types.InlineKeyboardButton(text='❌Отмена', callback_data='back')]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    old_mes = data.get('mes')
    old_mes = await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=old_mes.message_id,
                                          text='📝Отправьте выполненное задание на проверку (только текст):',
                                          reply_markup=keyboard)
    await state.update_data(old_mes=old_mes)
    await state.set_state(FMSuser.user_check_response_generate)


@dp.message(FMSuser.user_check_response_generate)
async def check_user_task_ai(message: types.Message, state: FSMContext):
    kb = [
        [types.InlineKeyboardButton(text='✅Выполнил(а)', callback_data='back')]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    data = await state.get_data()
    old_mes = data.get('mes')
    task_message = message.text
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await bot.edit_message_text(chat_id=message.chat.id, message_id=old_mes.message_id, text='✨Проверяю задание...')
    await state.update_data(old_mes=old_mes)
    user_ai_check = data.get('user_check_response')
    print(f'_____________________\n{user_ai_check}\n_______________________')
    mes = await generate_ai(
        f'Проверь мое задание. Поясни ответ на русском языке и дай правильный ответ или исправь ошибки с пояснением. Вот задание: {user_ai_check}\n Мой ответ на задание: {task_message}')
    processed_response = '\n'.join([
        f"<code>{line.lstrip('```').strip()}</code>" if line.strip().startswith('```') else
        f"<b>{line.replace('*', '').strip()}</b>" if '**' in line or '*' in line else
        f"<i>{line.lstrip('#').strip()}</i>" if line.strip().startswith('###') else
        line
        for line in mes.split('\n')
    ])
    await bot.edit_message_text(chat_id=message.chat.id, message_id=old_mes.message_id, text=f'{processed_response}',
                                reply_markup=keyboard)
    await state.update_data(old_mes=old_mes)
    await state.set_state()


@dp.callback_query(F.data == 'back')
async def back_menu(callback: types.CallbackQuery, state: FSMContext):
    async with aiosqlite.connect('base.db') as conn:
        user_id = callback.from_user.id
        cursor = await conn.cursor()
        data = await state.get_data()
        old_mes = data.get('mes')
        await cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        user_lang = await cursor.fetchone()
        for lang in languages:
            if user_lang[0] in lang:
                lang_user = lang[user_lang[0]]
        if user_lang[0]:
            kb = [
                [types.InlineKeyboardButton(text='✨Создать задание на грамматику', callback_data='grammar')],
                [types.InlineKeyboardButton(text='🔄Сменить изучаемый язык', callback_data='change_lang')]
            ]
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
            old_mes = await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=old_mes.message_id,
                                                  text=f'{start_text}\n\nСейчас выбран: <b>{lang_user}</b> язык.',
                                                  reply_markup=keyboard)
            await state.set_state()
            await state.update_data(mes=old_mes)
            await callback.answer()


@dp.message(FMSuser.user_gen)
async def stop_mes(message: types.Message, state: FSMContext):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    old_mes = await bot.send_message(chat_id=message.chat.id, text='❗️Подождите, ваш запрос обрабатывается...')
    await state.update_data(mes=old_mes)


@dp.message(Command('us'))
async def adm_user(message: types.Message):
    user_id = message.from_user.id
    if user_id in ID_ADM:
        async with aiosqlite.connect('base.db') as conn:
            cursor = await conn.cursor()
            await cursor.execute('SELECT COUNT(user_id) FROM users')
            result = await cursor.fetchone()
            count = result[0]
            await bot.send_message(message.chat.id, f'Кол-во пользователей: {count}')


@dp.message()
async def generate_response(message: types.Message, state: FSMContext):
    async with aiosqlite.connect('base.db') as conn:
        await state.set_state(FMSuser.user_gen)
        data = await state.get_data()
        old_mes = data.get('mes')
        old_mes = await bot.edit_message_text(chat_id=message.chat.id, message_id=old_mes.message_id,
                                              text='✨Генерирую задание...')
        await state.update_data(mes=old_mes)
        user_id = message.from_user.id
        cursor = await conn.cursor()
        data = await state.get_data()
        old_mes = data.get('mes')
        await cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        user_lang = await cursor.fetchone()
        for lang in languages:
            if user_lang[0] in lang:
                lang_user = lang[user_lang[0]]
        response = message.text
        response_text = f"Привет! представь что ты мой репетитор {lang_user} языку, сам я знаю только Русский язык и пиши название задания только на Русском языке. Помоги мне справиться с проблемой {response}"
        ai_response = await generate_ai(response_text=response_text)
        processed_response = '\n'.join([
            f"<code>{line.lstrip('```').strip()}</code>" if line.strip().startswith('```') else
            f"<b>{line.replace('*', '').strip()}</b>" if '**' in line or '*' in line else
            f"<i>{line.lstrip('#').strip()}</i>" if line.strip().startswith('###') else
            line
            for line in ai_response.split('\n')
        ])
        kb = [
            [types.InlineKeyboardButton(text='В меню', callback_data='back')]
        ]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            old_mes = await bot.edit_message_text(chat_id=message.chat.id, message_id=old_mes.message_id,
                                                  text=processed_response, reply_markup=keyboard)
            await state.clear()
            await state.update_data(mes=old_mes)
        except Exception as e:
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            old_mes = await bot.send_message(chat_id=message.chat.id,
                                             text=processed_response, reply_markup=keyboard)
            await state.clear()
            await state.update_data(mes=old_mes)


async def generate_ai(response_text):
    model = "mistral-small-2409"
    client = Mistral(api_key=token_ai)
    txt = ''

    retries = 33
    delay = 1

    for attempt in range(1, retries + 1):
        try:
            response = await client.chat.stream_async(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": response_text,
                    },
                ],
            )
            async for chunk in response:
                if chunk.data.choices[0].delta.content is not None:
                    txt += chunk.data.choices[0].delta.content
            return txt

        except Exception as e:
            if "Status 429" in str(e):
                print(
                    f"Попытка {attempt}/{retries}: Ошибка 429 - превышен лимит запросов. Ожидание {delay} секунд перед повторной попыткой...")
                await asyncio.sleep(delay)
            else:
                raise e

    raise Exception("Превышено число повторных попыток из-за ошибки 429 (превышен лимит запросов).")


async def main():
    while True:
        try:
            await bot.delete_webhook(True)
            await base()
            await dp.start_polling(bot, skip_updates=True)
        except TelegramNetworkError as e:
            print(f"Ошибка соединения: {e}")
            await asyncio.sleep(5)

        except TelegramRetryAfter as a:
            print(f"Лимит запросов. Перезапуск {a.retry_after} секунд")
            await asyncio.sleep(a.retry_after)


if __name__ == "__main__":
    asyncio.run(main())
