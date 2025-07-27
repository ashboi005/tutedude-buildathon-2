import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# --- Email Configuration ---
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

# --- Twilio Configuration ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")


def send_email(to_email: str, subject: str, body_html: str):
    """Sends an email using SMTP."""
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_SENDER]):
        logger.error("SMTP settings are not fully configured. Cannot send email.")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = EMAIL_SENDER
    message["To"] = to_email
    message.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, message.as_string())
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_sms(to_phone_number: str, body: str):
    """Sends an SMS using Twilio."""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        logger.error("Twilio settings are not fully configured. Cannot send SMS.")
        return False

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone_number
        )
        logger.info(f"SMS sent successfully to {to_phone_number}, SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_phone_number}: {e}")
        return False


# Email Templates
def get_order_confirmation_email(order_data: dict, is_buyer: bool = True) -> tuple[str, str]:
    """Generate order confirmation email template"""
    role = "buyer" if is_buyer else "seller"
    action = "placed" if is_buyer else "received"
    
    subject = f"Order {action.title()} - Order #{str(order_data['id'])[:8]}"
    
    body = f"""
    <html>
    <body>
        <h2>Order {action.title()}!</h2>
        <p>Hello,</p>
        <p>An order has been {action} with the following details:</p>
        
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
            <h3>Order Details:</h3>
            <p><strong>Order ID:</strong> {order_data['id']}</p>
            <p><strong>Product:</strong> {order_data.get('product_name', 'N/A')}</p>
            <p><strong>Quantity:</strong> {order_data['quantity']}</p>
            <p><strong>Price per Unit:</strong> ₹{order_data['price_per_unit']}</p>
            <p><strong>Total Amount:</strong> ₹{order_data['total_amount']}</p>
            <p><strong>Order Type:</strong> {order_data['order_type'].replace('_', ' ').title()}</p>
            <p><strong>Payment Status:</strong> {order_data['payment_status'].title()}</p>
        </div>
        
        <p>Thank you for using our platform!</p>
        <p>Best regards,<br>TuteDude Team</p>
    </body>
    </html>
    """
    
    return subject, body


def get_bulk_order_finalized_email(bulk_window_data: dict, orders: list) -> tuple[str, str]:
    """Generate bulk order finalized email template"""
    subject = f"Bulk Order Window Finalized - {bulk_window_data['title']}"
    
    body = f"""
    <html>
    <body>
        <h2>Bulk Order Window Finalized!</h2>
        <p>Hello,</p>
        <p>The bulk order window "{bulk_window_data['title']}" has been finalized.</p>
        
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
            <h3>Window Summary:</h3>
            <p><strong>Total Participants:</strong> {bulk_window_data['total_participants']}</p>
            <p><strong>Total Amount:</strong> ₹{bulk_window_data['total_amount']}</p>
            <p><strong>Orders Count:</strong> {len(orders)}</p>
        </div>
        
        <h3>Your Orders:</h3>
        <div style="background-color: #e8f4fd; padding: 15px; border-radius: 5px;">
        """
    
    for order in orders:
        body += f"""
            <div style="margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 10px;">
                <p><strong>Order ID:</strong> {order['id']}</p>
                <p><strong>Product:</strong> {order.get('product_name', 'N/A')}</p>
                <p><strong>Quantity:</strong> {order['quantity']}</p>
                <p><strong>Final Price:</strong> ₹{order['price_per_unit']} per unit</p>
                <p><strong>Total:</strong> ₹{order['total_amount']}</p>
                <p><strong>Status:</strong> {order['payment_status'].title()}</p>
            </div>
        """
    
    body += """
        </div>
        <p>Thank you for participating in bulk ordering!</p>
        <p>Best regards,<br>TuteDude Team</p>
    </body>
    </html>
    """
    
    return subject, body


def get_supplier_update_email(supplier_name: str, update_type: str, product_name: str = None) -> tuple[str, str]:
    """Generate supplier update notification email"""
    subject = f"Supplier Update - {supplier_name}"
    
    if update_type == "product_update" and product_name:
        message = f"The supplier {supplier_name} has updated the product '{product_name}'."
    elif update_type == "pricing_update" and product_name:
        message = f"The supplier {supplier_name} has updated pricing for the product '{product_name}'."
    else:
        message = f"The supplier {supplier_name} has made updates to their products."
    
    body = f"""
    <html>
    <body>
        <h2>Supplier Update Notification</h2>
        <p>Hello,</p>
        <p>{message}</p>
        
        <p>You may want to check their latest offerings on our platform.</p>
        
        <p>Best regards,<br>TuteDude Team</p>
    </body>
    </html>
    """
    
    return subject, body


# SMS Templates
def get_order_confirmation_sms(order_data: dict, is_buyer: bool = True) -> str:
    """Generate order confirmation SMS template"""
    action = "placed" if is_buyer else "received"
    return f"Order {action}! Order #{str(order_data['id'])[:8]} for {order_data['quantity']} units of {order_data.get('product_name', 'product')} - ₹{order_data['total_amount']}. Status: {order_data['payment_status']}. - TuteDude"


def get_bulk_order_finalized_sms(bulk_window_title: str, orders_count: int, total_amount: float) -> str:
    """Generate bulk order finalized SMS template"""
    return f"Bulk order '{bulk_window_title}' finalized! {orders_count} orders processed, total: ₹{total_amount}. Check your account for details. - TuteDude"


def get_supplier_update_sms(supplier_name: str, update_type: str) -> str:
    """Generate supplier update SMS template"""
    if update_type == "product_update":
        return f"Supplier update: {supplier_name} has updated their products. Check the latest offerings! - TuteDude"
    elif update_type == "pricing_update":
        return f"Price update: {supplier_name} has updated their pricing. Check for better deals! - TuteDude"
    else:
        return f"Update from {supplier_name}. Check their latest changes on TuteDude!"
