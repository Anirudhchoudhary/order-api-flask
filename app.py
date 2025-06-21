import os
import json
import boto3
import urllib.parse
from flask import Flask, request, jsonify
from flask_cors import CORS
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ENV variables
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
RANGE_NAME = os.environ.get("RANGE_NAME", "Daily-Order!A1")
SECRET_NAME = os.environ.get("SECRET_NAME", "google-sheets-service-account")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

def get_credentials_from_secret(secret_name, region_name):
    """Load Google service account credentials from AWS Secrets Manager"""
    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)
    service_account_info = json.loads(response["SecretString"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return credentials

# Initialize credentials (once)
credentials = get_credentials_from_secret(SECRET_NAME, AWS_REGION)

@app.route('/')
def index():
    return jsonify({'message': 'Order API is running'}), 200

@app.route('/add-order', methods=['POST'])
def add_order():
    try:
        data = request.json
        order_data = data.get('orderData')
        cart_items = data.get('cartItems')

        # Decode and format message
        decoded_message = urllib.parse.unquote(order_data.get('message', '')).strip()
        decoded_message = decoded_message.replace("*", "").replace("•", "🔹")

        cart_summary = ', '.join([
            f"{item['name']} x{item['cartQuantity']} (₹{item['price']})"
            for item in cart_items
        ])

        row = [
            order_data.get('name'),
            order_data.get('phone'),
            order_data.get('address'),
            order_data.get('city'),
            order_data.get('pincode'),
            decoded_message,
            order_data.get('totalPrice'),
            cart_summary,
        ]

        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()

        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption='RAW',
            body={'values': [row]}
        ).execute()

        return jsonify({'message': 'Order added successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=os.environ.get('ENV') != 'production')
