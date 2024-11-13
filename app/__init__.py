from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Inicializa o banco de dados
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # Configurações do app
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pagamentos.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa o banco de dados com o app
    db.init_app(app)

    # Importa e registra as rotas
    from .routes import main
    app.register_blueprint(main)

    return app