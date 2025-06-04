from flask import Blueprint, request, jsonify
from .models import db, User, Merchant, UserType
from .services import process_transaction # Adicionado process_transaction
from werkzeug.security import generate_password_hash, check_password_hash
import re # Para validação de CPF/CNPJ (simples)
from sqlalchemy.exc import IntegrityError # Para tratar erros de unicidade
import uuid # Para converter string de ID para UUID

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return "Sistema de Pagamentos - Bem-vindo!"

@main.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    required_fields = ['full_name', 'email', 'password', 'document', 'user_type']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    user_type_str = data.get('user_type', '').lower()
    full_name = data.get('full_name')
    email = data.get('email')
    password = data.get('password')
    document = data.get('document')

    # Basic validation for document format (simplistic)
    if user_type_str == UserType.COMMON.value:
        if not re.match(r'^\d{11}$', document):
            return jsonify({"error": "Invalid CPF format. Must be 11 digits."}), 400
    elif user_type_str == UserType.MERCHANT.value:
        if not re.match(r'^\d{14}$', document):
            return jsonify({"error": "Invalid CNPJ format. Must be 14 digits."}), 400
    else:
        return jsonify({"error": "Invalid user_type. Must be 'common' or 'merchant'."}), 400

    hashed_password = generate_password_hash(password)

    if user_type_str == UserType.COMMON.value:
        # Check if CPF or Email already exists for User
        if User.query.filter((User.cpf == document) | (User.email == email)).first():
            return jsonify({"error": "CPF or Email already exists for a common user."}), 409
        new_user = User(
            full_name=full_name,
            cpf=document,
            email=email,
            password_hash=hashed_password,
            user_type=UserType.COMMON
        )
    elif user_type_str == UserType.MERCHANT.value:
        # Check if CNPJ or Email already exists for Merchant
        if Merchant.query.filter((Merchant.cnpj == document) | (Merchant.email == email)).first():
            return jsonify({"error": "CNPJ or Email already exists for a merchant."}), 409
        new_user = Merchant(
            full_name=full_name,
            cnpj=document,
            email=email,
            password_hash=hashed_password,
            user_type=UserType.MERCHANT
        )
    else: # Should have been caught earlier, but as a safeguard
        return jsonify({"error": "Invalid user_type specified"}), 400

    try:
        db.session.add(new_user)
        db.session.commit()
        # Return user info, excluding password_hash
        user_data = {
            "id": str(new_user.id),
            "full_name": new_user.full_name,
            "email": new_user.email,
            "user_type": new_user.user_type.value
        }
        if hasattr(new_user, 'cpf'):
            user_data['cpf'] = new_user.cpf
        if hasattr(new_user, 'cnpj'):
            user_data['cnpj'] = new_user.cnpj

        return jsonify(user_data), 201
    except IntegrityError as e:
        db.session.rollback()
        # This might be redundant if checks above are thorough, but good for race conditions
        return jsonify({"error": "Database integrity error. User with this document or email likely already exists.", "details": str(e)}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An unexpected error occurred.", "details": str(e)}), 500

@main.route('/transactions', methods=['POST'])
def create_transaction():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    payer_id = data.get('payer_id')
    payee_id = data.get('payee_id')
    amount = data.get('amount')

    if not all([payer_id, payee_id, amount]):
        return jsonify({"error": "Missing fields: payer_id, payee_id, or amount are required."}), 400

    try:
        # Convert amount to string in case it's a number, as process_transaction expects string for Decimal conversion
        result, status_code = process_transaction(str(payer_id), str(payee_id), str(amount))
        return jsonify(result), status_code
    except ValueError as e: # Catch potential errors if amount cannot be converted to string for Decimal
        return jsonify({"error": f"Invalid amount format: {str(e)}"}), 400
    except Exception as e: # Catch any other unexpected errors from service layer
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@main.route('/users/<user_id>/balance', methods=['GET'])
def get_user_balance(user_id):
    try:
        # Attempt to parse the user_id as a UUID
        try:
            val_uuid = uuid.UUID(user_id, version=4)
        except ValueError:
            return jsonify({"error": "Invalid user ID format."}), 400

        # Try to find in User table
        user = db.session.get(User, val_uuid) # Usando db.session.get
        if user:
            return jsonify({"user_id": str(user.id), "balance": str(user.balance), "user_type": "common"}), 200

        # Try to find in Merchant table
        merchant = db.session.get(Merchant, val_uuid) # Usando db.session.get
        if merchant:
            return jsonify({"user_id": str(merchant.id), "balance": str(merchant.balance), "user_type": "merchant"}), 200

        return jsonify({"error": "User not found"}), 404

    except Exception as e:
        return jsonify({"error": "An unexpected error occurred.", "details": str(e)}), 500
