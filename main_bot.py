import asyncio
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

from climate_engine import WeatherEngine
from charting_units import (
    create_single_day_chart,
    create_three_day_chart,
    create_five_day_chart
)

load_dotenv()
BOT_API_TOKEN = os.getenv('TOKEN')
ACCUWEATHER_TOKEN = 'spjsEssJ8EuxFAXimFcaxTYL9XlzyNOT'

bot_instance = Bot(token=BOT_API_TOKEN)
mainDispatcher = Dispatcher()

#состояния бота
class CityStates(StatesGroup):
    cityOfOrigin = State()
    cityOfDestination = State()
    cityStopovers = State()

userRoutes = {}
temperatureCache = {}

#инициализируем сервис
weatherEngine = WeatherEngine(api_key=ACCUWEATHER_TOKEN)

#выводим ошибки
async def userErrorReport(chat_identifier, bot_obj, error_text):
    await bot_obj.send_message(chat_identifier, f'Обнаружена ошибка: {error_text}')

@mainDispatcher.message(F.text == '/start')
async def greet_user(message: types.Message):
    await message.answer(
        'Бот создан для отображения погоды на вашем маршруте. Используйте команду /help чтобы получить инструкцию.'
    )

@mainDispatcher.message(F.text == '/help')
async def help_menu(message: types.Message):
    await message.answer(
        '/weather - комманда для того чтобы узнать погоду на маршруте'
    )

@mainDispatcher.message(F.text == '/weather')
async def begin_weather_flow(message: types.Message, state: FSMContext):
    try:
        userRoutes[message.from_user.id] = []
        await state.set_state(CityStates.cityOfOrigin)
        await message.answer('Введите город отправлеия:')
    except Exception as err:
        await userErrorReport(message.chat.id, bot_instance, err)

@mainDispatcher.message((F.text | F.location), CityStates.cityOfOrigin)
async def ask_destination_city(message: types.Message, state: FSMContext):
    try:
        userRoutes[message.from_user.id].append(message.text.strip())
        await state.set_state(CityStates.cityOfDestination)
        await message.answer('Введите город, являющийся концом маршрута:')
    except Exception as err:
        await userErrorReport(message.chat.id, bot_instance, err)

@mainDispatcher.message((F.text | F.location), CityStates.cityOfDestination)
async def handle_stopovers_question(message: types.Message, state: FSMContext):
    try:
        userRoutes[message.from_user.id].append(message.text.strip())
        markup_stopovers = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='Да', callback_data='wanna_stop'),
            InlineKeyboardButton(text='Нет', callback_data='no_stop')
        ]])
        await state.clear()
        await message.answer(
            'Желаете узнать погоду для промежуточных городов',
            reply_markup=markup_stopovers
        )
    except Exception as err:
        await userErrorReport(message.chat.id, bot_instance, err)

@mainDispatcher.callback_query(F.data == 'wanna_stop')
async def add_stopover_city(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await state.set_state(CityStates.cityStopovers)
        await callback.message.answer('Введите название промежуточного города:')
    except Exception as err:
        await userErrorReport(callback.message.chat.id, bot_instance, err)

#получаем промежуточные города
@mainDispatcher.message(F.text, CityStates.cityStopovers)
async def collect_stopovers(message: types.Message, state: FSMContext):
    try:
        userRoutes[message.from_user.id].append(message.text.strip())
        markup_more_stops = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='Да', callback_data='wanna_stop'),
            InlineKeyboardButton(text='Нет', callback_data='no_stop')
        ]])
        await message.answer(
            'Хотите узнать погоду в еще одном промежуточном городе',
            reply_markup=markup_more_stops
        )
    except Exception as err:
        await userErrorReport(message.chat.id, bot_instance, err)

@mainDispatcher.callback_query(F.data == 'no_stop')
async def choose_forecast_period(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        forecast_markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='1 день', callback_data='forecast_1'),
            InlineKeyboardButton(text='3 дня', callback_data='forecast_3'),
            InlineKeyboardButton(text='5 дней', callback_data='forecast_5')
        ]])
        await callback.message.answer('Выберите желаемый период прогноза:', reply_markup=forecast_markup)
        await state.clear()
    except Exception as err:
        await userErrorReport(callback.message.chat.id, bot_instance, err)

@mainDispatcher.callback_query(F.data == 'forecast_1')
async def forecast_for_one_day(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        temperatureCache[user_id] = {}

        results_message = ''
        for city in userRoutes.get(user_id, []):
            cityKey = weatherEngine.retrieveCityId(city)
            one_day_data = weatherEngine.gatherWeather(cityKey, '1day')
            analysis_result = weatherEngine.evaluate_weather(
                one_day_data['temp'],
                one_day_data['humidity'],
                one_day_data['wind_speed'],
                one_day_data['precipitation_probability']
            )

            if isinstance(analysis_result, str):
                summary, level_info = analysis_result, '—'
            else:
                summary = '. '.join(analysis_result[:-1])
                level_info = analysis_result[-1]

            temperatureCache[user_id][city] = one_day_data['temp']
            results_message += (
                f"Город: {city}\n"
                f"Дата: {one_day_data['date']}\n"
                f"Температура: {one_day_data['temp']}°C\n"
                f"Влажность: {one_day_data['humidity']}%\n"
                f"Скорость ветра: {one_day_data['wind_speed']} км/ч\n"
                f"Вероятность осадков: {one_day_data['precipitation_probability']}%\n"
                f"Анализ: {summary}\n\n"
            )

        await callback.message.answer(results_message)
        userRoutes[user_id] = []

        see_chart_markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='Да', callback_data='show_chart_1'),
            InlineKeyboardButton(text='Нет', callback_data='no_chart')
        ]])
        await callback.message.answer('Показать температуру на графике?', reply_markup=see_chart_markup)
    except Exception as err:
        await userErrorReport(callback.message.chat.id, bot_instance, err)

@mainDispatcher.callback_query(F.data == 'forecast_3')
async def forecast_for_three_days(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        temperatureCache[user_id] = {}

        results_message = ''
        for city in userRoutes.get(user_id, []):
            cityKey = weatherEngine.retrieveCityId(city)
            three_day_data = weatherEngine.gatherWeather(cityKey, '3day')
            temperatureCache[user_id][city] = []

            for day_info in three_day_data:
                daily_analysis = weatherEngine.evaluate_weather(
                    day_info['temp'],
                    day_info['humidity'],
                    day_info['wind_speed'],
                    day_info['precipitation_probability']
                )

                if isinstance(daily_analysis, str):
                    summary, level_info = daily_analysis, '—'
                else:
                    summary = '. '.join(daily_analysis[:-1])
                    level_info = daily_analysis[-1]

                temperatureCache[user_id][city].append((day_info['date'], day_info['temp']))
                results_message += (
                    f"Город: {city}\n"
                    f"Дата: {day_info['date']}\n"
                    f"Температура: {day_info['temp']}°C\n"
                    f"Влажность: {day_info['humidity']}%\n"
                    f"Ветер: {day_info['wind_speed']} км/ч\n"
                    f"Вероятность осадков: {day_info['precipitation_probability']}%\n"
                    f"Анализ: {summary}\n\n"
                )

        await callback.message.answer(results_message)
        userRoutes[user_id] = []

        see_chart_markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='Да', callback_data='display_3_chart'),
            InlineKeyboardButton(text='Нет', callback_data='no_chart')
        ]])
        await callback.message.answer('Показать температуру на графике?', reply_markup=see_chart_markup)
    except Exception as err:
        await userErrorReport(callback.message.chat.id, bot_instance, err)

@mainDispatcher.callback_query(F.data == 'forecast_5')
async def forecast_for_five_days(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        temperatureCache[user_id] = {}

        results_message = ''
        for city in userRoutes.get(user_id, []):
            cityKey = weatherEngine.retrieveCityId(city)
            five_day_data = weatherEngine.gatherWeather(cityKey, '5day')
            temperatureCache[user_id][city] = []

            for day_info in five_day_data:
                daily_analysis = weatherEngine.evaluate_weather(
                    day_info['temp'],
                    day_info['humidity'],
                    day_info['wind_speed'],
                    day_info['precipitation_probability']
                )

                if isinstance(daily_analysis, str):
                    summary, level_info = daily_analysis, '—'
                else:
                    summary = '. '.join(daily_analysis[:-1])
                    level_info = daily_analysis[-1]

                temperatureCache[user_id][city].append((day_info['date'], day_info['temp']))
                results_message += (
                    f"Город: {city}\n"
                    f"Дата: {day_info['date']}\n"
                    f"Температура: {day_info['temp']}°C\n"
                    f"Влажность: {day_info['humidity']}%\n"
                    f"Ветер: {day_info['wind_speed']} км/ч\n"
                    f"Вероятность осадков: {day_info['precipitation_probability']}%\n"
                    f"Анализ: {summary}\n\n"
                )

        await callback.message.answer(results_message)
        userRoutes[user_id] = []

        see_chart_markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='Да', callback_data='display_5_chart'),
            InlineKeyboardButton(text='Нет', callback_data='no_chart')
        ]])
        await callback.message.answer('Показать температуру на графике?', reply_markup=see_chart_markup)
    except Exception as err:
        await userErrorReport(callback.message.chat.id, bot_instance, err)

@mainDispatcher.callback_query(F.data == 'no_chart')
async def no_graphics_response(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        userRoutes[user_id] = []
        temperatureCache[user_id] = {}
        await callback.answer()
        await callback.message.answer('Спасибо за использование бота!')
    except Exception as err:
        await userErrorReport(callback.message.chat.id, bot_instance, err)

@mainDispatcher.callback_query(F.data == 'display_3_chart')
async def display_three_day_chart(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        stored_data = temperatureCache.get(user_id, {})
        if not stored_data:
            raise Exception("Нет достаточных данных для построения графика.")

        chart_path = create_three_day_chart(stored_data)
        image_obj = FSInputFile(path=chart_path)
        await bot_instance.send_photo(chat_id=callback.message.chat.id, photo=image_obj)
        os.remove(chart_path)
    except Exception as err:
        await userErrorReport(callback.message.chat.id, bot_instance, err)

@mainDispatcher.callback_query(F.data == 'display_5_chart')
async def display_five_day_chart(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        stored_data = temperatureCache.get(user_id, {})
        if not stored_data:
            raise Exception("Недостаточно данных для построения графика.")

        chart_path = create_five_day_chart(stored_data)
        image_obj = FSInputFile(path=chart_path)
        await bot_instance.send_photo(chat_id=callback.message.chat.id, photo=image_obj)
        os.remove(chart_path)
    except Exception as err:
        await userErrorReport(callback.message.chat.id, bot_instance, err)

@mainDispatcher.callback_query(F.data == 'show_chart_1')
async def display_single_day_chart(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        stored_data = temperatureCache.get(user_id, {})
        if not stored_data:
            raise Exception("Недостаточно данных для построения графика.")

        city_list = list(stored_data.keys())
        temp_list = list(stored_data.values())

        chart_path = create_single_day_chart(temp_list, city_list)
        image_obj = FSInputFile(path=chart_path)
        await bot_instance.send_photo(chat_id=callback.message.chat.id, photo=image_obj)
        os.remove(chart_path)
    except Exception as err:
        await userErrorReport(callback.message.chat.id, bot_instance, err)

@mainDispatcher.message()
async def unknown_input(message: types.Message):
    await message.answer(
        'Я не понимаю эту комманду. Введите /help чтобы узнать о возможностях'
    )

if __name__ == '__main__':
    async def main_run():
        await mainDispatcher.start_polling(bot_instance)

    asyncio.run(main_run())