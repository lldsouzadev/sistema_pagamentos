import pytest
import json
from unittest.mock import patch
import uuid # Adicionado para conversão de string para UUID
from app.models import User, Merchant, Transaction, UserType, TransactionStatus, db as _db
from decimal import Decimal

@pytest.fixture
def common_user_payer(db):
    """Cria um usuário comum pagador com saldo."""
    user = User(
        full_name="Payer Test User",
        cpf="10020030044",
        email="payer.test@example.com",
        password_hash="hashed_password",
        balance=Decimal("1000.00") # Saldo inicial para testes
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def common_user_payee(db):
    """Cria um usuário comum recebedor."""
    user = User(
        full_name="Payee Test User",
        cpf="50060070088",
        email="payee.user.test@example.com",
        password_hash="hashed_password_payee"
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def merchant_payee(db):
    """Cria um lojista recebedor."""
    merchant = Merchant(
        full_name="Payee Test Merchant",
        cnpj="10203040000155",
        email="payee.merchant.test@example.com",
        password_hash="hashed_password_merchant"
    )
    db.session.add(merchant)
    db.session.commit()
    return merchant

# Testes para POST /transactions

@patch('app.services.send_notification_external')
@patch('app.services.authorize_transaction_external')
def test_transaction_user_to_user_success(mock_authorize, mock_notify, client, db, common_user_payer, common_user_payee):
    """Testa transação bem-sucedida de usuário para usuário."""
    mock_authorize.return_value = True # Mock para autorização bem-sucedida
    mock_notify.return_value = True    # Mock para notificação bem-sucedida

    payload = {
        "payer_id": str(common_user_payer.id),
        "payee_id": str(common_user_payee.id),
        "amount": "100.00"
    }
    response = client.post('/transactions', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 200 # Sucesso na transação
    data = response.get_json()
    assert data['message'] == "Transaction completed successfully."
    assert data['status'] == TransactionStatus.COMPLETED.value

    # Verificar mocks
    mock_authorize.assert_called_once()
    # Acessar o objeto da sessão do banco de dados através da fixture db (que é _db de conftest)
    # para garantir que estamos pegando os objetos atualizados.
    updated_payer = db.session.get(User, common_user_payer.id)
    updated_payee = db.session.get(User, common_user_payee.id)

    mock_notify.assert_called_once_with(updated_payee.id, Decimal("100.00"))

    # Verificar saldos
    assert updated_payer.balance == Decimal("900.00")
    assert updated_payee.balance == Decimal("100.00")

    # Verificar registro da transação
    transaction = db.session.get(Transaction, uuid.UUID(data['transaction_id'])) # Convertido para UUID
    assert transaction is not None
    assert transaction.status == TransactionStatus.COMPLETED

@patch('app.services.send_notification_external')
@patch('app.services.authorize_transaction_external')
def test_transaction_user_to_merchant_success(mock_authorize, mock_notify, client, db, common_user_payer, merchant_payee):
    """Testa transação bem-sucedida de usuário para lojista."""
    mock_authorize.return_value = True
    mock_notify.return_value = True

    payload = {
        "payer_id": str(common_user_payer.id),
        "payee_id": str(merchant_payee.id),
        "amount": "50.50"
    }
    response = client.post('/transactions', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == "Transaction completed successfully."

    updated_payer = db.session.get(User, common_user_payer.id)
    updated_merchant_payee = db.session.get(Merchant, merchant_payee.id)

    assert updated_payer.balance == Decimal("949.50") # 1000 - 50.50
    assert updated_merchant_payee.balance == Decimal("50.50")

@patch('app.services.authorize_transaction_external') # Notificação não deve ser chamada se falhar antes
def test_transaction_insufficient_balance(mock_authorize, client, db, common_user_payer, common_user_payee):
    """Testa transação com saldo insuficiente."""
    # Não precisamos mockar authorize aqui, pois a verificação de saldo vem antes na lógica do serviço

    payload = {
        "payer_id": str(common_user_payer.id),
        "payee_id": str(common_user_payee.id),
        "amount": "2000.00" # common_user_payer tem 1000.00
    }
    response = client.post('/transactions', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 400 # Erro de saldo insuficiente
    data = response.get_json()
    assert data['error'] == "Insufficient balance."

    updated_payer = db.session.get(User, common_user_payer.id)
    updated_payee = db.session.get(User, common_user_payee.id)

    assert updated_payer.balance == Decimal("1000.00") # Saldo não deve mudar
    assert updated_payee.balance == Decimal("0.00")   # Saldo não deve mudar
    mock_authorize.assert_not_called() # Autorização não deve ser chamada

@patch('app.services.authorize_transaction_external')
def test_transaction_payer_is_merchant(mock_authorize, client, db, merchant_payee, common_user_payee):
    """Testa transação onde o pagador é um lojista (deve falhar)."""
    payload = {
        "payer_id": str(merchant_payee.id), # Lojista como pagador
        "payee_id": str(common_user_payee.id),
        "amount": "10.00"
    }
    response = client.post('/transactions', data=json.dumps(payload), content_type='application/json')

    # O serviço retorna 404 se o pagador não for encontrado como UserType.COMMON
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == "Payer not found or is not a common user."
    mock_authorize.assert_not_called()

def test_transaction_invalid_payer_id(client, db, common_user_payee):
    """Testa transação com ID de pagador inválido/inexistente."""
    import uuid
    payload = {
        "payer_id": str(uuid.uuid4()), # ID inexistente
        "payee_id": str(common_user_payee.id),
        "amount": "10.00"
    }
    response = client.post('/transactions', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == "Payer not found or is not a common user."

def test_transaction_invalid_payee_id(client, db, common_user_payer):
    """Testa transação com ID de recebedor inválido/inexistente."""
    import uuid
    payload = {
        "payer_id": str(common_user_payer.id),
        "payee_id": str(uuid.uuid4()), # ID inexistente
        "amount": "10.00"
    }
    response = client.post('/transactions', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == "Payee not found."

@patch('app.services.send_notification_external')
@patch('app.services.authorize_transaction_external')
def test_transaction_authorization_failed(mock_authorize, mock_notify, client, db, common_user_payer, common_user_payee):
    """Testa transação onde a autorização externa falha."""
    mock_authorize.return_value = False # Autorização falha

    # Usar db.session.get para garantir que estamos pegando o estado mais recente da sessão do SQLAlchemy
    # antes da transação.
    payer_before_transaction = db.session.get(User, common_user_payer.id)
    payee_before_transaction = db.session.get(User, common_user_payee.id)
    initial_payer_balance = payer_before_transaction.balance
    initial_payee_balance = payee_before_transaction.balance

    payload = {
        "payer_id": str(payer_before_transaction.id),
        "payee_id": str(payee_before_transaction.id),
        "amount": "50.00"
    }
    response = client.post('/transactions', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 403 # Erro de autorização
    data = response.get_json()
    assert data['error'] == "Transaction not authorized by external service."

    mock_authorize.assert_called_once()
    mock_notify.assert_not_called() # Notificação não deve ser chamada

    # Saldos não devem mudar
    payer_after_transaction = db.session.get(User, payer_before_transaction.id)
    payee_after_transaction = db.session.get(User, payee_before_transaction.id)
    assert payer_after_transaction.balance == initial_payer_balance
    assert payee_after_transaction.balance == initial_payee_balance

    transaction = db.session.query(Transaction).filter_by(payer_id=payer_before_transaction.id).order_by(Transaction.timestamp.desc()).first()
    assert transaction is not None
    assert transaction.status == TransactionStatus.FAILED
    assert transaction.amount == Decimal("50.00")

def test_transaction_missing_fields(client):
    """Testa a rota de transação com campos faltando no payload."""
    payload = {"payer_id": "some_id", "amount": "100"} # payee_id faltando
    response = client.post('/transactions', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    data = response.get_json()
    assert "Missing fields" in data['error']

def test_transaction_negative_amount(client, common_user_payer, common_user_payee):
    """Testa transação com valor negativo."""
    payload = {
        "payer_id": str(common_user_payer.id),
        "payee_id": str(common_user_payee.id),
        "amount": "-50.00"
    }
    response = client.post('/transactions', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400 # Erro de valor inválido
    data = response.get_json()
    assert "Transaction amount must be positive" in data['error']
