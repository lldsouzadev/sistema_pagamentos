from .models import db, User, Merchant, Transaction, TransactionStatus, UserType
from decimal import Decimal
import uuid # Required for converting string IDs to UUID objects
import requests
from flask import current_app

# Mock external services - TO BE REPLACED WITH ACTUAL CALLS
# def mock_authorize_transaction():
#     print("Mock Authorizer: Transaction authorized.")
#     return True

# def mock_send_notification(payee_id, message):
#     print(f"Mock Notifier: Sending notification to {payee_id}: {message}")
#     return True

def authorize_transaction_external():
    # This URL was mentioned in some contexts as an authorizer mock.
    # It returns: {"message": "Autorizado"}
    auth_url = current_app.config.get('AUTHORIZATION_SERVICE_URL', 'https://run.mocky.io/v3/5794d450-d2e2-4412-8131-73d0293ac1cc')
    try:
        response = requests.get(auth_url)
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        if data.get("message") == "Autorizado":
            print(f"External Authorizer ({auth_url}): Transaction authorized.")
            return True
        else:
            print(f"External Authorizer ({auth_url}): Transaction NOT authorized. Response: {data}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"External Authorizer ({auth_url}): Request failed: {e}")
        return False # Fail safe: if service is down, consider not authorized

def send_notification_external(payee_id, amount):
    # This URL was mentioned as a notification mock.
    # It returns: {"message": true}
    notify_url = current_app.config.get('NOTIFICATION_SERVICE_URL', 'https://run.mocky.io/v3/54dc2cf1-3add-45b5-b5a9-6bf7e7f1f4a6')
    payload = {"payee_id": str(payee_id), "amount": str(amount)} # Example payload
    try:
        response = requests.post(notify_url, json=payload) # Using POST as is common for notifications
        response.raise_for_status()
        data = response.json()
        if data.get("message") == True or data.get("message") == "true": # Mocky might return string "true"
            print(f"External Notifier ({notify_url}): Notification sent successfully for payee {payee_id}.")
            return True
        else:
            print(f"External Notifier ({notify_url}): Notification failed or service indicated failure. Response: {data}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"External Notifier ({notify_url}): Request failed: {e}")
        return False # Fail safe: if service is down, consider notification failed

def process_transaction(payer_id_str, payee_id_str, amount_str):
    try:
        payer_id = uuid.UUID(payer_id_str)
        payee_id = uuid.UUID(payee_id_str)
        amount = Decimal(amount_str) # Use Decimal for currency
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid input format: {str(e)}"}, 400

    if amount <= 0:
        return {"error": "Transaction amount must be positive."}, 400

    # 1. Verify Payer
    payer = User.query.filter_by(id=payer_id, user_type=UserType.COMMON).first()
    if not payer:
        return {"error": "Payer not found or is not a common user."}, 404

    # 2. Verify Payee
    payee_user = User.query.get(payee_id)
    payee_merchant = Merchant.query.get(payee_id)

    if not payee_user and not payee_merchant:
        return {"error": "Payee not found."}, 404

    payee = payee_user if payee_user else payee_merchant

    # 3. Check Payer's Balance
    if payer.balance < amount:
        return {"error": "Insufficient balance."}, 400

    # 4. External Authorization
    if not authorize_transaction_external(): # MODIFICADO
        # Record failed transaction attempt due to authorization failure
        transaction = Transaction(
            payer_id=payer.id,
            payee_id=payee.id,
            amount=amount,
            status=TransactionStatus.FAILED
        )
        db.session.add(transaction)
        db.session.commit()
        return {"error": "Transaction not authorized by external service."}, 403

    # 5. Perform Transaction
    try:
        payer.balance -= amount
        payee.balance += amount

        transaction = Transaction(
            payer_id=payer.id,
            payee_id=payee.id, # payee.id will correctly get the id from either User or Merchant object
            amount=amount,
            status=TransactionStatus.COMPLETED
        )
        db.session.add(transaction)
        db.session.commit()

        # 6. External Notification
        if not send_notification_external(payee.id, amount): # MODIFICADO
            # Log or handle notification failure if necessary, but transaction is already committed.
            # This is a common pattern: transaction success is primary, notification is secondary.
            print(f"Warning: Notification failed for transaction {transaction.id} to payee {payee.id}")

        return {
            "message": "Transaction completed successfully.",
            "transaction_id": str(transaction.id),
            "status": transaction.status.value
        }, 200

    except Exception as e:
        db.session.rollback()
        # Record failed transaction attempt
        transaction = Transaction(
            payer_id=payer.id,
            payee_id=payee.id,
            amount=amount,
            status=TransactionStatus.FAILED
        )
        # We should try to save this failed transaction if possible, but the session might be in a bad state
        try:
            db.session.add(transaction)
            db.session.commit()
        except Exception as inner_e:
            print(f"Failed to save failed transaction record: {inner_e}")
            # Potentially log this critical failure to save transaction status

        return {"error": f"Transaction failed during processing: {str(e)}"}, 500
