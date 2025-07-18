import sys
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Then modify your ConfigManager class:
class ConfigManager:
    def __init__(self):
        self.app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        os.makedirs(self.app_data_dir, exist_ok=True)
        self.config_file = os.path.join(self.app_data_dir, 'config.json')
        self.key_file = os.path.join(self.app_data_dir, '.key')
        self.settings = QSettings('Fan FindR', 'CreatorTool')
        
        # Handle Firebase key path for portable app
        firebase_key_path = None
        potential_paths = [
            resource_path('firebase-key.json'),  # Bundled with exe
            os.path.join(self.app_data_dir, 'firebase-key.json'),  # User data dir
            'firebase-key.json'  # Current directory
        ]
        
        for path in potential_paths:
            if os.path.exists(path):
                firebase_key_path = path
                break
        
        if firebase_key_path:
            os.environ['FIREBASE_KEY_PATH'] = firebase_key_path
        
        self._init_encryption()


import sys
import os
import subprocess
import json
import threading
import hashlib
import base64
from subscription_ui import SubscriptionDialog
from license_manager import LicenseManager
from datetime import datetime
from cryptography.fernet import Fernet
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QTextEdit, QPushButton, 
                             QLabel, QLineEdit, QSpinBox, QCheckBox, QGroupBox,
                             QProgressBar, QComboBox, QMessageBox, QFileDialog, 
                             QFrame, QTextBrowser, QScrollArea, QListWidget, QDialog)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt, QSettings, QStandardPaths, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QIcon
from subscription_ui import SubscriptionDialog, SubscriptionRenewalDialog
from license_manager import LicenseManager
from dotenv import load_dotenv


load_dotenv()
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Set up Firebase key path
firebase_key_bundled = resource_path('firebase-key.json')
if os.path.exists(firebase_key_bundled):
    os.environ['FIREBASE_KEY_PATH'] = firebase_key_bundled
    print(f"[INFO] Using bundled Firebase key: {firebase_key_bundled}")

def get_script_path(script_name):
    """Get the correct path for script files in both dev and executable"""
    # Try bundled location first (for executable)
    bundled_path = resource_path(script_name)
    if os.path.exists(bundled_path):
        print(f"[INFO] Found script at bundled location: {bundled_path}")
        return bundled_path
    
    # Try current working directory
    cwd_path = os.path.join(os.getcwd(), script_name)
    if os.path.exists(cwd_path):
        print(f"[INFO] Found script in working directory: {cwd_path}")
        return cwd_path
    
    # Try same directory as app.py
    app_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir_path = os.path.join(app_dir, script_name)
    if os.path.exists(app_dir_path):
        print(f"[INFO] Found script in app directory: {app_dir_path}")
        return app_dir_path
    
    # If not found anywhere, return bundled path anyway and let error handling deal with it
    print(f"[WARNING] Script {script_name} not found in any location, using bundled path")
    return bundled_path   
class ConfigManager:
    """Centralized configuration management with encryption"""
    
    def __init__(self):
        self.app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        os.makedirs(self.app_data_dir, exist_ok=True)
        self.config_file = os.path.join(self.app_data_dir, 'config.json')
        self.key_file = os.path.join(self.app_data_dir, '.key')
        self.settings = QSettings('MaloumAutomation', 'Suite')
        self._init_encryption()
        
    def _init_encryption(self):
        """Initialize encryption key"""
        try:
            if os.path.exists(self.key_file):
                with open(self.key_file, 'rb') as f:
                    self.key = f.read()
            else:
                self.key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(self.key)
            self.cipher = Fernet(self.key)
        except Exception as e:
            print("Encryption init error")
            self.cipher = None
    
    def encrypt_password(self, password):
        """Encrypt password for secure storage"""
        if not password or not self.cipher:
            return password
        try:
            return base64.b64encode(self.cipher.encrypt(password.encode())).decode()
        except:
            return password
    
    def decrypt_password(self, encrypted_password):
        """Decrypt password for use"""
        if not encrypted_password or not self.cipher:
            return encrypted_password
        try:
            return self.cipher.decrypt(base64.b64decode(encrypted_password.encode())).decode()
        except:
            return encrypted_password
    
    def save_config(self, config_data):
        """Save configuration with encrypted passwords"""
        encrypted_config = config_data.copy()
        if 'discovery_password' in encrypted_config and self.cipher:
            encrypted_config['discovery_password'] = self.encrypt_password(encrypted_config['discovery_password'])
        if 'keyword_password' in encrypted_config and self.cipher:
            encrypted_config['keyword_password'] = self.encrypt_password(encrypted_config['keyword_password'])
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(encrypted_config, f, indent=2)
            return True
        except Exception as e:
            return False
    
    def load_config(self):
        """Load configuration with decrypted passwords"""
        default_config = {
            'discovery_email': '',
            'discovery_password': '',
            'discovery_hide_browser': True,
            'discovery_target_users': 50,
            'discovery_posts_per_filter': 50,
            'keyword_email': '',
            'keyword_password': '',
            'keyword_hide_browser': True,
            'keyword_target_users': 50,
            'keyword_posts_per_keyword': 50,
            'last_saved': datetime.now().isoformat()
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # Decrypt passwords
                if 'discovery_password' in config and self.cipher:
                    config['discovery_password'] = self.decrypt_password(config['discovery_password'])
                if 'keyword_password' in config and self.cipher:
                    config['keyword_password'] = self.decrypt_password(config['keyword_password'])
                
                # Merge with defaults to ensure all keys exist
                default_config.update(config)
                return default_config
            except Exception as e:
                return default_config
        
        return default_config

class CredentialValidator:
    """Validate and manage credentials securely"""
    
    @staticmethod
    def validate_email(username):
        """Basic username/email validation - accepts any reasonable format"""
        username = username.strip()
        if len(username) < 3:
            return False
        # Allow any format as long as it's reasonable length and has valid characters
        import re
        pattern = r'^[a-zA-Z0-9._%+-@]+$'  # Letters, numbers, and common symbols
        return re.match(pattern, username) is not None
    
    @staticmethod
    def validate_password(password):
        """Basic password validation"""
        return len(password) >= 6
    
    @staticmethod
    def sanitize_input(text):
        """Sanitize user input"""
        if not text:
            return ""
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`']
        for char in dangerous_chars:
            text = text.replace(char, '')
        return text.strip()

class SmartProgressBar(QProgressBar):
    """Enhanced progress bar with smart animation based on actual progress"""
    
    def __init__(self, script_name=""):
        super().__init__()
        self.script_name = script_name
        self.actual_progress = 0
        self.is_setup_mode = False
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_step)
        self.animation_position = 0
        self.beam_width = 20  # Width of scanning beam
        
        # Set base styling
        self.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                font-weight: 500;
                font-size: 10px;
                max-height: 20px;
                background-color: #3c3c3c;
            }}
            QProgressBar::chunk {{
                background-color: #ff6600;
                border-radius: 3px;
            }}
        """)
        
    def start_setup_animation(self):
        """Start scanning animation for setup phase (0% progress)"""
        self.is_setup_mode = True
        self.actual_progress = 0
        self.setValue(0)  # Always keep at 0 for setup
        self.animation_position = -self.beam_width
        self.animation_timer.start(50)  # 50ms for smooth animation
        self.setFormat(f"Setting up {self.script_name}...")
    
    def animate_step(self):
        """Single animation step"""
        if self.is_setup_mode and self.actual_progress == 0:
            # Move the beam position
            self.animation_position += 4  # Faster movement for blur effect
            
            # Reset when beam completely exits right side
            if self.animation_position > 100 + self.beam_width:
                self.animation_position = -self.beam_width
            
            # Calculate beam visibility
            beam_start = self.animation_position
            beam_end = self.animation_position + self.beam_width
            
            # Create the moving beam effect with motion blur
            if beam_end > 0 and beam_start < 100:
                # Beam is at least partially visible
                visible_start = max(0, beam_start)
                visible_end = min(100, beam_end)
                
                # Create smooth gradient with trailing effect (motion blur)
                gradient_stops = []
                
                # Background before beam
                if visible_start > 0:
                    gradient_stops.append(f"stop:0 #3c3c3c")
                    gradient_stops.append(f"stop:{(visible_start-0.5)/100} #3c3c3c")
                
                # Motion blur effect - longer trailing gradient
                beam_center = (visible_start + visible_end) / 2
                trail_start = max(0, visible_start - 8)  # Trailing effect
                
                # Create trailing blur
                if trail_start < visible_start:
                    gradient_stops.append(f"stop:{trail_start/100} rgba(255, 153, 51, 0.1)")  # Very faint trail start
                    gradient_stops.append(f"stop:{(visible_start-2)/100} rgba(255, 153, 51, 0.3)")  # Fade in
                
                # Main beam with soft edges
                gradient_stops.append(f"stop:{visible_start/100} rgba(255, 153, 51, 0.6)")  # Soft start
                gradient_stops.append(f"stop:{(visible_start + 3)/100} rgba(255, 102, 0, 0.9)")  # Build up
                gradient_stops.append(f"stop:{beam_center/100} rgba(255, 102, 0, 1.0)")  # Peak intensity
                gradient_stops.append(f"stop:{(visible_end - 2)/100} rgba(255, 102, 0, 0.8)")  # Fade out
                gradient_stops.append(f"stop:{visible_end/100} rgba(255, 153, 51, 0.4)")  # Soft end
                
                # Trailing blur after main beam
                trail_end = min(100, visible_end + 5)
                if trail_end > visible_end:
                    gradient_stops.append(f"stop:{(visible_end + 1)/100} rgba(255, 153, 51, 0.2)")  # Trail
                    gradient_stops.append(f"stop:{trail_end/100} rgba(255, 153, 51, 0.05)")  # Fade to nothing
                
                # Background after beam
                if visible_end < 100:
                    gradient_stops.append(f"stop:{(visible_end + 6)/100} #3c3c3c")
                    gradient_stops.append(f"stop:1 #3c3c3c")
                
                gradient_str = ", ".join(gradient_stops)
                
                self.setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid #555555;
                        border-radius: 4px;
                        text-align: center;
                        color: #ffffff;
                        font-weight: 500;
                        font-size: 10px;
                        max-height: 20px;
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, {gradient_str});
                    }}
                """)
            else:
                # Beam not visible, show normal background
                self.setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid #555555;
                        border-radius: 4px;
                        text-align: center;
                        color: #ffffff;
                        font-weight: 500;
                        font-size: 10px;
                        max-height: 20px;
                        background-color: #3c3c3c;
                    }}
                """)
        
        elif self.actual_progress > 0:
            # Progress mode - show filled bar with fast-moving wave
            max_pos = self.actual_progress
            
            # Move wave faster within the progress area
            self.animation_position += 3
            if self.animation_position > max_pos + 15:
                self.animation_position = -15
            
            # Calculate wave position with blur effect
            wave_center = max(0, min(max_pos, self.animation_position))
            wave_width = min(10, max_pos / 3)
            
            # Create motion blur effect within progress
            gradient_stops = []
            
            # Base progress color
            gradient_stops.append(f"stop:0 #ff6600")
            
            # Wave with motion blur
            if wave_center >= 0 and wave_center <= max_pos:
                wave_trail_start = max(0, wave_center - wave_width - 5)
                wave_trail_end = min(max_pos, wave_center + wave_width + 3)
                
                # Trail before wave
                if wave_trail_start < wave_center - wave_width:
                    gradient_stops.append(f"stop:{wave_trail_start/100} #ff6600")
                    gradient_stops.append(f"stop:{(wave_center - wave_width)/100} rgba(255, 204, 102, 0.8)")
                
                # Main wave with soft edges
                gradient_stops.append(f"stop:{(wave_center - wave_width/2)/100} rgba(255, 204, 102, 0.9)")
                gradient_stops.append(f"stop:{wave_center/100} rgba(255, 235, 153, 1.0)")  # Bright center
                gradient_stops.append(f"stop:{(wave_center + wave_width/2)/100} rgba(255, 204, 102, 0.9)")
                
                # Trail after wave
                if wave_trail_end > wave_center + wave_width:
                    gradient_stops.append(f"stop:{(wave_center + wave_width)/100} rgba(255, 204, 102, 0.6)")
                    gradient_stops.append(f"stop:{wave_trail_end/100} #ff6600")
            
            # End of progress
            if max_pos < 100:
                gradient_stops.append(f"stop:{max_pos/100} #ff6600")
                gradient_stops.append(f"stop:{(max_pos+0.1)/100} #3c3c3c")
                gradient_stops.append(f"stop:1 #3c3c3c")
            
            gradient_str = ", ".join(gradient_stops)
            
            self.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #555555;
                    border-radius: 4px;
                    text-align: center;
                    color: #ffffff;
                    font-weight: 500;
                    font-size: 10px;
                    max-height: 20px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, {gradient_str});
                }}
            """)
    
    def set_user_progress(self, collected, target, script_name=""):
        """Set progress based on collected users"""
        if target > 0:
            new_progress = min(100, (collected / target) * 100)
            self.actual_progress = new_progress
            self.setValue(int(new_progress))
            
            if new_progress > 0:
                self.is_setup_mode = False
                self.setFormat(f"{collected}/{target} users ({new_progress:.1f}%)")
                
                # Start progress animation if not already running
                if not self.animation_timer.isActive():
                    self.animation_position = 0
                    self.animation_timer.start(50)
            else:
                # Still in setup mode
                self.start_setup_animation()
    
    def stop_animation(self):
        """Stop all animations"""
        self.is_setup_mode = False
        self.animation_timer.stop()
        
        # Reset to normal styling
        self.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                font-weight: 500;
                font-size: 10px;
                max-height: 20px;
                background-color: #3c3c3c;
            }}
            QProgressBar::chunk {{
                background-color: #ff6600;
                border-radius: 3px;
            }}
        """)
        
        if self.actual_progress > 0:
            self.setFormat(f"Completed ({self.actual_progress:.1f}%)")
        else:
            self.setFormat("Ready")

class EnhancedScriptRunner(QThread):
    """Enhanced thread for running automation scripts with settings integration"""
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str, bool)
    error_signal = pyqtSignal(str)
    user_collected_signal = pyqtSignal(str, int, int)  # username, collected_count, target
    setup_status_signal = pyqtSignal(str)  # Setup status messages
    
    def __init__(self, script_path, script_name, ui_settings, config_manager=None):
        super().__init__()
        self.script_path = script_path
        self.script_name = script_name
        self.ui_settings = ui_settings
        self.config_manager = config_manager
        self.process = None
        self.is_cancelled = False
        self.collected_users = set()
        self.target_users = ui_settings.get('target_users', 300)
        self.chrome_processes = set()  # Track Chrome processes for this script only
        self.internal_driver = None 

    def _build_script_arguments(self):
        """Build command line arguments based on UI settings"""
        args = []
        
        # Add email (required for user-specific data)
        email = self.ui_settings.get('email', '').strip()
        if email:
            args.extend(['--email', email])
        
        # Add password (required for login)
        password = self.ui_settings.get('password', '').strip()
        if password:
            args.extend(['--password', password])
        
        # Browser settings
        if self.ui_settings.get('hide_browser', True):
            args.append('--headless')
        
        # Script-specific settings
        if 'discoverySearch.py' in self.script_path:
            target_users = self.ui_settings.get('target_users', 300)
            posts_per_filter = self.ui_settings.get('posts_per_filter', 500)
            args.extend(['--target-users', str(target_users)])
            args.extend(['--posts-per-filter', str(posts_per_filter)])
            
        elif 'keywordSearch.py' in self.script_path:
            target_users = self.ui_settings.get('target_users', 500)
            args.extend(['--target-users', str(target_users)])
        
        # GUI mode flag
        args.append('--gui')
        
        return args
    
    def _monitor_chrome_processes(self):
        """Monitor for new Chrome processes created by this script"""
        try:
            import psutil
            
            # Get current Chrome processes before script starts
            existing_chrome_pids = set()
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                        existing_chrome_pids.add(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Wait a bit for script to start Chrome
            import time
            time.sleep(5)
            
            # Find new Chrome processes that appeared after script started
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if (proc.info['name'] and 'chrome' in proc.info['name'].lower() and
                        proc.info['cmdline']):
                        
                        cmdline = ' '.join(proc.info['cmdline'])
                        
                        # Check for automation flags
                        automation_indicators = [
                            '--test-type',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-dev-shm-usage',
                            '--no-sandbox',
                            '--disable-extensions',
                            '--headless'
                        ]
                        
                        # If it has automation flags and wasn't there before, it's ours
                        if (any(flag in cmdline for flag in automation_indicators) and
                            proc.info['pid'] not in existing_chrome_pids):
                            self.chrome_processes.add(proc.info['pid'])
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except ImportError:
            pass  # Silent fallback if psutil not available
        except Exception:
            pass  # Silent fallback for any other errors
        
    def run(self):
        try:
            # Validate credentials before starting
            email = self.ui_settings.get('email', '').strip()
            password = self.ui_settings.get('password', '').strip()
            
            if not email or not password:
                self.error_signal.emit("Email and password are required")
                self.finished_signal.emit("Missing credentials", False)
                return
                
            if not CredentialValidator.validate_email(email):
                self.error_signal.emit("Invalid email format")
                self.finished_signal.emit("Invalid email", False)
                return
                
            if not CredentialValidator.validate_password(password):
                self.error_signal.emit("Password must be at least 6 characters")
                self.finished_signal.emit("Invalid password", False)
                return
            
            # Build arguments with current UI settings
            script_args = self._build_script_arguments()
            
            mode_text = "headless" if "--headless" in script_args else "normal"
            
            self.output_signal.emit(f"Starting {self.script_name} in {mode_text} mode...\n")
            self.output_signal.emit(f"User: {email}\n")
            self.setup_status_signal.emit("Initializing browser...")
            self.progress_signal.emit(10)
            
            # Check if running as bundled executable
            if getattr(sys, 'frozen', False):
                # Running as bundled executable
                self.output_signal.emit("Running in bundled mode...\n")
                self._run_script_bundled(script_args)
                return
            
            # Running in development mode
            python_exe = sys.executable
            
            # Set environment variables for real-time output
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            env['PYTHONUNBUFFERED'] = '1'  # Force unbuffered output
            
            # Build complete command
            command = [python_exe, self.script_path] + script_args
            
            self.output_signal.emit(f"Command: {' '.join(command[:2])} [script with credentials]\n")
            self.progress_signal.emit(20)
            
            # Run the script with unbuffered output
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env,
                cwd=os.path.dirname(self.script_path) if os.path.dirname(self.script_path) else os.getcwd(),
                bufsize=0,  # Unbuffered
                universal_newlines=True
            )
            
            self.progress_signal.emit(30)
            
            # Start monitoring Chrome processes in a separate thread
            import threading
            monitor_thread = threading.Thread(target=self._monitor_chrome_processes, daemon=True)
            monitor_thread.start()
            
            # Use a separate thread to read output in real-time
            import queue
            
            def read_output():
                """Read output from process in a separate thread"""
                try:
                    while True:
                        line = self.process.stdout.readline()
                        if not line:
                            break
                        if line:
                            output_queue.put(line)
                except:
                    pass
                finally:
                    output_queue.put(None)  # Signal end
            
            output_queue = queue.Queue()
            reader_thread = threading.Thread(target=read_output, daemon=True)
            reader_thread.start()
            
            # Process output line by line
            line_count = 0
            
            while True:
                if self.is_cancelled:
                    self.process.terminate()
                    self.output_signal.emit("Script cancelled by user\n")
                    return
                
                try:
                    # Get line from queue with timeout
                    try:
                        line = output_queue.get(timeout=0.1)
                    except queue.Empty:
                        # Check if process is still running
                        if self.process.poll() is not None:
                            break
                        continue
                    
                    if line is None:  # End signal
                        break
                    
                    clean_line = line.strip()
                    if clean_line:
                        self.output_signal.emit(line)
                        
                        # Parse for user collection
                        if "New user found:" in clean_line or "Collected user:" in clean_line:
                            try:
                                # Extract username from log
                                username_start = clean_line.find(": ") + 2
                                username_end = clean_line.find(" (", username_start)
                                if username_end == -1:
                                    username_end = len(clean_line)
                                username = clean_line[username_start:username_end].strip()
                                
                                if username and username not in self.collected_users:
                                    self.collected_users.add(username)
                                    self.user_collected_signal.emit(username, len(self.collected_users), self.target_users)
                            except:
                                pass
                        
                        # Parse for setup status
                        if "[INFO]" in clean_line:
                            if "Navigating to" in clean_line or "Login" in clean_line or "Starting" in clean_line:
                                status = clean_line.split("[INFO]", 1)[1].strip()
                                self.setup_status_signal.emit(status)
                        
                        # Update progress based on output content
                        line_count += 1
                        if line_count % 5 == 0:
                            current_progress = min(90, 30 + (line_count // 5) * 1)
                            self.progress_signal.emit(current_progress)
                        
                except Exception as e:
                    continue
            
            # Check return code
            return_code = self.process.poll()
            success = return_code == 0
            
            self.progress_signal.emit(100)
            
            if success:
                self.finished_signal.emit(f"{self.script_name} completed successfully!", True)
            else:
                self.finished_signal.emit(f"{self.script_name} failed with code {return_code}", False)
                
        except Exception as e:
            self.error_signal.emit(f"Error running {self.script_name}: {str(e)}")
            self.finished_signal.emit(f"Error running {self.script_name}: {str(e)}", False)
            
    def _run_script_bundled(self, script_args):
        """Run script internally in bundled mode - NO external process, NO console"""
        try:
            self.output_signal.emit("Running script internally (no console)...\n")
            
            # Parse the script arguments into a config-like object
            config = self._parse_script_args(script_args)
            
            # Run the appropriate script directly as a function
            if "discoverySearch.py" in self.script_path:
                self._run_discovery_internal(config)
            elif "keywordSearch.py" in self.script_path:
                self._run_keyword_internal(config)
            else:
                self.error_signal.emit(f"Unknown script: {self.script_path}")
                
        except Exception as e:
            self.error_signal.emit(f"Error in internal execution: {str(e)}")
            self.finished_signal.emit(f"Error running {self.script_name}: {str(e)}", False)

    def _parse_script_args(self, script_args):
        """Convert script arguments back to config object"""
        config = {
            'email': '',
            'password': '',
            'headless': False,
            'target_users': 300,
            'posts_per_filter': 500,
            'posts_per_keyword': 50,
            'rate_delay': 2,
            'max_retries': 3,
            'timeout': 30,
            'gui_mode': True
        }
        
        # Parse arguments
        i = 0
        while i < len(script_args):
            arg = script_args[i]
            if arg == '--email' and i + 1 < len(script_args):
                config['email'] = script_args[i + 1]
                i += 2
            elif arg == '--password' and i + 1 < len(script_args):
                config['password'] = script_args[i + 1]
                i += 2
            elif arg == '--target-users' and i + 1 < len(script_args):
                config['target_users'] = int(script_args[i + 1])
                i += 2
            elif arg == '--posts-per-filter' and i + 1 < len(script_args):
                config['posts_per_filter'] = int(script_args[i + 1])
                i += 2
            elif arg == '--headless':
                config['headless'] = True
                i += 1
            elif arg == '--gui':
                config['gui_mode'] = True
                i += 1
            else:
                i += 1
        
        return config

    def _run_discovery_internal(self, config):
        """Run discovery search internally without subprocess"""
        try:
            self.output_signal.emit(f"Starting Discovery Search internally...\n")
            self.output_signal.emit(f"User: {config['email']}\n")
            self.output_signal.emit(f"Target Users: {config['target_users']}\n")
            
            # Import the discovery script functions
            import discoverySearch
            
            # Create a mock config object that the script expects
            class MockArgs:
                def __init__(self, config_dict):
                    for key, value in config_dict.items():
                        setattr(self, key, value)
            
            mock_args = MockArgs(config)
            
            # Override the script's output functions to send to our GUI
            original_print = print
            def gui_print(*args, **kwargs):
                message = ' '.join(str(arg) for arg in args) + '\n'
                self.output_signal.emit(message)
                # Also parse for user collection
                if "New user found:" in message or "Collected user:" in message:
                    try:
                        username_start = message.find(": ") + 2
                        username_end = message.find(" (", username_start)
                        if username_end == -1:
                            username_end = len(message)
                        username = message[username_start:username_end].strip()
                        
                        if username and username not in self.collected_users:
                            self.collected_users.add(username)
                            self.user_collected_signal.emit(username, len(self.collected_users), self.target_users)
                    except:
                        pass
            
            # Temporarily replace print
            import builtins
            builtins.print = gui_print
            
            try:
                # Run the discovery script's main logic
                script_config = discoverySearch.ScriptConfig(mock_args)
                
                # Load existing users
                existing_users = discoverySearch.load_existing_users(config['email'])
                collected_users = set()
                
                # Setup browser and TRACK IT
                self.internal_driver = discoverySearch.setup_chrome_driver(script_config)
                
                # Monitor for cancellation in a separate thread
                import threading
                def check_cancellation():
                    while not self.is_cancelled and self.internal_driver:
                        import time
                        time.sleep(0.5)
                    if self.is_cancelled and self.internal_driver:
                        try:
                            self.output_signal.emit("🛑 Stopping script and closing browser...\n")
                            self.internal_driver.quit()
                            self.internal_driver = None
                            self.output_signal.emit("✅ Browser closed successfully\n")
                        except:
                            pass
                
                cancel_thread = threading.Thread(target=check_cancellation, daemon=True)
                cancel_thread.start()
                
                try:
                    # Check for cancellation before each major step
                    if self.is_cancelled:
                        return
                        
                    # Login
                    if discoverySearch.login_to_maloum(self.internal_driver, script_config):
                        self.output_signal.emit("Login successful\n")
                        
                        if self.is_cancelled:
                            return
                        
                        # Sync users list
                        discoverySearch.sync_all_users_list(self.internal_driver, script_config, existing_users)
                        
                        if self.is_cancelled:
                            return
                        
                        # Run main discovery loop with cancellation checks
                        self._run_discovery_loop_with_cancellation(self.internal_driver, script_config, existing_users, collected_users)
                        
                        if not self.is_cancelled:
                            self.finished_signal.emit(f"Discovery Search completed successfully!", True)
                    else:
                        self.error_signal.emit("Login failed")
                        
                finally:
                    # Always close the browser
                    if self.internal_driver:
                        try:
                            self.internal_driver.quit()
                            self.output_signal.emit("✅ Browser closed\n")
                        except:
                            pass
                        self.internal_driver = None
                    
            finally:
                # Restore original print
                builtins.print = original_print
                
        except Exception as e:
            # Close browser on error too
            if self.internal_driver:
                try:
                    self.internal_driver.quit()
                    self.output_signal.emit("✅ Browser closed (after error)\n")
                except:
                    pass
                self.internal_driver = None
                
            import traceback
            self.error_signal.emit(f"Discovery script error: {str(e)}")
            self.output_signal.emit(f"Error details: {traceback.format_exc()}\n")
            self.finished_signal.emit(f"Discovery Search failed: {str(e)}", False)

    def _run_discovery_loop_with_cancellation(self, driver, script_config, existing_users, collected_users):
        """Discovery loop that checks for cancellation"""
        import discoverySearch
        
        filter_cycle = 0
        while len(collected_users) < script_config.target_users and not self.is_cancelled:
            filter_cycle += 1
            
            if self.is_cancelled:
                break
                
            # Go to Discovery page
            if not discoverySearch.go_to_discovery_page(driver, script_config):
                if self.is_cancelled:
                    break
                continue
            
            if self.is_cancelled:
                break
                
            # Apply random filter
            discoverySearch.apply_random_filter(driver, script_config)
            
            if self.is_cancelled:
                break
                
            # Wait for first post
            if not discoverySearch.wait_for_first_post(driver, script_config):
                continue
            
            # Process posts with cancellation checks
            post_index = 0
            posts_processed = 0
            max_posts = script_config.posts_per_filter
            
            while (len(collected_users) < script_config.target_users and 
                posts_processed < max_posts and not self.is_cancelled):
                
                if discoverySearch.process_single_post(driver, post_index, script_config, existing_users, collected_users):
                    post_index += 1
                    posts_processed += 1
                else:
                    break

    def _run_keyword_internal(self, config):
        """Run keyword search internally without subprocess"""
        try:
            self.output_signal.emit(f"Starting Keyword Search internally...\n")
            self.output_signal.emit(f"User: {config['email']}\n")
            self.output_signal.emit(f"Target Users: {config['target_users']}\n")
            
            # Import the keyword script functions
            import keywordSearch
            
            # Create a mock config object that the script expects
            class MockArgs:
                def __init__(self, config_dict):
                    for key, value in config_dict.items():
                        setattr(self, key, value)
            
            mock_args = MockArgs(config)
            
            # Override print for GUI output
            original_print = print
            def gui_print(*args, **kwargs):
                message = ' '.join(str(arg) for arg in args) + '\n'
                self.output_signal.emit(message)
                if "New user found:" in message or "Collected user:" in message:
                    try:
                        username_start = message.find(": ") + 2
                        username_end = message.find(" (", username_start)
                        if username_end == -1:
                            username_end = len(message)
                        username = message[username_start:username_end].strip()
                        
                        if username and username not in self.collected_users:
                            self.collected_users.add(username)
                            self.user_collected_signal.emit(username, len(self.collected_users), self.target_users)
                    except:
                        pass
            
            import builtins
            builtins.print = gui_print
            
            try:
                script_config = keywordSearch.ScriptConfig(mock_args)
                existing_users = keywordSearch.load_existing_users(config['email'])
                
                # Setup browser and TRACK IT
                self.internal_driver = keywordSearch.setup_chrome_driver(script_config)
                
                # Monitor for cancellation
                import threading
                def check_cancellation():
                    while not self.is_cancelled and self.internal_driver:
                        import time
                        time.sleep(0.5)
                    if self.is_cancelled and self.internal_driver:
                        try:
                            self.output_signal.emit("🛑 Stopping script and closing browser...\n")
                            self.internal_driver.quit()
                            self.internal_driver = None
                            self.output_signal.emit("✅ Browser closed successfully\n")
                        except:
                            pass
                
                cancel_thread = threading.Thread(target=check_cancellation, daemon=True)
                cancel_thread.start()
                
                try:
                    if self.is_cancelled:
                        return
                        
                    # Login
                    if keywordSearch.login_to_maloum(self.internal_driver, script_config):
                        self.output_signal.emit("Login successful\n")
                        
                        if self.is_cancelled:
                            return
                        
                        # Sync users list
                        keywordSearch.sync_all_users_list(self.internal_driver, script_config, existing_users)
                        
                        if self.is_cancelled:
                            return
                        
                        # Process keywords with cancellation checks
                        collected_users = set()
                        for keyword in script_config.keywords:
                            if len(collected_users) >= config['target_users'] or self.is_cancelled:
                                break
                            self.output_signal.emit(f"Processing keyword: {keyword}\n")
                            
                            if keywordSearch.go_to_discovery_and_search(self.internal_driver, keyword, script_config):
                                keywordSearch.process_keyword_posts(self.internal_driver, keyword, script_config, existing_users, collected_users)
                        
                        if not self.is_cancelled:
                            self.finished_signal.emit(f"Keyword Search completed successfully!", True)
                    else:
                        self.error_signal.emit("Login failed")
                        
                finally:
                    # Always close browser
                    if self.internal_driver:
                        try:
                            self.internal_driver.quit()
                            self.output_signal.emit("✅ Browser closed\n")
                        except:
                            pass
                        self.internal_driver = None
                    
            finally:
                builtins.print = original_print
                
        except Exception as e:
            # Close browser on error
            if self.internal_driver:
                try:
                    self.internal_driver.quit()
                    self.output_signal.emit("✅ Browser closed (after error)\n")
                except:
                    pass
                self.internal_driver = None
                
            import traceback
            self.error_signal.emit(f"Keyword script error: {str(e)}")
            self.finished_signal.emit(f"Keyword Search failed: {str(e)}", False)
    def stop(self):
        """Stop the running script forcefully with proper browser cleanup"""
        self.is_cancelled = True
        
        # Close internal driver if running
        if self.internal_driver:
            try:
                self.output_signal.emit(f"\n🛑 Stopping {self.script_name} and closing browser...\n")
                self.internal_driver.quit()
                self.internal_driver = None
                self.output_signal.emit(f"✅ Browser closed for {self.script_name}\n")
            except Exception as e:
                self.output_signal.emit(f"Error closing browser: {str(e)}\n")
        
        # Handle external process if exists
        if self.process:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            except Exception as e:
                self.output_signal.emit(f"Error stopping process: {str(e)}\n")
        
        # Cleanup any remaining automation Chrome processes
        self._kill_script_chrome_processes()
        
        self.finished_signal.emit(f"{self.script_name} stopped by user", True)
    
    def _kill_script_chrome_processes(self):
        """Kill Chrome processes that belong to THIS specific script"""
        try:
            import psutil
            import time
            
            killed_count = 0
            
            # Method 1: Kill tracked Chrome processes
            for pid in self.chrome_processes.copy():
                try:
                    proc = psutil.Process(pid)
                    if proc.is_running():
                        proc.kill()
                        killed_count += 1
                        self.chrome_processes.remove(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    self.chrome_processes.discard(pid)
                    continue
            
            # Method 2: For bundled mode - kill Chrome processes with automation flags
            if getattr(sys, 'frozen', False):
                # Running as executable - be more aggressive about Chrome cleanup
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if (proc.info['name'] and 'chrome' in proc.info['name'].lower() and
                            proc.info['cmdline']):
                            
                            cmdline = ' '.join(proc.info['cmdline'])
                            
                            # Check for automation flags that indicate our script's Chrome
                            automation_indicators = [
                                '--test-type',
                                '--disable-blink-features=AutomationControlled',
                                '--disable-dev-shm-usage',
                                '--no-sandbox',
                                '--disable-extensions',
                                '--headless',
                                '--user-data-dir',  # Selenium typically uses custom user data dirs
                                '--remote-debugging-port'
                            ]
                            
                            # If it has automation flags, it's likely from our script
                            if any(flag in cmdline for flag in automation_indicators):
                                try:
                                    proc.kill()
                                    killed_count += 1
                                    self.output_signal.emit(f"Killed automation Chrome process (PID: {proc.info['pid']})\n")
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    continue
                                    
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                    except Exception:
                        continue
            
            if killed_count > 0:
                self.output_signal.emit(f"Closed {killed_count} browser windows for {self.script_name}\n")
            else:
                self.output_signal.emit(f"No automation browsers found to close for {self.script_name}\n")
                        
        except ImportError:
            # Fallback if psutil not available - try basic process killing
            try:
                import os
                if sys.platform == "win32":
                    # On Windows, kill Chrome processes with automation characteristics
                    os.system('taskkill /f /im chrome.exe /fi "WINDOWTITLE eq Chrome*automation*" >nul 2>&1')
                    self.output_signal.emit(f"Attempted to close automation browsers using taskkill\n")
            except:
                pass
        except Exception as e:
            self.output_signal.emit(f"Error during browser cleanup: {str(e)}\n")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.script_threads = {}
        self.current_settings = {}
        self.collected_usernames = []
        self.init_ui()
        self.load_user_data()
        self.discovery_email_input.textChanged.connect(self.update_subscription_status)
        self.keyword_email_input.textChanged.connect(self.update_subscription_status)
    def init_ui(self):
        self.setWindowTitle("Fan FindR - Maloum Creator Outreach Tool")

        self.set_dark_title_bar()

        # Window sizing with better minimum sizes and centering
        self.default_width = 1000
        self.default_height = 650
        
        # Center the window on screen
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.default_width) // 2
        y = (screen.height() - self.default_height) // 2
        
        self.setGeometry(x, y, self.default_width, self.default_height)
        self.setMinimumSize(900, 600)
        
        # Professional dark theme with ORANGE accent color
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
                border-radius: 4px;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: 500;
                font-size: 11px;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background-color: #ff6600;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
            QPushButton {
                background-color: #ff6600;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 11px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #e55a00;
            }
            QPushButton:pressed {
                background-color: #cc4f00;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #888888;
            }
            QPushButton.stop-button {
                background-color: #d13438;
            }
            QPushButton.stop-button:hover {
                background-color: #e74c3c;
            }
            QPushButton.success {
                background-color: #28a745;
            }
            QPushButton.warning {
                background-color: #ffc107;
                color: #000000;
            }
            QTextEdit, QTextBrowser {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 10px;
                padding: 8px;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                padding: 6px;
                border-radius: 4px;
                font-size: 11px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #ff6600;
                background-color: #ffffff;
            }
            QLineEdit.error {
                border-color: #dc3545;
                background-color: #fff5f5;
            }
            QLineEdit.success {
                border-color: #28a745;
                background-color: #f5fff5;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #e0e0e0;
            }
            QGroupBox {
                font-weight: 500;
                border: 1px solid #555555;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
                font-size: 12px;
                color: #ffffff;
                background-color: transparent;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #ff6600;
                font-weight: 600;
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-size: 11px;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #ff6600;
                border: 1px solid #ff6600;
                border-radius: 3px;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                font-weight: 500;
                font-size: 10px;
                max-height: 20px;
                background-color: #3c3c3c;
            }
            QProgressBar::chunk {
                background-color: #ff6600;
                border-radius: 3px;
            }
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                font-size: 10px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 2px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:selected {
                background-color: #ff6600;
                color: #ffffff;
            }
            QScrollArea {
                background-color: #2b2b2b;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #2b2b2b;
            }
            QFrame {
                background-color: #2b2b2b;
            }
            QTabWidget > QWidget {
                background-color: #2b2b2b;
            }
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create title
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)
        
        title_label = QLabel("Fan FindR")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #ff6600; font-size: 25px; font-family: Times New Roman; margin-top: 5px;font-weight: 700;")

        
        # version_label = QLabel("Creator Outreach Tool")
        # version_label.setAlignment(Qt.AlignCenter)
        # version_label.setStyleSheet("color: #ffffff; font-size: 9px; font-style: italic; letter-spacing: 2px; font-weight: 700;")
        
        title_layout.addWidget(title_label)
        # title_layout.addWidget(version_label)
        
        main_layout.addLayout(title_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_automation_tab()
        self.create_ds_log_tab()
        self.create_ks_log_tab()
        
        # Status bar
        self.statusBar().showMessage("Ready - System operational")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #3c3c3c; 
                color: #ffffff; 
                padding: 5px; 
                font-size: 10px;
                border-top: 1px solid #555555;
            }
        """)

    def set_dark_title_bar(self):
        """Set dark title bar - cross-platform safe"""
        try:
            import platform
            system = platform.system()
            
            if system == "Windows":
                import ctypes
                from ctypes import wintypes
                
                # Get window handle
                hwnd = int(self.winId())
                
                # Set dark title bar (Windows 10 version 1903+)
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                value = ctypes.c_int(1)  # 1 for dark, 0 for light
                
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(value),
                    ctypes.sizeof(value)
                )
                print("[INFO] Dark title bar enabled on Windows")
                
            elif system == "Darwin":  # macOS
                # macOS automatically uses dark title bar if the app theme is dark
                print("[INFO] macOS - using system theme for title bar")
                
            elif system == "Linux":
                # Linux window managers handle this differently
                print("[INFO] Linux - title bar controlled by window manager")
                
        except Exception as e:
            print(f"[INFO] Could not set dark title bar: {e}")
            # Silently continue - not critical for app functionality

    def check_subscription(self, username=None):
        """Check if current username has active subscription"""
        try:
            # Use provided username or get from appropriate input field
            if not username:
                # This fallback should rarely be used now
                username = self.discovery_email_input.text().strip()
                if not username:
                    username = self.keyword_email_input.text().strip()
            
            if not username:
                QMessageBox.warning(self, "No Username", "Please enter a username first.")
                return False
            
            # Check subscription status
            license_manager = LicenseManager()
            is_active = license_manager.check_subscription(username)
            
            if not is_active:
                # Show subscription dialog
                dialog = SubscriptionDialog(username, self)
                result = dialog.exec_()
                return result == QMessageBox.Accepted
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Subscription Check Error", f"Could not verify subscription: {e}")
            return False
        
    def create_automation_tab(self):
        """Create the main automation control tab with new layout"""
        automation_widget = QWidget()
        layout = QVBoxLayout(automation_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # System Status Section (full width at top)
        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout(status_group)
        status_layout.setSpacing(10)
        status_layout.setContentsMargins(15, 20, 15, 15)
        
        # Status line
        status_line_layout = QHBoxLayout()
        status_line_layout.addWidget(QLabel("Status:"))
        self.system_status_label = QLabel("Ready - No scripts running")
        self.system_status_label.setStyleSheet("color: #28a745; font-weight: 500;")
        status_line_layout.addWidget(self.system_status_label)
        status_line_layout.addStretch()
        status_layout.addLayout(status_line_layout)
        
        # System Status Section (full width at top)
        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout(status_group)
        status_layout.setSpacing(8)
        status_layout.setContentsMargins(15, 15, 15, 10)
        
        # Status line
        status_line_layout = QHBoxLayout()
        status_line_layout.addWidget(QLabel("Status:"))
        self.system_status_label = QLabel("Ready - No scripts running")
        self.system_status_label.setStyleSheet("color: #28a745; font-weight: 500;")
        status_line_layout.addWidget(self.system_status_label)
        status_line_layout.addStretch()
        status_layout.addLayout(status_line_layout)
        
        # Progress bars in a horizontal layout for better space usage
        progress_container = QHBoxLayout()
        progress_container.setSpacing(15)
        
        # Discovery Progress
        discovery_progress_section = QVBoxLayout()
        discovery_progress_section.setSpacing(3)
        
        discovery_label_layout = QHBoxLayout()
        discovery_label_layout.addWidget(QLabel("Discovery Progress:"))
        self.discovery_progress_info_label = QLabel("0/0 users (0%)")
        self.discovery_progress_info_label.setStyleSheet("color: #ff6600; font-weight: 500; font-size: 10px;")
        discovery_label_layout.addWidget(self.discovery_progress_info_label)
        discovery_label_layout.addStretch()
        discovery_progress_section.addLayout(discovery_label_layout)
        
        # Discovery activity status
        self.discovery_activity_label = QLabel("Ready")
        self.discovery_activity_label.setStyleSheet("color: #cccccc; font-style: italic; font-size: 9px;")
        self.discovery_activity_label.setWordWrap(True)
        discovery_progress_section.addWidget(self.discovery_activity_label)
        
        self.discovery_progress_bar = SmartProgressBar("Discovery")
        self.discovery_progress_bar.setFixedHeight(20)
        discovery_progress_section.addWidget(self.discovery_progress_bar)
        
        progress_container.addLayout(discovery_progress_section)
        
        # Keyword Progress
        keyword_progress_section = QVBoxLayout()
        keyword_progress_section.setSpacing(3)
        
        keyword_label_layout = QHBoxLayout()
        keyword_label_layout.addWidget(QLabel("Keyword Progress:"))
        self.keyword_progress_info_label = QLabel("0/0 users (0%)")
        self.keyword_progress_info_label.setStyleSheet("color: #ff6600; font-weight: 500; font-size: 10px;")
        keyword_label_layout.addWidget(self.keyword_progress_info_label)
        keyword_label_layout.addStretch()
        keyword_progress_section.addLayout(keyword_label_layout)
        
        # Keyword activity status
        self.keyword_activity_label = QLabel("Ready")
        self.keyword_activity_label.setStyleSheet("color: #cccccc; font-style: italic; font-size: 9px;")
        self.keyword_activity_label.setWordWrap(True)
        keyword_progress_section.addWidget(self.keyword_activity_label)
        
        self.keyword_progress_bar = SmartProgressBar("Keyword")
        self.keyword_progress_bar.setFixedHeight(20)
        keyword_progress_section.addWidget(self.keyword_progress_bar)
        
        progress_container.addLayout(keyword_progress_section)
        
        status_layout.addLayout(progress_container)
        
        # Recently Collected Users with column layout
        users_section = QVBoxLayout()
        users_section.setSpacing(5)
        users_section.addWidget(QLabel("Recently Collected Users:"))
        
        # Create a custom widget for multi-column user display
        self.users_display_widget = QWidget()
        self.users_display_layout = QVBoxLayout(self.users_display_widget)
        self.users_display_layout.setContentsMargins(5, 5, 5, 5)
        self.users_display_layout.setSpacing(2)
        
        # Container for user columns
        self.users_container = QWidget()
        self.users_container_layout = QVBoxLayout(self.users_container)
        self.users_container_layout.setContentsMargins(0, 0, 0, 0)
        self.users_container_layout.setSpacing(1)
        
        self.users_display_layout.addWidget(self.users_container)
        self.users_display_layout.addStretch()
        
        # Set styling for users display
        self.users_display_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QLabel {
                color: #ffffff;
                font-size: 9px;
                padding: 1px 3px;
            }
        """)
        self.users_display_widget.setFixedHeight(80)
        
        users_section.addWidget(self.users_display_widget)
        status_layout.addLayout(users_section)
        
        # Initialize user tracking
        self.collected_usernames = []
        
        layout.addWidget(status_group)
        
        # Two Column Layout for Discovery and Keyword Search
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        
        # Discovery Search Column
        discovery_group = QGroupBox("Discovery Search")
        discovery_layout = QVBoxLayout(discovery_group)
        discovery_layout.setSpacing(8)
        discovery_layout.setContentsMargins(12, 15, 12, 12)
        
        # Discovery credentials in grid layout for better space usage
        creds_grid = QVBoxLayout()
        creds_grid.setSpacing(6)
        
        # Username
        email_layout = QHBoxLayout()
        email_label = QLabel("Username:")
        email_label.setMinimumWidth(70)
        email_layout.addWidget(email_label)
        self.discovery_email_input = QLineEdit()
        self.discovery_email_input.setPlaceholderText("Maloum username")
        email_layout.addWidget(self.discovery_email_input)
        creds_grid.addLayout(email_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        password_label.setMinimumWidth(70)
        password_layout.addWidget(password_label)
        self.discovery_password_input = QLineEdit()
        self.discovery_password_input.setEchoMode(QLineEdit.Password)
        self.discovery_password_input.setPlaceholderText("Maloum password")
        password_layout.addWidget(self.discovery_password_input)
        creds_grid.addLayout(password_layout)
        
        discovery_layout.addLayout(creds_grid)
        
        # Discovery settings in compact layout
        settings_grid = QVBoxLayout()
        settings_grid.setSpacing(6)
        
        # Hide browser checkbox
        self.discovery_hide_browser_check = QCheckBox("Hide Browser")
        self.discovery_hide_browser_check.setChecked(True)
        settings_grid.addWidget(self.discovery_hide_browser_check)
        
        # Target users and posts in horizontal layout
        numbers_layout = QHBoxLayout()
        numbers_layout.setSpacing(10)
        
        # Target users
        target_layout = QVBoxLayout()
        target_layout.setSpacing(2)
        target_layout.addWidget(QLabel("Target Users:"))
        self.discovery_target_users_spin = QSpinBox()
        self.discovery_target_users_spin.setRange(1, 10000)
        self.discovery_target_users_spin.setValue(300)
        self.discovery_target_users_spin.setSuffix(" users")
        target_layout.addWidget(self.discovery_target_users_spin)
        numbers_layout.addLayout(target_layout)
        
        # Posts per filter
        posts_layout = QVBoxLayout()
        posts_layout.setSpacing(2)
        posts_layout.addWidget(QLabel("Posts per Filter:"))
        self.discovery_posts_per_filter_spin = QSpinBox()
        self.discovery_posts_per_filter_spin.setRange(1, 1000)
        self.discovery_posts_per_filter_spin.setValue(500)
        self.discovery_posts_per_filter_spin.setSuffix(" posts")
        posts_layout.addWidget(self.discovery_posts_per_filter_spin)
        numbers_layout.addLayout(posts_layout)
        
        settings_grid.addLayout(numbers_layout)
        discovery_layout.addLayout(settings_grid)
        
        # Discovery run button
        self.discovery_run_btn = QPushButton("Run Discovery Search")
        self.discovery_run_btn.setMinimumHeight(35)
        self.discovery_run_btn.clicked.connect(lambda: self.toggle_discovery_script())
        discovery_layout.addWidget(self.discovery_run_btn)
        
        # Add stretch to push everything to top
        discovery_layout.addStretch()
        
        columns_layout.addWidget(discovery_group)
        
        # Keyword Search Column (similar compact layout)
        keyword_group = QGroupBox("Keyword Search")
        keyword_layout = QVBoxLayout(keyword_group)
        keyword_layout.setSpacing(8)
        keyword_layout.setContentsMargins(12, 15, 12, 12)
        
        # Keyword credentials in grid layout
        keyword_creds_grid = QVBoxLayout()
        keyword_creds_grid.setSpacing(6)
        
        # Username
        keyword_email_layout = QHBoxLayout()
        keyword_email_label = QLabel("Username:")
        keyword_email_label.setMinimumWidth(70)
        keyword_email_layout.addWidget(keyword_email_label)
        self.keyword_email_input = QLineEdit()
        self.keyword_email_input.setPlaceholderText("Maloum username")
        keyword_email_layout.addWidget(self.keyword_email_input)
        keyword_creds_grid.addLayout(keyword_email_layout)
        
        # Password
        keyword_password_layout = QHBoxLayout()
        keyword_password_label = QLabel("Password:")
        keyword_password_label.setMinimumWidth(70)
        keyword_password_layout.addWidget(keyword_password_label)
        self.keyword_password_input = QLineEdit()
        self.keyword_password_input.setEchoMode(QLineEdit.Password)
        self.keyword_password_input.setPlaceholderText("Maloum password")
        keyword_password_layout.addWidget(self.keyword_password_input)
        keyword_creds_grid.addLayout(keyword_password_layout)
        
        keyword_layout.addLayout(keyword_creds_grid)
        
        # Keyword settings in compact layout
        keyword_settings_grid = QVBoxLayout()
        keyword_settings_grid.setSpacing(6)
        
        # Hide browser checkbox
        self.keyword_hide_browser_check = QCheckBox("Hide Browser")
        self.keyword_hide_browser_check.setChecked(True)
        keyword_settings_grid.addWidget(self.keyword_hide_browser_check)
        
        # Target users and posts in horizontal layout
        keyword_numbers_layout = QHBoxLayout()
        keyword_numbers_layout.setSpacing(10)
        
        # Target users
        keyword_target_layout = QVBoxLayout()
        keyword_target_layout.setSpacing(2)
        keyword_target_layout.addWidget(QLabel("Target Users:"))
        self.keyword_target_users_spin = QSpinBox()
        self.keyword_target_users_spin.setRange(1, 10000)
        self.keyword_target_users_spin.setValue(500)
        self.keyword_target_users_spin.setSuffix(" users")
        keyword_target_layout.addWidget(self.keyword_target_users_spin)
        keyword_numbers_layout.addLayout(keyword_target_layout)
        
        # Posts per keyword
        keyword_posts_layout = QVBoxLayout()
        keyword_posts_layout.setSpacing(2)
        keyword_posts_layout.addWidget(QLabel("Posts per Keyword:"))
        self.keyword_posts_per_keyword_spin = QSpinBox()
        self.keyword_posts_per_keyword_spin.setRange(1, 1000)
        self.keyword_posts_per_keyword_spin.setValue(50)
        self.keyword_posts_per_keyword_spin.setSuffix(" posts")
        keyword_posts_layout.addWidget(self.keyword_posts_per_keyword_spin)
        keyword_numbers_layout.addLayout(keyword_posts_layout)
        
        keyword_settings_grid.addLayout(keyword_numbers_layout)
        keyword_layout.addLayout(keyword_settings_grid)
        
        # Keyword run button
        self.keyword_run_btn = QPushButton("Run Keyword Search")
        self.keyword_run_btn.setMinimumHeight(35)
        self.keyword_run_btn.clicked.connect(lambda: self.toggle_keyword_script())
        keyword_layout.addWidget(self.keyword_run_btn)
        
        # Add stretch to push everything to top
        keyword_layout.addStretch()
        
        columns_layout.addWidget(keyword_group)
        
        layout.addLayout(columns_layout)
        
        self.tab_widget.addTab(automation_widget, "Automation")
        
        # Setup status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_system_status)
        self.status_timer.start(2000)
    
    def create_ds_log_tab(self):
        """Create Discovery Search log tab"""
        ds_log_widget = QWidget()
        layout = QVBoxLayout(ds_log_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Discovery Search Log")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #ff6600;")  # Reduced from 14px to 12px
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Auto-scroll toggle
        self.ds_auto_scroll_check = QCheckBox("Auto Scroll")
        self.ds_auto_scroll_check.setChecked(True)
        self.ds_auto_scroll_check.setStyleSheet("font-size: 10px;")
        header_layout.addWidget(self.ds_auto_scroll_check)
        
        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.setMaximumWidth(80)  # Reduced from 100 to 80
        clear_btn.setMaximumHeight(25)  # Added height limit
        clear_btn.setStyleSheet("font-size: 10px; padding: 4px 8px;")  # Smaller font and padding
        clear_btn.clicked.connect(lambda: self.ds_log_output.clear())
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # Log output area
        self.ds_log_output = QTextEdit()
        self.ds_log_output.setReadOnly(True)
        self.ds_log_output.setPlaceholderText("Discovery Search output will appear here...")
        layout.addWidget(self.ds_log_output)
        
        self.tab_widget.addTab(ds_log_widget, "DS Log")
    
    def create_ks_log_tab(self):
        """Create Keyword Search log tab"""
        ks_log_widget = QWidget()
        layout = QVBoxLayout(ks_log_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Keyword Search Log")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #ff6600;")  # Reduced from 14px to 12px
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Auto-scroll toggle
        self.ks_auto_scroll_check = QCheckBox("Auto Scroll")
        self.ks_auto_scroll_check.setChecked(True)
        self.ks_auto_scroll_check.setStyleSheet("font-size: 10px;")
        header_layout.addWidget(self.ks_auto_scroll_check)
        
        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.setMaximumWidth(80)  # Reduced from 100 to 80
        clear_btn.setMaximumHeight(25)  # Added height limit
        clear_btn.setStyleSheet("font-size: 10px; padding: 4px 8px;")  # Smaller font and padding
        clear_btn.clicked.connect(lambda: self.ks_log_output.clear())
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # Log output area
        self.ks_log_output = QTextEdit()
        self.ks_log_output.setReadOnly(True)
        self.ks_log_output.setPlaceholderText("Keyword Search output will appear here...")
        layout.addWidget(self.ks_log_output)
        
        self.tab_widget.addTab(ks_log_widget, "KS Log")
    
    def get_discovery_settings(self):
        """Get discovery script settings"""
        return {
            'email': CredentialValidator.sanitize_input(self.discovery_email_input.text()),
            'password': self.discovery_password_input.text(),
            'hide_browser': self.discovery_hide_browser_check.isChecked(),
            'target_users': self.discovery_target_users_spin.value(),
            'posts_per_filter': self.discovery_posts_per_filter_spin.value(),
        }
    
    def get_keyword_settings(self):
        """Get keyword script settings"""
        return {
            'email': CredentialValidator.sanitize_input(self.keyword_email_input.text()),
            'password': self.keyword_password_input.text(),
            'hide_browser': self.keyword_hide_browser_check.isChecked(),
            'target_users': self.keyword_target_users_spin.value(),
            'posts_per_keyword': self.keyword_posts_per_keyword_spin.value(),
        }
    
    def toggle_discovery_script(self):
        """Toggle discovery script between run and stop states"""
        script_name = "discoverySearch.py"
        if script_name in self.script_threads and self.script_threads[script_name].isRunning():
            self.stop_script(script_name, self.discovery_run_btn)
        else:
            self.run_discovery_script()
    
    def toggle_keyword_script(self):
        """Toggle keyword script between run and stop states"""
        script_name = "keywordSearch.py"
        if script_name in self.script_threads and self.script_threads[script_name].isRunning():
            self.stop_script(script_name, self.keyword_run_btn)
        else:
            self.run_keyword_script()



    def run_discovery_script(self):
        """Run discovery search script"""
        settings = self.get_discovery_settings()
        
        # Check subscription with discovery username specifically
        if not self.check_subscription(settings['email']):
            return
            
        script_name = "discoverySearch.py"
        script_path = get_script_path(script_name)
        
        if not os.path.exists(script_path):
            # Create a properly styled warning message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Script Not Found")
            msg_box.setText(f"Script not found: {script_path}")
            msg_box.setIcon(QMessageBox.Warning)
            
            # Apply light styling to the message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMessageBox QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #ffc107;
                    color: #000000;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: 500;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            
            msg_box.exec_()
            return
        
        # Validate credentials
        if not settings['email'] or not settings['password']:
            # Create a properly styled warning message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Missing Credentials")
            msg_box.setText("Please enter username and password for Discovery Search.")
            msg_box.setIcon(QMessageBox.Warning)
            
            # Apply light styling to the message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMessageBox QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #ffc107;
                    color: #000000;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: 500;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            
            msg_box.exec_()
            return
        
        if not CredentialValidator.validate_email(settings['email']):
            # Create a properly styled warning message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Invalid Username")
            msg_box.setText("Please enter a valid username/email for Discovery Search.")
            msg_box.setIcon(QMessageBox.Warning)
            
            # Apply light styling to the message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMessageBox QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #ffc107;
                    color: #000000;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: 500;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            
            msg_box.exec_()
            return
        
        if not CredentialValidator.validate_password(settings['password']):
            # Create a properly styled warning message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Invalid Password")
            msg_box.setText("Password must be at least 6 characters long.")
            msg_box.setIcon(QMessageBox.Warning)
            
            # Apply light styling to the message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMessageBox QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #ffc107;
                    color: #000000;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: 500;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            
            msg_box.exec_()
            return
        
        # Create and start thread
        thread = EnhancedScriptRunner(script_path, "Discovery Search", settings, self.config_manager)
        thread.output_signal.connect(lambda text: self.append_output(text, "discovery"))
        thread.progress_signal.connect(self.update_progress)
        thread.finished_signal.connect(lambda msg, success: self.script_finished("discoverySearch.py", self.discovery_run_btn, msg, success))
        thread.error_signal.connect(self.handle_script_error)
        thread.user_collected_signal.connect(lambda username, collected, target: self.user_collected(username, collected, target, "discovery"))
        thread.setup_status_signal.connect(self.update_setup_status)
        
        self.script_threads[script_name] = thread
        thread.start()
        
        # Update UI
        self.discovery_run_btn.setText("Stop Discovery Search")
        self.discovery_run_btn.setProperty("class", "stop-button")
        self.discovery_run_btn.style().unpolish(self.discovery_run_btn)
        self.discovery_run_btn.style().polish(self.discovery_run_btn)
        
        # Start setup animation for discovery
        self.discovery_progress_bar.start_setup_animation()
        self.discovery_activity_label.setText("Setting up Discovery Search...")
        
        self.statusBar().showMessage("Discovery Search started", 3000)
    
    def run_keyword_script(self):
        """Run keyword search script"""
        settings = self.get_keyword_settings()
        
        # Check subscription with keyword username specifically
        if not self.check_subscription(settings['email']):
            return
            
        script_name = "keywordSearch.py"
        script_path = get_script_path(script_name)
        
        if not os.path.exists(script_path):
            # Create a properly styled warning message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Script Not Found")
            msg_box.setText(f"Script not found: {script_path}")
            msg_box.setIcon(QMessageBox.Warning)
            
            # Apply light styling to the message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMessageBox QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #ffc107;
                    color: #000000;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: 500;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            
            msg_box.exec_()
            return
        
        # Validate credentials
        if not settings['email'] or not settings['password']:
            # Create a properly styled warning message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Missing Credentials")
            msg_box.setText("Please enter username and password for Keyword Search.")
            msg_box.setIcon(QMessageBox.Warning)
            
            # Apply light styling to the message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMessageBox QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #ffc107;
                    color: #000000;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: 500;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            
            msg_box.exec_()
            return
        
        if not CredentialValidator.validate_email(settings['email']):
            # Create a properly styled warning message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Invalid Username")
            msg_box.setText("Please enter a valid username/email for Keyword Search.")
            msg_box.setIcon(QMessageBox.Warning)
            
            # Apply light styling to the message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMessageBox QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #ffc107;
                    color: #000000;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: 500;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            
            msg_box.exec_()
            return
        
        if not CredentialValidator.validate_password(settings['password']):
            # Create a properly styled warning message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Invalid Password")
            msg_box.setText("Password must be at least 6 characters long.")
            msg_box.setIcon(QMessageBox.Warning)
            
            # Apply light styling to the message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMessageBox QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #ffc107;
                    color: #000000;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: 500;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            
            msg_box.exec_()
            return
        
        # Create and start thread
        thread = EnhancedScriptRunner(script_path, "Keyword Search", settings, self.config_manager)
        thread.output_signal.connect(lambda text: self.append_output(text, "keyword"))
        thread.progress_signal.connect(self.update_progress)
        thread.finished_signal.connect(lambda msg, success: self.script_finished("keywordSearch.py", self.keyword_run_btn, msg, success))
        thread.error_signal.connect(self.handle_script_error)
        thread.user_collected_signal.connect(lambda username, collected, target: self.user_collected(username, collected, target, "keyword"))
        thread.setup_status_signal.connect(self.update_setup_status)
        
        self.script_threads[script_name] = thread
        thread.start()
        
        # Update UI
        self.keyword_run_btn.setText("Stop Keyword Search")
        self.keyword_run_btn.setProperty("class", "stop-button")
        self.keyword_run_btn.style().unpolish(self.keyword_run_btn)
        self.keyword_run_btn.style().polish(self.keyword_run_btn)
        
        # Start setup animation for keyword
        self.keyword_progress_bar.start_setup_animation()
        self.keyword_activity_label.setText("Setting up Keyword Search...")
        
        self.statusBar().showMessage("Keyword Search started", 3000)

    def update_subscription_status(self):
        """Update subscription status display (optional feature)"""
        try:
            # Get current username
            username = self.discovery_email_input.text().strip()
            if not username:
                username = self.keyword_email_input.text().strip()
            
            if not username:
                return
            
            # Check subscription
            license_manager = LicenseManager()
            if license_manager.db:
                subscription_info = license_manager.get_subscription_info(username)
                
                if subscription_info:
                    status = subscription_info['status']
                    days_remaining = subscription_info.get('days_remaining', 0)
                    
                    if status == 'active':
                        status_text = f"Subscription: Active ({days_remaining} days remaining)"
                        self.statusBar().showMessage(status_text)
                    elif status == 'expired':
                        status_text = f"Subscription: Expired - Renewal Required"
                        self.statusBar().showMessage(status_text)
                    else:
                        status_text = f"Subscription: {status.title()}"
                        self.statusBar().showMessage(status_text)
                else:
                    self.statusBar().showMessage("Subscription: Not Found")
        
        except Exception as e:
            # Silent error - don't bother user with status check errors
            pass
    def manual_activate_subscription(self, username, payment_reference=None):
        """Manually activate subscription (for admin use)"""
        try:
            license_manager = LicenseManager()
            
            if license_manager.db:
                success = license_manager.activate_subscription(username, payment_reference)
                
                if success:
                    print(f"[SUCCESS] Manually activated subscription for: {username}")
                    return True
                else:
                    print(f"[ERROR] Failed to activate subscription for: {username}")
                    return False
            else:
                print("[ERROR] Could not connect to Firebase")
                return False
        
        except Exception as e:
            print(f"[ERROR] Manual activation failed: {e}")
            return False
    def stop_script(self, script_name, button):
        """Stop a running script"""
        if script_name in self.script_threads:
            thread = self.script_threads[script_name]
            if thread.isRunning():
                # Update button state immediately
                if script_name == "discoverySearch.py":
                    button.setText("Run Discovery Search")
                    # Stop and reset discovery progress bar
                    self.discovery_progress_bar.stop_animation()
                    self.discovery_progress_bar.setValue(0)
                    self.discovery_progress_info_label.setText("0/0 users (0%)")
                    self.discovery_activity_label.setText("Stopping...")
                else:
                    button.setText("Run Keyword Search")
                    # Stop and reset keyword progress bar
                    self.keyword_progress_bar.stop_animation()
                    self.keyword_progress_bar.setValue(0)
                    self.keyword_progress_info_label.setText("0/0 users (0%)")
                    self.keyword_activity_label.setText("Stopping...")
                    
                button.setProperty("class", "")
                button.style().unpolish(button)
                button.style().polish(button)
                
                # Stop the thread
                thread.stop()
                
                # Wait for thread to stop
                if not thread.wait(10000):
                    thread.terminate()
                
                # Clean up
                self.script_threads.pop(script_name, None)
                
                # Update activity status
                if script_name == "discoverySearch.py":
                    self.discovery_activity_label.setText("Ready")
                else:
                    self.keyword_activity_label.setText("Ready")
                
                self.statusBar().showMessage(f"{script_name.replace('.py', '')} stopped", 3000)
    
    def script_finished(self, script_name, button, message, success):
        """Handle script completion"""
        # Update button state back to run
        if script_name == "discoverySearch.py":
            button.setText("Run Discovery Search")
            # Stop discovery progress bar animation
            self.discovery_progress_bar.stop_animation()
            if success:
                self.discovery_activity_label.setText("Completed successfully")
            else:
                self.discovery_activity_label.setText("Failed")
        else:
            button.setText("Run Keyword Search")
            # Stop keyword progress bar animation
            self.keyword_progress_bar.stop_animation()
            if success:
                self.keyword_activity_label.setText("Completed successfully")
            else:
                self.keyword_activity_label.setText("Failed")
            
        button.setProperty("class", "")
        button.style().unpolish(button)
        button.style().polish(button)
        
        # Clean up thread
        self.script_threads.pop(script_name, None)
        
        if success:
            self.statusBar().showMessage("Script completed successfully", 5000)
        else:
            self.statusBar().showMessage("Script failed", 5000)
    
    def update_progress(self, value):
        """Update progress bar (fallback for manual updates)"""
        # This is kept for compatibility but the smart progress bars handle their own updates
        pass
    
    def handle_script_error(self, error_msg):
        """Handle script errors"""
        # Only log critical errors, not minor issues
        if "CRITICAL" in error_msg or "Failed" in error_msg:
            print(f"Script error: {error_msg}")
    
    def update_users_display(self):
        """Update the multi-column users display"""
        # Clear existing layout
        for i in reversed(range(self.users_container_layout.count())):
            child = self.users_container_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Display users in 5 columns format
        users_per_row = 5
        total_users = len(self.collected_usernames)
        
        if total_users == 0:
            no_users_label = QLabel("No users collected yet")
            no_users_label.setStyleSheet("color: #888888; font-style: italic; text-align: center;")
            no_users_label.setAlignment(Qt.AlignCenter)
            self.users_container_layout.addWidget(no_users_label)
            return
        
        # Calculate rows needed
        rows_needed = min(15, (total_users + users_per_row - 1) // users_per_row)  # Max 15 rows
        
        for row in range(rows_needed):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(5)
            
            for col in range(users_per_row):
                user_index = row * users_per_row + col
                
                if user_index < total_users:
                    user_info = self.collected_usernames[user_index]
                    user_label = QLabel(f"{user_index + 1}. {user_info['username'][:12]}...")  # Truncate long names
                    
                    # Color code by script type
                    if user_info['script'] == 'discovery':
                        user_label.setStyleSheet("color: #66ccff; font-size: 8px; padding: 1px;")
                    else:
                        user_label.setStyleSheet("color: #ffcc66; font-size: 8px; padding: 1px;")
                    
                    row_layout.addWidget(user_label)
                else:
                    # Empty placeholder
                    empty_label = QLabel("")
                    empty_label.setFixedWidth(60)
                    row_layout.addWidget(empty_label)
            
            row_widget = QWidget()
            row_widget.setLayout(row_layout)
            row_widget.setFixedHeight(12)
            self.users_container_layout.addWidget(row_widget)
    
    def user_collected(self, username, collected_count, target_count, script_type):
        """Handle new user collection for specific script type"""
        # Add to internal tracking with script info
        user_info = {
            'username': username,
            'script': script_type,
            'timestamp': datetime.now()
        }
        self.collected_usernames.append(user_info)
        
        # Keep only last 75 users (15 rows × 5 columns)
        if len(self.collected_usernames) > 75:
            self.collected_usernames = self.collected_usernames[-75:]
        
        # Update the multi-column display
        self.update_users_display()
        
        # Update appropriate progress bar
        if script_type == "discovery":
            self.discovery_progress_bar.set_user_progress(collected_count, target_count)
            progress_percent = (collected_count / target_count) * 100 if target_count > 0 else 0
            self.discovery_progress_info_label.setText(f"{collected_count}/{target_count} users ({progress_percent:.1f}%)")
            self.discovery_activity_label.setText(f"Found: {username}")
        elif script_type == "keyword":
            self.keyword_progress_bar.set_user_progress(collected_count, target_count)
            progress_percent = (collected_count / target_count) * 100 if target_count > 0 else 0
            self.keyword_progress_info_label.setText(f"{collected_count}/{target_count} users ({progress_percent:.1f}%)")
            self.keyword_activity_label.setText(f"Found: {username}")
    
    def update_setup_status(self, status):
        """Update setup status for the active script"""
        # Determine which script is sending the status and update accordingly
        for script_name, thread in self.script_threads.items():
            if thread.isRunning():
                if script_name == "discoverySearch.py":
                    self.discovery_activity_label.setText(status)
                elif script_name == "keywordSearch.py":
                    self.keyword_activity_label.setText(status)
                break
    
    def update_system_status(self):
        """Update system status"""
        running_scripts = []
        
        for script_name, thread in self.script_threads.items():
            if thread.isRunning():
                display_name = script_name.replace('.py', '').replace('Search', ' Search')
                running_scripts.append(display_name)
        
        if running_scripts:
            self.system_status_label.setText(f"Running: {', '.join(running_scripts)}")
            self.system_status_label.setStyleSheet("color: #ff6600; font-weight: 500;")
        else:
            self.system_status_label.setText("Ready - No scripts running")
            self.system_status_label.setStyleSheet("color: #28a745; font-weight: 500;")
            # Reset progress info when no scripts running
            if not any(thread.isRunning() for thread in self.script_threads.values()):
                self.discovery_progress_info_label.setText("0/0 users (0%)")
                self.keyword_progress_info_label.setText("0/0 users (0%)")
                self.discovery_progress_bar.setValue(0)
                self.keyword_progress_bar.setValue(0)
                self.discovery_activity_label.setText("Ready")
                self.keyword_activity_label.setText("Ready")
    
    def append_output(self, text, script_type):
        """Filter and display output to appropriate log tabs"""
        # Filter out technical/developer messages
        text = text.strip()
        
        # Skip empty lines
        if not text:
            return
            
        # Skip technical logs that users don't need to see
        skip_patterns = [
            "gradient",
            "scrollTop",
            "scrollHeight", 
            "element_to_be_clickable",
            "WebDriverWait",
            "arguments[0]",
            "javascript",
            "CSS",
            "selector",
            "dom",
            "xpath",
            "timeout",
            "expected_conditions",
            "driver.execute",
            "find_element",
            "click()",
            "send_keys",
            "ActionChains",
            "psutil",
            "Process",
            ".pid",
            "Chrome process",
            "subprocess",
            "stderr",
            "stdout"
        ]
        
        # Check if this line contains technical information users don't need
        text_lower = text.lower()
        if any(pattern.lower() in text_lower for pattern in skip_patterns):
            return
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_text = f"[{timestamp}] {text}"
        
        # Route to appropriate log tab
        if script_type == "discovery":
            self.ds_log_output.append(formatted_text)
            # Auto-scroll to bottom only if enabled
            if self.ds_auto_scroll_check.isChecked():
                scrollbar = self.ds_log_output.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        elif script_type == "keyword":
            self.ks_log_output.append(formatted_text)
            # Auto-scroll to bottom only if enabled
            if self.ks_auto_scroll_check.isChecked():
                scrollbar = self.ks_log_output.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
    
    def save_settings(self):
        """Save current settings"""
        try:
            current_settings = {
                'discovery_email': self.discovery_email_input.text(),
                'discovery_password': self.discovery_password_input.text(),
                'discovery_hide_browser': self.discovery_hide_browser_check.isChecked(),
                'discovery_target_users': self.discovery_target_users_spin.value(),
                'discovery_posts_per_filter': self.discovery_posts_per_filter_spin.value(),
                'keyword_email': self.keyword_email_input.text(),
                'keyword_password': self.keyword_password_input.text(),
                'keyword_hide_browser': self.keyword_hide_browser_check.isChecked(),
                'keyword_target_users': self.keyword_target_users_spin.value(),
                'keyword_posts_per_keyword': self.keyword_posts_per_keyword_spin.value(),
            }
            
            if self.config_manager.save_config(current_settings):
                # Create a properly styled message box
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Settings Saved")
                msg_box.setText("Settings have been saved successfully!")
                msg_box.setIcon(QMessageBox.Information)
                
                # Apply light styling to the message box
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #ffffff;
                        color: #000000;
                    }
                    QMessageBox QLabel {
                        color: #000000;
                        background-color: transparent;
                    }
                    QMessageBox QPushButton {
                        background-color: #ff6600;
                        color: #ffffff;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-weight: 500;
                        min-width: 60px;
                    }
                    QMessageBox QPushButton:hover {
                        background-color: #e55a00;
                    }
                """)
                
                msg_box.exec_()
                self.statusBar().showMessage("Settings saved securely", 3000)
            else:
                # Create a properly styled error message box
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Save Error")
                msg_box.setText("Failed to save settings. Please check file permissions.")
                msg_box.setIcon(QMessageBox.Critical)
                
                # Apply light styling to the error message box
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #ffffff;
                        color: #000000;
                    }
                    QMessageBox QLabel {
                        color: #000000;
                        background-color: transparent;
                    }
                    QMessageBox QPushButton {
                        background-color: #dc3545;
                        color: #ffffff;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-weight: 500;
                        min-width: 60px;
                    }
                    QMessageBox QPushButton:hover {
                        background-color: #c82333;
                    }
                """)
                
                msg_box.exec_()
                
        except Exception as e:
            # Create a properly styled error message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Save Error")
            msg_box.setText(f"Failed to save settings:\n{str(e)}")
            msg_box.setIcon(QMessageBox.Critical)
            
            # Apply light styling to the error message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMessageBox QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    background-color: #dc3545;
                    color: #ffffff;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: 500;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            
            msg_box.exec_()
    
    def load_user_data(self):
        """Load user data and settings"""
        try:
            config = self.config_manager.load_config()
            
            # Load discovery settings
            self.discovery_email_input.setText(config.get('discovery_email', ''))
            self.discovery_password_input.setText(config.get('discovery_password', ''))
            self.discovery_hide_browser_check.setChecked(config.get('discovery_hide_browser', True))
            self.discovery_target_users_spin.setValue(config.get('discovery_target_users', 300))
            self.discovery_posts_per_filter_spin.setValue(config.get('discovery_posts_per_filter', 500))
            
            # Load keyword settings
            self.keyword_email_input.setText(config.get('keyword_email', ''))
            self.keyword_password_input.setText(config.get('keyword_password', ''))
            self.keyword_hide_browser_check.setChecked(config.get('keyword_hide_browser', True))
            self.keyword_target_users_spin.setValue(config.get('keyword_target_users', 500))
            self.keyword_posts_per_keyword_spin.setValue(config.get('keyword_posts_per_keyword', 50))
            
        except Exception as e:
            pass  # Silent error handling for user experience
    
    def closeEvent(self, event):
        """Handle application close event"""
        try:
            # Stop all running scripts
            running_scripts = []
            for script_name, thread in self.script_threads.items():
                if thread.isRunning():
                    running_scripts.append(script_name)
            
            if running_scripts:
                reply = QMessageBox.question(
                    self, "Scripts Running", 
                    f"Scripts are still running. Do you want to stop them and exit?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    event.ignore()
                    return
                
                # Stop all scripts
                for script_name in running_scripts:
                    if script_name == "discoverySearch.py":
                        self.stop_script(script_name, self.discovery_run_btn)
                    else:
                        self.stop_script(script_name, self.keyword_run_btn)
                
                # Wait for threads to stop
                for thread in self.script_threads.values():
                    if thread.isRunning():
                        thread.wait(3000)
            
            # Save current settings
            self.save_settings()
            event.accept()
            
        except Exception as e:
            pass  # Silent error handling for user experience
            event.accept()

def check_dependencies():
    """Check for required dependencies"""
    required_packages = [
        ('cryptography', 'pip install cryptography'),
        ('selenium', 'pip install selenium'),
        ('undetected_chromedriver', 'pip install undetected-chromedriver'),
        ('PyQt5', 'pip install PyQt5')
    ]
    
    missing_packages = []
    
    for package, install_cmd in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append((package, install_cmd))
    
    if missing_packages:
        missing_list = '\n'.join([f"• {pkg}: {cmd}" for pkg, cmd in missing_packages])
        error_msg = f"Missing required dependencies:\n\n{missing_list}\n\nPlease install the missing packages and try again."
        
        try:
            QMessageBox.critical(None, "Missing Dependencies", error_msg)
        except:
            print(f"ERROR: {error_msg}")
        
        return False
    
    return True

def create_application():
    """Create and configure the application"""
    app = QApplication(sys.argv)
    app.setApplicationName("Maloum Automation Suite")
    app.setApplicationVersion("Professional")
    app.setOrganizationName("MaloumAutomation")
    app.setOrganizationDomain("maloumautomation.local")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Set application icon if available
    icon_paths = ['icon.png', 'icon.ico', 'assets/icon.png']
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            try:
                app.setWindowIcon(QIcon(icon_path))
                break
            except:
                continue
    
    return app

def main():
    """Enhanced main application entry point"""
    try:
        # Check for subscription dependencies
        try:
            import firebase_admin
            from dotenv import load_dotenv
        except ImportError as e:
            missing_package = str(e).split("'")[1] if "'" in str(e) else "unknown package"
            error_msg = f"Missing required package: {missing_package}\n\n"
            error_msg += "Please install required packages:\n"
            error_msg += "pip install firebase-admin python-dotenv"
            
            QMessageBox.critical(None, "Missing Dependencies", error_msg)
            sys.exit(1)
        
        # Check dependencies first
        if not check_dependencies():
            sys.exit(1)
        
        # Create application
        app = create_application()
        
        # Create main window
        window = MainWindow()
        window.show()
        
        # Show welcome message for new users
        if not os.path.exists(window.config_manager.config_file):
            welcome_msg = """Welcome to Maloum Automation Suite - Professional Edition!

Features:
• Separate Discovery and Keyword Search automation
• Real-time progress tracking with animated progress bar
• Individual credential management per script
• Professional, clean interface with orange accent theme
• Encrypted credential storage for security

Getting Started:
1. Enter credentials for Discovery Search and/or Keyword Search
2. Configure target users and other parameters
3. Click "Run" to start automation
4. Monitor progress in the System Status section

Your settings will be automatically saved!"""
            
            QMessageBox.information(window, "Welcome!", welcome_msg)
        
        # Start application event loop
        sys.exit(app.exec_())
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        error_msg = f"Failed to start application: {str(e)}"
        try:
            QMessageBox.critical(None, "Critical Error", error_msg)
        except:
            print(f"CRITICAL ERROR: {error_msg}")
        sys.exit(1)

if __name__ == '__main__':
    main()