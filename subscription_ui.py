import os
import sys
import webbrowser
import shutil
import re
from datetime import datetime
from dotenv import load_dotenv
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QFrame, QApplication,
                             QMessageBox, QSpacerItem, QSizePolicy, QWidget,
                             QLineEdit, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon

# Load environment variables
load_dotenv()

class SubscriptionDialog(QDialog):
    """Professional subscription dialog for payment instructions"""
    
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.parent_window = parent
        self.screenshot_path = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the subscription dialog UI"""
        self.setWindowTitle("Subscription Required")
        self.setFixedSize(650, 580)  # Smaller height with compact content
        self.setModal(True)
        
        # Apply professional styling consistent with main app
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: Arial, sans-serif;
            }
            QLabel {
                color: #ffffff;
                font-size: 10px;
            }
            QLabel.title {
                font-size: 16px;
                font-weight: bold;
                color: #ff6600;
            }
            QLabel.price {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
            }
            QLabel.section-header {
                font-size: 12px;
                font-weight: bold;
                color: #ff6600;
                margin-top: 6px;
                margin-bottom: 3px;
            }
            QLabel.info-text {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 4px;
                font-family: Arial, sans-serif;
                font-size: 10px;
                padding: 8px;
                margin: 3px 0px;
                line-height: 1.3;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                padding: 4px;
                border-radius: 3px;
                font-size: 10px;
                max-height: 24px;
            }
            QLineEdit:focus {
                border-color: #ff6600;
            }
            QPushButton {
                background-color: #ff6600;
                color: #ffffff;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: 500;
                font-size: 10px;
                min-height: 20px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #e55a00;
            }
            QPushButton:pressed {
                background-color: #cc4f00;
            }
            QPushButton.secondary {
                background-color: #555555;
                color: #ffffff;
            }
            QPushButton.secondary:hover {
                background-color: #666666;
            }
            QFrame.separator {
                background-color: #555555;
                max-height: 1px;
                border: none;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)  # Reduced spacing
        main_layout.setContentsMargins(15, 10, 15, 10)  # Smaller margins
        
        # Title section
        title_label = QLabel("Monthly Subscription Required")
        title_label.setProperty("class", "title")
        title_label.setAlignment(Qt.AlignCenter)
        username_label = QLabel(f"For Maloum Username: {self.username}")
        username_label.setAlignment(Qt.AlignCenter)
        username_label.setStyleSheet("color: #ff6600; font-weight: bold; font-size: 11px;")
        main_layout.addWidget(title_label)
        main_layout.addWidget(username_label)
   
        # Separator
        separator1 = QFrame()
        separator1.setProperty("class", "separator")
        separator1.setFrameShape(QFrame.HLine)

        main_layout.addWidget(separator1)
        
        # Price section
        price_layout = QVBoxLayout()
        price_layout.setSpacing(3)  # Smaller spacing
        
        price_label = QLabel(f"Price: EUR {os.getenv('MONTHLY_PRICE', '19.99')} per username per month")
        price_label.setProperty("class", "price")
        price_label.setAlignment(Qt.AlignCenter)
        price_layout.addWidget(price_label)
        


        
        main_layout.addLayout(price_layout)     
        
        # Payment instructions section
        payment_header = QLabel("Make a Payment to:")
        payment_header.setProperty("class", "section-header")
        main_layout.addWidget(payment_header)
        
        # Payment details as label (no scroll bars)
        payment_text = self.get_payment_instructions()
        payment_display = QLabel(payment_text)
        payment_display.setProperty("class", "info-text")
        payment_display.setWordWrap(True)
        payment_display.setAlignment(Qt.AlignTop)
        payment_display.setMinimumHeight(90)  # Smaller height
        main_layout.addWidget(payment_display)
        
        # Important notes section
        notes_header = QLabel("Important Notes")
        notes_header.setProperty("class", "section-header")
        main_layout.addWidget(notes_header)
        
        # Important notes as label (no scroll bars)
        notes_text = self.get_important_notes()
        notes_display = QLabel(notes_text)
        notes_display.setProperty("class", "info-text")
        notes_display.setWordWrap(True)
        notes_display.setAlignment(Qt.AlignTop)
        notes_display.setMinimumHeight(70)  # Smaller height
        main_layout.addWidget(notes_display)
        
        # Screenshot upload section
        screenshot_section = QVBoxLayout()
        screenshot_section.setSpacing(5)  # Smaller spacing
        
        screenshot_header = QLabel("Payment Screenshot (Optional)")
        screenshot_header.setProperty("class", "section-header")
        screenshot_section.addWidget(screenshot_header)
        
        # Screenshot upload button and status in horizontal layout
        screenshot_layout = QHBoxLayout()
        
        self.screenshot_button = QPushButton("Upload")
        self.screenshot_button.setProperty("class", "secondary")
        self.screenshot_button.setMinimumWidth(110)  # Smaller button
        self.screenshot_button.setMaximumWidth(110)
        self.screenshot_button.setMinimumHeight(26)  # Smaller height
        self.screenshot_button.clicked.connect(self.upload_screenshot)
        screenshot_layout.addWidget(self.screenshot_button)
        
        self.screenshot_status = QLabel("No screenshot uploaded")
        self.screenshot_status.setStyleSheet("color: #cccccc; font-size: 9px; font-style: italic; margin-left: 8px;")
        screenshot_layout.addWidget(self.screenshot_status)
        
        screenshot_layout.addStretch()
        screenshot_section.addLayout(screenshot_layout)
        main_layout.addLayout(screenshot_section)
        
        # Email input section (moved here, below screenshot)
        email_header = QLabel("Email Address (for activation confirmation):")
        email_header.setProperty("class", "section-header")
        main_layout.addWidget(email_header)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email address")
        self.email_input.setMaximumHeight(24)  # Smaller email input
        main_layout.addWidget(self.email_input)
        
        # Separator
        separator2 = QFrame()
        separator2.setProperty("class", "separator")
        separator2.setFrameShape(QFrame.HLine)
        main_layout.addWidget(separator2)
        
        # Button section
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)  # Smaller spacing between buttons
        
        # Add spacer to center buttons
        button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # Copy payment details button
        copy_button = QPushButton("Copy Payment Details")
        copy_button.setMinimumWidth(120)  # Smaller button
        copy_button.clicked.connect(self.copy_payment_details)
        button_layout.addWidget(copy_button)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumWidth(80)  # Smaller button
        cancel_button.setProperty("class", "secondary")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # I've Paid button
        paid_button = QPushButton("I've Sent Payment")
        paid_button.setMinimumWidth(110)  # Smaller button
        paid_button.clicked.connect(self.payment_sent)
        button_layout.addWidget(paid_button)
        
        button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        main_layout.addLayout(button_layout)
        
        # Center the dialog on screen
        self.center_on_screen()
    
    def get_payment_instructions(self):
        """Get formatted payment instructions"""
        iban = os.getenv('PAYONEER_EUR_IBAN', 'YOUR_EUR_IBAN')
        bic = os.getenv('PAYONEER_BIC', 'YOUR_BIC')
        price = os.getenv('MONTHLY_PRICE', '19.99')
        
        instructions = f"""Payment Method: Bank Transfer
Amount: EUR {price}
Currency: EUR (Euro)
IBAN: {iban}
BIC/SWIFT: {bic}
Beneficiary Name: Noel Periarce
Country: Luxembourg
Reference: USERNAME_{self.username}"""
        
        return instructions
    
    def get_important_notes(self):
        """Get important notes text"""
        notes = f"""1. You MUST include "USERNAME_{self.username}" in the transfer reference field
2. Use the exact amount: EUR {os.getenv('MONTHLY_PRICE', '19.99')}
3. After payment, click "I've Sent Payment" below
4. Account activation within 24 hours after payment verification
5. Subscription renews monthly - transfer the same amount each month"""
        
        return notes
    
    def upload_screenshot(self):
        """Handle screenshot upload"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Upload Payment Screenshot",
                "",
                "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
            )
            
            if file_path:
                # Create screenshots directory if it doesn't exist
                screenshots_dir = os.path.join(os.path.expanduser("~"), ".maloum_automation", "payment_screenshots", self.username)
                os.makedirs(screenshots_dir, exist_ok=True)
                
                # Generate filename with username and timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_extension = os.path.splitext(file_path)[1]
                new_filename = f"{self.username}_{timestamp}{file_extension}"
                new_path = os.path.join(screenshots_dir, new_filename)
                
                # Copy file to screenshots directory
                shutil.copy2(file_path, new_path)
                
                # Update UI
                self.screenshot_path = new_path
                self.screenshot_status.setText(f"✅ Screenshot uploaded: {new_filename}")
                self.screenshot_status.setStyleSheet("color: #28a745; font-size: 10px; font-weight: 500;")
                self.screenshot_button.setText("Change Screenshot")
                
                QMessageBox.information(
                    self,
                    "Screenshot Uploaded",
                    f"Payment screenshot uploaded successfully!\n\nFile: {new_filename}\n\nThis will be included with your payment notification."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Upload Error", f"Failed to upload screenshot: {str(e)}")
    
    def copy_payment_details(self):
        """Copy payment details to clipboard"""
        try:
            payment_text = self.get_payment_instructions()
            
            # Get clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(payment_text)
            
            # Show confirmation
            QMessageBox.information(self, "Copied", 
                                  "Payment details copied to clipboard!")
            
        except Exception as e:
            QMessageBox.warning(self, "Copy Failed", 
                              f"Could not copy to clipboard: {e}")
    
    def payment_sent(self):
        """Handle when user confirms they've sent payment"""
        try:
            # Validate email
            user_email = self.email_input.text().strip()
            if not user_email:
                QMessageBox.warning(self, "Email Required", "Please enter your email address for activation confirmation.")
                return
                
            # Basic email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, user_email):
                QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
                return
            
            # Show confirmation dialog
            reply = QMessageBox.question(
                self, 
                "Payment Confirmation",
                f"Have you sent EUR {os.getenv('MONTHLY_PRICE', '19.99')} to the provided bank account "
                f"with reference 'USERNAME_{self.username}'?\n\n"
                f"Your account will be activated within 24 hours after we verify the payment.\n"
                f"Confirmation will be sent to: {user_email}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Send notifications to Discord with screenshot and email
                self.send_payment_notification(user_email)
                
                # Show final confirmation
                QMessageBox.information(
                    self,
                    "Payment Submitted",
                    f"Thank you! We will verify your payment and activate your account within 24 hours.\n\n"
                    f"Username: {self.username}\n"
                    f"Email: {user_email}\n"
                    f"Amount: EUR {os.getenv('MONTHLY_PRICE', '19.99')}\n"
                    f"Reference: USERNAME_{self.username}\n\n"
                    f"You will receive email confirmation once your account is activated."
                )
                
                # Close dialog with success code
                self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
    
    def send_payment_notification(self, user_email):
        """Send payment notification to Discord with screenshot and email"""
        try:
            import requests
            import json
            
            # Prepare notification data
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            username = self.username
            amount = os.getenv('MONTHLY_PRICE', '19.99')
            reference = f"USERNAME_{username}"
            
            # Discord webhook notification
            discord_webhook = "https://discordapp.com/api/webhooks/1395443249107439667/Hk8aCQdkud175xgHY8yKmLaLaHRbzNQaSbXXYIlKBR2wOudRNDa2ruc0CrgQ7RhXT4eV"
            
            # Prepare Discord message
            discord_data = {
                "embeds": [{
                    "title": "🔔 New Payment Notification",
                    "description": "A user has confirmed payment for Maloum Automation subscription",
                    "color": 16750848,  # Orange color
                    "fields": [
                        {"name": "👤 Username", "value": username, "inline": True},
                        {"name": "📧 Email", "value": user_email, "inline": True},
                        {"name": "💰 Amount", "value": f"EUR {amount}", "inline": True},
                        {"name": "🔖 Reference", "value": reference, "inline": True},
                        {"name": "🕒 Time", "value": timestamp, "inline": True},
                        {"name": "📸 Screenshot", "value": "✅ Uploaded" if self.screenshot_path else "❌ Not provided", "inline": True},
                        {"name": "⚠️ Action Required", "value": "1. Check Payoneer for payment\n2. Verify reference matches\n3. Activate user in admin panel\n4. Send confirmation email", "inline": False}
                    ],
                    "footer": {"text": "Maloum Automation - License System"},
                    "timestamp": datetime.now().isoformat()
                }]
            }
            
            # Send Discord notification with screenshot if available
            try:
                if self.screenshot_path and os.path.exists(self.screenshot_path):
                    # Send with file attachment
                    with open(self.screenshot_path, 'rb') as file:
                        files = {
                            'file': (os.path.basename(self.screenshot_path), file, 'image/png')
                        }
                        payload = {
                            'payload_json': json.dumps(discord_data)
                        }
                        response = requests.post(discord_webhook, data=payload, files=files, timeout=10)
                else:
                    # Send without file
                    response = requests.post(discord_webhook, json=discord_data, timeout=10)
                
                if response.status_code == 204:
                    print(f"✅ Discord notification sent for {username}")
                else:
                    print(f"❌ Discord notification failed: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Discord notification error: {e}")
            
            # Create activation email template
            activation_email_template = f"""
Subject: Account Activation Confirmation - Maloum Automation

Dear {username},

Your Maloum Automation subscription has been successfully activated!

Account Details:
- Username: {username}
- Email: {user_email}
- Subscription: Monthly (EUR {amount})
- Activated: {timestamp}

You can now use all features of the Maloum Automation Suite.

Thank you for your subscription!

Best regards,
Maloum Automation Team
"""
            
            print(f"📧 Activation email template prepared:")
            print(f"To: {user_email}")
            print(activation_email_template)
            
        except Exception as e:
            print(f"❌ Notification error: {e}")
    
    def center_on_screen(self):
        """Center the dialog on the screen"""
        if self.parent_window:
            # Center relative to parent window
            parent_geometry = self.parent_window.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
        else:
            # Center on screen
            screen = QApplication.desktop().screenGeometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)


class SubscriptionRenewalDialog(QDialog):
    """Dialog for subscription renewal (when subscription expired)"""
    
    def __init__(self, username, expiry_date, parent=None):
        super().__init__(parent)
        self.username = username
        self.expiry_date = expiry_date
        self.parent_window = parent
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the renewal dialog UI"""
        self.setWindowTitle("Subscription Expired")
        self.setFixedSize(550, 400)
        self.setModal(True)
        
        # Apply same styling as subscription dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: Arial, sans-serif;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QLabel.title {
                font-size: 18px;
                font-weight: bold;
                color: #ff6600;
            }
            QLabel.expired {
                font-size: 14px;
                font-weight: bold;
                color: #dc3545;
            }
            QPushButton {
                background-color: #ff6600;
                color: #ffffff;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
                min-height: 25px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e55a00;
            }
            QPushButton.secondary {
                background-color: #555555;
                color: #ffffff;
            }
            QPushButton.secondary:hover {
                background-color: #666666;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title_label = QLabel("Subscription Expired")
        title_label.setProperty("class", "title")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Expiry info
        expiry_info = QLabel(f"Your subscription for '{self.username}' expired on {self.expiry_date}")
        expiry_info.setProperty("class", "expired")
        expiry_info.setAlignment(Qt.AlignCenter)
        expiry_info.setWordWrap(True)
        main_layout.addWidget(expiry_info)
        
        # Message
        message = QLabel("To continue using the automation tools, please renew your subscription.")
        message.setAlignment(Qt.AlignCenter)
        message.setWordWrap(True)
        main_layout.addWidget(message)
        
        # Price
        price_label = QLabel(f"Renewal Price: EUR {os.getenv('MONTHLY_PRICE', '19.99')} for 30 days")
        price_label.setAlignment(Qt.AlignCenter)
        price_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ff6600;")
        main_layout.addWidget(price_label)
        
        # Add some spacing
        main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        cancel_button = QPushButton("Not Now")
        cancel_button.setProperty("class", "secondary")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        renew_button = QPushButton("Renew Subscription")
        renew_button.clicked.connect(self.show_renewal_instructions)
        button_layout.addWidget(renew_button)
        
        button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        main_layout.addLayout(button_layout)
        
        # Center the dialog
        self.center_on_screen()
    
    def show_renewal_instructions(self):
        """Show renewal payment instructions"""
        # Close this dialog and show subscription dialog
        self.accept()
        
        # Show subscription dialog for renewal
        subscription_dialog = SubscriptionDialog(self.username, self.parent_window)
        subscription_dialog.exec_()
    
    def center_on_screen(self):
        """Center the dialog on the screen"""
        if self.parent_window:
            parent_geometry = self.parent_window.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
        else:
            screen = QApplication.desktop().screenGeometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)


# Test function to preview the dialogs
def test_subscription_dialogs():
    """Test function to preview subscription dialogs"""
    app = QApplication(sys.argv)
    
    # Test subscription dialog
    dialog = SubscriptionDialog("testuser123")
    result = dialog.exec_()
    
    if result == QDialog.Accepted:
        print("User confirmed payment sent")
    else:
        print("User cancelled subscription")
    
    # Test renewal dialog
    renewal_dialog = SubscriptionRenewalDialog("testuser123", "2025-01-15")
    renewal_result = renewal_dialog.exec_()
    
    sys.exit()

if __name__ == "__main__":
    # Run test when file is executed directly
    test_subscription_dialogs()