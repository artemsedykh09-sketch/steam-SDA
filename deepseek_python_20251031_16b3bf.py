import requests
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_funpay_access():
    print("🔍 Тестируем доступ к FunPay...")
    
    # Читаем куки
    try:
        with open('cookies.txt', 'r', encoding='utf-8') as f:
            cookie_content = f.read().strip()
        
        if not cookie_content:
            print("❌ Файл cookies.txt пустой!")
            return False
            
        print(f"📄 Содержимое cookies.txt: {cookie_content[:80]}...")
        
    except FileNotFoundError:
        print("❌ Файл cookies.txt не найден!")
        return False
    
    # Подготавливаем headers
    headers = {
        'Cookie': cookie_content,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
    }
    
    # Пробуем разные URL
    test_urls = [
        'https://funpay.com/',
        'https://funpay.com/orders/trade',
        'https://funpay.com/users/balance'
    ]
    
    for url in test_urls:
        try:
            print(f"🌐 Проверяем {url}...")
            response = requests.get(url, headers=headers, timeout=15)
            
            print(f"📊 Статус код: {response.status_code}")
            
            if response.status_code == 200:
                # Проверяем признаки авторизации
                auth_indicators = [
                    'user-link-name', 
                    'my-profile',
                    'account-link',
                    'btn-profile'
                ]
                
                is_authorized = any(indicator in response.text for indicator in auth_indicators)
                
                if is_authorized:
                    print(f"✅ УСПЕХ! Доступ к {url} есть, авторизация прошла")
                    return True
                else:
                    print(f"⚠️  Страница загрузилась, но нет признаков авторизации")
            else:
                print(f"❌ Ошибка доступа: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Ошибка при проверке {url}: {e}")
    
    print("❌ Не удалось получить доступ к FunPay")
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("FUNPAY COOKIE TESTER")
    print("=" * 50)
    
    if test_funpay_access():
        print("\n🎉 ВСЕ ОТЛИЧНО! Куки рабочие, можно запускать бота!")
    else:
        print("\n💥 ПРОБЛЕМА! Куки не работают, нужно обновить")
    
    input("\nНажмите Enter для выхода...")