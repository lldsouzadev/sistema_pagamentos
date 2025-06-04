from flask import Flask
# Removido: from flask_sqlalchemy import SQLAlchemy
from .models import db # Import db de .models

# Removido: db = SQLAlchemy() - Será inicializado em models.py

def create_app():
    app = Flask(__name__)

    # Configurações do app
    # Assegurar que o URI do banco de dados e outras configs SQLAlchemy estejam aqui
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///payments.db' # Atualizado para 'payments.db' como na instrução
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # External Service URLs (can be overridden by environment variables later)
    app.config['AUTHORIZATION_SERVICE_URL'] = 'https://run.mocky.io/v3/5794d450-d2e2-4412-8131-73d0293ac1cc'
    app.config['NOTIFICATION_SERVICE_URL'] = 'https://run.mocky.io/v3/54dc2cf1-3add-45b5-b5a9-6bf7e7f1f4a6'

    # Inicializa o SQLAlchemy com o app
    db.init_app(app)

    with app.app_context(): # Adicionar contexto para db.create_all()
        db.create_all() # Cria tabelas se não existirem

    # Importa e registra as rotas
    from .routes import main
    app.register_blueprint(main)

    return app