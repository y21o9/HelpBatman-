import asyncio
import logging
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = 8917408909:AAFf5AM69SXz1MleEOPUkntXtWI4l8S9EPk

SERVICES = {
    "barber": {"name": "✂️ Барбершоп", "price": "от 1500₽"},
    "repair": {"name": "🔧 Ремонт", "price": "от 1000₽"},
    "manicure": {"name": "💅 Маникюр", "price": "от 2000₽"},
    "pedicure": {"name": "🦶 Педикюр", "price": "от 2500₽"}
}

class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()

async def init_db():
    async with aiosqlite.connect('bookings.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, username TEXT, service TEXT, date TEXT, time TEXT
            )
        ''')
        await db.commit()

async def main():
    await init_db()
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        await state.clear()
        builder = InlineKeyboardBuilder()
        for key, value in SERVICES.items():
            builder.button(text=f"{value['name']} ({value['price']})", callback_data=f"service_{key}")
        builder.adjust(1)
        await message.answer("👋 Привет! Выберите услугу:", reply_markup=builder.as_markup())
        await state.set_state(BookingStates.choosing_service)

    @dp.callback_query(F.data.startswith('service_'))
    async def process_service(callback: CallbackQuery, state: FSMContext):
        service_key = callback.data.split('_')[1]
        await state.update_data(service=service_key, service_name=SERVICES[service_key]['name'])
        await callback.message.edit_text(f"✅ {SERVICES[service_key]['name']}\n\n📅 Введите дату (ДД.ММ.ГГГГ):")
        await state.set_state(BookingStates.choosing_date)
        await callback.answer()

    @dp.message(BookingStates.choosing_date)
    async def process_date(message: Message, state: FSMContext):
        try:
            datetime.strptime(message.text, '%d.%m.%Y')
            await state.update_data(date=message.text)
            builder = InlineKeyboardBuilder()
            for t in ["10:00", "12:00", "14:00", "16:00", "18:00"]:
                builder.button(text=t, callback_data=f"time_{t}")
            builder.adjust(3)
            await message.answer(f"📅 Дата: {message.text}\n⏰ Выберите время:", reply_markup=builder.as_markup())
            await state.set_state(BookingStates.choosing_time) # В оригинале была опечатка, исправлено на choosing_time
        except ValueError:
            await message.answer("❌ Формат ДД.ММ.ГГГГ (например, 20.07.2026):")

    @dp.callback_query(F.data.startswith('time_'))
    async def process_time(callback: CallbackQuery, state: FSMContext):
        time = callback.data.split('_')[1]
        await state.update_data(time=time)
        data = await state.get_data()
        user = callback.from_user
        
        async with aiosqlite.connect('bookings.db') as db:
            await db.execute("INSERT INTO bookings (user_id, username, service, date, time) VALUES (?, ?, ?, ?, ?)",
                (user.id, user.username or user.first_name, data['service_name'], data['date'], data['time']))
            await db.commit()

        await callback.message.edit_text(
            f"✅ <b>Запись создана!</b>\n\n"
            f"🛠 {data['service_name']}\n📅 {data['date']}\n⏰ {data['time']}\n\n"
            f"Нажмите /start для новой записи."
        )
        await state.clear()
        await callback.answer()

    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
