# -*- coding: utf-8 -*-

import sqlite3
import telebot
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8011487557:AAGpAS7G9CvJhvBdSpiiYd5DsUHnEOniOaI"
ADMIN_ID = 1766101476
bot = telebot.TeleBot(TOKEN)

DB_PATH = "/home/bitnami/schoolar/database.db"
ADMINS_DB_PATH = "/home/bitnami/schoolar/admins.db"

def init_admins_db():
    conn = sqlite3.connect(ADMINS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
    """)
    # Добавляем главного админа, если его нет
    cursor.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)", (ADMIN_ID, ""))
    conn.commit()
    conn.close()

init_admins_db()

def create_table(group_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS '{group_id}' (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 0,
            last_play INTEGER DEFAULT 0,
            character_level INTEGER DEFAULT 1,
            farm_level INTEGER DEFAULT 1,
            vampirism INTEGER DEFAULT 0,
            clprice INTEGER DEFAULT 70,
            farmprice INTEGER DEFAULT 120,
            vamprice INTEGER DEFAULT 100,
            chronos BOOLEAN DEFAULT 0,
            ares BOOLEAN DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def check_admin(user_id):
    conn = sqlite3.connect(ADMINS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None or user_id == ADMIN_ID

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if not message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return

    try:
        _, identifier = message.text.split()
    except ValueError:
        bot.reply_to(message, "Использование: /admin id/username")
        return

    conn = sqlite3.connect(ADMINS_DB_PATH)
    cursor = conn.cursor()

    # Проверяем, является ли identifier числом (ID)
    if identifier.isdigit():
        user_id = int(identifier)
        cursor.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)", (user_id, ""))
        bot.reply_to(message, f"Пользователь с ID {user_id} добавлен в администраторы.")
    else:
        # Удаляем @ если он есть
        username = identifier[1:] if identifier.startswith('@') else identifier
        cursor.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (NULL, ?)", (username,))
        bot.reply_to(message, f"Пользователь @{username} добавлен в администраторы.")

    conn.commit()
    conn.close()

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return

    try:
        _, target_username, ban_time = message.text.split()
        if not target_username.startswith('@'):
            raise ValueError("Неправильный формат имени пользователя.")
        ban_time = int(ban_time)
    except ValueError:
        bot.reply_to(message, "Использование: /ban @username time (минуты)")
        return

    group_id = message.chat.id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_id FROM '{group_id}' WHERE username = ?", (target_username[1:],))
    target_user_id = cursor.fetchone()
    
    if not target_user_id:
        bot.reply_to(message, f"Пользователь {target_username} не найден в этой группе.")
        conn.close()
        return

    target_user_id = target_user_id[0]
    ban_until = int(time.time()) + (ban_time * 60)
    cursor.execute(f"UPDATE '{group_id}' SET last_play = ? WHERE user_id = ?", (ban_until, target_user_id))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"Пользователь {target_username} забанен на {ban_time} минут.")

@bot.message_handler(commands=['reset'])
def reset_data(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return

    try:
        _, subcommand, target_username = message.text.split()
        if not target_username.startswith('@'):
            raise ValueError("Неправильный формат имени пользователя.")
    except ValueError:
        bot.reply_to(message, "Использование: /reset time/stats @username")
        return

    group_id = message.chat.id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_id FROM '{group_id}' WHERE username = ?", (target_username[1:],))
    target_user_id = cursor.fetchone()
    
    if not target_user_id:
        bot.reply_to(message, f"Пользователь {target_username} не найден в этой группе.")
        conn.close()
        return

    target_user_id = target_user_id[0]

    if subcommand == 'time':
        cursor.execute(f"UPDATE '{group_id}' SET last_play = 0 WHERE user_id = ?", (target_user_id,))
        bot.reply_to(message, f"Время перезарядки для {target_username} сброшено.")
    elif subcommand == 'stats':
        cursor.execute(f"UPDATE '{group_id}' SET points = 0, last_play = 0, character_level = 1, farm_level = 1, vampirism = 0, clprice = 70, farmprice = 120, vamprice = 100, chronos = 0, ares = 0 WHERE user_id = ?", (target_user_id,))
        bot.reply_to(message, f"Статистика {target_username} сброшена.")
    else:
        bot.reply_to(message, "Использование: /reset time/stats @username")
        return

    conn.commit()
    conn.close()

@bot.message_handler(commands=['add'])
def add_points(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return

    try:
        _, subcommand, target_username, points = message.text.split()
        if not target_username.startswith('@') or subcommand != 'points':
            raise ValueError("Неправильный формат команды.")
        points = int(points)
    except ValueError:
        bot.reply_to(message, "Использование: /add points @username количество")
        return

    group_id = message.chat.id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_id FROM '{group_id}' WHERE username = ?", (target_username[1:],))
    target_user_id = cursor.fetchone()
    
    if not target_user_id:
        bot.reply_to(message, f"Пользователь {target_username} не найден в этой группе.")
        conn.close()
        return

    target_user_id = target_user_id[0]
    cursor.execute(f"UPDATE '{group_id}' SET points = points + ? WHERE user_id = ?", (points, target_user_id))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"Пользователю {target_username} добавлено {points} очков.")

@bot.message_handler(commands=['set'])
def set_skill(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return

    try:
        _, subcommand, skill_name, level = message.text.split()
        level = int(level)
    except ValueError:
        bot.reply_to(message, "Использование: /set skill название уровень")
        return

    group_id = message.chat.id
    skill_column = {
        'character': 'character_level',
        'farm': 'farm_level',
        'vampirism': 'vampirism',
        'ares': 'ares',
        'chronos': 'chronos'
    }.get(skill_name.lower())

    if not skill_column:
        bot.reply_to(message, "Недопустимое название способности. Используйте character, farm, vampirism, ares или chronos.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE '{group_id}' SET {skill_column} = ? WHERE user_id = ?", (level, message.from_user.id))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"Уровень способности {skill_name} установлен на {level}.")

@bot.message_handler(commands=['info'])
def user_info(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return

    try:
        _, target_username = message.text.split()
        if not target_username.startswith('@'):
            raise ValueError("Неправильный формат имени пользователя.")
    except ValueError:
        bot.reply_to(message, "Использование: /info @username")
        return

    group_id = message.chat.id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM '{group_id}' WHERE username = ?", (target_username[1:],))
    user_data = cursor.fetchone()
    conn.close()

    if not user_data:
        bot.reply_to(message, f"Пользователь {target_username} не найден.")
        return

    response = (f"Информация о {target_username}:\n"
                f"Очки: {user_data[2]}\n"
                f"Время последней игры: {user_data[3]}\n"
                f"Уровень персонажа: {user_data[4]}\n"
                f"Уровень фермы: {user_data[5]}\n"
                f"Вампиризм: {user_data[6]}\n"
                f"Цена повышения уровня персонажа: {user_data[7]}\n"
                f"Цена повышения уровня фермы: {user_data[8]}\n"
                f"Цена повышения вампиризма: {user_data[9]}\n"
                f"Chronos: {'Да' if user_data[10] else 'Нет'}\n"
                f"Ares: {'Да' if user_data[11] else 'Нет'}")
    bot.reply_to(message, response)

@bot.message_handler(commands=['stop'])
def stop_bot(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return

    bot.reply_to(message, "Бот остановлен.")
    bot.stop_polling()

bot.polling(none_stop=True)
