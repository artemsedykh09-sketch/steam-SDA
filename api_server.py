from flask import Flask, request, jsonify
from flask_cors import CORS
from steam_manager import SteamAccountManager
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app)
manager = SteamAccountManager()

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Получить список всех аккаунтов"""
    try:
        accounts = manager.get_accounts()
        # Не возвращаем пароли в ответе
        safe_accounts = []
        for acc in accounts:
            safe_accounts.append({
                'id': acc['id'],
                'login': acc['login'],
                'nickname': acc['nickname'],
                'auto_change_enabled': acc['auto_change_enabled'],
                'change_interval_hours': acc['change_interval_hours'],
                'last_password_change': acc['last_password_change'],
                'next_scheduled_change': acc['next_scheduled_change'],
                'time_remaining_seconds': acc['time_remaining_seconds']
            })
        return jsonify({'success': True, 'accounts': safe_accounts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/accounts', methods=['POST'])
def add_account():
    """Добавить новый аккаунт"""
    try:
        data = request.json
        login = data.get('login')
        password = data.get('password')
        mafile = data.get('mafile')
        nickname = data.get('nickname')
        
        if not all([login, password, mafile]):
            return jsonify({'success': False, 'error': 'Не все поля заполнены'})
        
        success = manager.add_account(login, password, mafile, nickname)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/accounts/<int:account_id>/code', methods=['GET'])
def generate_code(account_id):
    """Сгенерировать код Steam Guard"""
    try:
        code = manager.generate_guard_code(account_id)
        if code:
            return jsonify({'success': True, 'code': code})
        else:
            return jsonify({'success': False, 'error': 'Не удалось сгенерировать код'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/accounts/<int:account_id>/password', methods=['POST'])
def change_password(account_id):
    """Сменить пароль аккаунта"""
    try:
        data = request.json
        new_password = data.get('new_password')  # Опционально
        
        result = manager.change_password(account_id, new_password)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/accounts/<int:account_id>/auto-change', methods=['POST'])
def set_auto_change(account_id):
    """Настроить автоматическую смену пароля"""
    try:
        data = request.json
        enabled = data.get('enabled', False)
        interval_hours = data.get('interval_hours', 24)
        
        success = manager.set_auto_password_change(account_id, enabled, interval_hours)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    """Удалить аккаунт"""
    try:
        success = manager.delete_account(account_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работы сервера"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚀 Запуск Steam Account Manager API...")
    print("📱 API доступно по адресу: http://localhost:5001")
    print("🔧 Эндпоинты:")
    print("   GET  /api/accounts - список аккаунтов")
    print("   POST /api/accounts - добавить аккаунт")
    print("   GET  /api/accounts/<id>/code - код Steam Guard")
    print("   POST /api/accounts/<id>/password - сменить пароль")
    print("   POST /api/accounts/<id>/auto-change - автосмена пароля")
    print("   DELETE /api/accounts/<id> - удалить аккаунт")
    
    app.run(host='0.0.0.0', port=5001, debug=False)
