from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QTableWidget, 
                             QTableWidgetItem, QFileDialog, QProgressBar, 
                             QTextEdit, QMessageBox, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import pandas as pd
from core.email_validator import EmailValidator

class VerificationWorker(QThread):
    """Background thread for email verification"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    status = pyqtSignal(str)
    
    def __init__(self, df, email_column):
        super().__init__()
        self.df = df
        self.email_column = email_column
        self.validator = EmailValidator()
    
    def run(self):
        results = {
            'corrected': [],
            'invalid': [],
            'valid': [],
            'total': len(self.df)
        }
        
        for idx, row in self.df.iterrows():
            email = row[self.email_column]
            self.status.emit(f"Verifying: {email}")
            
            result = self.validator.validate_and_correct(email)
            
            if result['status'] == 'corrected':
                self.df.at[idx, self.email_column] = result['corrected_email']
                results['corrected'].append({
                    'original': email,
                    'corrected': result['corrected_email'],
                    'reason': result['reason']
                })
            elif result['status'] == 'invalid':
                results['invalid'].append({
                    'email': email,
                    'reason': result['reason']
                })
            else:
                results['valid'].append(email)
            
            progress_pct = int((idx + 1) / len(self.df) * 100)
            self.progress.emit(progress_pct)
        
        results['df'] = self.df
        self.finished.emit(results)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.df = None
        self.csv_path = None
        self.results = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Email Verification Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # File selection section
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.load_btn = QPushButton("Load CSV")
        self.load_btn.clicked.connect(self.load_csv)
        file_layout.addWidget(QLabel("CSV File:"))
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.load_btn)
        layout.addLayout(file_layout)
        
        # Column selection
        column_layout = QHBoxLayout()
        self.column_combo = QComboBox()
        self.column_combo.setEnabled(False)
        column_layout.addWidget(QLabel("Email Column:"))
        column_layout.addWidget(self.column_combo)
        layout.addLayout(column_layout)
        
        # Verify button
        self.verify_btn = QPushButton("Start Verification")
        self.verify_btn.setEnabled(False)
        self.verify_btn.clicked.connect(self.start_verification)
        layout.addWidget(self.verify_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        
        # Splitter for table and report
        splitter = QSplitter(Qt.Vertical)
        
        # Data table
        self.table = QTableWidget()
        splitter.addWidget(self.table)
        
        # Report area
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        splitter.addWidget(self.report_text)
        
        splitter.setSizes([500, 300])
        layout.addWidget(splitter)
        
        # Export buttons
        export_layout = QHBoxLayout()
        self.export_corrected_btn = QPushButton("Export Corrected CSV")
        self.export_corrected_btn.setEnabled(False)
        self.export_corrected_btn.clicked.connect(self.export_corrected)
        
        self.export_invalid_btn = QPushButton("Export Invalid Emails")
        self.export_invalid_btn.setEnabled(False)
        self.export_invalid_btn.clicked.connect(self.export_invalid)
        
        self.export_report_btn = QPushButton("Export Report")
        self.export_report_btn.setEnabled(False)
        self.export_report_btn.clicked.connect(self.export_report)
        
        export_layout.addWidget(self.export_corrected_btn)
        export_layout.addWidget(self.export_invalid_btn)
        export_layout.addWidget(self.export_report_btn)
        layout.addLayout(export_layout)
    
    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                self.df = pd.read_csv(file_path)
                self.csv_path = file_path
                self.file_label.setText(file_path.split('/')[-1])
                
                # Populate column dropdown
                self.column_combo.clear()
                self.column_combo.addItems(self.df.columns.tolist())
                self.column_combo.setEnabled(True)
                self.verify_btn.setEnabled(True)
                
                # Display data in table
                self.display_dataframe(self.df)
                
                self.status_label.setText(f"Loaded {len(self.df)} rows")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")
    
    def display_dataframe(self, df):
        self.table.setRowCount(df.shape[0])
        self.table.setColumnCount(df.shape[1])
        self.table.setHorizontalHeaderLabels(df.columns.tolist())
        
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                self.table.setItem(i, j, QTableWidgetItem(str(df.iloc[i, j])))
    
    def start_verification(self):
        email_column = self.column_combo.currentText()
        
        if not email_column:
            QMessageBox.warning(self, "Warning", "Please select an email column")
            return
        
        self.verify_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Start verification in background thread
        self.worker = VerificationWorker(self.df.copy(), email_column)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.verification_complete)
        self.worker.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def verification_complete(self, results):
        self.results = results
        self.df = results['df']
        
        # Update table with corrected emails
        self.display_dataframe(self.df)
        
        # Generate report
        report = self.generate_report(results)
        self.report_text.setText(report)
        
        # Enable export buttons
        self.export_corrected_btn.setEnabled(True)
        self.export_invalid_btn.setEnabled(True)
        self.export_report_btn.setEnabled(True)
        
        self.verify_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        self.status_label.setText("Verification complete!")
        
        QMessageBox.information(self, "Complete", "Email verification completed!")
    
    def generate_report(self, results):
        report = "EMAIL VERIFICATION REPORT\n"
        report += "=" * 50 + "\n\n"
        report += f"Total emails processed: {results['total']}\n"
        report += f"Valid emails: {len(results['valid'])}\n"
        report += f"Corrected emails: {len(results['corrected'])}\n"
        report += f"Invalid emails: {len(results['invalid'])}\n\n"
        
        if results['corrected']:
            report += "\nCORRECTED EMAILS:\n"
            report += "-" * 50 + "\n"
            for item in results['corrected']:
                report += f"Original: {item['original']}\n"
                report += f"Corrected: {item['corrected']}\n"
                report += f"Reason: {item['reason']}\n\n"
        
        if results['invalid']:
            report += "\nINVALID EMAILS:\n"
            report += "-" * 50 + "\n"
            for item in results['invalid']:
                report += f"Email: {item['email']}\n"
                report += f"Reason: {item['reason']}\n\n"
        
        return report
    
    def export_corrected(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Corrected CSV", "", "CSV Files (*.csv)"
        )
        if file_path:
            self.df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Success", "Corrected CSV exported!")
    
    def export_invalid(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Invalid Emails", "", "CSV Files (*.csv)"
        )
        if file_path and self.results:
            invalid_df = pd.DataFrame(self.results['invalid'])
            invalid_df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Success", "Invalid emails exported!")
    
    def export_report(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", "", "Text Files (*.txt)"
        )
        if file_path:
            with open(file_path, 'w') as f:
                f.write(self.report_text.toPlainText())
            QMessageBox.information(self, "Success", "Report exported!")