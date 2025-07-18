import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables
load_dotenv()

class LicenseManager:
    """Manage Firebase subscriptions and license validation"""
    
    def __init__(self):
        """Initialize Firebase connection"""
        self.db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Get the service account key path from environment
                key_path = os.getenv('FIREBASE_KEY_PATH', 'firebase-key.json')
                
                # Check if key file exists
                if not os.path.exists(key_path):
                    raise FileNotFoundError(f"Firebase key file not found: {key_path}")
                
                # Initialize Firebase Admin SDK
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
                print("[INFO] Firebase initialized successfully")
            
            # Get Firestore client
            self.db = firestore.client()
            
        except Exception as e:
            print(f"[ERROR] Firebase initialization failed: {e}")
            self.db = None
    
    def check_subscription(self, username):
        """Check if username has active subscription"""
        try:
            if not self.db:
                print("[ERROR] Firebase not initialized")
                return False
            
            if not username or len(username.strip()) == 0:
                print("[ERROR] Invalid username provided")
                return False
            
            username = username.strip().lower()  # Normalize username
            
            # Get subscription document from Firebase
            doc_ref = self.db.collection('subscriptions').document(username)
            doc = doc_ref.get()
            
            if not doc.exists:
                print(f"[INFO] No subscription found for username: {username}")
                return False
            
            # Get subscription data
            subscription_data = doc.to_dict()
            
            # Check subscription status
            status = subscription_data.get('status', 'inactive')
            if status != 'active':
                print(f"[INFO] Subscription status is '{status}' for username: {username}")
                return False
            
            # Check subscription expiry
            subscription_end = subscription_data.get('subscription_end')
            if subscription_end:
                # Parse subscription end date
                if isinstance(subscription_end, str):
                    try:
                        end_date = datetime.strptime(subscription_end, '%Y-%m-%d')
                    except ValueError:
                        try:
                            end_date = datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            print(f"[ERROR] Invalid date format in subscription_end: {subscription_end}")
                            return False
                else:
                    # Assume it's a Firebase timestamp
                    end_date = subscription_end.replace(tzinfo=None) if hasattr(subscription_end, 'replace') else subscription_end
                
                # Check if subscription has expired
                current_date = datetime.now()
                if current_date > end_date:
                    print(f"[INFO] Subscription expired on {end_date} for username: {username}")
                    # Update status to expired
                    self._update_subscription_status(username, 'expired')
                    return False
                else:
                    days_remaining = (end_date - current_date).days
                    print(f"[INFO] Subscription active, {days_remaining} days remaining for username: {username}")
            
            print(f"[SUCCESS] Active subscription confirmed for username: {username}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error checking subscription for {username}: {e}")
            return False
    
    def activate_subscription(self, username, payment_reference=None):
        """Activate subscription for username"""
        try:
            if not self.db:
                print("[ERROR] Firebase not initialized")
                return False
            
            if not username or len(username.strip()) == 0:
                print("[ERROR] Invalid username provided")
                return False
            
            username = username.strip().lower()  # Normalize username
            
            # Calculate subscription dates
            start_date = datetime.now()
            end_date = start_date + timedelta(days=30)  # 30 days subscription
            
            # Get subscription price from environment
            monthly_price = float(os.getenv('MONTHLY_PRICE', '19.99'))
            
            # Prepare subscription data
            subscription_data = {
                'status': 'active',
                'subscription_start': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                'subscription_end': end_date.strftime('%Y-%m-%d %H:%M:%S'),
                'last_payment': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                'price': monthly_price,
                'currency': 'EUR',
                'payment_reference': payment_reference or f"USERNAME_{username}",
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Save to Firebase
            doc_ref = self.db.collection('subscriptions').document(username)
            doc_ref.set(subscription_data)
            
            print(f"[SUCCESS] Subscription activated for username: {username}")
            print(f"[INFO] Subscription valid until: {end_date.strftime('%Y-%m-%d')}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error activating subscription for {username}: {e}")
            return False
    
    def renew_subscription(self, username, payment_reference=None):
        """Renew existing subscription for username"""
        try:
            if not self.db:
                print("[ERROR] Firebase not initialized")
                return False
            
            username = username.strip().lower()  # Normalize username
            
            # Get current subscription
            doc_ref = self.db.collection('subscriptions').document(username)
            doc = doc_ref.get()
            
            if not doc.exists:
                print(f"[INFO] No existing subscription found, creating new one for: {username}")
                return self.activate_subscription(username, payment_reference)
            
            # Get current subscription data
            subscription_data = doc.to_dict()
            
            # Calculate new end date (30 days from now or from current end date if still valid)
            current_end = subscription_data.get('subscription_end')
            current_date = datetime.now()
            
            if current_end:
                try:
                    if isinstance(current_end, str):
                        end_date = datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
                    else:
                        end_date = current_end.replace(tzinfo=None) if hasattr(current_end, 'replace') else current_end
                    
                    # If subscription is still valid, extend from current end date
                    if end_date > current_date:
                        new_end_date = end_date + timedelta(days=30)
                    else:
                        new_end_date = current_date + timedelta(days=30)
                        
                except ValueError:
                    new_end_date = current_date + timedelta(days=30)
            else:
                new_end_date = current_date + timedelta(days=30)
            
            # Update subscription data
            update_data = {
                'status': 'active',
                'subscription_end': new_end_date.strftime('%Y-%m-%d %H:%M:%S'),
                'last_payment': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                'payment_reference': payment_reference or f"USERNAME_{username}",
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Update in Firebase
            doc_ref.update(update_data)
            
            print(f"[SUCCESS] Subscription renewed for username: {username}")
            print(f"[INFO] New expiry date: {new_end_date.strftime('%Y-%m-%d')}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error renewing subscription for {username}: {e}")
            return False
    
    def get_subscription_info(self, username):
        """Get subscription information for username"""
        try:
            if not self.db:
                return None
            
            username = username.strip().lower()  # Normalize username
            
            doc_ref = self.db.collection('subscriptions').document(username)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            subscription_data = doc.to_dict()
            
            # Calculate days remaining
            subscription_end = subscription_data.get('subscription_end')
            days_remaining = 0
            
            if subscription_end:
                try:
                    if isinstance(subscription_end, str):
                        end_date = datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
                    else:
                        end_date = subscription_end.replace(tzinfo=None) if hasattr(subscription_end, 'replace') else subscription_end
                    
                    current_date = datetime.now()
                    days_remaining = max(0, (end_date - current_date).days)
                    
                except ValueError:
                    pass
            
            return {
                'username': username,
                'status': subscription_data.get('status', 'unknown'),
                'subscription_start': subscription_data.get('subscription_start'),
                'subscription_end': subscription_data.get('subscription_end'),
                'last_payment': subscription_data.get('last_payment'),
                'price': subscription_data.get('price', 0),
                'currency': subscription_data.get('currency', 'EUR'),
                'days_remaining': days_remaining
            }
            
        except Exception as e:
            print(f"[ERROR] Error getting subscription info for {username}: {e}")
            return None
    
    def _update_subscription_status(self, username, status):
        """Internal method to update subscription status"""
        try:
            if not self.db:
                return False
            
            username = username.strip().lower()
            
            doc_ref = self.db.collection('subscriptions').document(username)
            doc_ref.update({
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error updating status for {username}: {e}")
            return False
    
    def list_all_subscriptions(self):
        """List all subscriptions (for admin purposes)"""
        try:
            if not self.db:
                return []
            
            docs = self.db.collection('subscriptions').stream()
            subscriptions = []
            
            for doc in docs:
                data = doc.to_dict()
                data['username'] = doc.id
                subscriptions.append(data)
            
            return subscriptions
            
        except Exception as e:
            print(f"[ERROR] Error listing subscriptions: {e}")
            return []
    
    def delete_subscription(self, username):
        """Delete subscription (for admin purposes)"""
        try:
            if not self.db:
                return False
            
            username = username.strip().lower()
            
            doc_ref = self.db.collection('subscriptions').document(username)
            doc_ref.delete()
            
            print(f"[SUCCESS] Subscription deleted for username: {username}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error deleting subscription for {username}: {e}")
            return False

# Test function for manual testing
def test_license_manager():
    """Test function to check if LicenseManager works"""
    try:
        lm = LicenseManager()
        
        # Test username
        test_username = "testuser123"
        
        print(f"Testing with username: {test_username}")
        
        # Check initial subscription status
        print(f"Initial status: {lm.check_subscription(test_username)}")
        
        # Activate subscription
        print(f"Activating subscription...")
        activation_result = lm.activate_subscription(test_username, "TEST_PAYMENT_REF")
        print(f"Activation result: {activation_result}")
        
        # Check status after activation
        print(f"Status after activation: {lm.check_subscription(test_username)}")
        
        # Get subscription info
        info = lm.get_subscription_info(test_username)
        if info:
            print(f"Subscription info: {info}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

if __name__ == "__main__":
    # Run test when file is executed directly
    test_license_manager()