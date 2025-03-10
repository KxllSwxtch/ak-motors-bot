import json
import telebot
import os
import re
import requests
import locale
import logging
import urllib.parse

from bs4 import BeautifulSoup
from io import BytesIO
from telebot import types
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from utils import (
    generate_encar_photo_url,
    clean_number,
    get_customs_fees,
    calculate_age,
    format_number,
    get_customs_fees_manual,
)

CALCULATE_CAR_TEXT = "Рассчитать Автомобиль (Encar, KBChaCha, ChutCha)"

load_dotenv()
bot_token = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(bot_token)

# Set locale for number formatting
locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

# Storage for the last error message ID
last_error_message_id = {}

# global variables
car_data = {}
car_id_external = ""
total_car_price = 0
krw_rub_rate = 0
rub_to_krw_rate = 0
usd_rate = 0
users = set()
user_data = {}

car_month = None
car_year = None

vehicle_id = None
vehicle_no = None

usd_to_krw_rate = 0
usd_to_rub_rate = 0

usdt_to_krw_rate = 0


################## КОД ДЛЯ СТАТУСОВ
# Храним заказы пользователей
user_orders = {
    7311646338: [
        {
            "id": "38947857",
            "title": "Hyundai Tucson N Line Inspiration",
            "price": "₩31,900,000",
            "link": "https://fem.encar.com/cars/detail/38947857",
            "year": "23",
            "month": "01",
            "mileage": "24,054 км",
            "engine_volume": 1998,
            "transmission": "Автомат",
            "first_name": "Дмитрий",
            "last_name": "Шин",
            "user_name": "@dmitriyshin99",
            "phone_number": "821065763105",
            "images": [
                "https://ci.encar.com//carpicture04/pic3894/38941549_019.jpg",
                "https://ci.encar.com//carpicture04/pic3894/38941549_022.jpg",
                "https://ci.encar.com//carpicture04/pic3894/38941549_024.jpg",
                "https://ci.encar.com//carpicture04/pic3894/38941549_007.jpg",
                "https://ci.encar.com//carpicture04/pic3894/38941549_008.jpg",
                "https://ci.encar.com//carpicture04/pic3894/38941549_018.jpg",
                "https://ci.encar.com//carpicture04/pic3894/38941549_001.jpg",
                "https://ci.encar.com//carpicture04/pic3894/38941549_015.jpg",
                "https://ci.encar.com//carpicture04/pic3894/38941549_003.jpg",
                "https://ci.encar.com//carpicture04/pic3894/38941549_017.jpg",
            ],
            "status": "🕒 Ожидает подтверждения",
            "total_cost_usd": 39781.206119598035,
            "total_cost_krw": 58852316.33333334,
            "total_cost_rub": 3580308.550763823,
        },
        {
            "id": "38343298",
            "title": "Porsche Cayenne ",
            "price": "₩135,500,000",
            "link": "https://fem.encar.com/cars/detail/38343298",
            "year": "22",
            "month": "12",
            "mileage": "27,706 км",
            "engine_volume": 2995,
            "transmission": "Автомат",
            "first_name": "Дмитрий",
            "last_name": "Шин",
            "user_name": "@dmitriyshin99",
            "phone_number": "821065763105",
            "images": [
                "https://ci.encar.com//carpicture04/pic3834/38342004_001.jpg",
                "https://ci.encar.com//carpicture04/pic3834/38342004_018.jpg",
                "https://ci.encar.com//carpicture04/pic3834/38342004_001.jpg",
                "https://ci.encar.com//carpicture04/pic3834/38342004_010.jpg",
                "https://ci.encar.com//carpicture04/pic3834/38342004_020.jpg",
                "https://ci.encar.com//carpicture04/pic3834/38342004_001.jpg",
                "https://ci.encar.com//carpicture04/pic3834/38342004_024.jpg",
                "https://ci.encar.com//carpicture04/pic3834/38342004_015.jpg",
                "https://ci.encar.com//carpicture04/pic3834/38342004_001.jpg",
                "https://ci.encar.com//carpicture04/pic3834/38342004_023.jpg",
            ],
            "status": "🕒 Ожидает подтверждения",
            "total_cost_usd": 146560.792765382,
            "total_cost_krw": 216763412.5,
            "total_cost_rub": 13190471.348884381,
        },
    ]
}
user_contacts = {}

MANAGERS = [728438182]

ORDER_STATUSES = {
    "1": "🚗 Авто выкуплен (на базе)",
    "2": "🚢 Отправлен в порт г. Пусан на погрузку",
    "3": "🌊 В пути во Владивосток",
    "4": "🛃 Таможенная очистка",
    "5": "📦 Погрузка до МСК",
    "6": "🚛 Доставляется клиенту",
}


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_favorite_"))
def add_favorite_car(call):
    global car_data
    user_id = call.message.chat.id

    if not car_data or "name" not in car_data:
        bot.answer_callback_query(
            call.id, "🚫 Ошибка: Данные о машине отсутствуют.", show_alert=True
        )
        return

    if user_id not in user_orders:
        user_orders[user_id] = []

    car_info = {
        "id": car_data.get("car_id", "Нет ID"),
        "title": car_data.get("name", "Неизвестно"),
        "price": f"₩{format_number(car_data.get('car_price', 0))}",
        "link": car_data.get("link", "Нет ссылки"),
        "year": car_data.get("year", "Неизвестно"),
        "month": car_data.get("month", "Неизвестно"),
        "mileage": car_data.get("mileage", "Неизвестно"),
        "fuel": car_data.get("fuel", "Неизвестно"),
        "engine_volume": car_data.get("engine_volume", "Неизвестно"),
        "transmission": car_data.get("transmission", "Неизвестно"),
        "images": car_data.get("images", []),
        "status": "🔄 Не заказано",
        "total_cost_usd": car_data.get("total_cost_usd", 0),
        "total_cost_krw": car_data.get("total_cost_krw", 0),
        "total_cost_rub": car_data.get("total_cost_rub", 0),
    }

    user_orders[user_id].append(car_info)
    bot.answer_callback_query(
        call.id, "⭐ Автомобиль добавлен в избранное!", show_alert=True
    )


@bot.message_handler(commands=["my_cars"])
def show_favorite_cars(message):
    user_id = message.chat.id

    # Проверяем, есть ли у пользователя сохранённые авто
    if user_id not in user_orders or not user_orders[user_id]:
        bot.send_message(user_id, "❌ У вас нет сохранённых автомобилей.")
        return

    for car in user_orders[user_id]:
        car_id = car.get("id", "Неизвестно")
        car_title = car.get("title", "Неизвестно")
        car_status = car.get("status", "🔄 Не заказано")
        car_link = car.get("link", "Нет ссылки")
        car_year = car.get("year", "Неизвестно")
        car_month = car.get("month", "Неизвестно")
        car_mileage = car.get("mileage", "Неизвестно")
        car_engine_volume = car.get("engine_volume", "Неизвестно")
        car_transmission = car.get("transmission", "Неизвестно")
        total_cost_usd = car.get("total_cost_usd", 0)
        total_cost_krw = car.get("total_cost_krw", "")
        total_cost_rub = car.get("total_cost_rub", "")

        # Формируем текст сообщения
        response_text = (
            f"🚗 *{car_title} ({car_id})*\n\n"
            f"📅 {car_month}/{car_year} | ⚙️ {car_transmission}\n"
            f"🔢 Пробег: {car_mileage} | 🏎 Объём: {car_engine_volume} cc\n\n"
            f"Стоимость авто под ключ:\n"
            f"${format_number(total_cost_usd)} | ₩{format_number(total_cost_krw)} | {format_number(total_cost_rub)} ₽\n\n"
            f"📌 *Статус:* {car_status}\n\n"
            f"[🔗 Ссылка на автомобиль]({car_link})"
        )

        # Создаём клавиатуру
        keyboard = types.InlineKeyboardMarkup()

        # Кнопка "Заказать" только для незакзанных авто
        if car_status == "🔄 Не заказано":
            keyboard.add(
                types.InlineKeyboardButton(
                    f"📦 Заказать {car_title}",
                    callback_data=f"order_car_{car_id}",
                )
            )

        bot.send_message(
            user_id, response_text, parse_mode="Markdown", reply_markup=keyboard
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("order_car_"))
def order_car(call):
    user_id = call.message.chat.id
    car_id = call.data.split("_")[-1]  # Получаем ID авто из callback_data

    # Проверяем контактные данные
    user = call.from_user
    username = user.username
    phone_number = user_contacts.get(user_id)  # Теперь берём номер из user_contacts

    if not username and not phone_number:
        # Если нет данных – запрашиваем телефон
        bot.send_message(
            user_id, "📞 Укажите ваш контактный номер телефона для связи с менеджером."
        )

        # Сохраняем ожидание ввода телефона
        user_contacts[user_id] = car_id

        # Отправляем кнопку запроса номера телефона
        keyboard = types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True
        )
        keyboard.add(
            types.KeyboardButton("📱 Отправить номер телефона", request_contact=True)
        )
        bot.send_message(
            user_id,
            "Нажмите на кнопку ниже, чтобы отправить номер телефона:",
            reply_markup=keyboard,
        )
    else:
        # Данные есть – оформляем заказ
        process_order(user_id, car_id, username, phone_number)


# Обработчик получения номера телефона
@bot.message_handler(content_types=["contact"])
def receive_phone_number(message):
    user_id = message.chat.id

    # Проверяем, ожидаем ли номер телефона от этого пользователя
    if user_id in user_contacts:
        phone_number = message.contact.phone_number  # Получаем номер телефона
        car_id = user_contacts.pop(user_id)  # Получаем ID авто, которое хотели заказать

        # Сохраняем номер телефона в user_contacts
        user_contacts[user_id] = phone_number

        bot.send_message(user_id, "✅ Спасибо! Ваш номер телефона сохранён.")

        # Запускаем процесс оформления заказа
        process_order(user_id, car_id, message.from_user.username, phone_number)


# Функция оформления заказа
def process_order(user_id, car_id, username, phone_number):
    # Достаём авто из списка
    car = next(
        (car for car in user_orders.get(user_id, []) if car["id"] == car_id), None
    )

    if not car:
        bot.send_message(user_id, "❌ Ошибка: автомобиль не найден.")
        return

    car_title = car.get("title", "Неизвестно")
    car_link = car.get("link", "Нет ссылки")

    # Менеджер, которому отправлять заявку
    manager_chat_id = MANAGERS[0]  # Здесь нужно указать ID менеджера

    # Сообщение менеджеру
    manager_text = (
        f"📢 *Новый заказ на автомобиль!*\n\n"
        f"🚗 {car_title}\n"
        f"🔗 [Ссылка на автомобиль]({car_link})\n\n"
        f"🔹 Username: @{username if username else 'Не указан'}\n"
        f"📞 Телефон: {phone_number if phone_number else 'Не указан'}\n"
    )

    bot.send_message(manager_chat_id, manager_text, parse_mode="Markdown")

    # Обновляем статус авто
    car["status"] = "🕒 Ожидает подтверждения"
    bot.send_message(
        user_id,
        f"✅ Ваш заказ на {car_title} оформлен! Менеджер скоро свяжется с вами.",
    )


@bot.message_handler(commands=["orders"])
def show_orders(message):
    manager_id = message.chat.id

    # Проверяем, является ли пользователь менеджером
    if manager_id not in MANAGERS:
        bot.send_message(manager_id, "❌ У вас нет доступа к заказам.")
        return

    # Проверяем, есть ли заказы
    if not user_orders:
        bot.send_message(manager_id, "📭 Нет активных заказов.")
        return

    # Перебираем всех пользователей и их заказы
    for user_id, orders in user_orders.items():
        for order in orders:
            car_title = order.get("title", "🚗 Автомобиль")
            car_link = order.get("link", "Нет ссылки")
            user_name = order.get("first_name", "Неизвестный")
            phone_number = order.get("phone_number", "Неизвестно")
            car_status = order.get("status", "🔄 Не заказано")
            car_price = order.get("price", "💰 Цена неизвестна")
            car_mileage = order.get("mileage", "❓ Пробег неизвестен")
            car_engine = order.get("engine_volume", "❓ Объём неизвестен")
            car_transmission = order.get("transmission", "❓ КПП неизвестно")
            car_images = order.get("images", [])

            # Формируем текст карточки
            response_text = (
                f"🚗 *{car_title}*\n"
                f"💰 Цена: {car_price}\n"
                f"📅 Пробег: {car_mileage}\n"
                f"🏎 Объём двигателя: {car_engine} cc\n"
                f"⚙️ КПП: {car_transmission}\n"
                f"📌 *Статус:* {car_status}\n\n"
                f"👤 Заказчик: [{user_name}](tg://user?id={user_id})\n"
                f"📞 Номер телефона: {phone_number}\n"
                f"[🔗 Ссылка на авто]({car_link})"
            )

            # Создаём клавиатуру с кнопкой "Обновить статус"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    f"📌 Обновить статус",
                    callback_data=f"update_status_{user_id}_{order['id']}",
                )
            )

            bot.send_message(
                manager_id,
                response_text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )


@bot.callback_query_handler(func=lambda call: call.data.startswith("update_status_"))
def update_order_status(call):
    manager_id = call.message.chat.id
    order_id = call.data.split("_")[-1]

    print(f"🔍 Менеджер {manager_id} пытается обновить статус заказа {order_id}")

    order_found = None
    user_id_found = None

    # Ищем заказ среди всех пользователей
    for user_id, orders in user_orders.items():
        for order in orders:
            if str(order["id"]) == str(order_id):
                order_found = order
                user_id_found = user_id
                break
        if order_found:
            break

    if not order_found:
        print(f"❌ Ошибка: заказ {order_id} не найден!")
        bot.answer_callback_query(call.id, "❌ Ошибка: заказ не найден.")
        return

    # 🔥 Генерируем короткие callback_data (код статуса вместо строки)
    keyboard = types.InlineKeyboardMarkup()
    for status_code, status_text in ORDER_STATUSES.items():
        keyboard.add(
            types.InlineKeyboardButton(
                status_text,
                callback_data=f"set_status_{user_id_found}_{order_id}_{status_code}",
            )
        )

    bot.send_message(manager_id, "📌 Выберите новый статус:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("set_status_"))
def set_new_status(call):
    manager_id = call.message.chat.id

    print(f"🔄 Получен `callback_data`: {call.data}")  # Логирование данных

    # Разбиваем callback_data на 5 частей (берём 4 после "set_status")
    data_parts = call.data.split("_", 4)

    if len(data_parts) < 5:
        print(
            f"❌ Ошибка: callback_data имеет некорректный формат: {data_parts}"
        )  # Лог
        bot.answer_callback_query(call.id, "❌ Ошибка: неверный формат данных.")
        return

    _, _, user_id, order_id, status_code = data_parts  # Теперь корректное разбиение

    if not user_id.isdigit():
        print(f"❌ Ошибка: user_id некорректный: {user_id}")  # Лог
        bot.answer_callback_query(call.id, "❌ Ошибка: неверный ID пользователя.")
        return

    user_id = int(user_id)

    # Проверяем, существует ли этот код статуса
    if status_code not in ORDER_STATUSES:
        print(f"❌ Ошибка: неверный код статуса: {status_code}")  # Лог
        bot.answer_callback_query(call.id, "❌ Ошибка: неверный статус.")
        return

    new_status = ORDER_STATUSES[status_code]  # Получаем текст статуса по коду

    print(
        f"🔄 Менеджер {manager_id} меняет статус заказа {order_id} для {user_id} на {new_status}"
    )  # Логирование

    # Проверяем, существует ли заказ у пользователя
    if user_id not in user_orders:
        print(f"❌ Ошибка: у пользователя {user_id} нет заказов!")  # Лог
        bot.answer_callback_query(call.id, "❌ Ошибка: у пользователя нет заказов.")
        return

    order_found = None
    for order in user_orders[user_id]:
        if str(order["id"]) == str(order_id):  # Приводим к строке для сравнения
            order_found = order
            break

    if not order_found:
        print(f"❌ Ошибка: заказ {order_id} не найден!")  # Лог
        bot.answer_callback_query(call.id, "❌ Ошибка: заказ не найден.")
        return

    # Обновляем статус
    order_found["status"] = new_status

    # Уведомляем клиента
    bot.send_message(
        user_id,
        f"📢 *Обновление статуса заказа!*\n\n"
        f"🚗 [{order_found['title']}]({order_found['link']})\n"
        f"📌 Новый статус: *{new_status}*",
        parse_mode="Markdown",
    )

    # Подтверждение менеджеру
    bot.answer_callback_query(call.id, f"✅ Статус обновлён на {new_status}!")

    # Автоархивация завершённых заказов
    archive_completed_orders()

    # Обновляем список заказов у менеджеров
    show_orders(call.message)


@bot.callback_query_handler(func=lambda call: call.data.startswith("place_order_"))
def place_order(call):
    user_id = call.message.chat.id
    order_id = call.data.split("_")[-1]

    # Проверяем, есть ли этот заказ
    if order_id not in user_orders:
        bot.answer_callback_query(call.id, "❌ Ошибка: заказ не найден.")
        return

    order = user_orders[order_id]

    # Создаём кнопку "Обновить статус" (только для менеджеров)
    keyboard = types.InlineKeyboardMarkup()
    if user_id in MANAGERS:
        keyboard.add(
            types.InlineKeyboardButton(
                "📌 Обновить статус", callback_data=f"update_status_{order_id}"
            )
        )

    bot.send_message(
        user_id,
        f"📢 *Заказ оформлен!*\n\n"
        f"🚗 [{order['title']}]({order['link']})\n"
        f"👤 Клиент: [{order['user_name']}](tg://user?id={order['user_id']})\n"
        f"📌 *Текущий статус:* {order['status']}",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    bot.answer_callback_query(call.id, "✅ Заказ отправлен менеджерам!")


def archive_completed_orders():
    global user_orders
    completed_orders = []

    # Проверяем все заказы всех пользователей
    for user_id, orders in user_orders.items():
        for order in orders:
            if (
                order["status"] == "🚛 Доставляется клиенту"
            ):  # ✅ Проверяем как элемент списка
                completed_orders.append(order)

        # Убираем завершённые заказы из активных
        user_orders[user_id] = [
            order for order in orders if order["status"] != "🚛 Доставляется клиенту"
        ]

    print(f"📦 Архивировано {len(completed_orders)} заказов")  # Логирование


################## КОД ДЛЯ СТАТУСОВ


def print_message(message):
    print("\n\n##############")
    print(f"{message}")
    print("##############\n\n")
    return None


# Функция для установки команд меню
def set_bot_commands():
    commands = [
        types.BotCommand("start", "Запустить бота"),
        types.BotCommand("cbr", "Курсы валют"),
        types.BotCommand("my_cars", "Мои избранные автомобили"),
        types.BotCommand("orders", "Список заказов"),
    ]

    # Проверяем, является ли пользователь менеджером
    user_id = bot.get_me().id
    if user_id in MANAGERS:
        commands.extend(
            [
                types.BotCommand("orders", "Просмотр всех заказов (для менеджеров)"),
            ]
        )

    bot.set_my_commands(commands)


def get_usdt_to_krw_rate():
    global usdt_to_krw_rate

    # URL для получения курса USDT к KRW
    url = "https://api.coinbase.com/v2/exchange-rates?currency=USDT"
    response = requests.get(url)
    data = response.json()

    # Извлечение курса KRW
    krw_rate = data["data"]["rates"]["KRW"]
    usdt_to_krw_rate = float(krw_rate) + 4

    print(f"Курс USDT к KRW -> {str(usdt_to_krw_rate)}")

    return float(krw_rate) + 4


def get_rub_to_krw_rate():
    global rub_to_krw_rate

    url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/rub.json"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверяем, что запрос успешный (код 200)
        data = response.json()

        rub_to_krw = data["rub"]["krw"]  # Достаем курс рубля к воне
        rub_to_krw_rate = rub_to_krw

    except requests.RequestException as e:
        print(f"Ошибка при получении курса: {e}")
        return None


def get_currency_rates():
    global usd_rate, usd_to_krw_rate, usd_to_rub_rate

    print_message("ПОЛУЧАЕМ КУРСЫ ВАЛЮТ")

    # Получаем курс USD → KRW
    get_usd_to_krw_rate()

    # Получаем курс USD → RUB
    get_usd_to_rub_rate()

    rates_text = (
        f"USD → KRW: <b>{usd_to_krw_rate:.2f} ₩</b>\n"
        f"USD → RUB: <b>{usd_to_rub_rate:.2f} ₽</b>"
    )

    return rates_text


# Функция для получения курсов валют с API
def get_usd_to_krw_rate():
    global usd_to_krw_rate

    url = "https://api.manana.kr/exchange/rate/KRW/USD.json"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверяем успешность запроса
        data = response.json()

        # Получаем курс и добавляем +25 KRW
        usd_to_krw = data[0]["rate"] + 25
        usd_to_krw_rate = usd_to_krw

        print(f"Курс USD → KRW (с учетом +25 KRW): {usd_to_krw_rate}")
    except requests.RequestException as e:
        print(f"Ошибка при получении курса USD → KRW: {e}")
        usd_to_krw_rate = None


def get_usd_to_rub_rate():
    global usd_to_rub_rate

    url = "https://mosca.moscow/api/v1/rate/"
    headers = {
        "Access-Token": "JI_piVMlX9TsvIRKmduIbZOWzLo-v2zXozNfuxxXj4_MpsUKd_7aQS16fExzA7MVFCVVoAAmrb_-aMuu_UIbJA"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Проверяем успешность запроса
        data = response.json()

        # Получаем курс USD → RUB
        usd_to_rub = data["buy"]
        usd_to_rub_rate = usd_to_rub

        print(f"Курс USD → RUB: {usd_to_rub_rate}")
    except requests.RequestException as e:
        print(f"Ошибка при получении курса USD → RUB: {e}")
        usd_to_rub_rate = None


# Обработчик команды /cbr
@bot.message_handler(commands=["cbr"])
def cbr_command(message):
    try:
        rates_text = get_currency_rates()

        # Создаем клавиатуру с кнопкой для расчета автомобиля
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "Рассчитать стоимость автомобиля", callback_data="calculate_another"
            )
        )

        # Отправляем сообщение с курсами и клавиатурой
        bot.send_message(
            message.chat.id, rates_text, reply_markup=keyboard, parse_mode="HTML"
        )
    except Exception as e:
        bot.send_message(
            message.chat.id, "Не удалось получить курсы валют. Попробуйте позже."
        )
        print(f"Ошибка при получении курсов валют: {e}")


# Main menu creation function
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(
        types.KeyboardButton(CALCULATE_CAR_TEXT),
        types.KeyboardButton("Ручной расчёт"),
        types.KeyboardButton("Заказ запчастей"),
    )
    keyboard.add(
        types.KeyboardButton("Написать менеджеру"),
        types.KeyboardButton("О нас"),
        types.KeyboardButton("Telegram-канал"),
        # types.KeyboardButton("Написать в WhatsApp"),
        types.KeyboardButton("Instagram"),
        # types.KeyboardButton("Tik-Tok"),
        # types.KeyboardButton("Facebook"),
    )
    return keyboard


# Start command handler
@bot.message_handler(commands=["start"])
def send_welcome(message):
    get_currency_rates()

    user_first_name = message.from_user.first_name
    welcome_message = (
        f"Здравствуйте, {user_first_name}!\n\n"
        "Я бот компании AK Motors. Я помогу вам рассчитать стоимость понравившегося вам автомобиля из Южной Кореи до стран СНГ.\n\n"
        "Выберите действие из меню ниже."
    )

    # Логотип компании
    logo_url = "https://res.cloudinary.com/pomegranitedesign/image/upload/v1740623897/AK%20Motors/akmotorslogo.jpg"

    # Отправляем логотип перед сообщением
    bot.send_photo(
        message.chat.id,
        photo=logo_url,
    )

    # Отправляем приветственное сообщение
    bot.send_message(message.chat.id, welcome_message, reply_markup=main_menu())


# Error handling function
def send_error_message(message, error_text):
    global last_error_message_id

    # Remove previous error message if it exists
    if last_error_message_id.get(message.chat.id):
        try:
            bot.delete_message(message.chat.id, last_error_message_id[message.chat.id])
        except Exception as e:
            logging.error(f"Error deleting message: {e}")

    # Send new error message and store its ID
    error_message = bot.reply_to(message, error_text, reply_markup=main_menu())
    last_error_message_id[message.chat.id] = error_message.id
    logging.error(f"Error sent to user {message.chat.id}: {error_text}")


def get_car_info(url):
    global car_id_external, vehicle_no, vehicle_id, car_year, car_month

    if "fem.encar.com" in url:
        car_id_match = re.findall(r"\d+", url)
        car_id = car_id_match[0]
        car_id_external = car_id

        url = f"https://api.encar.com/v1/readside/vehicle/{car_id}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "http://www.encar.com/",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
        }

        response = requests.get(url, headers=headers).json()

        # Информация об автомобиле
        car_make = response["category"]["manufacturerEnglishName"]  # Марка
        car_model = response["category"]["modelGroupEnglishName"]  # Модель
        car_trim = response["category"]["gradeDetailEnglishName"] or ""  # Комплектация

        car_title = f"{car_make} {car_model} {car_trim}"  # Заголовок

        # Получаем все необходимые данные по автомобилю
        car_price = str(response["advertisement"]["price"])
        car_date = response["category"]["yearMonth"]
        year = car_date[2:4]
        month = car_date[4:]
        car_year = year
        car_month = month

        # Пробег (форматирование)
        mileage = response["spec"]["mileage"]
        formatted_mileage = f"{mileage:,} км"

        # Тип КПП
        transmission = response["spec"]["transmissionName"]
        formatted_transmission = "Автомат" if "오토" in transmission else "Механика"

        car_engine_displacement = str(response["spec"]["displacement"])
        car_type = response["spec"]["bodyName"]

        # Список фотографий (берем первые 10)
        car_photos = [
            generate_encar_photo_url(photo["path"]) for photo in response["photos"][:10]
        ]
        car_photos = [url for url in car_photos if url]

        # Дополнительные данные
        vehicle_no = response["vehicleNo"]
        vehicle_id = response["vehicleId"]

        # Форматируем
        formatted_car_date = f"01{month}{year}"
        formatted_car_type = "crossover" if car_type == "SUV" else "sedan"

        print_message(
            f"ID: {car_id}\nType: {formatted_car_type}\nDate: {formatted_car_date}\nCar Engine Displacement: {car_engine_displacement}\nPrice: {car_price} KRW"
        )

        return [
            car_price,
            car_engine_displacement,
            formatted_car_date,
            car_title,
            formatted_mileage,
            formatted_transmission,
            car_photos,
            year,
            month,
        ]
    elif "kbchachacha.com" in url:
        url = f"https://www.kbchachacha.com/public/car/detail.kbc?carSeq={car_id_external}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
            "Connection": "keep-alive",
        }

        response = requests.get(url=url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        # Находим JSON в <script type="application/ld+json">
        json_script = soup.find("script", {"type": "application/ld+json"})
        if json_script:
            json_data = json.loads(json_script.text.strip())

            # Извлекаем данные
            car_name = json_data.get("name", "Неизвестная модель")
            car_images = json_data.get("image", [])[:10]  # Берем первые 10 фото
            car_price = json_data.get("offers", {}).get("price", "Не указано")

            # Находим таблицу с информацией
            table = soup.find("table", {"class": "detail-info-table"})
            if table:
                rows = table.find_all("tr")

                # Достаём данные
                car_number = None
                car_year = None
                car_mileage = None
                car_fuel = None
                car_engine_displacement = None

                for row in rows:
                    headers = row.find_all("th")
                    values = row.find_all("td")

                    for th, td in zip(headers, values):
                        header_text = th.text.strip()
                        value_text = td.text.strip()

                        if header_text == "차량정보":  # Номер машины
                            car_number = value_text
                        elif header_text == "연식":  # Год выпуска
                            car_year = value_text
                        elif header_text == "주행거리":  # Пробег
                            car_mileage = value_text
                        elif header_text == "연료":  # Топливо
                            car_fuel = value_text
                        elif header_text == "배기량":  # Объем двигателя
                            car_engine_displacement = value_text
            else:
                print("❌ Таблица информации не найдена")

            car_info = {
                "name": car_name,
                "car_price": car_price,
                "images": car_images,
                "number": car_number,
                "year": car_year,
                "mileage": car_mileage,
                "fuel": car_fuel,
                "engine_volume": car_engine_displacement,
                "transmission": "오토",
            }

            return car_info
        else:
            print(
                "❌ Не удалось найти JSON-данные в <script type='application/ld+json'>"
            )
    elif "chutcha" in url:
        print("🔍 Парсим Chutcha.net...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
            "Referer": "https://web.chutcha.net/bmc/search?brandGroup=1&modelTree=%7B%7D&priceRange=0%2C0&mileage=0%2C0&year=&saleType=&accident=&fuel=&transmission=&region=&color=&option=&cpo=&theme=&sort=1&currPage=&carType=",
        }

        response = requests.get(url, headers=headers)

        soup = BeautifulSoup(response.text, "lxml")

        # Extract JSON data from <script type="application/ld+json">
        script_tag = soup.find("script", {"type": "application/json"})
        vehicle_data = None

        if not script_tag:
            return "Error: JSON data not found"

        try:
            data = json.loads(script_tag.string)
        except json.JSONDecodeError:
            return "Error: Failed to parse JSON"

        # Перемещение к ldJson (содержит основную информацию о машине)
        vehicle_data = (
            data.get("props", {})
            .get("pageProps", {})
            .get("dehydratedState", {})
            .get("queries", [])[0]
            .get("state", {})
            .get("data", {})
        )

        # Получение изображений
        img_list_data = vehicle_data.get("img_list", [])
        img_list = []
        for query in img_list_data:
            img_list.append(
                f"https://imgsc.chutcha.kr{query.get('img_path','').replace('.jpg', '_ori.jpg')}?s=1024x768&t=crop"
            )

        name = (
            vehicle_data.get("base_info", {}).get("brand_name", "")
            + " "
            + vehicle_data.get("base_info", {}).get("model_name", "")
            + " "
            + vehicle_data.get("base_info", {}).get("sub_model_name", "")
            + " "
            + vehicle_data.get("base_info", {}).get("grade_name", "")
        )
        car_price = vehicle_data.get("base_info", {}).get("plain_price", "")
        car_number = vehicle_data.get("base_info", {}).get("number_plate", "")
        car_year = vehicle_data.get("base_info", {}).get("first_reg_year", "")[2:]
        car_month = str(
            vehicle_data.get("base_info", {}).get("first_reg_month", "")
        ).zfill(2)
        car_mileage = vehicle_data.get("base_info", {}).get("plain_mileage", "")
        car_fuel = vehicle_data.get("base_info", {}).get("fuel_name", "")
        car_engine_displacement = vehicle_data.get("base_info", {}).get(
            "displacement", ""
        )
        car_transmission = vehicle_data.get("base_info", {}).get(
            "transmission_name", ""
        )

        # Список всех страховых
        car_history = (
            vehicle_data.get("safe_info", {})
            .get("carhistory_safe", {})
            .get("insurance", {})
            .get("list", [])
        )

        # Инициализация сумм страховых выплат
        own_damage_total = 0  # Выплаты по текущему авто
        other_damage_total = 0  # Выплаты по другим авто

        # Обработка выплат, если они есть
        if car_history:
            for claim in car_history:
                claim_type = claim.get("type")
                claim_price = int(
                    claim.get("price", 0)
                )  # Преобразуем в число, если есть цена

                if claim_type == "1":  # Выплаты по текущему авто
                    own_damage_total += claim_price
                elif claim_type == "2":  # Выплаты по другим авто
                    other_damage_total += claim_price

        # Формирование итогового JSON
        car_info = {
            "name": name,
            "car_price": car_price,
            "images": img_list,
            "number": car_number,
            "year": car_year,
            "month": car_month,
            "mileage": car_mileage,
            "fuel": car_fuel,
            "engine_volume": car_engine_displacement,
            "transmission": car_transmission,
            "insurance_claims": {
                "own_damage_total": own_damage_total if car_history else "Недоступно",
                "other_damage_total": (
                    other_damage_total if car_history else "Недоступно"
                ),
            },
        }

        return car_info


# Function to calculate the total cost
def calculate_cost(link, message):
    global car_data, car_id_external, car_month, car_year, krw_rub_rate, eur_rub_rate, rub_to_krw_rate, usd_rate, usdt_to_krw_rate

    print_message("ЗАПРОС НА РАСЧЁТ АВТОМОБИЛЯ")

    # Отправляем сообщение и сохраняем его ID
    processing_message = bot.send_message(
        message.chat.id, "Обрабатываю данные. Пожалуйста подождите ⏳"
    )

    car_id = None
    car_title = ""

    if "fem.encar.com" in link:
        car_id_match = re.findall(r"\d+", link)
        if car_id_match:
            car_id = car_id_match[0]  # Use the first match of digits
            car_id_external = car_id
            link = f"https://fem.encar.com/cars/detail/{car_id}"
        else:
            send_error_message(message, "🚫 Не удалось извлечь carid из ссылки.")
            return

    elif "kbchachacha.com" in link:
        parsed_url = urlparse(link)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carSeq", [None])[0]

        if car_id:
            car_id_external = car_id
            link = f"https://www.kbchachacha.com/public/car/detail.kbc?carSeq={car_id}"
        else:
            send_error_message(message, "🚫 Не удалось извлечь carSeq из ссылки.")
            return

    elif "web.chutcha.net" in link:
        parsed_url = urlparse(link)
        path_parts = parsed_url.path.split("/")

        if len(path_parts) >= 4 and path_parts[-2] == "detail":
            car_id = path_parts[-1]  # Берём последний элемент из пути
            car_id_external = car_id
            link = f"https://web.chutcha.net/bmc/detail/{car_id}"
        else:
            send_error_message(
                message, "🚫 Не удалось извлечь ID автомобиля из ссылки Chutcha.net."
            )
            return

    else:
        # Извлекаем carid с URL encar
        parsed_url = urlparse(link)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]

    # Если ссылка с encar
    if "fem.encar.com" in link:
        result = get_car_info(link)
        (
            car_price,
            car_engine_displacement,
            formatted_car_date,
            car_title,
            formatted_mileage,
            formatted_transmission,
            car_photos,
            year,
            month,
        ) = result

        preview_link = f"https://fem.encar.com/cars/detail/{car_id}"

    # Если ссылка с kbchacha
    if "kbchachacha.com" in link:
        result = get_car_info(link)

        car_title = result["name"]

        match = re.search(r"(\d{2})년(\d{2})월", result["year"])
        if match:
            car_year = match.group(1)
            car_month = match.group(2)  # Получаем двухзначный месяц
        else:
            car_year = "Не найдено"
            car_month = "Не найдено"

        month = car_month
        year = car_year

        car_engine_displacement = re.sub(r"[^\d]", "", result["engine_volume"])
        car_price = int(result["car_price"]) / 10000
        formatted_car_date = f"01{car_month}{match.group(1)}"
        formatted_mileage = result["mileage"]
        formatted_transmission = (
            "Автомат" if "오토" in result["transmission"] else "Механика"
        )
        car_photos = result["images"]

        preview_link = (
            f"https://www.kbchachacha.com/public/car/detail.kbc?carSeq={car_id}"
        )

    if "web.chutcha.net" in link:
        result = get_car_info(link)

        car_title = result["name"]

        month = result["year"]
        year = result["month"]

        # Очищаем объём двигателя от "cc"
        car_engine_displacement = re.sub(r"\D+", "", result["engine_volume"])

        # Преобразуем цену из формата "3,450만원 / 월 62만원"
        car_price = result["car_price"]

        # Форматируем дату
        formatted_car_date = (
            f"01{car_month}{car_year[-2:]}"
            if car_year != "Не найдено"
            else "Не найдено"
        )

        # Форматируем пробег
        formatted_mileage = format_number(result["mileage"]) + " км"

        # Определяем КПП
        formatted_transmission = (
            "Автомат" if "오토" in result["transmission"] else "Механика"
        )

        # Получаем фотографии автомобиля
        car_photos = result["images"]

        preview_link = f"https://web.chutcha.net/bmc/detail/{car_id}"

        own_car_insurance_payments = result["insurance_claims"]["own_damage_total"]
        other_car_insurance_payments = result["insurance_claims"]["other_damage_total"]

    if not car_price and car_engine_displacement and formatted_car_date:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "Написать менеджеру", url="https://t.me/@timyo97"
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "Рассчитать стоимость другого автомобиля",
                callback_data="calculate_another",
            )
        )
        bot.send_message(
            message.chat.id, "Ошибка", parse_mode="Markdown", reply_markup=keyboard
        )
        bot.delete_message(message.chat.id, processing_message.message_id)
        return

    if car_price and car_engine_displacement and formatted_car_date:
        car_engine_displacement = int(car_engine_displacement)

        # Форматирование данных
        formatted_car_year = f"20{car_year}"
        engine_volume_formatted = f"{format_number(car_engine_displacement)} cc"

        age = calculate_age(int(formatted_car_year), car_month)

        age_formatted = (
            "до 3 лет"
            if age == "0-3"
            else (
                "от 3 до 5 лет"
                if age == "3-5"
                else "от 5 до 7 лет" if age == "5-7" else "от 7 лет"
            )
        )

        # Конвертируем стоимость авто в рубли
        price_krw = int(car_price) * 10000
        price_usd = price_krw / usd_to_krw_rate
        price_rub = price_usd * usd_to_rub_rate

        response = get_customs_fees(
            car_engine_displacement,
            price_krw,
            int(formatted_car_year),
            car_month,
            engine_type=1,
        )

        # Таможенный сбор
        customs_fee = clean_number(response["sbor"])
        customs_duty = clean_number(response["tax"])
        recycling_fee = clean_number(response["util"])

        # Расчет итоговой стоимости автомобиля в рублях
        total_cost = (
            price_rub
            + ((1400000 / usd_to_krw_rate) * usd_to_rub_rate)
            + ((1400000 / usd_to_krw_rate) * usd_to_rub_rate)
            + ((440000 / usd_to_krw_rate) * usd_to_rub_rate)
            + 120000
            + customs_fee
            + customs_duty
            + recycling_fee
            + 13000
            + 230000
        )

        total_cost_krw = (
            price_krw
            + 1400000
            + 1400000
            + 440000
            + (120000 / usd_to_rub_rate) * usd_to_krw_rate
            + (customs_fee / usd_to_rub_rate) * usd_to_krw_rate
            + (customs_duty / usd_to_rub_rate) * usd_to_krw_rate
            + (recycling_fee / usd_to_rub_rate) * usd_to_krw_rate
            + (13000 / usd_to_rub_rate) * usd_to_krw_rate
            + (230000 / usd_to_rub_rate) * usd_to_krw_rate
        )

        total_cost_usd = (
            price_usd
            + (1400000 / usd_to_krw_rate)
            + (1400000 / usd_to_krw_rate)
            + (440000 / usd_to_krw_rate)
            + (120000 / usd_to_rub_rate)
            + (customs_fee / usd_to_rub_rate)
            + (customs_duty / usd_to_rub_rate)
            + (recycling_fee / usd_to_rub_rate)
            + (13000 / usd_to_rub_rate)
            + (230000 / usd_to_rub_rate)
        )

        car_data["total_cost_usd"] = total_cost_usd
        car_data["total_cost_krw"] = total_cost_krw
        car_data["total_cost_rub"] = total_cost

        car_data["company_fees_usd"] = 1400000 / usd_to_krw_rate
        car_data["company_fees_krw"] = 1400000
        car_data["company_fees_rub"] = (1400000 / usd_to_krw_rate) * usd_to_rub_rate

        car_data["agent_korea_rub"] = 50000
        car_data["agent_korea_usd"] = 50000 / usd_to_rub_rate
        car_data["agent_korea_krw"] = (50000 / usd_to_rub_rate) * usd_to_krw_rate

        car_data["advance_rub"] = (1000000 / usd_to_krw_rate) * usd_to_rub_rate
        car_data["advance_usd"] = 1000000 * usd_to_krw_rate
        car_data["advance_krw"] = 1000000

        car_data["car_price_krw"] = price_krw
        car_data["car_price_usd"] = price_usd
        car_data["car_price_rub"] = price_rub

        car_data["dealer_korea_usd"] = 440000 / usd_to_krw_rate
        car_data["dealer_korea_krw"] = 440000
        car_data["dealer_korea_rub"] = (440000 / usd_to_krw_rate) * usd_to_rub_rate

        car_data["delivery_korea_usd"] = 100000 / usd_to_krw_rate
        car_data["delivery_korea_krw"] = 100000
        car_data["delivery_korea_rub"] = (100000 / usd_to_krw_rate) * usd_to_rub_rate

        car_data["transfer_korea_usd"] = 350000 / usd_to_krw_rate
        car_data["transfer_korea_krw"] = 350000
        car_data["transfer_korea_rub"] = (350000 / usd_to_krw_rate) * usd_to_rub_rate

        car_data["freight_korea_usd"] = 1400000 / usd_to_krw_rate
        car_data["freight_korea_krw"] = 1400000
        car_data["freight_korea_rub"] = (1400000 / usd_to_krw_rate) * usd_to_rub_rate

        car_data["korea_total_usd"] = (
            (50000 / usd_to_rub_rate)
            + (440000 / usd_to_krw_rate)
            + (100000 / usd_to_krw_rate)
            + (350000 / usd_to_krw_rate)
            + (600)
        )

        car_data["korea_total_krw"] = (
            ((50000 / usd_to_rub_rate) * usd_to_krw_rate)
            + (440000)
            + (100000)
            + 350000
            + (600 * usd_to_krw_rate)
        )

        car_data["korea_total_rub"] = (
            (50000)
            + ((440000 / usd_to_krw_rate) * usd_to_rub_rate)
            + ((100000 / usd_to_krw_rate) * usd_to_rub_rate)
            + ((350000 / usd_to_krw_rate) * usd_to_rub_rate)
            + (600 * usd_to_rub_rate)
        )

        car_data["korea_total_plus_car_usd"] = (
            (50000 / usd_to_rub_rate)
            + (price_usd)
            + (440000 / usd_to_krw_rate)
            + (100000 / usd_to_krw_rate)
            + (350000 / usd_to_krw_rate)
            + (600)
        )
        car_data["korea_total_plus_car_krw"] = (
            ((50000 / usd_to_rub_rate) * usd_to_krw_rate)
            + (price_krw)
            + (440000)
            + (100000)
            + 350000
            + (600 * usd_to_krw_rate)
        )
        car_data["korea_total_plus_car_rub"] = (
            (50000)
            + (price_rub)
            + ((440000 / usd_to_krw_rate) * usd_to_rub_rate)
            + ((100000 / usd_to_krw_rate) * usd_to_rub_rate)
            + ((350000 / usd_to_krw_rate) * usd_to_rub_rate)
            + (600 * usd_to_rub_rate)
        )

        # Расходы Россия
        car_data["customs_duty_usd"] = customs_duty / usd_to_rub_rate
        car_data["customs_duty_krw"] = (
            customs_duty / usd_to_rub_rate
        ) * usd_to_krw_rate
        car_data["customs_duty_rub"] = customs_duty

        car_data["customs_fee_usd"] = customs_fee / usd_to_rub_rate
        car_data["customs_fee_krw"] = (customs_fee / usd_to_rub_rate) * usd_to_krw_rate
        car_data["customs_fee_rub"] = customs_fee

        car_data["util_fee_usd"] = recycling_fee / usd_to_rub_rate
        car_data["util_fee_krw"] = (recycling_fee / usd_to_rub_rate) * usd_to_krw_rate
        car_data["util_fee_rub"] = recycling_fee

        car_data["broker_russia_usd"] = 120000 / usd_to_rub_rate
        car_data["broker_russia_krw"] = (120000 / usd_to_rub_rate) * usd_to_krw_rate
        car_data["broker_russia_rub"] = 120000

        car_data["moscow_transporter_usd"] = 230000 / usd_to_rub_rate
        car_data["moscow_transporter_krw"] = (
            230000 / usd_to_rub_rate
        ) * usd_to_krw_rate
        car_data["moscow_transporter_rub"] = 230000

        car_data["vladivostok_transfer_usd"] = 13000 / usd_to_rub_rate
        car_data["vladivostok_transfer_krw"] = (
            13000 / usd_to_rub_rate
        ) * usdt_to_krw_rate
        car_data["vladivostok_transfer_rub"] = 13000

        car_data["svh_russia_usd"] = 50000 / usd_to_rub_rate
        car_data["svh_russia_krw"] = (50000 / usd_to_rub_rate) * usd_to_krw_rate
        car_data["svh_russia_rub"] = 50000

        car_data["lab_russia_usd"] = 30000 / usd_to_rub_rate
        car_data["lab_russia_krw"] = (30000 / usd_to_rub_rate) * usd_to_krw_rate
        car_data["lab_russia_rub"] = 30000

        car_data["perm_registration_russia_usd"] = 8000 / usd_to_rub_rate
        car_data["perm_registration_russia_krw"] = (
            8000 / usd_to_rub_rate
        ) * usd_to_krw_rate
        car_data["perm_registration_russia_rub"] = 8000

        car_data["russia_total_usd"] = (
            (customs_duty / usd_to_rub_rate)
            + (customs_fee / usd_to_rub_rate)
            + (recycling_fee / usd_to_rub_rate)
            + (346)
            + (50000 / usd_to_rub_rate)
            + (8000 / usd_to_rub_rate)
        )
        car_data["russia_total_krw"] = (
            ((customs_duty / usd_to_rub_rate) * usd_to_krw_rate)
            + ((customs_fee / usd_to_rub_rate) * usd_to_krw_rate)
            + ((recycling_fee / usd_to_rub_rate) * usd_to_krw_rate)
            + (346 * usd_to_krw_rate)
            + ((50000 / usd_to_rub_rate) * usd_to_krw_rate)
            + ((8000 / usd_to_rub_rate) * usd_to_krw_rate)
        )
        car_data["russia_total_rub"] = (
            customs_duty
            + customs_fee
            + recycling_fee
            + (346 * usd_to_rub_rate)
            + 50000
            + 8000
        )

        car_insurance_payments_chutcha = ""
        if "web.chutcha.net" in link:
            own_insurance_text = (
                f"₩{format_number(own_car_insurance_payments)}"
                if isinstance(own_car_insurance_payments, int)
                else "Нет"
            )
            other_insurance_text = (
                f"₩{format_number(other_car_insurance_payments)}"
                if isinstance(other_car_insurance_payments, int)
                else "Нет"
            )

            car_insurance_payments_chutcha = (
                f"Страховые выплаты по данному автомобилю:\n{own_insurance_text}\n"
                f"Страховые выплаты другому автомобилю:\n{other_insurance_text}\n\n"
            )

        # Формирование сообщения результата
        result_message = (
            f"{car_title}\n\n"
            f"Возраст: {age_formatted} (дата регистрации: {month}/{year})\n"
            f"Пробег: {formatted_mileage}\n"
            f"Объём двигателя: {engine_volume_formatted}\n"
            f"КПП: {formatted_transmission}\n\n"
            f"Стоимость автомобиля в Корее: ₩{format_number(price_krw)}\n"
            f"Стоимость автомобиля под ключ до Владивостока: \n<b>${format_number(total_cost_usd)} </b> | <b>₩{format_number(total_cost_krw)} </b> | <b>{format_number(total_cost)} ₽</b>\n\n"
            f"{car_insurance_payments_chutcha}"
            f"💵 <b>Курс USDT к Воне: ₩{format_number(usdt_to_krw_rate)}</b>\n\n"
            f"🔗 <a href='{preview_link}'>Ссылка на автомобиль</a>\n\n"
            "Если данное авто попадает под санкции, пожалуйста уточните возможность отправки в вашу страну у наших менеджеров:\n\n"
            f"▪️ +82 10-2934-8855 (Артур)\n"
            f"▪️ +82 10-5528-0997 (Тимур)\n"
            # f"▪️ +82 10-5128-8082 (Александр) \n\n"
            "🔗 <a href='https://t.me/akmotors96'>Официальный телеграм канал</a>\n"
        )

        # Клавиатура с дальнейшими действиями
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Детали расчёта", callback_data="detail")
        )

        # Кнопка для добавления в избранное
        keyboard.add(
            types.InlineKeyboardButton(
                "⭐ Добавить в избранное",
                callback_data=f"add_favorite_{car_id_external}",
            )
        )

        if "fem.encar.com" in link:
            keyboard.add(
                types.InlineKeyboardButton(
                    "Технический Отчёт об Автомобиле", callback_data="technical_card"
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "Выплаты по ДТП",
                    callback_data="technical_report",
                )
            )
        keyboard.add(
            types.InlineKeyboardButton(
                "Написать менеджеру", url="https://t.me/@timyo97"
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "Расчёт другого автомобиля",
                callback_data="calculate_another",
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "Главное меню",
                callback_data="main_menu",
            )
        )

        # Отправляем до 10 фотографий
        # media_group = []
        # for photo_url in sorted(car_photos):
        #     try:
        #         response = requests.get(photo_url)
        #         if response.status_code == 200:
        #             photo = BytesIO(response.content)  # Загружаем фото в память
        #             media_group.append(
        #                 types.InputMediaPhoto(photo)
        #             )  # Добавляем в список

        #             # Если набрали 10 фото, отправляем альбом
        #             if len(media_group) == 10:
        #                 bot.send_media_group(message.chat.id, media_group)
        #                 media_group.clear()  # Очищаем список для следующей группы
        #         else:
        #             print(f"Ошибка загрузки фото: {photo_url} - {response.status_code}")
        #     except Exception as e:
        #         print(f"Ошибка при обработке фото {photo_url}: {e}")

        # # Отправка оставшихся фото, если их меньше 10
        # if media_group:
        #     bot.send_media_group(message.chat.id, media_group)

        car_data["car_id"] = car_id
        car_data["name"] = car_title
        car_data["images"] = car_photos if isinstance(car_photos, list) else []
        car_data["link"] = preview_link
        car_data["year"] = year
        car_data["month"] = month
        car_data["mileage"] = formatted_mileage
        car_data["engine_volume"] = car_engine_displacement
        car_data["transmission"] = formatted_transmission
        car_data["car_price"] = price_krw
        car_data["user_name"] = message.from_user.username
        car_data["first_name"] = message.from_user.first_name
        car_data["last_name"] = message.from_user.last_name

        bot.send_message(
            message.chat.id,
            result_message,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        bot.delete_message(
            message.chat.id, processing_message.message_id
        )  # Удаляем сообщение о передаче данных в обработку

    else:
        send_error_message(
            message,
            "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
        )
        bot.delete_message(message.chat.id, processing_message.message_id)


# Function to get insurance total
def get_insurance_total():
    global car_id_external, vehicle_no, vehicle_id

    print_message("[ЗАПРОС] ТЕХНИЧЕСКИЙ ОТЧËТ ОБ АВТОМОБИЛЕ")

    formatted_vehicle_no = urllib.parse.quote(str(vehicle_no).strip())
    url = f"https://api.encar.com/v1/readside/record/vehicle/{str(vehicle_id)}/open?vehicleNo={formatted_vehicle_no}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "http://www.encar.com/",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
        }

        response = requests.get(url, headers)
        json_response = response.json()

        # Форматируем данные
        damage_to_my_car = json_response["myAccidentCost"]
        damage_to_other_car = json_response["otherAccidentCost"]

        print(
            f"Выплаты по представленному автомобилю: {format_number(damage_to_my_car)}"
        )
        print(f"Выплаты другому автомобилю: {format_number(damage_to_other_car)}")

        return [format_number(damage_to_my_car), format_number(damage_to_other_car)]

    except Exception as e:
        print(f"Произошла ошибка при получении данных: {e}")
        return ["", ""]


def get_technical_card():
    global vehicle_id

    url = f"https://api.encar.com/v1/readside/inspection/vehicle/{vehicle_id}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "http://www.encar.com/",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
        }

        response = requests.get(url, headers)
        json_response = response.json()

        # Основная информация
        model_year = (
            json_response.get("master", {})
            .get("detail", {})
            .get("modelYear", "Не указано")
        )
        first_registration_date = (
            json_response.get("master", {})
            .get("detail", {})
            .get("firstRegistrationDate", "Не указано")
        )
        comments = json_response.get("master", {}).get("detail", {}).get("comments")
        comments = comments.strip() if comments else "Нет данных"

        usage_change_types = (
            json_response.get("master", {})
            .get("detail", {})
            .get("usageChangeTypes", [])
        )
        paint_part_types = (
            json_response.get("master", {}).get("detail", {}).get("paintPartTypes", [])
        )
        serious_types = (
            json_response.get("master", {}).get("detail", {}).get("seriousTypes", [])
        )
        tuning_state_types = (
            json_response.get("master", {})
            .get("detail", {})
            .get("tuningStateTypes", [])
        )
        etcs = json_response.get("etcs", [])

        # Перевод использования
        usage_translation = {
            "렌트": "Аренда",
            "리스": "Лизинг",
            "영업용": "Коммерческое использование",
        }
        usage_change = "Не указано"
        if usage_change_types:
            usage_change = usage_translation.get(
                usage_change_types[0].get("title", ""), "Не указано"
            )

        # Необходимость ремонта
        repair_needed = []
        for etc in etcs:
            title = etc["type"]["title"]
            if title == "수리필요":
                for child in etc["children"]:
                    repair_needed.append(child["type"]["title"])

        repair_translation = {
            "외장": "Кузов",
            "내장": "Интерьер",
            "광택": "Полировка",
            "룸 클리링": "Чистка салона",
            "휠": "Колёса",
            "타이어": "Шины",
            "유리": "Стекло",
        }
        repair_needed_translated = [
            repair_translation.get(item, item) for item in repair_needed
        ]
        repair_output = (
            "Нет данных"
            if not repair_needed_translated
            else "\n".join(
                [f"- {item}: Требуется ремонт" for item in repair_needed_translated]
            )
        )

        # Окрашенные элементы
        painted_parts = (
            "Нет данных" if not paint_part_types else "\n".join(paint_part_types)
        )

        # Серьёзные повреждения
        serious_damages = (
            "Нет данных" if not serious_types else "\n".join(serious_types)
        )

        # Тюнинг и модификации
        tuning_mods = (
            "Нет данных" if not tuning_state_types else "\n".join(tuning_state_types)
        )

        # Сборка сообщения
        output = (
            f"🚗 <b>Технический отчёт об автомобиле</b> 🚗\n\n"
            f"🛠 <b>Обновление тех. состояния</b>: {model_year}\n\n"
            f"🔧 <b>Использование автомобиля</b>: {usage_change}\n\n"
            f"⚙️ <b>Необходимость ремонта</b>:\n{repair_output}\n\n"
            f"🎨 <b>Окрашенные элементы</b>:\n{painted_parts}\n\n"
            f"🚧 <b>Серьёзные повреждения</b>:\n{serious_damages}\n\n"
            f"🔧 <b>Тюнинг и модификации</b>:\n{tuning_mods}"
        )

        return output

    except Exception as e:
        print(f"Произошла ошибка при получении данных: {e}")
        return "Произошла ошибка при получении данных"


# Callback query handler
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global car_data, car_id_external, usd_rate

    if call.data.startswith("detail"):
        print_message("[ЗАПРОС] ДЕТАЛИЗАЦИЯ РАСЧËТА")

        detail_message = (
            f"<i>ПЕРВАЯ ЧАСТЬ ОПЛАТЫ (КОРЕЯ)</i>:\n\n"
            f"Стоимость автомобиля:\n<b>${format_number(car_data['car_price_usd'])}</b> | <b>₩{format_number(car_data['car_price_krw'])}</b> | <b>{format_number(car_data['car_price_rub'])} ₽</b>\n\n"
            f"Услуги фирмы (поиск и подбор авто, документация, 3 осмотра):\n<b>${format_number(car_data['company_fees_usd'])}</b> | <b>₩{format_number(car_data['company_fees_krw'])}</b> | <b>{format_number(car_data['company_fees_rub'])} ₽</b>\n\n"
            f"Фрахт (отправка в порт, доставка автомобиля на базу, оплата судна):\n<b>${format_number(car_data['freight_korea_usd'])}</b> | <b>₩{format_number(car_data['freight_korea_krw'])}</b> | <b>{format_number(car_data['freight_korea_rub'])} ₽</b>\n\n\n"
            f"Диллерский сбор:\n<b>${format_number(car_data['dealer_korea_usd'])}</b> | <b>₩{format_number(car_data['dealer_korea_krw'])}</b> | <b>{format_number(car_data['dealer_korea_rub'])} ₽</b>\n\n"
            f"<i>ВТОРАЯ ЧАСТЬ ОПЛАТЫ (РОССИЯ)</i>:\n\n"
            f"Брокер-Владивосток:\n<b>${format_number(car_data['broker_russia_usd'])}</b> | <b>₩{format_number(car_data['broker_russia_krw'])}</b> | <b>{format_number(car_data['broker_russia_rub'])} ₽</b>\n\n\n"
            f"Единая таможенная ставка:\n<b>${format_number(car_data['customs_duty_usd'])}</b> | <b>₩{format_number(car_data['customs_duty_krw'])}</b> | <b>{format_number(car_data['customs_duty_rub'])} ₽</b>\n\n"
            f"Таможенное оформление:\n<b>${format_number(car_data['customs_fee_usd'])}</b> | <b>₩{format_number(car_data['customs_fee_krw'])}</b> | <b>{format_number(car_data['customs_fee_rub'])} ₽</b>\n\n"
            f"Утилизационный сбор:\n<b>${format_number(car_data['util_fee_usd'])}</b> | <b>₩{format_number(car_data['util_fee_krw'])}</b> | <b>{format_number(car_data['util_fee_rub'])} ₽</b>\n\n\n"
            f"Перегон во Владивостоке:\n<b>${format_number(car_data['vladivostok_transfer_usd'])}</b> | <b>₩{format_number(car_data['vladivostok_transfer_krw'])}</b> | <b>{format_number(car_data['vladivostok_transfer_rub'])} ₽</b>\n\n"
            f"Автовоз до Москвы:\n<b>${format_number(car_data['moscow_transporter_usd'])}</b> | <b>₩{format_number(car_data['moscow_transporter_krw'])}</b> | <b>{format_number(car_data['moscow_transporter_rub'])} ₽</b>\n\n"
            f"Итого под ключ: \n<b>${format_number(car_data['total_cost_usd'])}</b> | <b>₩{format_number(car_data['total_cost_krw'])}</b> | <b>{format_number(car_data['total_cost_rub'])} ₽</b>\n\n"
            f"<b>Доставку до вашего города уточняйте у менеджеров:</b>\n"
            f"▪️ +82 10-2934-8855 (Артур)\n"
            f"▪️ +82 10-5528-0997 (Тимур)\n"
            # f"▪️ +82 10-5128-8082 (Александр)\n\n"
        )

        # Inline buttons for further actions
        keyboard = types.InlineKeyboardMarkup()

        if call.data.startswith("detail_manual"):
            keyboard.add(
                types.InlineKeyboardButton(
                    "Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another_manual",
                )
            )
        else:
            keyboard.add(
                types.InlineKeyboardButton(
                    "Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )

        keyboard.add(
            types.InlineKeyboardButton("Главное меню", callback_data="main_menu")
        )

        bot.send_message(
            call.message.chat.id,
            detail_message,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    elif call.data == "technical_card":
        print_message("[ЗАПРОС] ТЕХНИЧЕСКАЯ ОТЧËТ ОБ АВТОМОБИЛЕ")

        technical_card_output = get_technical_card()

        bot.send_message(
            call.message.chat.id,
            "Запрашиваю отчёт по автомобилю. Пожалуйста подождите ⏳",
        )

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "Рассчитать стоимость другого автомобиля",
                callback_data="calculate_another",
            )
        )
        keyboard.add(
            types.InlineKeyboardButton("Главное меню", callback_data="main_menu")
        )
        # keyboard.add(
        #     types.InlineKeyboardButton(
        #         "Связаться с менеджером", url="https://t.me/@timyo97"
        #     )
        # )

        bot.send_message(
            call.message.chat.id,
            technical_card_output,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    elif call.data == "technical_report":
        bot.send_message(
            call.message.chat.id,
            "Запрашиваю отчёт по ДТП. Пожалуйста подождите ⏳",
        )

        # Retrieve insurance information
        insurance_info = get_insurance_total()

        # Проверка на наличие ошибки
        if (
            insurance_info is None
            or "Нет данных" in insurance_info[0]
            or "Нет данных" in insurance_info[1]
        ):
            error_message = (
                "Не удалось получить данные о страховых выплатах. \n\n"
                f'<a href="https://fem.encar.com/cars/report/accident/{car_id_external}">🔗 Посмотреть страховую историю вручную 🔗</a>\n\n\n'
                f"<b>Найдите две строки:</b>\n\n"
                f"보험사고 이력 (내차 피해) - Выплаты по представленному автомобилю\n"
                f"보험사고 이력 (타차 가해) - Выплаты другим участникам ДТП"
            )

            # Inline buttons for further actions
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "Связаться с менеджером", url="https://t.me/@timyo97"
                )
            )

            # Отправка сообщения об ошибке
            bot.send_message(
                call.message.chat.id,
                error_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            current_car_insurance_payments = (
                "0" if len(insurance_info[0]) == 0 else insurance_info[0]
            )
            other_car_insurance_payments = (
                "0" if len(insurance_info[1]) == 0 else insurance_info[1]
            )

            # Construct the message for the technical report
            tech_report_message = (
                f"Страховые выплаты по представленному автомобилю: \n<b>{current_car_insurance_payments} ₩</b>\n\n"
                f"Страховые выплаты другим участникам ДТП: \n<b>{other_car_insurance_payments} ₩</b>\n\n"
                f'<a href="https://fem.encar.com/cars/report/inspect/{car_id_external}">🔗 Ссылка на схему повреждений кузовных элементов 🔗</a>'
            )

            # Inline buttons for further actions
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "Связаться с менеджером", url="https://t.me/@timyo97"
                )
            )
            keyboard.add(
                types.InlineKeyboardButton("Главное меню", callback_data="main_menu")
            )

            bot.send_message(
                call.message.chat.id,
                tech_report_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

    elif call.data == "calculate_another":
        bot.send_message(
            call.message.chat.id,
            "Пожалуйста, введите ссылку на автомобиль с сайта (encar.com, kbchachacha.com, web.chutcha.net)",
        )

    elif call.data == "calculate_another_manual":
        msg = bot.send_message(
            call.message.chat.id,
            "Выберите возраст автомобиля",
        )
        bot.register_next_step_handler(msg, process_car_age)

    elif call.data == "main_menu":
        bot.send_message(call.message.chat.id, "Главное меню", reply_markup=main_menu())


def process_car_age(message):
    user_input = message.text.strip()

    # Проверяем ввод
    age_mapping = {
        "До 3 лет": "0-3",
        "От 3 до 5 лет": "3-5",
        "От 5 до 7 лет": "5-7",
        "Более 7 лет": "7-0",
    }

    if user_input not in age_mapping:
        bot.send_message(message.chat.id, "Пожалуйста, выберите возраст из списка.")
        return

    # Сохраняем возраст авто
    user_data[message.chat.id] = {"car_age": age_mapping[user_input]}

    # Запрашиваем объем двигателя
    bot.send_message(
        message.chat.id,
        "Введите объем двигателя в см³ (например, 1998):",
    )
    bot.register_next_step_handler(message, process_engine_volume)


def process_engine_volume(message):
    user_input = message.text.strip()

    # Проверяем, что введено число
    if not user_input.isdigit():
        bot.send_message(
            message.chat.id, "Пожалуйста, введите корректный объем двигателя в см³."
        )
        bot.register_next_step_handler(message, process_engine_volume)
        return

    # Сохраняем объем двигателя
    user_data[message.chat.id]["engine_volume"] = int(user_input)

    # Запрашиваем стоимость авто
    bot.send_message(
        message.chat.id,
        "Введите стоимость автомобиля в корейских вонах (например, 15000000):",
    )
    bot.register_next_step_handler(message, process_car_price)


def process_car_price(message):
    global usd_to_krw_rate, usd_to_rub_rate

    user_input = message.text.strip()

    # Проверяем, что введено число
    if not user_input.isdigit():
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите корректную стоимость автомобиля в вонах.",
        )
        bot.register_next_step_handler(message, process_car_price)
        return

    # Сохраняем стоимость автомобиля
    user_data[message.chat.id]["car_price_krw"] = int(user_input)

    # Извлекаем данные пользователя
    if message.chat.id not in user_data:
        user_data[message.chat.id] = {}

    if "car_age" not in user_data[message.chat.id]:
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте снова.")
        return  # Прерываем выполнение, если возраст не установлен

    age_group = user_data[message.chat.id]["car_age"]
    engine_volume = user_data[message.chat.id]["engine_volume"]
    car_price_krw = user_data[message.chat.id]["car_price_krw"]

    # Конвертируем стоимость автомобиля в USD и RUB
    price_usd = car_price_krw / usd_to_krw_rate
    price_rub = price_usd * usd_to_rub_rate

    # Рассчитываем таможенные платежи
    customs_fees = get_customs_fees_manual(engine_volume, car_price_krw, age_group)

    customs_duty = clean_number(customs_fees["tax"])  # Таможенная пошлина
    customs_fee = clean_number(customs_fees["sbor"])  # Таможенный сбор
    recycling_fee = clean_number(customs_fees["util"])  # Утилизационный сбор

    # Расчет итоговой стоимости автомобиля в рублях
    total_cost_rub = (
        price_rub
        + ((1400000 / usd_to_krw_rate) * usd_to_rub_rate)
        + ((1400000 / usd_to_krw_rate) * usd_to_rub_rate)
        + ((440000 / usd_to_krw_rate) * usd_to_rub_rate)
        + 120000
        + customs_fee
        + customs_duty
        + recycling_fee
        + 13000
        + 230000
    )

    total_cost_krw = (
        car_price_krw
        + 1400000
        + 1400000
        + 440000
        + (120000 / usd_to_rub_rate) * usd_to_krw_rate
        + (customs_fee / usd_to_rub_rate) * usd_to_krw_rate
        + (customs_duty / usd_to_rub_rate) * usd_to_krw_rate
        + (recycling_fee / usd_to_rub_rate) * usd_to_krw_rate
        + (13000 / usd_to_rub_rate) * usd_to_krw_rate
        + (230000 / usd_to_rub_rate) * usd_to_krw_rate
    )

    total_cost_usd = (
        price_usd
        + (1400000 / usd_to_krw_rate)
        + (1400000 / usd_to_krw_rate)
        + (440000 / usd_to_krw_rate)
        + (120000 / usd_to_rub_rate)
        + (customs_fee / usd_to_rub_rate)
        + (customs_duty / usd_to_rub_rate)
        + (recycling_fee / usd_to_rub_rate)
        + (13000 / usd_to_rub_rate)
        + (230000 / usd_to_rub_rate)
    )

    company_fees_krw = 1400000
    company_fees_usd = 1400000 / usdt_to_krw_rate
    company_fees_rub = (1400000 / usd_to_krw_rate) * usd_to_rub_rate

    freight_korea_krw = 1400000
    freight_korea_usd = 1400000 / usd_to_krw_rate
    freight_korea_rub = (1400000 / usd_to_krw_rate) * usd_to_rub_rate

    dealer_korea_krw = 440000
    dealer_korea_usd = 440000 / usd_to_krw_rate
    dealer_korea_rub = (440000 / usd_to_krw_rate) * usd_to_rub_rate

    broker_russia_rub = 120000
    broker_russia_usd = 120000 / usd_to_rub_rate
    broker_russia_krw = (120000 / usd_to_rub_rate) * usd_to_krw_rate

    customs_duty_rub = customs_duty
    customs_duty_usd = customs_duty / usd_to_rub_rate
    customs_duty_krw = (customs_duty / usd_to_rub_rate) * usd_to_krw_rate

    customs_fee_rub = customs_fee
    customs_fee_usd = customs_fee / usd_to_rub_rate
    customs_fee_krw = (customs_fee / usd_to_rub_rate) * usd_to_krw_rate

    util_fee_rub = recycling_fee
    util_fee_usd = recycling_fee / usd_to_rub_rate
    util_fee_krw = (recycling_fee / usd_to_rub_rate) * usd_to_krw_rate

    vladivostok_transfer_rub = 13000
    vladivostok_transfer_usd = 13000 / usd_to_rub_rate
    vladivostok_transfer_krw = (13000 / usd_to_rub_rate) * usdt_to_krw_rate

    moscow_transporter_rub = 230000
    moscow_transporter_usd = 230000 / usd_to_rub_rate
    moscow_transporter_krw = (230000 / usd_to_rub_rate) * usd_to_krw_rate

    # Формируем сообщение с расчетом стоимости
    result_message = (
        f"💰 <b>Расчёт стоимости автомобиля</b> 💰\n\n"
        f"📌 Возраст автомобиля: <b>{age_group} лет</b>\n"
        f"🚗 Объём двигателя: <b>{format_number(engine_volume)} см³</b>\n\n"
        f"<i>ПЕРВАЯ ЧАСТЬ ОПЛАТЫ (КОРЕЯ)</i>:\n\n"
        f"Стоимость автомобиля:\n<b>${format_number(price_usd)}</b> | <b>₩{format_number(car_price_krw)}</b> | <b>{format_number(price_rub)} ₽</b>\n\n"
        f"Услуги фирмы (поиск и подбор авто, документация, 3 осмотра):\n<b>${format_number(company_fees_usd)}</b> | <b>₩{format_number(company_fees_krw)}</b> | <b>{format_number(company_fees_rub)} ₽</b>\n\n"
        f"Фрахт (отправка в порт, доставка автомобиля на базу, оплата судна):\n<b>${format_number(freight_korea_usd)}</b> | <b>₩{format_number(freight_korea_krw)}</b> | <b>{format_number(freight_korea_rub)} ₽</b>\n\n\n"
        f"Диллерский сбор:\n<b>${format_number(dealer_korea_usd)}</b> | <b>₩{format_number(dealer_korea_krw)}</b> | <b>{format_number(dealer_korea_rub)} ₽</b>\n\n"
        f"<i>ВТОРАЯ ЧАСТЬ ОПЛАТЫ (РОССИЯ)</i>:\n\n"
        f"Брокер-Владивосток:\n<b>${format_number(broker_russia_usd)}</b> | <b>₩{format_number(broker_russia_krw)}</b> | <b>{format_number(broker_russia_rub)} ₽</b>\n\n\n"
        f"Единая таможенная ставка:\n<b>${format_number(customs_duty_usd)}</b> | <b>₩{format_number(customs_duty_krw)}</b> | <b>{format_number(customs_duty_rub)} ₽</b>\n\n"
        f"Утилизационный сбор:\n<b>${format_number(util_fee_usd)}</b> | <b>₩{format_number(util_fee_krw)}</b> | <b>{format_number(util_fee_rub)} ₽</b>\n\n\n"
        f"Таможенное оформление:\n<b>${format_number(customs_fee_usd)}</b> | <b>₩{format_number(customs_fee_krw)}</b> | <b>{format_number(customs_fee_rub)} ₽</b>\n\n"
        f"Перегон во Владивостоке:\n<b>${format_number(vladivostok_transfer_usd)}</b> | <b>₩{format_number(vladivostok_transfer_krw)}</b> | <b>{format_number(vladivostok_transfer_rub)} ₽</b>\n\n"
        f"Автовоз до Москвы:\n<b>${format_number(moscow_transporter_usd)}</b> | <b>₩{format_number(moscow_transporter_krw)}</b> | <b>{format_number(moscow_transporter_rub)} ₽</b>\n\n"
        f"Итого под ключ: \n<b>${format_number(total_cost_usd)}</b> | <b>₩{format_number(total_cost_krw)}</b> | <b>{format_number(total_cost_rub)} ₽</b>\n\n"
        f"<b>Доставку до вашего города уточняйте у менеджеров:</b>\n"
        f"▪️ +82 10-2934-8855 (Артур)\n"
        f"▪️ +82 10-5528-0997 (Тимур)\n"
        # f"▪️ +82 10-5128-8082 (Александр)\n\n"
    )

    # Клавиатура с дальнейшими действиями
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "Рассчитать другой автомобиль", callback_data="calculate_another_manual"
        )
    )
    keyboard.add(
        types.InlineKeyboardButton(
            "Связаться с менеджером", url="https://t.me/@timyo97"
        )
    )
    keyboard.add(types.InlineKeyboardButton("Главное меню", callback_data="main_menu"))

    # Отправляем сообщение пользователю
    bot.send_message(
        message.chat.id,
        result_message,
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    # Очищаем данные пользователя после расчета
    del user_data[message.chat.id]


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_message = message.text.strip()

    # Проверяем нажатие кнопки "Рассчитать автомобиль"
    if user_message == CALCULATE_CAR_TEXT:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите ссылку на автомобиль с одного из сайтов (encar.com, kbchachacha.com, web.chutcha.net):",
        )

    elif user_message == "Ручной расчёт":
        # Запрашиваем возраст автомобиля
        keyboard = types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True
        )
        keyboard.add("До 3 лет", "От 3 до 5 лет")
        keyboard.add("От 5 до 7 лет", "Более 7 лет")

        bot.send_message(
            message.chat.id,
            "Выберите возраст автомобиля:",
            reply_markup=keyboard,
        )
        bot.register_next_step_handler(message, process_car_age)

    elif user_message == "Заказ запчастей":
        bot.send_message(
            message.chat.id,
            "Для оформления заявки на заказ запчастей пожалуйста напишите нашему менеджеру\n@KHAN_ALEX2022",
        )

    # Проверка на корректность ссылки
    elif re.match(
        r"^https?://(www|fem)\.encar\.com/.*|^https?://(www\.)?kbchachacha\.com/.*|^https?://(web\.)?chutcha\.net/.*",
        user_message,
    ):
        calculate_cost(user_message, message)

    # Проверка на другие команды
    elif user_message == "Написать менеджеру":
        managers_list = [
            {"name": "Ким Артур (Корея)", "whatsapp": "https://wa.me/821029348855"},
            {"name": "Ким Артур (Россия)", "whatsapp": "https://wa.me/79999000070"},
            {"name": "Тимур", "whatsapp": "https://wa.me/821055280997"},
            # {"name": "Александр", "whatsapp": "https://wa.me/821051288082"},
        ]

        # Формируем сообщение со списком менеджеров
        message_text = "Вы можете связаться с одним из наших менеджеров:\n\n"
        for manager in managers_list:
            message_text += f"[{manager['name']}]({manager['whatsapp']})\n"

        # Отправляем сообщение с использованием Markdown
        bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

    elif user_message == "Написать в WhatsApp":
        contacts = [
            {"name": "Константин", "phone": "+82 10-7650-3034"},
            {"name": "Владимир", "phone": "+82 10-7930-2218"},
            {"name": "Илья", "phone": "+82 10-3458-2205"},
        ]

        message_text = "\n".join(
            [
                f"[{contact['name']}](https://wa.me/{contact['phone'].replace('+', '')})"
                for contact in contacts
            ]
        )
        bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

    elif user_message == "О нас":
        about_message = "AK Motors\nЮжнокорейская экспортная компания.\nСпециализируемся на поставках автомобилей из Южной Кореи в страны СНГ.\nОпыт работы более 5 лет.\n\nПочему выбирают нас?\n• Надежность и скорость доставки.\n• Индивидуальный подход к каждому клиенту.\n• Полное сопровождение сделки.\n\n💬 Ваш путь к надежным автомобилям начинается здесь!"
        bot.send_message(message.chat.id, about_message)

    elif user_message == "Telegram-канал":
        channel_link = "https://t.me/akmotors96"
        bot.send_message(
            message.chat.id, f"Подписывайтесь на наш Telegram-канал: {channel_link}"
        )
    elif user_message == "Instagram":
        instagram_link = "https://www.instagram.com/ak_motors_export"
        bot.send_message(
            message.chat.id,
            f"Посетите наш Instagram: {instagram_link}",
        )
    elif user_message == "Tik-Tok":
        tiktok_link = "https://www.tiktok.com/@kpp_motors"
        bot.send_message(
            message.chat.id,
            f"Следите за свежим контентом на нашем TikTok: {tiktok_link}",
        )
    elif user_message == "Facebook":
        facebook_link = "https://www.facebook.com/share/1D8bg2xL1i/?mibextid=wwXIfr"
        bot.send_message(
            message.chat.id,
            f"KPP Motors на Facebook: {facebook_link}",
        )
    else:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите корректную ссылку на автомобиль с сайта www.encar.com или fem.encar.com.",
        )


# Run the bot
if __name__ == "__main__":
    # initialize_db()
    set_bot_commands()
    get_rub_to_krw_rate()
    get_currency_rates()
    get_usdt_to_krw_rate()
    bot.polling(non_stop=True)
