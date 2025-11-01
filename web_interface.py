# web_interface.py
from flask import Flask, render_template, request, jsonify
import json
import threading
import time
from steam_manager import SteamAccountManager

app = Flask(__name__)
manager = SteamAccountManager()

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Steam Account Manager</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 20px; 
                background: #f5f5f5;
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .account-card { 
                border: 1px solid #ddd; 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 8px;
                background: #f9f9f9;
            }
            .button { 
                padding: 8px 16px; 
                margin: 5px; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer; 
            }
            .primary { background: #007bff; color: white; }
            .success { background: #28a745; color: white; }
            .warning { background: #ffc107; color: black; }
            .danger { background: #dc3545; color: white; }
            .timer { 
                background: #e7f3ff; 
                padding: 5px 10px; 
                border-radius: 4px; 
                margin: 5px 0;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 Steam Account Manager</h1>
            
            <div>
                <button class="button primary" onclick="loadAccounts()">🔄 Refresh</button>
                <button class="button success" onclick="showAddForm()">➕ Add Account</button>
            </div>
            
            <div id="accountsList"></div>
            
            <!-- Форма добавления аккаунта -->
            <div id="addForm" style="display: none; margin-top: 20px; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h3>Add Steam Account</h3>
                <form onsubmit="addAccount(event)">
                    <div style="margin: 10px 0;">
                        <label>Login:</label><br>
                        <input type="text" id="login" required style="width: 100%; padding: 8px; margin: 5px 0;">
                    </div>
                    <div style="margin: 10px 0;">
                        <label>Password:</label><br>
                        <input type="password" id="password" required style="width: 100%; padding: 8px; margin: 5px 0;">
                    </div>
                    <div style="margin: 10px 0;">
                        <label>Nickname (optional):</label><br>
                        <input type="text" id="nickname" style="width: 100%; padding: 8px; margin: 5px 0;">
                    </div>
                    <div style="margin: 10px 0;">
                        <label>maFile JSON:</label><br>
                        <textarea id="mafile" required style="width: 100%; height: 150px; padding: 8px; margin: 5px 0; font-family: monospace;"></textarea>
                    </div>
                    <button type="submit" class="button success">Add Account</button>
                    <button type="button" class="button" onclick="hideAddForm()">Cancel</button>
                </form>
            </div>
        </div>

        <script>
            let refreshInterval;
            
            function loadAccounts() {
                fetch('/api/accounts')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            displayAccounts(data.accounts);
                            // Автообновление каждые 30 секунд
                            if (refreshInterval) clearInterval(refreshInterval);
                            refreshInterval = setInterval(loadAccounts, 30000);
                        }
                    });
            }
            
            function displayAccounts(accounts) {
                const container = document.getElementById('accountsList');
                if (accounts.length === 0) {
                    container.innerHTML = '<p>No accounts added yet.</p>';
                    return;
                }
                
                container.innerHTML = accounts.map(acc => `
                    <div class="account-card">
                        <h3>${acc.nickname} <small style="color: #666;">(${acc.login})</small></h3>
                        
                        ${acc.auto_change_enabled && acc.time_remaining_seconds ? 
                            `<div class="timer">⏰ Auto change in: ${formatTime(acc.time_remaining_seconds)}</div>` : ''}
                        
                        <div>
                            <button class="button primary" onclick="generateCode(${acc.id})">🔐 Get Code</button>
                            <button class="button warning" onclick="changePassword(${acc.id})">🔄 Change Password</button>
                            <button class="button ${acc.auto_change_enabled ? 'success' : ''}" onclick="toggleAutoChange(${acc.id}, ${!acc.auto_change_enabled})">
                                ${acc.auto_change_enabled ? '✅' : '⏰'} Auto Change
                            </button>
                            <button class="button danger" onclick="deleteAccount(${acc.id})">🗑️ Delete</button>
                        </div>
                        
                        <div style="margin-top: 10px;">
                            <small>Last change: ${acc.last_password_change || 'Never'}</small>
                        </div>
                    </div>
                `).join('');
            }
            
            function formatTime(seconds) {
                const days = Math.floor(seconds / 86400);
                const hours = Math.floor((seconds % 86400) / 3600);
                const minutes = Math.floor((seconds % 3600) / 60);
                
                if (days > 0) return `${days}d ${hours}h`;
                if (hours > 0) return `${hours}h ${minutes}m`;
                return `${minutes}m`;
            }
            
            function generateCode(accountId) {
                fetch(`/api/accounts/${accountId}/code`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            alert(`Steam Guard Code: ${data.code}\\n\\nThis code will expire in 30 seconds.`);
                        } else {
                            alert('Error: ' + data.error);
                        }
                    });
            }
            
            function changePassword(accountId) {
                if (confirm('Are you sure you want to change the password?')) {
                    fetch(`/api/accounts/${accountId}/password`, { method: 'POST' })
                        .then(r => r.json())
                        .then(data => {
                            if (data.success) {
                                alert('Password changed successfully!');
                                loadAccounts();
                            } else {
                                alert('Error: ' + data.error);
                            }
                        });
                }
            }
            
            function toggleAutoChange(accountId, enabled) {
                fetch(`/api/accounts/${accountId}/auto-change`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled: enabled, interval_hours: 24 })
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        loadAccounts();
                    } else {
                        alert('Error: ' + data.error);
                    }
                });
            }
            
            function deleteAccount(accountId) {
                if (confirm('Are you sure you want to delete this account?')) {
                    fetch(`/api/accounts/${accountId}`, { method: 'DELETE' })
                        .then(r => r.json())
                        .then(data => {
                            if (data.success) {
                                loadAccounts();
                            } else {
                                alert('Error: ' + data.error);
                            }
                        });
                }
            }
            
            function showAddForm() {
                document.getElementById('addForm').style.display = 'block';
            }
            
            function hideAddForm() {
                document.getElementById('addForm').style.display = 'none';
            }
            
            function addAccount(event) {
                event.preventDefault();
                
                const formData = {
                    login: document.getElementById('login').value,
                    password: document.getElementById('password').value,
                    nickname: document.getElementById('nickname').value,
                    mafile: JSON.parse(document.getElementById('mafile').value)
                };
                
                fetch('/api/accounts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert('Account added successfully!');
                        hideAddForm();
                        loadAccounts();
                        // Очищаем форму
                        event.target.reset();
                    } else {
                        alert('Error: ' + data.error);
                    }
                });
            }
            
            // Загружаем аккаунты при старте
            loadAccounts();
        </script>
    </body>
    </html>
    """
