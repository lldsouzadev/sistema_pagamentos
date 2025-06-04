import pytest
from unittest.mock import patch, MagicMock
from app.services import process_transaction
from app.models import User, Merchant, Transaction, UserType, TransactionStatus, db as app_db # Renomeado para evitar conflito
from decimal import Decimal
import uuid

# Fixtures para usuários podem ser reutilizadas ou adaptadas de test_routes_transaction.py se necessário,
# mas para testes de unidade de serviço, podemos criá-los diretamente ou usar mocks mais profundos.
# Por simplicidade e para testar a interação com objetos reais do SQLAlchemy (com o db de teste),
# vamos criar objetos reais.

@pytest.fixture
def service_payer(db): # Usa a fixture db de conftest.py
    user = User(id=uuid.uuid4(), full_name="Service Payer", cpf="90080070066", email="service.payer@example.com", password_hash="pw", balance=Decimal("200.00"), user_type=UserType.COMMON)
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def service_payee_user(db):
    user = User(id=uuid.uuid4(), full_name="Service Payee User", cpf="90080070077", email="service.payee.user@example.com", password_hash="pw", balance=Decimal("50.00"), user_type=UserType.COMMON)
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def service_payee_merchant(db):
    merchant = Merchant(id=uuid.uuid4(), full_name="Service Payee Merchant", cnpj="90080070000188", email="service.payee.merchant@example.com", password_hash="pw", balance=Decimal("100.00"), user_type=UserType.MERCHANT)
    db.session.add(merchant)
    db.session.commit()
    return merchant

@patch('app.services.send_notification_external')
@patch('app.services.authorize_transaction_external')
def test_process_transaction_success_user_to_user(mock_authorize, mock_notify, app, db, service_payer, service_payee_user): # app fixture para contexto, db para acesso direto
    """Testa process_transaction bem-sucedida entre usuários."""
    mock_authorize.return_value = True
    mock_notify.return_value = True

    with app.app_context(): # Contexto da aplicação necessário para SQLAlchemy e current_app
        result, status_code = process_transaction(
            payer_id_str=str(service_payer.id),
            payee_id_str=str(service_payee_user.id),
            amount_str="50.00"
        )

    assert status_code == 200
    assert result['message'] == "Transaction completed successfully."
    assert result['status'] == TransactionStatus.COMPLETED.value

    mock_authorize.assert_called_once()

    # Atualizar referências dos objetos para refletir o estado pós-transação
    updated_payer = db.session.get(User, service_payer.id)
    updated_payee_user = db.session.get(User, service_payee_user.id)

    mock_notify.assert_called_once_with(updated_payee_user.id, Decimal("50.00"))

    # Verificar saldos no banco de dados real de teste
    db.session.refresh(updated_payer) # Adicionado refresh
    db.session.refresh(updated_payee_user) # Adicionado refresh
    assert updated_payer.balance == Decimal("150.00")
    assert updated_payee_user.balance == Decimal("100.00")

    transaction = db.session.get(Transaction, uuid.UUID(result['transaction_id']))
    assert transaction is not None
    assert transaction.status == TransactionStatus.COMPLETED

def test_process_transaction_insufficient_funds(app, db, service_payer, service_payee_user):
    """Testa process_transaction com fundos insuficientes."""
    with app.app_context():
        result, status_code = process_transaction(
            payer_id_str=str(service_payer.id),
            payee_id_str=str(service_payee_user.id),
            amount_str="300.00" # Payer tem 200.00
        )

    assert status_code == 400
    assert result['error'] == "Insufficient balance."
    updated_payer = db.session.get(User, service_payer.id)
    assert updated_payer.balance == Decimal("200.00") # Saldo inalterado

@patch('app.services.authorize_transaction_external')
def test_process_transaction_authorization_fails(mock_authorize, app, db, service_payer, service_payee_user):
    """Testa process_transaction quando a autorização externa falha."""
    mock_authorize.return_value = False

    with app.app_context():
        result, status_code = process_transaction(
            payer_id_str=str(service_payer.id),
            payee_id_str=str(service_payee_user.id),
            amount_str="50.00"
        )

    assert status_code == 403
    assert result['error'] == "Transaction not authorized by external service."
    updated_payer = db.session.get(User, service_payer.id)
    assert updated_payer.balance == Decimal("200.00") # Saldo inalterado

    # Verificar se a transação foi registrada como FAILED
    failed_tx = db.session.query(Transaction).filter_by(payer_id=service_payer.id, amount=Decimal("50.00"), status=TransactionStatus.FAILED).first()
    assert failed_tx is not None

def test_process_transaction_payer_is_merchant(app, service_payee_merchant, service_payee_user):
    """Testa process_transaction quando o pagador é um lojista."""
    with app.app_context():
        result, status_code = process_transaction(
            payer_id_str=str(service_payee_merchant.id), # Lojista pagando
            payee_id_str=str(service_payee_user.id),
            amount_str="10.00"
        )
    assert status_code == 404
    assert result['error'] == "Payer not found or is not a common user."

def test_process_transaction_invalid_amount(app, service_payer, service_payee_user):
    """Testa process_transaction com valor de transação inválido (negativo)."""
    with app.app_context():
        result, status_code = process_transaction(
            payer_id_str=str(service_payer.id),
            payee_id_str=str(service_payee_user.id),
            amount_str="-50.00"
        )
    assert status_code == 400
    assert result['error'] == "Transaction amount must be positive."

def test_process_transaction_payee_not_found(app, service_payer):
    """Testa process_transaction com ID de recebedor inexistente."""
    with app.app_context():
        result, status_code = process_transaction(
            payer_id_str=str(service_payer.id),
            payee_id_str=str(uuid.uuid4()), # ID aleatório
            amount_str="10.00"
        )
    assert status_code == 404
    assert result['error'] == "Payee not found."

@patch('app.services.send_notification_external')
@patch('app.services.authorize_transaction_external')
def test_process_transaction_notification_fails(mock_authorize, mock_notify, app, db, service_payer, service_payee_user):
    """Testa process_transaction quando a notificação falha (mas transação é bem-sucedida)."""
    mock_authorize.return_value = True
    mock_notify.return_value = False # Notificação falha

    with app.app_context():
        # Mock stdout para capturar o print de aviso
        with patch('builtins.print') as mock_print:
            result, status_code = process_transaction(
                payer_id_str=str(service_payer.id),
                payee_id_str=str(service_payee_user.id),
                amount_str="20.00"
            )

    assert status_code == 200 # Transação deve ser concluída mesmo se notificação falhar
    assert result['message'] == "Transaction completed successfully."

    notification_warning_found = False
    for call_args in mock_print.call_args_list:
        # Verifica se a mensagem de aviso específica foi impressa
        if "Warning: Notification failed for transaction" in call_args[0][0] and f"to payee {service_payee_user.id}" in call_args[0][0]:
            notification_warning_found = True
            break
    assert notification_warning_found

    updated_payer = db.session.get(User, service_payer.id)
    updated_payee_user = db.session.get(User, service_payee_user.id)
    db.session.refresh(updated_payer) # Adicionado refresh
    db.session.refresh(updated_payee_user) # Adicionado refresh
    assert updated_payer.balance == Decimal("180.00") # 200 - 20
    assert updated_payee_user.balance == Decimal("70.00") # 50 + 20
