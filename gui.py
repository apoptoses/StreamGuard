import sys
import os
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QGroupBox, QListWidget, QLineEdit, QPushButton, 
                             QFormLayout, QSpinBox, QMessageBox, QScrollArea, QPlainTextEdit,
                             QDialog, QLabel)
from PyQt6.QtCore import QTimer, Qt, Q_ARG, QMetaObject
from storage import (get_streamers, add_streamer, remove_streamer, get_server_data, set_server_data, 
                     get_youtubers, add_youtuber, remove_youtuber, get_all_guild_ids)
from app import get_current_streamer, check_stream_status, get_oauth_token

class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)

class StreamGuardGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StreamGuard")
        self.setGeometry(100, 100, 800, 600)

        # Set up logging
        self.logTextBox = QTextEditLogger(self)
        self.logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.logTextBox)
        logging.getLogger().setLevel(logging.INFO)

        self.get_all_streamers_func = None
        self.get_server_names_func = None

        self.setup_ui()

    def set_get_all_streamers_func(self, func):
        self.get_all_streamers_func = func
        self.update_servers_list()

    def set_get_server_names_func(self, func):
        self.get_server_names_func = func
        self.update_servers_list()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.setup_servers_tab()
        self.setup_logs_tab()

    def setup_servers_tab(self):
        servers_tab = QWidget()
        servers_layout = QVBoxLayout(servers_tab)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self.servers_list = QVBoxLayout()
        scroll_layout.addLayout(self.servers_list)
        scroll_layout.addStretch(1)  

        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)

        servers_layout.addWidget(scroll_area)

    
        refresh_button = QPushButton("Refresh Servers")
        refresh_button.clicked.connect(self.update_servers_list)
        servers_layout.addWidget(refresh_button)

        self.tab_widget.addTab(servers_tab, "Servers")

    def update_servers_list(self):

        for i in reversed(range(self.servers_list.count())):
            widget = self.servers_list.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        servers = self.get_discord_servers()
        for server_id, server_name in servers:
            server_widget = QWidget()
            server_layout = QHBoxLayout(server_widget)

            label = QLabel(f"{server_name} (ID: {server_id})")
            server_layout.addWidget(label)

            details_button = QPushButton("Details")
            details_button.clicked.connect(lambda checked, sid=server_id, sname=server_name: self.show_server_details(sid, sname))
            server_layout.addWidget(details_button)

            self.servers_list.addWidget(server_widget)

        self.servers_list.addStretch(1)

    def show_server_details(self, server_id, server_name):
    
        server_data = get_server_data(server_id)
    
        details_dialog = QDialog(self)
        details_dialog.setWindowTitle(f"Server Details: {server_name}")
        details_layout = QVBoxLayout(details_dialog)

    
        details_layout.addWidget(QLabel(f"Server Name: {server_name}"))
        details_layout.addWidget(QLabel(f"Server ID: {server_id}"))
    
    
        if server_data:
            for key, value in server_data.items():
                details_layout.addWidget(QLabel(f"{key}: {value}"))
        else:
            details_layout.addWidget(QLabel("No additional data available for this server."))

        close_button = QPushButton("Close")
        close_button.clicked.connect(details_dialog.close)
        details_layout.addWidget(close_button)

        details_dialog.setLayout(details_layout)
        details_dialog.exec()

    def get_discord_servers(self):
        try:
            guild_info = []
            guild_ids = get_all_guild_ids()
            server_names = self.get_server_names()
        
            logging.info(f"Fetched guild IDs: {guild_ids}")
            logging.info(f"Fetched server names: {server_names}")
        
            for guild_id in guild_ids:
                # Convert guild_id to int for comparison
                guild_id_int = int(guild_id)
                guild_name = server_names.get(guild_id_int, f"Unknown Server {guild_id}")
                guild_info.append((guild_id, guild_name))

            logging.info(f"Compiled guild info: {guild_info}")
            return guild_info
        except Exception as e:
            logging.error(f"Error in get_discord_servers: {e}")
            return []

        
    def get_server_names(self):
        try:
            if self.get_server_names_func:
                server_names = self.get_server_names_func()
                logging.info(f"Server names fetched: {server_names}")
                return server_names
            else:
                logging.warning("get_server_names_func is not set")
                return {}
        except Exception as e:
            logging.error(f"Error fetching server names: {e}")
            return {}
    

    def setup_logs_tab(self):
        logs_tab = QWidget()
        layout = QVBoxLayout()
        logs_tab.setLayout(layout)

        layout.addWidget(self.logTextBox.widget)

        self.tab_widget.addTab(logs_tab, "Logs")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StreamGuardGUI()
    window.show()
    sys.exit(app.exec())