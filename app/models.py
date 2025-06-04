from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
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
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.payee_id', backref='payee', lazy=True)

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

    # Relationship for transactions where this merchant is the payee
    transactions_as_payee = db.relationship('Transaction', foreign_keys='Transaction.payee_id', backref='merchant_payee', lazy=True)


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
    payee_id = db.Column(UUID(as_uuid=True), nullable=False) # Can be User or Merchant
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)

    # Note: payee_id can refer to a User or a Merchant.
    # You might need a polymorphic relationship or separate fields if you want strict FK constraints to both.
    # For simplicity, keeping it as a generic UUID and handling the type logic in services.

    def __repr__(self):
        return f"<Transaction {self.id} from {self.payer_id} to {self.payee_id} for {self.amount}>"
