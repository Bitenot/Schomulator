import sqlite3
import telebot
import random
import time
import os
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "7706693485:AAHLoO_HL0SEtjVlHBufRVPaX6DTB1_kVv8"

bot = telebot.TeleBot(TOKEN)

DB_PATH = r"C:\Users\shado\OneDrive\Documents\Telebot\database.db"

# Function to create a table if necessary
def create_table(group_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS '{group_id}' (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 0,
            last_play INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def check_achievement(points):
    return "\n\n🔞Достижения: Настя на ферме🔞" if points > 500 else ""

# Function to update local and global rankings
def get_rankings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Global ranking
    cursor.execute("SELECT user_id, SUM(points) FROM (" +
               " UNION ALL ".join(
                   [f"SELECT user_id, points FROM '{table[0]}'"
                    for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")]
               ) +
               ") GROUP BY user_id ORDER BY SUM(points) DESC"
)
    global_ranks = {row[0]: idx + 1 for idx, row in enumerate(cursor.fetchall())}
    
    conn.close()
    return global_ranks

# Command /play
@bot.message_handler(commands=['play'])
def play_game(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    group_id = message.chat.id
    create_table(group_id)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get the current user
    cursor.execute(f"SELECT points, last_play FROM '{group_id}' WHERE user_id = ?", (user_id, ))
    row = cursor.fetchone()
    
    now = int(time.time())
    if row:
        points, last_play = row
        if now - last_play < 43200:  # 12 hours = 43200 seconds
            bot.reply_to(message, "Не запрягайте своих рабов, подождите 12 часов. У нас 21 век!")
            return
    else:
        points, last_play = 0, 0
        cursor.execute(f"INSERT INTO '{group_id}' (user_id, username, points, last_play) VALUES (?, ?, 0, 0)", (user_id, username))
    
    # Calculate points change
    if random.random() < 0.3:
        delta = -random.randint(1, 5)
    else:
        delta = random.randint(1, 10)
    points += delta
    
    # Update user data
    cursor.execute(f"UPDATE '{group_id}' SET points = ?, last_play = ? WHERE user_id = ?", (points, now, user_id))
    conn.commit()
    
    achievement = check_achievement(points)
    achievement_text = f"\n{achievement}" if achievement else ""
    
    # Get rankings
    cursor.execute(f"SELECT user_id, points FROM '{group_id}' ORDER BY points DESC")
    local_ranks = {row[0]: idx + 1 for idx, row in enumerate(cursor.fetchall())}
    global_ranks = get_rankings()
    
    local_place = local_ranks.get(user_id, "N/A")
    global_place = global_ranks.get(user_id, "N/A")
    
    bot.reply_to(message, f"@{username}, твоё количество рабов изменилось на {delta}.\n"
                           f"Теперь у вас {points} Школьных.\n"
                           f"Вы занимаете {local_place} место в локальном топе."
                           f"{achievement}")
    
    conn.close()

# Command /statistic
@bot.message_handler(commands=['statistic'])
def show_stats(message):
    group_id = message.chat.id
    user_id = message.from_user.id
    create_table(group_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT username, points FROM '{group_id}' WHERE user_id = ?", (user_id,))
    stats = cursor.fetchone()
    conn.close()
    
    if not stats:
        bot.reply_to(message, "Вы ещё не играли!")
        return
    
    username, points = stats
    response = f"@{username}, у вас {points} Школьных."
    bot.reply_to(message, response)
    
@bot.message_handler(commands=['localtop'])
def show_stats(message):
    group_id = message.chat.id
    create_table(group_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT username, points FROM '{group_id}' ORDER BY points DESC")
    stats = cursor.fetchall()
    conn.close()
    
    if not stats:
        bot.reply_to(message, "Пока никто не играл!")
        return
    
    response = "🏆 Локальный рейтинг: \n" + "\n".join([f"{idx+1}. @{row[0]} - {row[1]} Школьных" for idx, row in enumerate(stats)])
    bot.reply_to(message, response)
    
# Command /top
@bot.message_handler(commands=['top'])
def global_top(message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    users = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT user_id, username, points FROM '{table_name}'")
        for user_id, username, points in cursor.fetchall():
            if user_id not in users or users[user_id][1] < points:
                users[user_id] = (username, points)
    
    sorted_users = sorted(users.values(), key=lambda x: x[1], reverse=True)
    top_list = "\n".join([f"{i+1}. @{user[0]} - {user[1]} рабов" for i, user in enumerate(sorted_users[:10])])
    conn.close()
    
    bot.reply_to(message, "🏆Глобальный рейтинг:\n" + (top_list if top_list else "Пока никто не играет."))

# Command /help
# Command /help
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "Прокачать ферму Школьных - /play.\nПросмотреть статистику - /statistic.\nГлобальный топ фермеров - /top.\n"
                           "Список команд: /commands.\n"
                           "Бросить вызов другому игроку - /battlez @username.")

@bot.message_handler(commands=['events'])
def events_command(message):
    bot.reply_to(message, "💵Информация о текущих событиях:\n"
                          "⭐️В честь возвращения Школьного с фермы мы запускаем эевент Возвращение!\nВремя перезарядки сокращено до 3-х часов!\nА так же вы имеете шанс получить 100 Школьных на свою ферму⭐️!!!!")

# Command /battlez
@bot.message_handler(commands=['battlez'])
def battlez_command(message):
    try:
        _, target_username = message.text.split()
        if not target_username.startswith('@'):
            raise ValueError("Неправильный формат имени пользователя.")
    except ValueError:
        bot.reply_to(message, "Использование: /battlez @username")
        return

    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
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
    
    markup = InlineKeyboardMarkup()
    accept_button = InlineKeyboardButton("Принять вызов", callback_data=f"accept_battle|{user_id}|{target_user_id}|{group_id}")
    markup.add(accept_button)
    
    sent_message = bot.reply_to(message, f"@{username} бросил вызов {target_username}", reply_markup=markup)
    conn.close()

def handle_battle_callback(call):
    if not call.data.startswith("accept_battle"):
        return

    _, challenger_id, target_id, group_id = call.data.split('|')
    challenger_id = int(challenger_id)
    target_id = int(target_id)
    group_id = int(group_id)

    if call.from_user.id != target_id:
        bot.answer_callback_query(call.id, "Вы не можете принять этот вызов.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"SELECT points FROM '{group_id}' WHERE user_id = ?", (challenger_id,))
    challenger_points = cursor.fetchone()[0]

    cursor.execute(f"SELECT points FROM '{group_id}' WHERE user_id = ?", (target_id,))
    target_points = cursor.fetchone()[0]

    if random.random() < 0.5:
        delta = random.randint(1, 10)
        winner_id, loser_id, points = target_id, challenger_id, delta
    else:
        delta = random.randint(1, 10)
        winner_id, loser_id, points = challenger_id, target_id, delta

    cursor.execute(f"UPDATE '{group_id}' SET points = points + ? WHERE user_id = ?", (points, winner_id))
    cursor.execute(f"UPDATE '{group_id}' SET points = points - ? WHERE user_id = ?", (points, loser_id))
    conn.commit()

    cursor.execute(f"SELECT username, points FROM '{group_id}' WHERE user_id = ?", (winner_id,))
    winner_username, winner_points = cursor.fetchone()

    cursor.execute(f"SELECT username, points FROM '{group_id}' WHERE user_id = ?", (loser_id,))
    loser_username, loser_points = cursor.fetchone()
    
    conn.close()

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"Битва завершена! @{winner_username} победил @{loser_username} и получил {points} очков.\n\n"
                               f"Баланс @{winner_username}: {winner_points} Школьных.\n"
                               f"Баланс @{loser_username}: {loser_points} Школьных.")

bot.register_callback_query_handler(handle_battle_callback, func=lambda call: call.data.startswith("accept_battle"))

bot.polling(none_stop=True)
