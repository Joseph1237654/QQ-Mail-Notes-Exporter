APP_STYLE = """
QWidget {
    background: #F2F2F2;
    color: #151515;
    font-family: "Segoe UI", "Microsoft YaHei";
    font-size: 13px;
}

QMainWindow {
    background: #F2F2F2;
}

QLabel {
    background: transparent;
}

QFrame#Header {
    background: #111111;
    border: 0;
}

QLabel#Brand {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 600;
}

QLabel#HeaderStatus {
    color: #D8D8D8;
    border: 1px solid #3A3A3A;
    border-radius: 4px;
    padding: 6px 10px;
}

QFrame#Sidebar {
    background: #FAFAFA;
    border: 0;
    border-right: 1px solid #D5D5D5;
}

QPushButton#SettingsButton {
    background: transparent;
    border: 1px solid transparent;
    color: #555555;
    padding: 0;
}

QPushButton#SettingsButton:hover {
    background: #E7E7E7;
    border-color: #D0D0D0;
}

QPushButton#SettingsButton:pressed {
    background: #DEDEDE;
}

QWidget#Content {
    background: #F2F2F2;
}

QLabel#SectionLabel {
    color: #666666;
    font-size: 11px;
    font-weight: 600;
}

QLabel#Muted {
    color: #777777;
    font-size: 12px;
}

QLabel#MetricLabel {
    color: #777777;
    font-size: 11px;
}

QLabel#MetricValue {
    color: #111111;
    font-size: 28px;
    font-weight: 600;
}

QLabel#CurrentItem {
    color: #555555;
    font-size: 12px;
}

QLineEdit {
    background: #FFFFFF;
    border: 1px solid #CFCFCF;
    border-radius: 4px;
    padding: 8px 10px;
    selection-background-color: #111111;
    selection-color: #FFFFFF;
}

QLineEdit:focus {
    border-color: #111111;
}

QComboBox {
    min-height: 36px;
    padding: 0 12px;
    border: 1px solid #CFCFCF;
    border-radius: 4px;
    background: #FFFFFF;
    color: #151515;
}

QComboBox:hover {
    border-color: #8C8C8C;
}

QComboBox:focus {
    border-color: #111111;
}

QComboBox::drop-down {
    width: 30px;
    border: 0;
}

QComboBox QAbstractItemView {
    background: #FFFFFF;
    color: #151515;
    border: 1px solid #CFCFCF;
    selection-background-color: #111111;
    selection-color: #FFFFFF;
    padding: 4px;
}

QPushButton {
    min-height: 36px;
    padding: 0 14px;
    border-radius: 4px;
    border: 1px solid #CFCFCF;
    background: #FFFFFF;
    color: #151515;
}

QPushButton:hover {
    border-color: #8C8C8C;
    background: #F7F7F7;
}

QPushButton:pressed {
    background: #EDEDED;
}

QPushButton#Primary {
    background: #111111;
    color: #FFFFFF;
    border-color: #111111;
    font-weight: 600;
}

QPushButton#Primary:hover {
    background: #2A2A2A;
    border-color: #2A2A2A;
}

QPushButton#Primary:pressed {
    background: #000000;
}

QPushButton:disabled {
    background: #E2E2E2;
    color: #969696;
    border-color: #D8D8D8;
}

QPushButton#Ghost {
    background: transparent;
    border-color: transparent;
    color: #4F4F4F;
}

QPushButton#Ghost:hover {
    background: #E7E7E7;
    border-color: #D0D0D0;
}

QProgressBar {
    background: #DEDEDE;
    border: 0;
    border-radius: 2px;
    min-height: 6px;
    max-height: 6px;
    text-align: center;
}

QProgressBar::chunk {
    background: #111111;
    border-radius: 2px;
}

QPlainTextEdit {
    background: #FFFFFF;
    border: 1px solid #D8D8D8;
    border-radius: 4px;
    padding: 8px;
    color: #333333;
    selection-background-color: #111111;
    selection-color: #FFFFFF;
}

QFrame#Rule {
    background: #D8D8D8;
    border: 0;
    max-height: 1px;
}

QDialog#SettingsDialog {
    background: #F2F2F2;
}

QFrame#SettingsNav {
    background: #FAFAFA;
    border: 0;
    border-right: 1px solid #D5D5D5;
}

QLabel#SettingsNavTitle {
    font-size: 20px;
    font-weight: 600;
}

QLabel#SettingsNavSubtitle {
    color: #777777;
    font-size: 11px;
}

QPushButton#SettingsNavItem {
    background: transparent;
    border: 1px solid transparent;
    text-align: left;
    padding: 0 12px;
    min-height: 42px;
}

QPushButton#SettingsNavItem:hover:!checked {
    background: #E7E7E7;
    border-color: #D0D0D0;
}

QPushButton#SettingsNavItem:checked {
    background: #111111;
    border-color: #111111;
    color: #FFFFFF;
    font-weight: 600;
}

QWidget#SettingsPanel {
    background: #F2F2F2;
}

QLabel#SettingsPageTitle {
    font-size: 24px;
    font-weight: 600;
}

QLabel#SettingsDescription {
    color: #555555;
    font-size: 13px;
}

QLabel#AboutName {
    font-size: 20px;
    font-weight: 600;
}

QLabel#AboutVersion {
    color: #777777;
    font-size: 12px;
}

QLabel#AboutTagline {
    color: #333333;
    font-size: 15px;
    font-weight: 600;
}

QLabel#AboutBody {
    color: #4A4A4A;
    font-size: 13px;
}

QToolTip {
    background: #111111;
    color: #FFFFFF;
    border: 0;
    padding: 5px;
}
"""
