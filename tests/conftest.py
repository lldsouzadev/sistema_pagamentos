import pytest
import sys
import os

# Adicionar o diretório raiz do projeto ao sys.path
# para permitir que 'app' seja importado pelos testes.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db as _db # Renomeado para evitar conflito com fixture db

@pytest.fixture(scope='session')
def app():
    '''Session-wide test `Flask` application.'''
    # Configurações específicas para teste
    # Usar um banco de dados em memória para testes é comum e rápido
    # Ou um arquivo de banco de dados de teste separado
    config_override = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # Banco de dados em memória
        # "SQLALCHEMY_DATABASE_URI": "sqlite:///test_payments.db", # Ou arquivo separado
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        # Manter os URLs de mock para os testes não baterem em serviços reais
        "AUTHORIZATION_SERVICE_URL": "https://run.mocky.io/v3/5794d450-d2e2-4412-8131-73d0293ac1cc",
        "NOTIFICATION_SERVICE_URL": "https://run.mocky.io/v3/54dc2cf1-3add-45b5-b5a9-6bf7e7f1f4a6",
    }

    # Criar a instância do app com as configurações de teste
    # A função create_app precisa ser capaz de aceitar overrides de configuração
    # ou precisamos encontrar outra maneira de configurar o app para teste.
    # Por agora, vamos assumir que create_app pode ser modificada ou já lida com isso.
    # Se create_app não aceita config_override diretamente, teremos que ajustar app.config após a criação.

    _app = create_app()
    _app.config.update(config_override)

    # O db.create_all() em create_app pode ser problemático se não estiver no contexto certo
    # ou se quisermos controle mais fino para testes.
    # Para :memory: SQLite, as tabelas precisam ser criadas para cada conexão.
    # Para arquivos, uma vez por sessão pode ser suficiente.

    # Garantir que estamos no contexto da aplicação para operações de DB
    with _app.app_context():
        # Limpar e recriar tabelas pode ser feito aqui ou em outra fixture
        # _db.drop_all() # Se necessário para garantir um estado limpo
        # _db.create_all() # create_all já está em create_app, mas para :memory: pode precisar ser chamado após cada conexão
        pass # create_all é chamado dentro de create_app

    return _app

@pytest.fixture() # Default scope is 'function'
def client(app):
    '''A test client for the app.'''
    return app.test_client()

@pytest.fixture(scope='function') # 'function' scope para garantir DB limpo por teste
def db(app):
    '''
    Function-scoped database fixture.
    Ensures the database is created and dropped for each test function.
    This is crucial for in-memory SQLite as data doesn't persist across connections/sessions.
    '''
    with app.app_context():
        # _db.drop_all() # Opcional se create_all recria corretamente ou se :memory: é sempre novo
        _db.create_all() # Garante que as tabelas existem para cada teste com :memory:

        yield _db # Fornece a sessão do banco de dados para os testes

        _db.session.remove() # Limpa a sessão
        _db.drop_all() # Limpa o banco de dados após o teste


@pytest.fixture(scope='function')
def runner(app):
    '''A test runner for the app's Click commands.'''
    return app.test_cli_runner()

# Pode ser necessário ajustar a função create_app em app/__init__.py
# para não chamar db.create_all() se estivermos usando um banco de dados em memória
# e quisermos controlar a criação de tabelas explicitamente nas fixtures de teste,
# ou para aceitar um config_override.

# Por enquanto, a fixture `db` acima tentará gerenciar o estado do banco de dados
# para cada teste. A chamada `_db.create_all()` dentro da fixture `db` é importante
# para bancos de dados em memória.
