from keep_alive import keep_alive
keep_alive()
import telebot
from telebot import types
import sqlite3
import random
import time

BOT_TOKEN = "7912698597:AAF-m1I0QTNJ7d8FeEYtC7TVbw6eyc5J4yI"
CREATOR_ID = 1197898604
ADMIN_PASSWORD = "6867435597"

bot = telebot.TeleBot(BOT_TOKEN)

conn = sqlite3.connect("ocudep.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        nickname TEXT,
        points INTEGER DEFAULT 0
    )
""")
conn.commit()

user_states = {}
cooldowns = {}

def get_rank(points):
    if points < 1000:
        return "🐣 Новичок"
    elif points < 5000:
        return "🪖 Бывалый"
    elif points < 15000:
        return "🎯 Эксперт"
    elif points < 40000:
        return "🧠 Мастер"
    elif points < 80000:
        return "🔮 Гуру"
    else:
        return "👑 Бог"

def show_main_menu(message):
    uid = message.from_user.id
    state = user_states.setdefault(uid, {})
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎯 Профиль", "🎰 Рулетка")
    markup.add("🏆 Лидерборд", "📊 Ранг")
    markup.add("⚙️ Настройки", "🛠 Админ")

    if state.get("first_entry"):
        text = "👋 Добро пожаловать в OCUDEP! Выбери действие:"
        state["first_entry"] = False
    else:
        text = "🏢 Главный офис OCUDEP"

    state["left_section"] = False
    bot.send_message(message.chat.id, text, reply_markup=markup)

def show_roulette_menu(message, uid, deped=False, custom_text=None, hide_dep=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if not hide_dep:
        btn_text = "💸 Додеп" if deped else "💸 Депнуть"
        markup.add(btn_text)
    markup.add("⬅️ Ливнуть")
    text = custom_text or ("🎰 Добро пожаловать в рулетку!\nВыбери действие:" if not deped else "🎰 Желаете продолжить?")
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    user = cursor.fetchone()
    user_states[uid] = {'reg': bool(user), 'first_entry': True}
    if user:
        show_main_menu(message)
    else:
        user_states[uid]["awaiting_nickname"] = True
        bot.send_message(uid, "👤 Введи свой ник для регистрации:")
    return

@bot.message_handler(commands=['ruletka'])
def cmd_ruletka(message):
    if message.chat.type in ["group", "supergroup"]:
        show_roulette_menu(message, message.from_user.id, hide_dep=True)
    return

@bot.message_handler(commands=['profil'])
def cmd_profil(message):
    uid = message.from_user.id
    cursor.execute("SELECT nickname, points FROM users WHERE user_id = ?", (uid,))
    user = cursor.fetchone()
    if user:
        rank = get_rank(user[1])
        bot.send_message(message.chat.id, f"👤 Ник: {user[0]}\n💰 Очки: {user[1]}\n🏅 Статус: {rank}")
    else:
        bot.send_message(message.chat.id, "❌ Ты не зарегистрирован. Напиши /start")
    return

@bot.message_handler(commands=['leaderboard'])
def cmd_leaderboard(message):
    cursor.execute("SELECT nickname, points FROM users ORDER BY points DESC LIMIT 10")
    top = cursor.fetchall()
    if top:
        text = "🏆 Лидеры OCUDEP:\n"
        for i, (nick, pts) in enumerate(top, 1):
            rank = get_rank(pts)
            text += f"{i}. {nick} — {pts} очков ({rank})\n"
        bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, "❌ Лидерборд пуст.")
    return

@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    uid = message.from_user.id
    text = message.text.strip()
    state = user_states.setdefault(uid, {})
    chat_type = message.chat.type
    is_private = chat_type == "private"

    if text == "⬅️ Ливнуть":
        state.clear()
        show_main_menu(message)
        return    
    if text == "🛠 Админ" and is_private:
        if state.get("admin_access"):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🧩 Управление", "🚫 Забанить", "⬅️ Ливнуть")
            bot.send_message(uid, "✅ Вы уже авторизованы.", reply_markup=markup)
        else:
            state["awaiting_admin_password"] = True
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("⬅️ Ливнуть")
            bot.send_message(uid, "🔐 Введите пароль для входа:", reply_markup=markup)
        return

    if state.get("awaiting_admin_password"):
        if text == ADMIN_PASSWORD:
            state["admin_access"] = True
            state["awaiting_admin_password"] = False
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🧩 Управление", "🚫 Забанить", "⬅️ Ливнуть")
            bot.send_message(uid, "✅ Доступ к админке открыт.", reply_markup=markup)
        else:
            state["awaiting_admin_password"] = False
            bot.send_message(uid, "🚫 Неверный пароль.")
            show_main_menu(message)
        return

    if state.get("awaiting_nickname"):
        nickname = text
        cursor.execute("INSERT INTO users (user_id, nickname) VALUES (?, ?)", (uid, nickname))
        conn.commit()
        state["awaiting_nickname"] = False
        bot.send_message(CREATOR_ID, f"🆕 Новый пользователь зарегистрирован:\n👤 Ник: {nickname}\n🆔 ID: {uid}")
        bot.send_message(uid, f"✅ Ник '{nickname}' зарегистрирован!")
        show_main_menu(message)
        return

    if state.get("awaiting_new_nickname"):
        new_nick = text
        cursor.execute("UPDATE users SET nickname = ? WHERE user_id = ?", (new_nick, uid))
        conn.commit()
        state["awaiting_new_nickname"] = False
        bot.send_message(uid, f"✅ Ник изменён на '{new_nick}'")
        show_main_menu(message)
        return

    if text == "🚫 Забанить" and is_private and state.get("admin_access"):
        cursor.execute("SELECT nickname FROM users ORDER BY nickname")
        users = cursor.fetchall()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for u in users:
            markup.add(u[0])
        markup.add("⬅️ Ливнуть")
        state["awaiting_ban_target"] = True
        bot.send_message(uid, "🚫 Выбери пользователя для удаления:", reply_markup=markup)
        return

    if state.get("awaiting_ban_target"):
        if text == "⬅️ Ливнуть":
            state["awaiting_ban_target"] = False
            show_main_menu(message)
            return

        cursor.execute("SELECT user_id FROM users WHERE nickname = ?", (text,))
        target = cursor.fetchone()
        if target:
            state["ban_confirm_id"] = target[0]
            state["ban_confirm_nick"] = text
            state["awaiting_ban_target"] = False
            state["awaiting_ban_confirm"] = True
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("✅ Подтвердить", "⬅️ Ливнуть")
            bot.send_message(uid, f"❗ Выбран: {text}\nНажми 'Подтвердить' для удаления.", reply_markup=markup)
        else:
            bot.send_message(uid, "❌ Пользователь не найден.")
            state["awaiting_ban_target"] = False
        return

    if state.get("awaiting_ban_confirm"):
        if text == "⬅️ Ливнуть":
            state["awaiting_ban_confirm"] = False
            show_main_menu(message)
            return

        if text == "✅ Подтвердить":
            target_id = state.get("ban_confirm_id")
            nickname = state.get("ban_confirm_nick")
            cursor.execute("DELETE FROM users WHERE user_id = ?", (target_id,))
            conn.commit()
            bot.send_message(uid, f"🚫 Пользователь '{nickname}' удалён из базы.")
            state["awaiting_ban_confirm"] = False
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🧩 Управление", "🚫 Забанить", "⬅️ Ливнуть")
            bot.send_message(uid, "🔧 Админка:", reply_markup=markup)
        return

    if text == "🧩 Управление" and is_private and state.get("admin_access"):
        cursor.execute("SELECT nickname FROM users ORDER BY nickname")
        users = cursor.fetchall()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for u in users:
            markup.add(u[0])
        markup.add("⬅️ Ливнуть")
        state["awaiting_balance_target"] = True
        bot.send_message(uid, "👥 Выбери пользователя для изменения баланса:", reply_markup=markup)
        return

    if state.get("awaiting_balance_target"):
        cursor.execute("SELECT user_id FROM users WHERE nickname = ?", (text,))
        target = cursor.fetchone()
        if target:
            state["balance_target_id"] = target[0]
            state["awaiting_balance_target"] = False
            state["awaiting_balance_change"] = True
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("+100", "+200", "+300")
            markup.add("-100", "-200", "-300")
            markup.add("⬅️ Ливнуть")
            bot.send_message(uid, f"✏️ Выбран: {text}\nВыбери изменение или введи новое значение:", reply_markup=markup)
        else:
            bot.send_message(uid, "❌ Пользователь не найден.")
            state["awaiting_balance_target"] = False
        return    
    if state.get("awaiting_balance_change"):
        target_id = state.get("balance_target_id")
        if text in ["+100", "+200", "+300", "-100", "-200", "-300"]:
            delta = int(text)
            cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (delta, target_id))
            conn.commit()
            bot.send_message(uid, f"✅ Баланс изменён на {('+' if delta > 0 else '')}{delta} очков.")
        else:
            try:
                new_value = int(text)
                cursor.execute("UPDATE users SET points = ? WHERE user_id = ?", (new_value, target_id))
                conn.commit()
                bot.send_message(uid, f"✅ Баланс установлен: {new_value} очков.")
            except:
                bot.send_message(uid, "⚠️ Введите корректное число или выбери кнопку.")
        state["awaiting_balance_change"] = False
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🧩 Управление", "🚫 Забанить", "⬅️ Ливнуть")
        bot.send_message(uid, "🔧 Админка:", reply_markup=markup)
        return

    if text == "🎰 Рулетка" and is_private:
        show_roulette_menu(message, uid, deped=state.get('deped_in_session', False))
        return

    if text in ["💸 Депнуть", "💸 Додеп"] and is_private:
        now = time.time()
        last = cooldowns.get(uid, 0)
        if now - last < 3:
            bot.send_message(uid, "⏳ Подожди немного перед следующим депом...")
            return

        cooldowns[uid] = now
        state['deped_in_session'] = True

        bot.send_message(uid, "🎰 Крутим рулетку...", reply_markup=types.ReplyKeyboardRemove())

        frames = ["🔄 ░░░░░░░░░░", "🔄 █░░░░░░░░", "🔄 ██░░░░░░", "🔄 ███░░░░", "🔄 ████░░", "🔄 ██████"]
        msg = bot.send_message(uid, frames[0])
        for frame in frames[1:]:
            time.sleep(0.4)
            bot.edit_message_text(chat_id=uid, message_id=msg.message_id, text=frame)

        jackpot = random.randint(1, 200) == 1
        if jackpot:
            roll = 5000
            result = "💥 ДЖЕКПОТ! +5000 очков!"
        else:
            roll = random.randint(1, 100)
            result = f"🎲 Выпало: {roll}\n💰 Зачислено +{roll} очков!"

        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (roll, uid))
        conn.commit()
        time.sleep(0.5)
        bot.edit_message_text(chat_id=uid, message_id=msg.message_id, text=result)

        time.sleep(3)
        show_roulette_menu(message, uid, deped=True)
        return

    if text == "🏆 Лидерборд" and is_private:
        cursor.execute("SELECT nickname, points FROM users ORDER BY points DESC LIMIT 10")
        top = cursor.fetchall()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("⬅️ Ливнуть")
        if top:
            text = "🏆 Лидеры OCUDEP:\n"
            for i, (nick, pts) in enumerate(top, 1):
                rank = get_rank(pts)
                text += f"{i}. {nick} — {pts} очков ({rank})\n"
            bot.send_message(uid, text, reply_markup=markup)
        else:
            bot.send_message(uid, "❌ Лидерборд пуст.", reply_markup=markup)
        return

    if text == "📊 Ранг" and is_private:
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (uid,))
        user = cursor.fetchone()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("⬅️ Ливнуть")
        if user:
            points = user[0]
            rank = get_rank(points)
            rank_info = (
                "📊 Градации OCUDEP:\n\n"
                "🐣 Новичок — 0–999 очков\n"
                "🪖 Бывалый — 1000–4999\n"
                "🎯 Эксперт — 5000–14999\n"
                "🧠 Мастер — 15000–39999\n"
                "🔮 Гуру — 40000–79999\n"
                "👑 Бог — 80000–100000\n\n"
                f"🏅 Твой ранг: {rank} ({points} очков)"
            )
            bot.send_message(uid, rank_info, reply_markup=markup)
        else:
            bot.send_message(uid, "❌ Ты не зарегистрирован. Напиши /start", reply_markup=markup)
        return

    if text == "⚙️ Настройки" and is_private:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("✏️ Сменить ник", "⬅️ Ливнуть")
        bot.send_message(uid, "⚙️ Настройки профиля:", reply_markup=markup)
        return

    if text == "✏️ Сменить ник" and is_private:
        state["awaiting_new_nickname"] = True
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("⬅️ Ливнуть")
        bot.send_message(uid, "✏️ Введите новый ник:", reply_markup=markup)
        return

    if text == "🎯 Профиль" and is_private:
        cursor.execute("SELECT nickname, points FROM users WHERE user_id = ?", (uid,))
        user = cursor.fetchone()
        if user:
            rank = get_rank(user[1])
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("⬅️ Ливнуть")
            bot.send_message(uid, f"👤 Ник: {user[0]}\n💰 Очки: {user[1]}\n🏅 Статус: {rank}", reply_markup=markup)
        else:
            bot.send_message(uid, "❌ Ты не зарегистрирован. Напиши /start")
        return

    bot.send_message(uid, "❓ Неизвестная команда.")
from keep_alive import keep_alive
keep_alive()
bot.polling()
