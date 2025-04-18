import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
import pyqtgraph as pg

class LEDIndicator(QWidget):
    def __init__(self, parent=None, size=20):
        super().__init__(parent)
        self.setMinimumSize(size, size)
        self.setMaximumSize(size, size)
        
        # 状态颜色
        self.colors = {
            'green_off': (0, 100, 0),      # 暗绿
            'green_on': (0, 255, 0),       # 亮绿
            'red_off': (100, 0, 0),        # 暗红
            'red_on': (255, 0, 0)          # 亮红
        }
        
        self.current_color = self.colors['green_off']
        
    def paintEvent(self, event):
        painter = pg.QtGui.QPainter(self)
        painter.setRenderHint(pg.QtGui.QPainter.Antialiasing)
        
        # 创建圆形
        rect = event.rect()
        
        # 绘制边框
        painter.setPen(pg.mkPen(color=(30, 30, 30), width=1))
        
        # 设置指示灯颜色
        painter.setBrush(pg.mkBrush(color=self.current_color))
        
        # 绘制圆形
        painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
        
    def set_status(self, status):
        """设置指示灯状态
        status: 'green_off', 'green_on', 'red_off', 'red_on'
        """
        self.current_color = self.colors[status]
        self.update()

class StatusIndicatorDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("状态指示灯演示")
        self.setGeometry(300, 300, 400, 200)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建指示灯和标签的水平布局
        indicator_layout = QHBoxLayout()
        
        # 创建状态指示灯
        self.status_green = LEDIndicator(size=30)
        self.status_green.set_status('green_off')
        self.status_red = LEDIndicator(size=30)
        self.status_red.set_status('red_off')
        
        # 添加标签
        indicator_layout.addWidget(QLabel("工作状态:"))
        indicator_layout.addWidget(self.status_green)
        indicator_layout.addWidget(QLabel("错误状态:"))
        indicator_layout.addWidget(self.status_red)
        indicator_layout.addStretch()
        
        # 创建控制按钮
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("开始工作")
        self.start_button.clicked.connect(self.start_working)
        
        self.stop_button = QPushButton("停止工作")
        self.stop_button.clicked.connect(self.stop_working)
        
        self.error_button = QPushButton("触发错误")
        self.error_button.clicked.connect(self.trigger_error)
        
        self.clear_button = QPushButton("清除错误")
        self.clear_button.clicked.connect(self.clear_error)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.error_button)
        button_layout.addWidget(self.clear_button)
        
        # 添加布局到主布局
        main_layout.addLayout(indicator_layout)
        main_layout.addLayout(button_layout)
        main_layout.addStretch()
        
        # 初始状态
        self.working = False
        self.error = False
        
    def start_working(self):
        self.working = True
        self.status_green.set_status('green_on')
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
    def stop_working(self):
        self.working = False
        self.status_green.set_status('green_off')
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def trigger_error(self):
        self.error = True
        self.status_red.set_status('red_on')
        self.clear_button.setEnabled(True)
        
    def clear_error(self):
        self.error = False
        self.status_red.set_status('red_off')
        self.clear_button.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 启用高DPI支持
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    window = StatusIndicatorDemo()
    window.show()
    
    sys.exit(app.exec_())