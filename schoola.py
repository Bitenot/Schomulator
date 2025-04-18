# -*- coding: utf-8 -*-
import sqlite3
import telebot
import random
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from telebot.types import Message
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "7706693485:AAHLoO_HL0SEtjVlHBufRVPaX6DTB1_kVv8"

bot = telebot.TeleBot(TOKEN)
AUTHORIZED_USER_ID = 1866831769
DB_PATH = "/home/bitnami/schoolar/database.db"

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
            clprice INTEGER DEFAULT 60,
            farmprice INTEGER DEFAULT 85,
            vamprice INTEGER DEFAULT 70,
            chronos BOOLEAN DEFAULT 0,
            ares BOOLEAN DEFAULT 0
        )
    """)

    columns = {
        "character_level": "INTEGER DEFAULT 1",
        "farm_level": "INTEGER DEFAULT 1",
        "vampirism": "INTEGER DEFAULT 0",
        "clprice": "INTEGER DEFAULT 60",
        "farmprice": "INTEGER DEFAULT 85",
        "vamprice": "INTEGER DEFAULT 70",
        "chronos": "BOOLEAN DEFAULT 0",
        "ares": "BOOLEAN DEFAULT 0"
    }
    for column, column_type in columns.items():
        cursor.execute(f"PRAGMA table_info('{group_id}')")
        existing_columns = [info[1] for info in cursor.fetchall()]
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE '{group_id}' ADD COLUMN {column} {column_type}")
    conn.commit()
    conn.close()


def get_time_word(value: int, word_type: str) -> str:
    forms = {
        'секунда': ('секунда', 'секунды', 'секунд'),
        'минута': ('минута', 'минуты', 'минут'),
        'час': ('час', 'часа', 'часов'),
    }

    if word_type not in forms:
        raise ValueError("Неверный тип времени. Используй: 'секунда', 'минута', 'час'.")

    n = abs(value)
    last_two = n % 100
    last_digit = n % 10

    # Определение формы слова
    if 11 <= last_two <= 14:
        form = forms[word_type][2]
    elif last_digit == 1:
        form = forms[word_type][0]
    elif 2 <= last_digit <= 4:
        form = forms[word_type][1]
    else:
        form = forms[word_type][2]

    return f"{value} {form}"

def check_achievement(points):
    return "\n\n🔞 Достижения: Настя на ферме 🔞" if points > 500 else ""

def get_rankings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

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

@bot.message_handler(commands=['admins'])
def admin_list(message):
    bot.reply_to(message, "🛡️ Действующие администраторы:\n\n👑 @Thermobyte - Owner\n⚜️ @lllapas - Heiress\n🤖 @AC_EvelineBot - Admin-bot")

@bot.message_handler(commands=['play'])
def play_game(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    group_id = message.chat.id
    create_table(group_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT points, last_play, character_level, farm_level, vampirism, chronos, ares FROM '{group_id}' WHERE user_id = ?",
        (user_id,))
    row = cursor.fetchone()

    now = int(time.time())
    if row:
        points, last_play, character_level, farm_level, vampirism, chronos, ares = row
        cooldown_time = 11880 if chronos else 19800
        if now - last_play < cooldown_time:
            remaining_time = cooldown_time - (now - last_play)
            hours, remainder = divmod(remaining_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            bot.reply_to(message,
                         f"Не запрягайте своих рабов, подождите {get_time_word(hours, 'час')} {get_time_word(minutes, 'минута')} {get_time_word(seconds, 'секунда')}. У нас 21 век!")
            return
    else:
        points, last_play, character_level, farm_level, vampirism, chronos, ares = 0, 0, 1, 1, 0, 0, 0
        cursor.execute(
            f"INSERT INTO '{group_id}' (user_id, username, points, last_play, character_level, farm_level, vampirism, chronos, ares) VALUES (?, ?, 0, 0, 1, 1, 0, 0, 0)",
            (user_id, username))


    jackpot_chance = 0.05
    if ares:
        if random.random() <= jackpot_chance:
            delta = 150
            bot.reply_to(message, f"🎉 Джекпот! Вы выиграли 150 очков! 🎉")
        else:
            delta = random.randint(1, 10 + (farm_level - 1) * 5)
        
    else:
        if random.random() <= jackpot_chance:
            delta = 150
            bot.reply_to(message, f"🎉 Джекпот! Вы выиграли 150 очков! 🎉")
        elif random.random() < 0.65:
            delta = random.randint(1, 10 + (farm_level - 1) * 5)
        else:
            delta = -random.randint(1, 10 + (farm_level - 1) * 3)

    if character_level > 1 and random.random() < 0.1 + 0.15 * (character_level - 1):
        delta += random.randint(1, 10 + (farm_level - 1) * 3)

    if vampirism > 0 and random.random() < 0.3:
        cursor.execute(f"SELECT user_id FROM '{group_id}' WHERE user_id != ?", (user_id,))
        other_users = cursor.fetchall()
        if other_users:
            victim_id = random.choice(other_users)[0]
            stolen_points = 3 * vampirism
            cursor.execute(f"UPDATE '{group_id}' SET points = points - ? WHERE user_id = ?", (stolen_points, victim_id))
            bot.reply_to(message, f"Вы забрали {stolen_points} Школьных")
            delta += stolen_points

    points += delta

    cursor.execute(f"UPDATE '{group_id}' SET points = ?, last_play = ? WHERE user_id = ?", (points, now, user_id))
    conn.commit()

    achievement = check_achievement(points)
    achievement_text = f"\n{achievement}" if achievement else ""

    cursor.execute(f"SELECT user_id, points FROM '{group_id}' ORDER BY points DESC")
    local_ranks = {row[0]: idx + 1 for idx, row in enumerate(cursor.fetchall())}
    global_ranks = get_rankings()

    local_place = local_ranks.get(user_id, "N/A")
    global_place = global_ranks.get(user_id, "N/A")

    bot.reply_to(message, f"💵 @{username}, твоё количество рабов изменилось на {delta}.\n"
                          f"👨🏿‍🦲 Теперь у вас {points} Школьных.\n"
                          f"🏆 Вы занимаете {local_place} место в локальном топе.")

    conn.close()


@bot.message_handler(commands=['statistic'])
def show_stats(message):
    group_id = message.chat.id
    user_id = message.from_user.id
    create_table(group_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT username, points, character_level, farm_level, vampirism, chronos, ares FROM '{group_id}' WHERE user_id = ?",
        (user_id,))
    stats = cursor.fetchone()
    conn.close()

    if not stats:
        bot.reply_to(message, "😰 Вы ещё не играли!")
        return

    username, points, character_level, farm_level, vampirism, chronos, ares = stats
    achievement = check_achievement(points)
    achievement_text = f"\n{achievement}" if achievement else "У вас нет достижений"

    response = f"📜 Ваша статистика:\n\n"\
               f"👨🏿‍🦲 @{username}, у вас {points} Школьных.\n" \
               f"🧑🏻‍🌾 Уровень персонажа: {character_level}\n" \
               f"🏡 Уровень фермы: {farm_level}\n" \
               f"🧛🏻‍♀️ Вампиризм: {vampirism}\n" \
               f"➖ Минусофобия: {'Есть' if ares else 'Нету'}\n" \
               f"⌛️ Часы Кроноса: {'Есть' if chronos else 'Нету'}\n"\
               f"🟡 {achievement_text}"
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
        bot.reply_to(message, "👿 Пока никто не играл!")
        return

    medals = ["🥇", "🥈", "🥉"]
    response = "🏆 Локальный рейтинг:\n\n"

    for idx, row in enumerate(stats):
        medal = medals[idx] if idx < 3 else f"{idx + 1}."
        response += f"{medal} @{row[0]} - {row[1]} 👨🏿‍🦲Школьных\n"

    bot.reply_to(message, response)


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

    # Exclude user with ID 6837339007
    users = {k: v for k, v in users.items() if k != 6837339007}

    sorted_users = sorted(users.items(), key=lambda x: x[1][1], reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    top_list = ""

    for i, (uid, (uname, pts)) in enumerate(sorted_users[:10]):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        if uid == 5375127224:
            top_list += f"{prefix} @{uname} - ♾️ рабов\n"
        else:
            top_list += f"{prefix} @{uname} - {pts} рабов\n"

    conn.close()
    response = "🏆 Глобальный рейтинг:\n\n" + (top_list if top_list else "🤬 Пока никто не играет.")
    bot.reply_to(message, response)


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message,
                 "🏡 Прокачать ферму Школьных - /play.\n🧐 Просмотреть статистику - /statistic.\n🏆 Глобальный топ фермеров - /top.\n"
                 "📖 Список команд: /commands.\n"
                 "⚔️ Бросить вызов другому игроку - /battlez @username.\n"
                 "⬆️ Прокачать уровни - /upgrade")


@bot.message_handler(commands=['events'])
def events_command(message):
    bot.reply_to(message, "📜 Информация о текущих событиях:\n"
                          "❌ Финальная стадия разработки. Конец сезона!\n\n Игрок который по окончанию сезона наберёт больше всего очков или ценность его статистики будет самой высокой - 84грн в звёздах телеграм")

@bot.message_handler(commands=['battlez'])
def battlez_command(message):
    try:
        _, target_username = message.text.split()
        if not target_username.startswith('@'):
            raise ValueError("❌ Неправильный формат имени пользователя.")
    except ValueError:
        bot.reply_to(message, "✅ Использование: /battlez @username")
        return

    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    group_id = message.chat.id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_id, points FROM '{group_id}' WHERE username = ?", (target_username[1:],))
    target_user = cursor.fetchone()

    if not target_user:
        bot.reply_to(message, f"❌ Пользователь {target_username} не найден в этой группе.")
        conn.close()
        return

    target_user_id, target_points = target_user
    if target_points <= 0:
        bot.reply_to(message, f"❌ Пользователя @{target_username} нельзя вызвать на дуэль, так как у него недостаточно очков.")
        conn.close()
        return

    if user_id == 6113547946:
        handle_battle(user_id, target_user_id, group_id, auto_accept=True)
    else:
        markup = InlineKeyboardMarkup()
        accept_button = InlineKeyboardButton("✅",
                                             callback_data=f"accept_battle|{user_id}|{target_user_id}|{group_id}")
        markup.add(accept_button)
        sent_message = bot.reply_to(message, f"⚔️ @{username} бросил вызов {target_username}", reply_markup=markup)
    conn.close()


def handle_battle_callback(call):
    if not call.data.startswith("accept_battle"):
        return

    _, challenger_id, target_id, group_id = call.data.split('|')
    challenger_id = int(challenger_id)
    target_id = int(target_id)
    group_id = int(group_id)

    if call.from_user.id != target_id:
        bot.answer_callback_query(call.id, "❌Вы не можете принять этот вызов.")
        return

    handle_battle(challenger_id, target_id, group_id, call=call)


def handle_battle(challenger_id, target_id, group_id, call=None, auto_accept=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"SELECT points FROM '{group_id}' WHERE user_id = ?", (challenger_id,))
    challenger_points = cursor.fetchone()[0]

    cursor.execute(f"SELECT points FROM '{group_id}' WHERE user_id = ?", (target_id,))
    target_points = cursor.fetchone()[0]

    if challenger_id == 1766101476:
        win_chance = 0.85
        max_points = 25
    else:
        win_chance = 0.5
        max_points = 25

    if random.random() < win_chance:
        delta = random.randint(1, max_points)
        winner_id, loser_id, points = challenger_id, target_id, delta
    else:
        delta = random.randint(1, max_points)
        winner_id, loser_id, points = target_id, challenger_id, delta

    cursor.execute(f"UPDATE '{group_id}' SET points = points + ? WHERE user_id = ?", (points, winner_id))
    cursor.execute(f"UPDATE '{group_id}' SET points = points - ? WHERE user_id = ?", (points, loser_id))
    conn.commit()

    cursor.execute(f"SELECT username, points FROM '{group_id}' WHERE user_id = ?", (winner_id,))
    winner_username, winner_points = cursor.fetchone()

    cursor.execute(f"SELECT username, points FROM '{group_id}' WHERE user_id = ?", (loser_id,))
    loser_username, loser_points = cursor.fetchone()

    conn.close()

    if call:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"⚔️ Битва завершена! @{winner_username} победил @{loser_username} и получил {points} очков.\n\n"
                                   f"👨🏿‍🦲 Баланс @{winner_username}: {winner_points} Школьных.\n"
                                   f"👨🏿‍🦲 Баланс @{loser_username}: {loser_points} Школьных.")
    else:
        bot.send_message(group_id,
                         text=f"⚔️ Битва завершена! @{winner_username} победил @{loser_username} и получил {points} очков.\n\n"
                              f"👨🏿‍🦲 Баланс @{winner_username}: {winner_points} Школьных.\n"
                              f"👨🏿‍🦲 Баланс @{loser_username}: {loser_points} Школьных.")


@bot.message_handler(commands=['upgradeinfo'])
def help_command(message):
    bot.reply_to(message,
                 "💵\n\nПрокачка рабовладельца даёт вам +17% шанса к получению дополнительных рабов на свою ферму за каждый уровень от 1 до 10 + очки от уровня фермы. Максимум: 5.\n\nПрокачка фермы повышает максимально возможное число получения и уменьшения рабов за 1 игру на 5 за каждый уровень.\n\nСпособность вампиризм даёт 30% шанс выкачать из рандомного игрока 5 очков + 3 за каждый уровень. Максимум: 7\n\nЧасы кроноса снижают время перезарядки /play на 40%")


@bot.message_handler(commands=['upgrade'])
def upgrade_command(message):
    user_id = message.from_user.id
    group_id = message.chat.id
    create_table(group_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT clprice, farmprice, vamprice, chronos FROM '{group_id}' WHERE user_id = ?", (user_id,))
    clprice, farmprice, vamprice, chronos = cursor.fetchone()
    conn.close()

    markup = InlineKeyboardMarkup()
    level_button = InlineKeyboardButton(f"👨🏿‍🦲 - {clprice}", callback_data=f"upgrade_character|{user_id}|{group_id}")
    farm_button = InlineKeyboardButton(f"🏡 - {farmprice}", callback_data=f"upgrade_farm|{user_id}|{group_id}")
    vamp_button = InlineKeyboardButton(f"🧛🏻‍♀️ - {vamprice}", callback_data=f"upgrade_vampirism|{user_id}|{group_id}")
    chronos_button = InlineKeyboardButton(f"⏳ - 150", callback_data=f"buy_chronos|{user_id}|{group_id}")
    markup.add(level_button, farm_button, vamp_button, chronos_button)

    bot.reply_to(message, "❓ Выберите, что вы хотите улучшить:", reply_markup=markup)


def handle_upgrade_callback(call):
    if call.data.startswith("upgrade_character"):
        _, user_id, group_id = call.data.split('|')
        user_id = int(user_id)
        group_id = int(group_id)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT points, character_level, clprice FROM '{group_id}' WHERE user_id = ?", (user_id,))
        points, character_level, clprice = cursor.fetchone()
        points, character_level, clprice = int(points), int(character_level), int(clprice)

        if points >= clprice and character_level < 5:
            points -= clprice
            character_level += 1
            clprice = int(clprice * 1.3)
            cursor.execute(f"UPDATE '{group_id}' SET points = ?, character_level = ?, clprice = ? WHERE user_id = ?",
                           (points, character_level, clprice, user_id))
            conn.commit()
            bot.answer_callback_query(call.id, f"👨🏿‍🦲 Уровень персонажа повышен до {character_level}!")
        else:
            bot.answer_callback_query(call.id,
                                      "❌ Недостаточно очков для повышения уровня или достигнут максимальный уровень.")

        conn.close()

    elif call.data.startswith("upgrade_farm"):
        _, user_id, group_id = call.data.split('|')
        user_id = int(user_id)
        group_id = int(group_id)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT points, farm_level, farmprice FROM '{group_id}' WHERE user_id = ?", (user_id,))
        points, farm_level, farmprice = cursor.fetchone()
        points, farm_level, farmprice = int(points), int(farm_level), int(farmprice)

        if points >= farmprice:
            points -= farmprice
            farm_level += 1
            farmprice = int(farmprice * 1.3)
            cursor.execute(f"UPDATE '{group_id}' SET points = ?, farm_level = ?, farmprice = ? WHERE user_id = ?",
                           (points, farm_level, farmprice, user_id))
            conn.commit()
            bot.answer_callback_query(call.id, f"✅ Уровень фермы повышен до {farm_level}!")
        else:
            bot.answer_callback_query(call.id, "❌ Недостаточно очков для повышения уровня.")

        conn.close()

    elif call.data.startswith("upgrade_vampirism"):
        _, user_id, group_id = call.data.split('|')
        user_id = int(user_id)
        group_id = int(group_id)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT points, vampirism, vamprice FROM '{group_id}' WHERE user_id = ?", (user_id,))
        points, vampirism, vamprice = cursor.fetchone()
        points, vampirism, vamprice = int(points), int(vampirism), int(vamprice)

        if points >= vamprice and vampirism < 7:
            points -= vamprice
            vampirism += 1
            vamprice = int(vamprice * 1.3)
            cursor.execute(f"UPDATE '{group_id}' SET points = ?, vampirism = ?, vamprice = ? WHERE user_id = ?",
                           (points, vampirism, vamprice, user_id))
            conn.commit()
            bot.answer_callback_query(call.id, f"✅ Вампиризм прокачан до {vampirism}!")
        else:
            bot.answer_callback_query(call.id,
                                      "❌ Недостаточно очков для прокачки вампиризма или достигнут максимальный уровень.")

        conn.close()

    elif call.data.startswith("buy_chronos"):
        _, user_id, group_id = call.data.split('|')
        user_id = int(user_id)
        group_id = int(group_id)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT points, chronos FROM '{group_id}' WHERE user_id = ?", (user_id,))
        points, chronos = cursor.fetchone()
        points, chronos = int(points), bool(chronos)

        if points >= 160 and not chronos:
            points -= 160
            chronos = 1
            cursor.execute(f"UPDATE '{group_id}' SET points = ?, chronos = ? WHERE user_id = ?",
                           (points, chronos, user_id))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ Часы Кроноса куплены!")
        else:
            bot.answer_callback_query(call.id, "❌ Недостаточно очков для покупки Chronos или он уже куплен.")

        conn.close()


bot.register_callback_query_handler(handle_upgrade_callback, func=lambda call: call.data.startswith(("upgrade", "buy_chronos")))
bot.register_callback_query_handler(handle_battle_callback, func=lambda call: call.data.startswith("accept_battle"))

bot.polling(none_stop=True)
