import asyncio
import locale
import logging
from datetime import datetime, timedelta
from io import BytesIO

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import *
from matplotlib import pyplot as plt

from settings import TELEGRAM_TOKEN
from weather import get_weather_by_city, get_weather_by_location, get_hourly_forecast

# Отладочная информация
logging.basicConfig(level=logging.INFO)

# Русский язык для даты
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


class WeatherStates(StatesGroup):
    waiting_for_city = State()
    waiting_for_type = State()


@dp.message_handler(commands=['start', 'help'], state='*')
async def weather_help(message: Message):
    await message.answer(
        'Приветствую! Введите /weather чтобы получить погоду.',
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message_handler(commands=['weather'], state='*')
async def select_city(message: Message):
    """Предложить выбрать город или текущее месторасположение."""
    location_button = KeyboardButton(
        'Отправить моё месторасположение', request_location=True
    )
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(location_button)

    await message.answer(
        'Введите город:',
        reply_markup=keyboard,
    )
    await WeatherStates.waiting_for_city.set()


@dp.message_handler(content_types=[ContentType.TEXT, ContentType.LOCATION],
                    state=WeatherStates.waiting_for_city)
async def select_type(message: Message, state: FSMContext):
    """Сохранить месторасположение и предложить выбрать опцию."""
    if message.location:
        await state.update_data(location=message.location)
    elif message.text:
        await state.update_data(city=message.text)
    else:
        await message.answer('Пожалуйста, введите город:')
        return
    buttons = [
        InlineKeyboardButton(
            text='Текущая погода', callback_data="weather_current"
        ),
        InlineKeyboardButton(
            text='Прогноз погоды на 48 часов', callback_data='weather_forecast_hours'
        )
    ]
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(*buttons)
    await message.answer('Выберите нужную опцию:', reply_markup=keyboard)
    await WeatherStates.waiting_for_type.set()


@dp.callback_query_handler(text='weather_current', state=WeatherStates.waiting_for_type)
async def send_current_weather(call: CallbackQuery, state: FSMContext):
    """Отправить текущую погоду."""
    data = await state.get_data()
    if 'location' in data:
        location = data['location']
        weather = get_weather_by_location(location.latitude, location.longitude)
    else:
        weather = get_weather_by_city(data['city'])

    if weather['cod'] != 200:
        await call.message.answer(
            'Произошла ошибка! Проверьте правильность ввода или попробуйте позже.'
        )
        await WeatherStates.waiting_for_city.set()
        await call.answer()
        return

    temp = round(weather['main']['temp'])
    temp_feels_like = round(weather['main']['feels_like'])
    description = weather['weather'][0]['description']
    city_name = weather['name']
    wind_sleep = weather['wind']['speed']
    humidity = weather['main']['humidity']
    pressure = round(weather['main']['pressure'] * 0.75006156)  # в миллиметры ртутного столба
    text = f'<u>Погода в городе <b>{city_name}</b></u>:\n' \
           f'{temp}°C, {description}\n' \
           f'Ощущается как {temp_feels_like}°C\n' \
           f'Скорость ветра {wind_sleep} м/с\n' \
           f'Влажность {humidity}%\n' \
           f'Атмосферное давление {pressure} мм'
    await call.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())
    await call.answer()


@dp.callback_query_handler(text='weather_forecast_hours', state=WeatherStates.waiting_for_type)
async def send_weather_forecast_hours(call: CallbackQuery, state: FSMContext):
    """Отправить прогноз погоды на 48 часов."""
    data = await state.get_data()

    # Получить координаты
    if 'location' in data:
        latitude = data['location'].latitude
        longitude = data['location'].longitude
    else:
        weather = get_weather_by_city(data['city'])
        if weather['cod'] != 200:
            await call.message.answer(
                'Произошла ошибка! Проверьте правильность ввода или попробуйте позже.'
            )
            await WeatherStates.waiting_for_city.set()
            await call.answer()
            return
        latitude = weather['coord']['lat']
        longitude = weather['coord']['lon']

    forecast = get_hourly_forecast(latitude, longitude)
    timezone_offset = forecast['timezone_offset']
    times = []
    dates = []
    temps = []

    for elem in forecast['hourly']:
        dt = datetime.utcfromtimestamp(elem['dt']) + timedelta(seconds=timezone_offset)
        temp = round(elem['temp'])
        times.append(dt.strftime('%H:%M'))
        dates.append(dt.strftime('%d %B'))
        temps.append(temp)

    plt.figure(figsize=(12, 6))
    plt.style.use('seaborn-darkgrid')
    plt.bar(range(len(temps)), temps)
    plt.xticks(range(len(temps)), times, rotation=60)
    plt.xlabel('Время')
    plt.ylabel('Температура, °C')
    plt.title(f'Прогноз погоды на 48 часов ({dates[0]} - {dates[-1]})')
    plt.margins(x=0.01)
    plt.tight_layout()
    image = BytesIO()
    plt.savefig(image, format='png')
    image.seek(0)

    await call.message.answer_photo(image, reply_markup=ReplyKeyboardRemove())
    await call.answer()


@dp.message_handler(lambda m: True)
async def unknown_command(message: Message):
    await message.reply('Неизвестная команда. Введите /weather чтобы получить погоду.')


async def set_commands(bot: Bot):
    """Зарегистрировать команды для отображения в телеграме."""
    commands = [
        BotCommand(command='/start', description='Запустить бота'),
        BotCommand(command='/help', description='Помощь'),
        BotCommand(command='/weather', description='Запросить погоду')
    ]
    await bot.set_my_commands(commands)


async def main():
    await set_commands(bot)
    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
