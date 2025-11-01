#!/usr/bin/env python3
import subprocess
import sys
import os

def install_requirements():
    """Установка зависимостей"""
    print("📦 Установка зависимостей...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def main():
    # Проверяем зависимости
    try:
        import flask
        import steam
        print("✅ Все зависимости установлены")
    except ImportError:
        print("❌ Зависимости не установлены. Устанавливаем...")
        install_requirements()
    
    # Запускаем сервер с веб-интерфейсом
    print("🚀 Запуск Steam Account Manager...")
    print("🌐 Веб-интерфейс доступен по адресу: http://localhost:5001")
    print("📱 Откройте в браузере на телефоне или компьютере")
    
    from web_interface import app
    app.run(host='0.0.0.0', port=5001, debug=False)

if __name__ == '__main__':
    main()
