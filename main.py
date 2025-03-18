"""
主程序入口
"""
import sys
import os

# 将项目根目录添加到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from src.ui.main_window import MainWindow

def main():
    # 设置高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 
    
    # 调焦
    # GPS时间
    #圆顶状态 角度 天窗开关
    # 去掉相机状态 和滤镜论
    # 主镜罩
    # 高度方位驱动器状态 写驱动器使能 和电源状态
    # 去掉相机温度