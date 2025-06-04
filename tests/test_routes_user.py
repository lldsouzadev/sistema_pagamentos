import pytest
import json
from app.models import User, Merchant, UserType, db as _db # Evitar conflito com fixture db
from werkzeug.security import check_password_hash # Para verificar o hash da senha se necessário, embora não seja o foco aqui

# Testes para POST /users

def test_create_common_user_route(client, db):
    """Testa a rota de criação de usuário comum."""
    payload = {
        "full_name": "Common User Route",
            "document": "11122233344", # Corrigido de "cpf" para "document"
        "email": "common.route@example.com",
        "password": "password123",
        "user_type": "common"
    }
    response = client.post('/users', data=json.dumps(payload), content_type='application/json')
    data = response.get_json()
        # print("DEBUG test_create_common_user_route:", data) # DEBUG Removido
    assert response.status_code == 201
    assert data['email'] == payload['email']
    assert data['user_type'] == UserType.COMMON.value
    assert 'id' in data

    user_in_db = User.query.filter_by(email=payload['email']).first()
    assert user_in_db is not None
    assert user_in_db.full_name == payload['full_name']
    assert check_password_hash(user_in_db.password_hash, payload['password'])

def test_create_merchant_user_route(client, db):
    """Testa a rota de criação de usuário lojista."""
    payload = {
        "full_name": "Merchant User Route",
        "cnpj": "11222333000155",
        "email": "merchant.route@example.com",
        "password": "password456",
        "user_type": "merchant"
    }
    # A rota espera 'document' como chave para CPF/CNPJ
    payload_corrected = {
        "full_name": payload["full_name"],
        "document": payload["cnpj"], # Corrigido para 'document'
        "email": payload["email"],
        "password": payload["password"],
        "user_type": payload["user_type"]
    }
    response = client.post('/users', data=json.dumps(payload_corrected), content_type='application/json')
    assert response.status_code == 201
    data = response.get_json()
    assert data['email'] == payload['email']
    assert data['user_type'] == UserType.MERCHANT.value

    merchant_in_db = Merchant.query.filter_by(email=payload['email']).first()
    assert merchant_in_db is not None
    assert merchant_in_db.full_name == payload['full_name']
    assert check_password_hash(merchant_in_db.password_hash, payload['password'])

def test_create_user_duplicate_cpf(client, db):
    """Testa a criação de usuário com CPF duplicado."""
    payload1 = {"full_name": "User CPF1", "document": "00011122233", "email": "cpf1@example.com", "password": "p1", "user_type": "common"}
    response1 = client.post('/users', data=json.dumps(payload1), content_type='application/json')
    assert response1.status_code == 201

    payload2 = {"full_name": "User CPF2", "document": "00011122233", "email": "cpf2@example.com", "password": "p2", "user_type": "common"}
    response2 = client.post('/users', data=json.dumps(payload2), content_type='application/json')
    assert response2.status_code == 409
    data = response2.get_json()
    assert "CPF or Email already exists" in data['error']

def test_create_user_duplicate_email(client, db):
    """Testa a criação de usuário com email duplicado."""
    payload1 = {"full_name": "User Email1", "document": "44455566677", "email": "email.dup@example.com", "password": "p1", "user_type": "common"}
    client.post('/users', data=json.dumps(payload1), content_type='application/json') # Assume 201

    payload2 = {"full_name": "User Email2", "document": "88899900011", "email": "email.dup@example.com", "password": "p2", "user_type": "common"}
    response2 = client.post('/users', data=json.dumps(payload2), content_type='application/json')
    assert response2.status_code == 409
    data = response2.get_json()
    assert "CPF or Email already exists" in data['error']

def test_create_user_missing_field(client, db):
    """Testa a criação de usuário com campo faltando."""
    payload = {"full_name": "Missing Field", "document": "12121212121", "password": "pw", "user_type": "common"} # Email faltando
    response = client.post('/users', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    data = response.get_json()
    assert "Missing field: email" in data['error']

def test_create_user_invalid_doc_format_cpf(client, db):
    """Testa a criação de usuário com formato de CPF inválido."""
    payload = {"full_name": "Inv CPF", "document": "123", "email": "invcpf@example.com", "password": "pw", "user_type": "common"}
    response = client.post('/users', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    data = response.get_json()
    assert "Invalid CPF format" in data['error']

def test_create_user_invalid_doc_format_cnpj(client, db):
    """Testa a criação de lojista com formato de CNPJ inválido."""
    payload = {"full_name": "Inv CNPJ", "document": "12345", "email": "invcnpj@example.com", "password": "pw", "user_type": "merchant"}
    response = client.post('/users', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    data = response.get_json()
    assert "Invalid CNPJ format" in data['error']

def test_create_user_invalid_user_type(client, db):
    """Testa a criação de usuário com user_type inválido."""
    payload = {"full_name": "Inv Type", "document": "12345678901", "email": "invtype@example.com", "password": "pw", "user_type": "unknown"}
    response = client.post('/users', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    data = response.get_json()
    assert "Invalid user_type" in data['error']

# Testes para GET /users/<id>/balance

def test_get_user_balance_common(client, db):
    """Testa a consulta de saldo para usuário comum."""
    # Criar usuário primeiro
    user = User(full_name="Balance User", cpf="77788899900", email="bal_user@example.com", password_hash="hash", balance=150.75)
    _db.session.add(user)
    _db.session.commit()

    response = client.get(f'/users/{user.id}/balance')
    assert response.status_code == 200
    data = response.get_json()
    assert data['user_id'] == str(user.id)
    assert data['balance'] == "150.75" # Balances são strings na resposta JSON
    assert data['user_type'] == "common"

def test_get_user_balance_merchant(client, db):
    """Testa a consulta de saldo para usuário lojista."""
    merchant = Merchant(full_name="Balance Merchant", cnpj="77889900000122", email="bal_merch@example.com", password_hash="hash", balance=2500.00)
    _db.session.add(merchant)
    _db.session.commit()

    response = client.get(f'/users/{merchant.id}/balance')
    assert response.status_code == 200
    data = response.get_json()
    assert data['user_id'] == str(merchant.id)
    assert data['balance'] == "2500.00"
    assert data['user_type'] == "merchant"

def test_get_user_balance_nonexistent(client, db):
    """Testa a consulta de saldo para usuário inexistente."""
    import uuid
    non_existent_uuid = uuid.uuid4()
    response = client.get(f'/users/{non_existent_uuid}/balance')
    assert response.status_code == 404
    data = response.get_json()
    assert "User not found" in data['error']

def test_get_user_balance_invalid_uuid(client, db):
    """Testa a consulta de saldo com UUID inválido."""
    response = client.get('/users/invalid-uuid-format/balance')
    assert response.status_code == 400 # A rota valida o formato do UUID
    data = response.get_json()
    assert "Invalid user ID format" in data['error']
