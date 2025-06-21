import os
import urllib.parse
from flask import Flask, request, jsonify
from flask_cors import CORS
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth import default as google_auth_default
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ENV VARIABLES
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', 'your-default-sheet-id')
RANGE_NAME = os.getenv('RANGE_NAME', 'Daily-Order!A1')
ENV = os.getenv('ENV', 'development')

# Load credentials
if ENV == 'production':
    credentials, _ = google_auth_default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
else:
    SERVICE_ACCOUNT_FILE = 'service-account.json'
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

@app.route('/add-order', methods=['POST'])
def add_order():
    try:
        data = request.json
        order_data = data.get('orderData')
        cart_items = data.get('cartItems')

        # Decode and format message
        decoded_message = urllib.parse.unquote(order_data.get('message') or '').strip()
        decoded_message = decoded_message.replace("*", "").replace("•", "🔹")

        # Create cart summary string
        cart_summary = ', '.join([
            f"{item['name']} x{item['cartQuantity']} (₹{item['price']})"
            for item in cart_items
        ])

        # Compose row for Sheet
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

        # Send to Google Sheets
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
    port = int(os.environ.get("PORT", 8080))
    debug = ENV != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)
