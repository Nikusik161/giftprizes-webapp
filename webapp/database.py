# database.py
import sqlite3
import json
from datetime import datetime, timedelta
import time

class StatisticsDB:
    def __init__(self, db_path='giftprises_stats.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_spent REAL DEFAULT 0,
                total_purchases INTEGER DEFAULT 0,
                wallet_address TEXT
            )
        ''')
        
        # Таблица онлайн пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS online_users (
                user_id TEXT PRIMARY KEY,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица покупок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                gift_name TEXT,
                gift_id TEXT,
                amount REAL,
                recipient_username TEXT,
                wallet_address TEXT,
                status TEXT DEFAULT 'pending',
                purchase_id TEXT UNIQUE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица популярных подарков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS popular_gifts (
                gift_id TEXT PRIMARY KEY,
                gift_name TEXT,
                total_sales INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица статистики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_users INTEGER DEFAULT 0,
                online_users INTEGER DEFAULT 0,
                daily_turnover REAL DEFAULT 0,
                gifts_sold INTEGER DEFAULT 0,
                total_revenue REAL DEFAULT 0
            )
        ''')
        
        # Таблица настроек кнопок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS button_settings (
                button_id TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT TRUE,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Инициализация настроек кнопок
        buttons = ['search', 'budget', 'sell', 'catalog']
        for button in buttons:
            cursor.execute('''
                INSERT OR IGNORE INTO button_settings (button_id, enabled)
                VALUES (?, ?)
            ''', (button, True))
        
        conn.commit()
        conn.close()
    
    def register_user_activity(self, user_id, username=None):
        """Регистрирует активность пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Обновляем или создаем пользователя
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, last_seen)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, username))
        
        # Добавляем в онлайн
        cursor.execute('''
            INSERT OR REPLACE INTO online_users (user_id, last_activity)
            VALUES (?, CURRENT_TIMESTAMP)
        ''', (user_id,))
        
        # Удаляем неактивных (более 5 минут)
        cursor.execute('''
            DELETE FROM online_users 
            WHERE datetime(last_activity) < datetime('now', '-5 minutes')
        ''')
        
        conn.commit()
        conn.close()
    
    def register_purchase(self, user_id, username, gift_id, gift_name, amount, recipient_username, wallet_address):
        """Регистрирует покупку"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        purchase_id = f"purchase_{int(time.time())}_{user_id}"
        
        # Обновляем пользователя
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, last_seen, total_spent, total_purchases, wallet_address)
            VALUES (?, ?, CURRENT_TIMESTAMP, 
                    COALESCE((SELECT total_spent FROM users WHERE user_id = ?), 0) + ?,
                    COALESCE((SELECT total_purchases FROM users WHERE user_id = ?), 0) + 1, ?)
        ''', (user_id, username, user_id, amount, user_id, 1, wallet_address))
        
        # Добавляем покупку
        cursor.execute('''
            INSERT INTO purchases (user_id, gift_name, gift_id, amount, recipient_username, wallet_address, purchase_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, gift_name, gift_id, amount, recipient_username, wallet_address, purchase_id))
        
        # Обновляем популярные подарки
        cursor.execute('''
            INSERT OR REPLACE INTO popular_gifts (gift_id, gift_name, total_sales, last_updated)
            VALUES (?, ?, COALESCE((SELECT total_sales FROM popular_gifts WHERE gift_id = ?), 0) + 1, CURRENT_TIMESTAMP)
        ''', (gift_id, gift_name, gift_id))
        
        # Обновляем дневную статистику
        cursor.execute('''
            INSERT OR REPLACE INTO daily_stats (date, total_users, online_users, daily_turnover, gifts_sold, total_revenue)
            VALUES (?, 
                    (SELECT COUNT(*) FROM users),
                    (SELECT COUNT(*) FROM online_users),
                    COALESCE((SELECT daily_turnover FROM daily_stats WHERE date = ?), 0) + ?,
                    COALESCE((SELECT gifts_sold FROM daily_stats WHERE date = ?), 0) + 1,
                    COALESCE((SELECT total_revenue FROM daily_stats WHERE date = ?), 0) + ?)
        ''', (today, today, amount, today, amount))
        
        conn.commit()
        conn.close()
        return purchase_id
    
    def update_purchase_status(self, purchase_id, status):
        """Обновляет статус покупки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE purchases SET status = ? WHERE purchase_id = ?
        ''', (status, purchase_id))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self):
        """Получает текущую статистику"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Получаем текущую статистику
        cursor.execute('''
            SELECT 
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM online_users) as today_online,
                COALESCE((SELECT daily_turnover FROM daily_stats WHERE date = ?), 0) as daily_turnover,
                (SELECT COUNT(*) FROM purchases) as gifts_sold,
                COALESCE((SELECT SUM(total_spent) FROM users), 0) as total_revenue,
                COALESCE((SELECT COUNT(*) FROM purchases WHERE date(timestamp) = ?), 0) as today_sales,
                COALESCE((SELECT SUM(amount) FROM purchases WHERE date(timestamp) >= date('now', '-7 days')), 0) as week_revenue
        ''', (today, today))
        
        stats = cursor.fetchone()
        
        result = {
            'totalUsers': stats[0],
            'todayOnline': stats[1],
            'dailyTurnover': round(stats[2], 2),
            'giftsSold': stats[3],
            'totalRevenue': round(stats[4], 2),
            'todayRevenue': round(stats[2], 2),
            'weekRevenue': round(stats[6], 2),
            'totalSales': stats[3]
        }
        
        conn.close()
        return result
    
    def get_top_buyers(self, limit=10):
        """Получает топ покупателей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, total_spent, total_purchases 
            FROM users 
            WHERE total_spent > 0 
            ORDER BY total_spent DESC 
            LIMIT ?
        ''', (limit,))
        
        buyers = []
        for row in cursor.fetchall():
            buyers.append({
                'username': row[0] or 'Аноним',
                'spent': round(row[1], 2),
                'purchases': row[2]
            })
        
        conn.close()
        return buyers
    
    def get_popular_gifts(self, limit=10):
        """Получает популярные подарки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT gift_name, total_sales 
            FROM popular_gifts 
            ORDER BY total_sales DESC 
            LIMIT ?
        ''', (limit,))
        
        gifts = []
        for row in cursor.fetchall():
            gifts.append({
                'name': row[0],
                'sales': row[1]
            })
        
        conn.close()
        return gifts
    
    def get_button_status(self, button_id):
        """Получает статус кнопки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT enabled FROM button_settings WHERE button_id = ?
        ''', (button_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else True
    
    def set_button_status(self, button_id, enabled):
        """Устанавливает статус кнопки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO button_settings (button_id, enabled)
            VALUES (?, ?)
        ''', (button_id, enabled))
        
        conn.commit()
        conn.close()

# Глобальный экземпляр базы данных
stats_db = StatisticsDB()
