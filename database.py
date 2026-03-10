import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Таблица пользователей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            total_answers INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            last_daily DATE,
            daily_count INTEGER DEFAULT 0,
            daily_goal INTEGER DEFAULT 5,
            exam_date TEXT,
            user_level TEXT DEFAULT 'beginner'
        )
    """)
    
    try:
        cur.execute("SELECT exam_date FROM users LIMIT 1")
    except sqlite3.OperationalError:
        cur.execute("ALTER TABLE users ADD COLUMN exam_date TEXT")
    
    try:
        cur.execute("SELECT user_level FROM users LIMIT 1")
    except sqlite3.OperationalError:
        cur.execute("ALTER TABLE users ADD COLUMN user_level TEXT DEFAULT 'beginner'")
    
    # Таблица заданий
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            subject TEXT,
            theme_id TEXT,
            text TEXT,
            options TEXT,
            correct TEXT,
            letters TEXT
        )
    """)
    
    # Таблица обратной связи
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            date TEXT
        )
    """)
    
    # Таблица статистики по темам
    cur.execute("""
        CREATE TABLE IF NOT EXISTS theme_stats (
            user_id INTEGER,
            subject TEXT,
            theme_id TEXT,
            total INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, subject, theme_id)
        )
    """)
    
    # Таблица избранных конспектов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER,
            subject TEXT,
            theme_id TEXT,
            added DATE DEFAULT CURRENT_DATE,
            PRIMARY KEY (user_id, subject, theme_id)
        )
    """)
    
    # Таблица напоминаний
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            user_id INTEGER PRIMARY KEY,
            reminder_time TEXT,
            active INTEGER DEFAULT 1
        )
    """)
    
    # Таблица подписок (премиум)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            subscription_type TEXT DEFAULT 'free',
            expires_at DATE,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # ===== НОВАЯ ТАБЛИЦА: подписки на предметы =====
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subject_premium (
            user_id INTEGER,
            subject TEXT,
            expires_at DATE,
            PRIMARY KEY (user_id, subject),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица истории подарков
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gift_history (
            gift_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER,
            to_user INTEGER,
            subject TEXT,
            days INTEGER,
            date DATE DEFAULT CURRENT_DATE,
            FOREIGN KEY (from_user) REFERENCES users(user_id),
            FOREIGN KEY (to_user) REFERENCES users(user_id)
        )
    """)
    
    # Таблица для хранения ожидающих платежей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_payments (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            subject TEXT,
            days INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица достижений (ачивок)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            icon TEXT,
            condition_type TEXT,
            condition_value INTEGER
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER,
            achievement_id INTEGER,
            earned_date DATE DEFAULT CURRENT_DATE,
            PRIMARY KEY (user_id, achievement_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (achievement_id) REFERENCES achievements(achievement_id)
        )
    """)
    
    # Таблица интервальных повторений
    cur.execute("""
        CREATE TABLE IF NOT EXISTS repetition_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_id TEXT,
            easiness REAL DEFAULT 2.5,
            interval INTEGER DEFAULT 1,
            repetitions INTEGER DEFAULT 0,
            next_review DATE,
            last_review DATE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        )
    """)
    
    # Таблица рефералов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            referrer_id INTEGER,
            referred_id INTEGER PRIMARY KEY,
            date DATE DEFAULT CURRENT_DATE,
            premium_bonus_given INTEGER DEFAULT 0,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id),
            FOREIGN KEY (referred_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица ежедневных челленджей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_challenges (
            challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE,
            description TEXT,
            target_count INTEGER,
            reward_exp INTEGER,
            reward_stars INTEGER
        )
    """)
    
    # Таблица участия в челленджах
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_challenges (
            user_id INTEGER,
            challenge_id INTEGER,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, challenge_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (challenge_id) REFERENCES daily_challenges(challenge_id)
        )
    """)
    
    conn.commit()
    conn.close()

# ---------- Работа с пользователями ----------
def get_user(user_id, username=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute("""
            INSERT INTO users (user_id, username, level, exp, total_answers, correct_answers, last_daily, daily_count, daily_goal, exam_date, user_level)
            VALUES (?, ?, 1, 0, 0, 0, date('now'), 0, 5, NULL, 'beginner')
        """, (user_id, username))
        conn.commit()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
    conn.close()
    columns = [desc[0] for desc in cur.description]
    return dict(zip(columns, row))

def update_user_stats(user_id, correct=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT total_answers, correct_answers, exp FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        get_user(user_id)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT total_answers, correct_answers, exp FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
    
    total, correct_ans, exp = row
    total += 1
    if correct:
        correct_ans += 1
        exp += 10
    else:
        exp += 1
    level = exp // 100 + 1
    cur.execute("""
        UPDATE users SET total_answers=?, correct_answers=?, exp=?, level=?
        WHERE user_id=?
    """, (total, correct_ans, exp, level, user_id))
    conn.commit()
    conn.close()

def update_daily(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT last_daily, daily_count FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        get_user(user_id)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT last_daily, daily_count FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
    last, count = row
    today = datetime.now().date().isoformat()
    if last == today:
        count += 1
    else:
        count = 1
    cur.execute("UPDATE users SET last_daily=?, daily_count=? WHERE user_id=?", (today, count, user_id))
    conn.commit()
    conn.close()
    return count

def get_daily_goal(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT last_daily, daily_count, daily_goal FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        get_user(user_id)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT last_daily, daily_count, daily_goal FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
    last, count, goal = row
    today = datetime.now().date().isoformat()
    if last != today:
        count = 0
    conn.close()
    return count, goal

def set_daily_goal(user_id, goal):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET daily_goal=? WHERE user_id=?", (goal, user_id))
    conn.commit()
    conn.close()

def set_exam_date(user_id, exam_date):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET exam_date=? WHERE user_id=?", (exam_date, user_id))
    conn.commit()
    conn.close()

def set_user_level(user_id, user_level):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET user_level=? WHERE user_id=?", (user_level, user_id))
    conn.commit()
    conn.close()

def get_all_users_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), SUM(total_answers), SUM(correct_answers) FROM users")
    total_users, total_answers, total_correct = cur.fetchone()
    conn.close()
    return total_users or 0, total_answers or 0, total_correct or 0

# ---------- Статистика по темам ----------
def update_theme_stats(user_id, subject, theme_id, correct):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO theme_stats (user_id, subject, theme_id, total, correct)
        VALUES (?, ?, ?, 1, ?)
        ON CONFLICT(user_id, subject, theme_id) DO UPDATE SET
            total = total + 1,
            correct = correct + excluded.correct
    """, (user_id, subject, theme_id, 1 if correct else 0))
    conn.commit()
    conn.close()

def get_theme_stats(user_id, subject=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if subject:
        cur.execute("SELECT subject, theme_id, total, correct FROM theme_stats WHERE user_id=? AND subject=?", (user_id, subject))
    else:
        cur.execute("SELECT subject, theme_id, total, correct FROM theme_stats WHERE user_id=?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"subject": r[0], "theme_id": r[1], "total": r[2], "correct": r[3]} for r in rows]

def get_worst_themes(user_id, subject=None, limit=3):
    stats = get_theme_stats(user_id, subject)
    stats = [s for s in stats if s['total'] >= 2]
    if not stats:
        return []
    stats.sort(key=lambda x: x['correct']/x['total'])
    return stats[:limit]

# ---------- Избранное ----------
def add_favorite(user_id, subject, theme_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO favorites (user_id, subject, theme_id) VALUES (?, ?, ?)", (user_id, subject, theme_id))
    conn.commit()
    conn.close()

def remove_favorite(user_id, subject, theme_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM favorites WHERE user_id=? AND subject=? AND theme_id=?", (user_id, subject, theme_id))
    conn.commit()
    conn.close()

def get_favorites(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT subject, theme_id FROM favorites WHERE user_id=?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"subject": r[0], "theme_id": r[1]} for r in rows]

def is_favorite(user_id, subject, theme_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM favorites WHERE user_id=? AND subject=? AND theme_id=?", (user_id, subject, theme_id))
    row = cur.fetchone()
    conn.close()
    return row is not None

# ---------- Напоминания ----------
def set_reminder(user_id, time_str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO reminders (user_id, reminder_time, active) VALUES (?, ?, 1)", (user_id, time_str))
    conn.commit()
    conn.close()

def disable_reminder(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE reminders SET active=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_active_reminders():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, reminder_time FROM reminders WHERE active=1")
    rows = cur.fetchall()
    conn.close()
    return rows

# ---------- Работа с заданиями ----------
def add_task(task_id, subject, theme_id, text, options, correct, letters):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO tasks (task_id, subject, theme_id, text, options, correct, letters)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (task_id, subject, theme_id, text, json.dumps(options, ensure_ascii=False), correct, letters))
    conn.commit()
    conn.close()

def get_tasks_by_theme(subject, theme_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE subject=? AND theme_id=?", (subject, theme_id))
    rows = cur.fetchall()
    conn.close()
    tasks = []
    for row in rows:
        tasks.append({
            "id": row[0],
            "subject": row[1],
            "theme_id": row[2],
            "text": row[3],
            "options": json.loads(row[4]),
            "correct": row[5],
            "letters": row[6]
        })
    return tasks

def get_task_by_id(task_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "subject": row[1],
            "theme_id": row[2],
            "text": row[3],
            "options": json.loads(row[4]),
            "correct": row[5],
            "letters": row[6]
        }
    return None

# ---------- Обратная связь ----------
def add_feedback(user_id, message):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO feedback (user_id, message, date) VALUES (?, ?, datetime('now'))", (user_id, message))
    conn.commit()
    conn.close()

# ---------- Предметные подписки ----------
def set_subject_premium(user_id, subject, days):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT expires_at FROM subject_premium WHERE user_id = ? AND subject = ?", (user_id, subject))
    row = cur.fetchone()
    if row and row[0]:
        expires = datetime.strptime(row[0], "%Y-%m-%d").date()
        new_expires = expires + timedelta(days=days)
    else:
        new_expires = datetime.now().date() + timedelta(days=days)
    cur.execute("""
        INSERT OR REPLACE INTO subject_premium (user_id, subject, expires_at)
        VALUES (?, ?, ?)
    """, (user_id, subject, new_expires.isoformat()))
    conn.commit()
    conn.close()
    return new_expires

def has_subject_premium(user_id, subject):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT expires_at FROM subject_premium WHERE user_id = ? AND subject = ?", (user_id, subject))
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        expires = datetime.strptime(row[0], "%Y-%m-%d").date()
        return expires >= datetime.now().date()
    return False

def get_user_premiums(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT subject, expires_at FROM subject_premium WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    today = datetime.now().date()
    active = []
    for subject, exp_str in rows:
        expires = datetime.strptime(exp_str, "%Y-%m-%d").date()
        if expires >= today:
            active.append({"subject": subject, "expires_at": exp_str})
    return active

def gift_subject_premium(from_user, to_user, subject, days):
    expires = set_subject_premium(to_user, subject, days)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO gift_history (from_user, to_user, subject, days)
        VALUES (?, ?, ?, ?)
    """, (from_user, to_user, subject, days))
    conn.commit()
    conn.close()
    return expires

# ---------- Платежи ----------
def save_pending_payment(order_id, user_id, subject, days):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO pending_payments (order_id, user_id, subject, days) VALUES (?, ?, ?, ?)",
                (order_id, user_id, subject, days))
    conn.commit()
    conn.close()

def get_pending_payment(order_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, subject, days FROM pending_payments WHERE order_id = ?", (order_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "subject": row[1], "days": row[2]}
    return None

def delete_pending_payment(order_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM pending_payments WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()

# ---------- Ачивки ----------
def init_achievements():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    achievements = [
        ("Новичок", "Решено 10 заданий", "🌱", "total_answers", 10),
        ("Трудяга", "Решено 100 заданий", "💪", "total_answers", 100),
        ("Эксперт", "Решено 500 заданий", "🏆", "total_answers", 500),
        ("Идеальный экзамен", "100% правильных ответов в экзамене (не менее 10 вопросов)", "💯", "exam_perfect", 10),
        ("Марафонец", "Решать задания 7 дней подряд", "🔥", "streak_days", 7),
        ("Эрудит", "Правильно ответить на 10 заданий подряд", "🧠", "correct_streak", 10),
    ]
    for name, desc, icon, cond_type, cond_val in achievements:
        cur.execute("INSERT OR IGNORE INTO achievements (name, description, icon, condition_type, condition_value) VALUES (?, ?, ?, ?, ?)",
                    (name, desc, icon, cond_type, cond_val))
    conn.commit()
    conn.close()

def get_user_achievements(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT a.name, a.description, a.icon, ua.earned_date
        FROM user_achievements ua
        JOIN achievements a ON ua.achievement_id = a.achievement_id
        WHERE ua.user_id = ?
        ORDER BY ua.earned_date
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"name": r[0], "description": r[1], "icon": r[2], "earned_date": r[3]} for r in rows]

def has_achievement(user_id, achievement_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM user_achievements ua
        JOIN achievements a ON ua.achievement_id = a.achievement_id
        WHERE ua.user_id = ? AND a.name = ?
    """, (user_id, achievement_name))
    row = cur.fetchone()
    conn.close()
    return row is not None

def give_achievement(user_id, achievement_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT achievement_id FROM achievements WHERE name = ?", (achievement_name,))
    ach = cur.fetchone()
    if ach:
        cur.execute("INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?, ?)", (user_id, ach[0]))
        conn.commit()
    conn.close()

# ---------- Интервальные повторения ----------
def add_repetition_item(user_id, task_id, easiness=2.5, interval=1, repetitions=0, next_review=None):
    if next_review is None:
        next_review = datetime.now().date()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO repetition_items (user_id, task_id, easiness, interval, repetitions, next_review, last_review)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, task_id, easiness, interval, repetitions, next_review, datetime.now().date()))
    conn.commit()
    conn.close()

def get_repetition_item(user_id, task_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM repetition_items WHERE user_id = ? AND task_id = ?", (user_id, task_id))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "user_id": row[1],
            "task_id": row[2],
            "easiness": row[3],
            "interval": row[4],
            "repetitions": row[5],
            "next_review": row[6],
            "last_review": row[7]
        }
    return None

def update_repetition_item(user_id, task_id, easiness, interval, repetitions, next_review):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE repetition_items
        SET easiness = ?, interval = ?, repetitions = ?, next_review = ?, last_review = ?
        WHERE user_id = ? AND task_id = ?
    """, (easiness, interval, repetitions, next_review, datetime.now().date(), user_id, task_id))
    conn.commit()
    conn.close()

def get_repetition_items_due(user_id, date):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM repetition_items
        WHERE user_id = ? AND next_review <= ?
    """, (user_id, date))
    rows = cur.fetchall()
    conn.close()
    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "user_id": row[1],
            "task_id": row[2],
            "easiness": row[3],
            "interval": row[4],
            "repetitions": row[5],
            "next_review": row[6],
            "last_review": row[7]
        })
    return items

def get_users_with_due_repetitions(date=None):
    if date is None:
        date = datetime.now().date()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT user_id FROM repetition_items WHERE next_review <= ?", (date,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

# ---------- Рефералы ----------
def user_exists(user_id):
    """Check if user already exists in the database (first-launch detection)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def get_referrer_for_user(user_id):
    """Get referral record for a referred user."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT referrer_id, premium_bonus_given FROM referrals WHERE referred_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"referrer_id": row[0], "premium_bonus_given": row[1]}
    return None


def mark_referral_bonus_given(referred_id):
    """Mark that the referral premium bonus has been given to the referrer."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE referrals SET premium_bonus_given = 1 WHERE referred_id = ?", (referred_id,))
    conn.commit()
    conn.close()


def add_referral(referrer_id, referred_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
    conn.commit()
    conn.close()

def is_referral_exists(referred_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM referrals WHERE referred_id = ?", (referred_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None

def get_referral_count(referrer_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (referrer_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_referral_bonus(referrer_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT SUM(premium_bonus_given) FROM referrals WHERE referrer_id = ?", (referrer_id,))
    total = cur.fetchone()[0]
    conn.close()
    return total or 0

def add_premium_days(user_id, days):
    sub = get_subscription(user_id)
    if sub["type"] == "premium" and sub["expires_at"]:
        expires = datetime.strptime(sub["expires_at"], "%Y-%m-%d").date()
        new_expires = expires + timedelta(days=days)
    else:
        new_expires = datetime.now().date() + timedelta(days=days)
    set_subscription(user_id, "premium", new_expires.isoformat())

# ---------- Ежедневные челленджи ----------
def get_daily_challenge(date):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM daily_challenges WHERE date = ?", (date,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "challenge_id": row[0],
            "date": row[1],
            "description": row[2],
            "target_count": row[3],
            "reward_exp": row[4],
            "reward_stars": row[5]
        }
    return None

def create_daily_challenge(date, description, target_count, reward_exp=0, reward_stars=0):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO daily_challenges (date, description, target_count, reward_exp, reward_stars)
        VALUES (?, ?, ?, ?, ?)
    """, (date, description, target_count, reward_exp, reward_stars))
    conn.commit()
    conn.close()
    return get_daily_challenge(date)

def get_challenge_progress(user_id, challenge_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT progress FROM user_challenges WHERE user_id = ? AND challenge_id = ?", (user_id, challenge_id))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def update_challenge_progress(user_id, challenge_id, progress):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_challenges (user_id, challenge_id, progress, completed)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(user_id, challenge_id) DO UPDATE SET progress = excluded.progress
    """, (user_id, challenge_id, progress))
    conn.commit()
    conn.close()

# ---------- Подписки (премиум) ----------
def get_subscription(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT subscription_type, expires_at FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"type": row[0], "expires_at": row[1]}
    return {"type": "free", "expires_at": None}

def set_subscription(user_id, sub_type, expires_at):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO subscriptions (user_id, subscription_type, expires_at)
        VALUES (?, ?, ?)
    """, (user_id, sub_type, expires_at))
    conn.commit()
    conn.close()

def has_premium(user_id):
    sub = get_subscription(user_id)
    if sub["type"] != "premium":
        return False
    if sub["expires_at"]:
        expires = datetime.strptime(sub["expires_at"], "%Y-%m-%d").date()
        if expires < datetime.now().date():
            return False
    return True
