import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from typing import List, Optional, Dict
import steam.webauth as wa
import steam.guard

logger = logging.getLogger(__name__)

class SteamAccountManager:
    def __init__(self, db_path: str = "steam_accounts.db"):
        self.db_path = db_path
        self.cipher = self._init_encryption()
        self.timers: Dict[int, threading.Timer] = {}
        self._init_database()
        self._load_scheduled_changes()
    
    def _init_encryption(self) -> Fernet:
        """Инициализация шифрования"""
        try:
            # Пробуем загрузить существующий ключ
            with open('encryption.key', 'rb') as f:
                key = f.read()
        except FileNotFoundError:
            # Создаем новый ключ
            key = Fernet.generate_key()
            with open('encryption.key', 'wb') as f:
                f.write(key)
        return Fernet(key)
    
    def _init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE NOT NULL,
                encrypted_password TEXT NOT NULL,
                encrypted_mafile TEXT NOT NULL,
                nickname TEXT,
                auto_change_enabled BOOLEAN DEFAULT 0,
                change_interval_hours INTEGER DEFAULT 24,
                last_password_change TIMESTAMP,
                next_scheduled_change TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def _load_scheduled_changes(self):
        """Загрузка запланированных смен паролей при запуске"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, next_scheduled_change FROM accounts 
                WHERE auto_change_enabled = 1 AND next_scheduled_change IS NOT NULL
            ''')
            rows = cursor.fetchall()
            conn.close()
            
            for account_id, next_change in rows:
                if next_change:
                    next_change_dt = datetime.fromisoformat(next_change)
                    if next_change_dt > datetime.now():
                        self._schedule_password_change(account_id, next_change_dt)
                    else:
                        # Время уже прошло, меняем пароль немедленно
                        self._change_password_async(account_id)
        except Exception as e:
            logger.error(f"Ошибка загрузки расписания: {e}")
    
    def add_account(self, login: str, password: str, mafile_json: dict, nickname: str = None) -> bool:
        """Добавление аккаунта в базу"""
        try:
            encrypted_password = self.cipher.encrypt(password.encode())
            encrypted_mafile = self.cipher.encrypt(json.dumps(mafile_json).encode())
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO accounts (login, encrypted_password, encrypted_mafile, nickname)
                VALUES (?, ?, ?, ?)
            ''', (login, encrypted_password, encrypted_mafile, nickname or login))
            conn.commit()
            conn.close()
            
            logger.info(f"Аккаунт {login} добавлен")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления аккаунта: {e}")
            return False
    
    def get_accounts(self) -> List[dict]:
        """Получение списка аккаунтов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, login, encrypted_password, encrypted_mafile, nickname, 
                   auto_change_enabled, change_interval_hours, 
                   last_password_change, next_scheduled_change
            FROM accounts
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        accounts = []
        for row in rows:
            try:
                password = self.cipher.decrypt(row[2]).decode()
                mafile = json.loads(self.cipher.decrypt(row[3]).decode())
                
                # Рассчитываем оставшееся время до смены пароля
                time_remaining = None
                if row[7] and row[5]:  # last_password_change и auto_change_enabled
                    last_change = datetime.fromisoformat(row[7])
                    next_change = last_change + timedelta(hours=row[6])
                    time_remaining = max(0, int((next_change - datetime.now()).total_seconds()))
                
                accounts.append({
                    'id': row[0],
                    'login': row[1],
                    'password': password,
                    'mafile': mafile,
                    'nickname': row[4],
                    'auto_change_enabled': bool(row[5]),
                    'change_interval_hours': row[6],
                    'last_password_change': row[7],
                    'next_scheduled_change': row[8],
                    'time_remaining_seconds': time_remaining
                })
            except Exception as e:
                logger.error(f"Ошибка расшифровки аккаунта {row[1]}: {e}")
        
        return accounts
    
    def set_auto_password_change(self, account_id: int, enabled: bool, interval_hours: int = 24) -> bool:
        """Включение/выключение автоматической смены пароля"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            next_scheduled_change = None
            if enabled:
                next_scheduled_change = datetime.now() + timedelta(hours=interval_hours)
                # Запускаем таймер
                self._schedule_password_change(account_id, next_scheduled_change)
            else:
                # Отменяем таймер если есть
                if account_id in self.timers:
                    self.timers[account_id].cancel()
                    del self.timers[account_id]
            
            cursor.execute('''
                UPDATE accounts 
                SET auto_change_enabled = ?, change_interval_hours = ?, next_scheduled_change = ?
                WHERE id = ?
            ''', (enabled, interval_hours, next_scheduled_change.isoformat() if next_scheduled_change else None, account_id))
            conn.commit()
            conn.close()
            
            logger.info(f"Автосмена пароля для аккаунта {account_id}: {'включена' if enabled else 'выключена'}")
            return True
        except Exception as e:
            logger.error(f"Ошибка настройки автосмены пароля: {e}")
            return False
    
    def _schedule_password_change(self, account_id: int, change_time: datetime):
        """Запланировать смену пароля"""
        try:
            # Отменяем существующий таймер
            if account_id in self.timers:
                self.timers[account_id].cancel()
            
            delay = (change_time - datetime.now()).total_seconds()
            if delay > 0:
                timer = threading.Timer(delay, self._change_password_async, [account_id])
                timer.start()
                self.timers[account_id] = timer
                logger.info(f"Смена пароля для {account_id} запланирована через {delay} секунд")
        except Exception as e:
            logger.error(f"Ошибка планирования смены пароля: {e}")
    
    def _change_password_async(self, account_id: int):
        """Асинхронная смена пароля (вызывается по таймеру)"""
        try:
            logger.info(f"Запуск автоматической смены пароля для аккаунта {account_id}")
            result = self.change_password(account_id)
            
            if result['success']:
                # Обновляем время последней смены и планируем следующую
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT change_interval_hours FROM accounts WHERE id = ?', (account_id,))
                interval = cursor.fetchone()[0]
                
                next_change = datetime.now() + timedelta(hours=interval)
                cursor.execute(
                    'UPDATE accounts SET last_password_change = ?, next_scheduled_change = ? WHERE id = ?',
                    (datetime.now().isoformat(), next_change.isoformat(), account_id)
                )
                conn.commit()
                conn.close()
                
                # Планируем следующую смену
                self._schedule_password_change(account_id, next_change)
                logger.info(f"Автосмена пароля для {account_id} завершена успешно")
            else:
                logger.error(f"Ошибка автосмены пароля для {account_id}: {result['error']}")
                
        except Exception as e:
            logger.error(f"Критическая ошибка в автосмене пароля: {e}")
    
    def generate_guard_code(self, account_id: int) -> Optional[str]:
        """Генерация кода Steam Guard"""
        try:
            accounts = self.get_accounts()
            account = next((acc for acc in accounts if acc['id'] == account_id), None)
            if not account:
                return None
            
            shared_secret = account['mafile'].get('shared_secret')
            if not shared_secret:
                return None
            
            return steam.guard.generate_code(shared_secret)
        except Exception as e:
            logger.error(f"Ошибка генерации кода: {e}")
            return None
    
    def change_password(self, account_id: int, new_password: Optional[str] = None) -> dict:
        """Смена пароля аккаунта"""
        try:
            accounts = self.get_accounts()
            account = next((acc for acc in accounts if acc['id'] == account_id), None)
            if not account:
                return {'success': False, 'error': 'Аккаунт не найден'}
            
            login = account['login']
            current_password = account['password']
            mafile = account['mafile']
            
            # Генерируем новый пароль если не указан
            if not new_password:
                new_password = self._generate_strong_password()
            
            # Создаем сессию Steam
            user = wa.WebAuth(login, current_password)
            
            # Генерируем Steam Guard код
            shared_secret = mafile.get('shared_secret')
            if not shared_secret:
                return {'success': False, 'error': 'Нет shared_secret в mafile'}
            
            guard_code = steam.guard.generate_code(shared_secret)
            
            # Логинимся и меняем пароль
            user.login(twofactor_code=guard_code)
            user.change_password(new_password)
            
            # Обновляем пароль в базе
            encrypted_password = self.cipher.encrypt(new_password.encode())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE accounts SET encrypted_password = ? WHERE id = ?',
                (encrypted_password, account_id)
            )
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'new_password': new_password,
                'message': f'Пароль для {login} успешно изменен'
            }
            
        except Exception as e:
            logger.error(f"Ошибка смены пароля: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_strong_password(self, length=16) -> str:
        """Генерация сильного пароля"""
        import random
        import string
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choice(chars) for _ in range(length))
    
    def delete_account(self, account_id: int) -> bool:
        """Удаление аккаунта"""
        try:
            # Отменяем таймер если есть
            if account_id in self.timers:
                self.timers[account_id].cancel()
                del self.timers[account_id]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
            conn.commit()
            conn.close()
            
            logger.info(f"Аккаунт {account_id} удален")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления аккаунта: {e}")
            return False
