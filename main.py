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
from device_manager import Telescope, Focuser, Rotator, ObservingConditions, Dome, Cooler, UPS

def connect_and_get_device(device_manager):
    """连接设备并返回设备信息"""
    if device_manager.connect():
        return device_manager.device
    return None

def search_telescope():
    """搜索 Alpaca 望远镜和电调焦设备"""
    all_devices = []
    
    print("\n正在搜索 Alpaca 设备...")
    telescope = Telescope()
    if telescope.connect():
        all_devices.append(telescope.device)
        print("✓ 望远镜设备已连接")
    
    focuser = Focuser()
    if focuser.connect():
        all_devices.append(focuser.device)
        print("✓ 电调焦设备已连接")
    
    rotator = Rotator()
    if rotator.connect():
        all_devices.append(rotator.device)
        print("✓ 消旋器设备已连接")
    
    weather = ObservingConditions()
    if weather.connect():
        weather_device = {
            'DeviceName': weather.device.get('DeviceName', 'ASCOM Observing Conditions Simulator'),
            'DeviceType': 'ObservingConditions',
            'DeviceNumber': weather.device.get('DeviceNumber', 0),
            'ApiVersion': weather.device.get('ApiVersion', '1.0')
        }
        all_devices.append(weather_device)
        print("✓ 气象站设备已连接")

    dome = Dome()
    if dome.connect():
        dome_device = {
            'DeviceName': dome.device.get('DeviceName', 'ASCOM Dome Simulator'),
            'DeviceType': 'Dome',
            'DeviceNumber': dome.device.get('DeviceNumber', 0),
            'ApiVersion': dome.device.get('ApiVersion', '1.0')
        }
        all_devices.append(dome_device)
        print("✓ 圆顶设备已连接")
    
    cooler = Cooler()
    if cooler.connect():
        all_devices.append(cooler.device)
        print("✓ 水冷机设备已连接")
    else:
        print("× 水冷机设备配置失败")
    
    ups = UPS()
    if ups.connect():
        all_devices.append(ups.device)
        print("✓ UPS电源设备已连接")
    else:
        print("× UPS电源设备配置失败")
    
    print("\n开始启动主程序...\n")
    return all_devices

def main():
    devices = search_telescope()
    
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    window = MainWindow(telescope_devices=devices)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 