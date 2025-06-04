from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import foreign # Adicionado para anotar colunas estrangeiras no primaryjoin
import uuid
from enum import Enum

db = SQLAlchemy()

class UserType(Enum):
    COMMON = "common"
    MERCHANT = "merchant"

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(11), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    user_type = db.Column(db.Enum(UserType), default=UserType.COMMON, nullable=False)

    # Relationships
    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.payer_id', backref='payer', lazy=True)
    # Para received_transactions, precisamos de um primaryjoin para especificar como User.id se relaciona com Transaction.payee_id
    # E, idealmente, como distinguir que o payee é um User.
    # Se User.id e Merchant.id são globalmente únicos, a condição de tipo pode não ser estritamente necessária no join,
    # mas seria bom para clareza e para evitar colisões se IDs pudessem, teoricamente, ser iguais.
    # Por ora, vamos assumir que o ID é suficiente para a junção.
    received_transactions = db.relationship(
        'Transaction',
        primaryjoin=f'foreign(Transaction.payee_id) == User.id',
        back_populates="payee_as_user",
        foreign_keys="[Transaction.payee_id]",
        # overlaps="transactions_as_payee" # Sugestão simétrica ao aviso do Merchant
    )

    def __repr__(self):
        return f"<User {self.id} {self.full_name}>"

class Merchant(db.Model):
    __tablename__ = 'merchants'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(14), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    user_type = db.Column(db.Enum(UserType), default=UserType.MERCHANT, nullable=False)

    transactions_as_payee = db.relationship(
        'Transaction',
        primaryjoin=f'foreign(Transaction.payee_id) == Merchant.id',
        back_populates="payee_as_merchant",
        foreign_keys="[Transaction.payee_id]",
        overlaps="received_transactions" # Conforme sugestão do aviso
    )

    def __repr__(self):
        return f"<Merchant {self.id} {self.full_name}>"

class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    payee_id = db.Column(UUID(as_uuid=True), nullable=False) # Can be User or Merchant ID. Não é uma FK direta.
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)

    # Note: payee_id can refer to a User or a Merchant.
    # You might need a polymorphic relationship or separate fields if you want strict FK constraints to both.
    # For simplicity, keeping it as a generic UUID and handling the type logic in services.

    # Relacionamentos reversos para payee
    payee_as_user = db.relationship(
        'User',
        primaryjoin=f'foreign(Transaction.payee_id) == User.id',
        back_populates="received_transactions",
        foreign_keys=[payee_id],
        overlaps="transactions_as_payee" # Conforme sugestão do aviso
    )
    payee_as_merchant = db.relationship(
        'Merchant',
        primaryjoin=f'foreign(Transaction.payee_id) == Merchant.id',
        back_populates="transactions_as_payee",
        foreign_keys=[payee_id],
        overlaps="payee_as_user,received_transactions" # Conforme sugestão do aviso
    )


    def __repr__(self):
        return f"<Transaction {self.id} from {self.payer_id} to {self.payee_id} for {self.amount}>"
