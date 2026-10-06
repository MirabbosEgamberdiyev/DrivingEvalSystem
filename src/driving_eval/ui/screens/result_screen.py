"""Final exam results screen with PASS/FAIL status, itemized violations, and PDF export."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from driving_eval.ui.i18n import tr


class ResultScreen(QWidget):
    """Displays final evaluation outcome, violations ledger, and export actions."""

    pdf_export_requested = Signal()
    usb_export_requested = Signal()
    next_candidate_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)

        # Header Badge
        self.badge_frame = QFrame()
        self.badge_frame.setFixedHeight(90)
        self.badge_layout = QHBoxLayout(self.badge_frame)

        self.result_title = QLabel(tr("pass_label"))
        self.result_title.setFont(QFont("Arial", 22, QFont.Bold))
        self.result_title.setStyleSheet("color: white;")

        self.score_label = QLabel("Ball: 100 / 100")
        self.score_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.score_label.setStyleSheet("color: white;")

        self.badge_layout.addWidget(self.result_title)
        self.badge_layout.addStretch()
        self.badge_layout.addWidget(self.score_label)
        layout.addWidget(self.badge_frame)
        layout.addSpacing(15)

        # Violations Table
        lbl_v = QLabel("Qayd Etilgan Qoidabuzarliklar:")
        lbl_v.setFont(QFont("Arial", 14, QFont.Bold))
        lbl_v.setStyleSheet("color: white;")
        layout.addWidget(lbl_v)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Vaqt", "Holat", "Mashq", "Qoida", "Jarima", "Batafsil"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1A202C;
                color: white;
                gridline-color: #4A5568;
                border: 1px solid #4A5568;
            }
            QHeaderView::section {
                background-color: #2D3748;
                color: white;
                font-weight: bold;
                padding: 6px;
            }
        """)
        layout.addWidget(self.table)
        layout.addSpacing(15)

        # Action Buttons
        btn_layout = QHBoxLayout()

        self.btn_pdf = QPushButton(tr("btn_export_pdf"))
        self.btn_pdf.setStyleSheet("background-color: #3182CE; color: white; padding: 12px 20px; font-weight: bold; border-radius: 8px;")
        self.btn_pdf.clicked.connect(self.pdf_export_requested.emit)
        btn_layout.addWidget(self.btn_pdf)

        self.btn_usb = QPushButton(tr("btn_export_usb"))
        self.btn_usb.setStyleSheet("background-color: #D69E2E; color: white; padding: 12px 20px; font-weight: bold; border-radius: 8px;")
        self.btn_usb.clicked.connect(self.usb_export_requested.emit)
        btn_layout.addWidget(self.btn_usb)

        btn_layout.addStretch()

        self.btn_next = QPushButton(tr("btn_next_student"))
        self.btn_next.setStyleSheet("background-color: #38A169; color: white; padding: 12px 25px; font-weight: bold; border-radius: 8px;")
        self.btn_next.clicked.connect(self.next_candidate_requested.emit)
        btn_layout.addWidget(self.btn_next)

        layout.addLayout(btn_layout)

    def display_result(
        self,
        final_score: int,
        is_pass: bool,
        violations: list[dict],
    ) -> None:
        bg_color = "#22543D" if is_pass else "#742A2A"
        badge_text = tr("pass_label") if is_pass else tr("fail_label")

        self.badge_frame.setStyleSheet(f"background-color: {bg_color}; border-radius: 12px; padding: 10px;")
        self.result_title.setText(badge_text)
        self.score_label.setText(f"Ball: {final_score} / 100")

        self.table.setRowCount(len(violations))
        for row, v in enumerate(violations):
            ts = v.get("timestamp", "")[11:19]
            status = v.get("status", "CONFIRMED")
            exercise = v.get("exercise", "")
            title = v.get("title", v.get("rule_code", ""))
            penalty = f"-{v.get('penalty', 0)}" if status == "CONFIRMED" else "0 (SUSPECT)"
            desc = v.get("description", "")

            self.table.setItem(row, 0, QTableWidgetItem(ts))
            self.table.setItem(row, 1, QTableWidgetItem(status))
            self.table.setItem(row, 2, QTableWidgetItem(exercise))
            self.table.setItem(row, 3, QTableWidgetItem(title))
            self.table.setItem(row, 4, QTableWidgetItem(penalty))
            self.table.setItem(row, 5, QTableWidgetItem(desc))
