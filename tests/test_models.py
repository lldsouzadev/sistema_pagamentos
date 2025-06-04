import pytest
from app.models import User, Merchant, Transaction, UserType, TransactionStatus, db as _db # Usar _db para evitar conflito com fixture db
from decimal import Decimal
import uuid

# Os testes de modelo usarão a fixture 'db' de conftest.py para interagir com o banco de dados de teste.

def test_create_common_user(db):
    """Testa a criação de um usuário comum."""
    user_data = {
        "full_name": "Test User Common",
        "cpf": "12345678901",
        "email": "common@example.com",
        "password_hash": "hashed_password",
        # balance e user_type têm valores padrão
    }
    user = User(**user_data)

    db.session.add(user)
    db.session.commit()

    retrieved_user = User.query.filter_by(email="common@example.com").first()
    assert retrieved_user is not None
    assert retrieved_user.full_name == "Test User Common"
    assert retrieved_user.cpf == "12345678901"
    assert retrieved_user.email == "common@example.com"
    assert retrieved_user.password_hash == "hashed_password"
    assert retrieved_user.balance == Decimal("0.00") # Verifica valor padrão
    assert retrieved_user.user_type == UserType.COMMON # Verifica valor padrão
    assert isinstance(retrieved_user.id, uuid.UUID)

def test_create_merchant_user(db):
    """Testa a criação de um usuário lojista."""
    merchant_data = {
        "full_name": "Test User Merchant",
        "cnpj": "12345678000199",
        "email": "merchant@example.com",
        "password_hash": "hashed_password_merchant",
    }
    merchant = Merchant(**merchant_data)

    db.session.add(merchant)
    db.session.commit()

    retrieved_merchant = Merchant.query.filter_by(email="merchant@example.com").first()
    assert retrieved_merchant is not None
    assert retrieved_merchant.full_name == "Test User Merchant"
    assert retrieved_merchant.cnpj == "12345678000199"
    assert retrieved_merchant.email == "merchant@example.com"
    assert retrieved_merchant.password_hash == "hashed_password_merchant"
    assert retrieved_merchant.balance == Decimal("0.00")
    assert retrieved_merchant.user_type == UserType.MERCHANT
    assert isinstance(retrieved_merchant.id, uuid.UUID)

def test_create_transaction(db):
    """Testa a criação de uma transação e relacionamentos básicos."""
    # Criar um pagador (User) e um recebedor (Merchant) para o teste
    payer = User(full_name="Payer User", cpf="11122233344", email="payer@example.com", password_hash="pass1")
    payee_merchant = Merchant(full_name="Payee Merchant", cnpj="11222333000155", email="payee.merchant@example.com", password_hash="pass2")

    db.session.add_all([payer, payee_merchant])
    db.session.commit()

    # Verificar se IDs foram gerados
    assert payer.id is not None
    assert payee_merchant.id is not None

    transaction_data = {
        "payer_id": payer.id,
        "payee_id": payee_merchant.id, # Pode ser ID de User ou Merchant
        "amount": Decimal("100.50"),
        # status e timestamp têm valores padrão
    }
    transaction = Transaction(**transaction_data)

    db.session.add(transaction)
    db.session.commit()

    retrieved_transaction = db.session.get(Transaction, transaction.id) # Usando db.session.get
    assert retrieved_transaction is not None
    assert retrieved_transaction.payer_id == payer.id
    assert retrieved_transaction.payee_id == payee_merchant.id
    assert retrieved_transaction.amount == Decimal("100.50")
    assert retrieved_transaction.status == TransactionStatus.PENDING # Verifica valor padrão
    assert retrieved_transaction.timestamp is not None

    # Testar relacionamentos (básico)
    # Atualizar payer para pegar a transação da sessão
    payer_from_db = db.session.get(User, payer.id)
    db.session.refresh(payer_from_db) # Refresh para carregar o relacionamento
    assert retrieved_transaction in payer_from_db.sent_transactions

    # Atualizar payee_merchant para pegar a transação da sessão
    merchant_from_db = db.session.get(Merchant, payee_merchant.id)
    db.session.refresh(merchant_from_db) # Refresh para carregar o relacionamento
    assert retrieved_transaction in merchant_from_db.transactions_as_payee


def test_transaction_with_user_payee(db):
    """Testa uma transação onde o recebedor é um usuário comum."""
    payer = User(full_name="Payer User 2", cpf="22233344455", email="payer2@example.com", password_hash="pass3")
    payee_user = User(full_name="Payee User", cpf="55566677788", email="payee.user@example.com", password_hash="pass4")

    db.session.add_all([payer, payee_user])
    db.session.commit()

    transaction = Transaction(payer_id=payer.id, payee_id=payee_user.id, amount=Decimal("25.00"))
    db.session.add(transaction)
    db.session.commit()

    retrieved_transaction = db.session.get(Transaction, transaction.id) # Usando db.session.get
    assert retrieved_transaction is not None
    assert retrieved_transaction.payee_id == payee_user.id

    # Testar relacionamentos
    payer_from_db = db.session.get(User, payer.id)
    db.session.refresh(payer_from_db) # Refresh
    payee_from_db = db.session.get(User, payee_user.id)
    db.session.refresh(payee_from_db) # Refresh
    assert retrieved_transaction in payer_from_db.sent_transactions
    assert retrieved_transaction in payee_from_db.received_transactions
