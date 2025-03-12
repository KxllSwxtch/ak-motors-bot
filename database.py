import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  # Берём из переменных окружения


def connect_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def create_tables():
    """Создаём таблицу заказов, если её нет."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    car_id TEXT NOT NULL,  -- ✅ Добавили car_id
                    title TEXT NOT NULL,
                    price TEXT,
                    link TEXT NOT NULL,
                    year TEXT,
                    month TEXT,
                    mileage TEXT,
                    engine_volume INT,
                    transmission TEXT,
                    user_name TEXT,
                    full_name TEXT,
                    phone_number TEXT,
                    images TEXT[],
                    status TEXT DEFAULT '🔄 Не заказано',
                    total_cost_usd FLOAT,
                    total_cost_krw FLOAT,
                    total_cost_rub FLOAT
                );
            """
            )

            # ✅ Добавляем таблицу расчётов
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS calculations (
                    user_id BIGINT PRIMARY KEY,
                    count INT DEFAULT 0
                );
            """
            )

            conn.commit()


def add_order(order):
    """Добавляем заказ в базу данных."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO orders (user_id, car_id, title, price, link, year, month, mileage, engine_volume, 
                                    transmission, user_name, phone_number, images, status, total_cost_usd, total_cost_krw, total_cost_rub)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """,
                (
                    order["user_id"],
                    order["car_id"],
                    order["title"],
                    order["price"],
                    order["link"],
                    order["year"],
                    order["month"],
                    order["mileage"],
                    order["engine_volume"],
                    order["transmission"],
                    order["user_name"],
                    order["phone_number"],
                    order["images"],
                    order["status"],
                    order["total_cost_usd"],
                    order["total_cost_krw"],
                    order["total_cost_rub"],
                ),
            )
            conn.commit()


def get_orders(user_id):
    """Получает список заказов пользователя из базы данных"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, car_id, title, status, link, year, month, mileage, engine_volume, transmission,
               total_cost_usd, total_cost_krw, total_cost_rub, user_name, full_name
        FROM orders
        WHERE user_id = %s
    """,
        (user_id,),
    )

    orders = cur.fetchall()
    cur.close()
    conn.close()

    # Преобразуем в список словарей
    return [
        {
            "id": order[1],  # ✅ car_id теперь вместо id
            "car_id": order[1],
            "title": order[2],
            "status": order[3],
            "link": order[4],
            "year": order[5],
            "month": order[6],
            "mileage": order[7],
            "engine_volume": order[8],
            "transmission": order[9],
            "total_cost_usd": order[10],
            "total_cost_krw": order[11],
            "total_cost_rub": order[12],
            "user_name": order[13],
            "full_name": order[14],  # ✅ ФИО клиента теперь загружается
        }
        for order in orders
    ]


def get_all_orders():
    """Получает список всех заказов для менеджеров"""
    with connect_db() as conn:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:  # ✅ Добавили `RealDictCursor`
            cur.execute(
                """
                SELECT id, car_id, user_id, user_name, phone_number, title, status, link, 
                       year, month, mileage, engine_volume, transmission, 
                       total_cost_usd, total_cost_krw, total_cost_rub, full_name
                FROM orders
            """
            )
            orders = cur.fetchall()

    return orders  # Теперь `orders` — список словарей, а не кортежей!


def update_order_status_in_db(order_id, new_status):
    """Обновляет статус заказа в базе данных"""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = %s WHERE id = %s;",  # ❗ Используем `id`
                (new_status, order_id),
            )
            conn.commit()


def update_user_phone(user_id, phone_number, car_id):
    """Обновляет номер телефона в конкретном заказе пользователя."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE orders SET phone_number = %s WHERE user_id = %s AND car_id = %s;",  # ✅ Обновляем только один заказ
                (phone_number, user_id, str(car_id)),
            )
            conn.commit()


def delete_order_from_db(order_id):
    """Удаляет заказ из базы данных по order_id"""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM orders WHERE id = %s;", (order_id,))
            conn.commit()
    print(f"✅ Заказ {order_id} удалён из базы!")


def update_user_name(user_id, full_name):
    """Обновляет ФИО пользователя в базе данных."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE orders SET user_name = %s WHERE user_id = %s;",
                (full_name, user_id),
            )
            conn.commit()


def get_calculation_count(user_id):
    """Получает количество расчётов пользователя."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count FROM calculations WHERE user_id = %s;", (user_id,)
            )
            result = cur.fetchone()
            return result["count"] if result else 0


def increment_calculation_count(user_id):
    """Увеличивает количество расчётов пользователя."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO calculations (user_id, count)
                VALUES (%s, 1)
                ON CONFLICT (user_id) DO UPDATE 
                SET count = calculations.count + 1;
                """,
                (user_id,),
            )
            conn.commit()


def reset_calculation_count(user_id):
    """Сбрасывает количество расчётов (например, после подписки)."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE calculations SET count = 0 WHERE user_id = %s;", (user_id,)
            )
            conn.commit()
