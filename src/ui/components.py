"""
UI组件模块
"""
from PyQt5.QtWidgets import (QLabel, QGroupBox, QVBoxLayout, QHBoxLayout,
                           QPushButton, QComboBox, QWidget, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QImage
import math
from src.utils.i18n import i18n
from api_client import AlpacaClient
from src.services.telescope_monitor import TelescopeMonitor
from utils import load_config
import os

class DeviceSignals(QObject):
    """设备信号类"""
    location_updated = pyqtSignal(float, float, float)  # 经度、纬度、海拔
    coordinates_updated = pyqtSignal(float, float, float, float)  # 赤经、赤纬、高度角、方位角
    status_updated = pyqtSignal(dict)  # 望远镜状态信号

class LabelPair:
    """标签对组件"""
    def __init__(self, key, value=None, value_class='status-text'):
        self.layout = QHBoxLayout()
        self.key = key
        
        self.label = QLabel(f"{i18n.get_text(key)}:")
        self.label.setProperty('class', 'label-title')
        
        self.value_label = QLabel(value if value else '')
        self.value_label.setProperty('class', value_class)
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.value_label)
        
        # 设置布局属性
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)

    def set_value(self, value):
        """设置值"""
        self.value_label.setText(str(value))

    def update_text(self):
        """更新文本"""
        self.label.setText(f"{i18n.get_text(self.key)}:")

    def get_layout(self):
        """获取布局"""
        return self.layout

class DeviceControl:
    """设备控制组件"""
    def __init__(self, device_id, name):
        self.layout = QHBoxLayout()
        self.device_id = device_id
        self.is_connected = False
        self.signals = DeviceSignals()
        self.is_serial_device = False  # 是否是串口设备
        self.serial_connection = None  # 串口连接对象
        self.last_status = None  # 保存最后一次的状态数据
        
        # 根据设备类型创建对应的 API 客户端
        config = load_config()
        # 修复 device_id 映射
        device_type = device_id
        if device_id == 'mount':
            device_type = 'telescope'
        elif device_id == 'weather':
            device_type = 'observingconditions'
        elif device_id == 'cover':
            device_type = 'covercalibrator'
        elif device_id == 'dome':
            device_type = 'dome'
        device_config = config.get("devices", {}).get(device_type, {})
        api_url = device_config.get("api_url")
        self.client = AlpacaClient(base_url=api_url)
        
        # 创建监控线程（用于望远镜、电调焦、消旋器、气象站、镜头盖和圆顶设备）
        self.telescope_monitor = None
        if device_id in ['mount', 'focuser', 'rotator', 'weather', 'cover', 'dome']:
            device_type = 'telescope' if device_id == 'mount' else (
                'observingconditions' if device_id == 'weather' else (
                    'covercalibrator' if device_id == 'cover' else (
                        'dome' if device_id == 'dome' else device_id
                    )
                )
            )
            self.telescope_monitor = TelescopeMonitor(device_type=device_type)
            # 连接监控线程的信号
            if device_id == 'mount':
                self.telescope_monitor.coordinates_updated.connect(
                    self.signals.coordinates_updated.emit
                )
                self.telescope_monitor.status_updated.connect(
                    self.signals.status_updated.emit
                )
            elif device_id == 'focuser':
                # 连接电调焦状态更新信号
                self.telescope_monitor.focuser_updated.connect(self.update_focuser_status)
            elif device_id == 'rotator':
                # 连接消旋器状态更新信号
                self.telescope_monitor.rotator_updated.connect(self.update_rotator_status)
            elif device_id == 'weather':
                # 连接气象站数据更新信号
                self.telescope_monitor.weather_updated.connect(self.update_weather_info)
            elif device_id == 'cover':
                # 连接镜头盖状态更新信号
                self.telescope_monitor.cover_updated.connect(self.update_cover_status)
            elif device_id == 'dome':
                # 连接圆顶状态更新信号
                self.telescope_monitor.dome_updated.connect(self.update_dome_status)
            
            # 连接设备列表更新信号
            self.telescope_monitor.devices_updated.connect(self.update_devices)
        
        self.label = QLabel(name)
        self.label.setProperty('class', 'label-title')
        self.label.setAlignment(Qt.AlignCenter)  # 居中对齐文本
        self.label.setFixedWidth(70)  # 设置固定宽度，确保所有标签宽度一致
        
        # 使用统一的下拉菜单和连接按钮界面
        if device_id in ['mount', 'focuser', 'rotator', 'weather', 'cover', 'dome', 'cooler']:
            self.combo = QComboBox()
            self.combo.setMinimumWidth(200)  # 设置最小宽度以便显示设备名称
            self.combo.setMaximumWidth(300)  # 设置最大宽度，避免过长
            self.combo.setStyleSheet("QComboBox { min-height: 25px; }")  # 确保高度足够
            
            self.connect_button = QPushButton(i18n.get_text("connected") if self.is_connected else i18n.get_text("disconnected"))
            self.connect_button.setProperty('class', 'primary-button')
            self.connect_button.clicked.connect(self.toggle_connection)
            self.connect_button.setMinimumWidth(100)  # 设置最小宽度
            self.connect_button.setFixedWidth(100)  # 设置固定宽度
            
            # 创建固定布局，确保所有控件对齐
            self.layout.addWidget(self.label)
            self.layout.addWidget(self.combo, 1)  # 添加拉伸因子，使下拉菜单占据更多空间
            self.layout.addWidget(self.connect_button)
            self.layout.setAlignment(Qt.AlignLeft)  # 整体左对齐
            
            # 打印布局信息，用于调试
            print(f"设备控制组件 {device_id} 布局: 标签宽度={self.label.sizeHint().width()}, 下拉菜单宽度={self.combo.sizeHint().width()}, 按钮宽度={self.connect_button.sizeHint().width()}")
        else:  # 其他设备保持原有的三按钮设计
            self.combo = QComboBox()
            self.combo.addItems(["COM1", "COM2", "COM3"])
            
            self.buttons = []
            for i in range(1, 4):
                btn = QPushButton(str(i))
                btn.setProperty('class', 'square-button')
                btn.setFixedSize(32, 32)
                self.buttons.append(btn)
            
            self.layout.addWidget(self.label)
            self.layout.addWidget(self.combo)
            for btn in self.buttons:
                self.layout.addWidget(btn)
            
        # 设置布局属性
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        
        # 存储设备列表
        self.devices = []
        
        # 创建定时器用于水冷机状态轮询
        if device_id == 'cooler':
            from PyQt5.QtCore import QTimer
            self.cooler_timer = QTimer()
            self.cooler_timer.timeout.connect(self.poll_cooler_status)
            self.cooler_timer.setInterval(1000)  # 1秒轮询一次

    def update_devices(self, devices):
        """更新设备列表"""
        print(f"\n正在更新 {self.device_id} 的设备列表...")
        print(f"收到的设备列表: {devices}")
        
        if self.device_id in ['mount', 'focuser', 'rotator', 'weather', 'cover', 'dome']:
            # 过滤当前设备类型的设备
            device_type = {
                'mount': 'Telescope',
                'focuser': 'Focuser',
                'rotator': 'Rotator',
                'weather': 'ObservingConditions',
                'cover': 'CoverCalibrator',
                'dome': 'Dome'
            }[self.device_id]
            
            # 过滤并确保每个设备都有必要的字段
            filtered_devices = []
            for d in devices:
                if d.get('DeviceType') == device_type:
                    device = {
                        'DeviceName': d.get('DeviceName', 'Unknown Device'),
                        'DeviceType': d.get('DeviceType', device_type),
                        'DeviceNumber': d.get('DeviceNumber', 0),
                        'ApiVersion': d.get('ApiVersion', '1.0')
                    }
                    filtered_devices.append(device)
            
            print(f"过滤后的设备列表: {filtered_devices}")
            
            self.devices = filtered_devices
            self.combo.clear()
            
            # 添加设备到下拉菜单
            for device in filtered_devices:
                device_name = device['DeviceName']
                device_type = device['DeviceType']
                device_number = device['DeviceNumber']
                api_version = device['ApiVersion']
                display_name = f"{device_name} ({device_type} #{device_number})"
                print(f"添加设备到下拉菜单: {display_name}")
                self.combo.addItem(display_name, device)
            
            # 如果没有设备，添加一个默认选项
            if not filtered_devices:
                default_device = {
                    'DeviceName': 'ASCOM CoverCalibrator Simulator',
                    'DeviceType': device_type,
                    'DeviceNumber': 0,
                    'ApiVersion': '1.0'
                }
                display_name = f"{default_device['DeviceName']} ({device_type} #0)"
                print(f"添加默认设备到下拉菜单: {display_name}")
                self.combo.addItem(display_name, default_device)
            
            print(f"下拉菜单项数: {self.combo.count()}")
            
            # 如果有设备，默认选择第一个
            if self.combo.count() > 0:
                self.combo.setCurrentIndex(0)

    def get_telescope_location(self):
        """获取望远镜位置信息"""
        if not self.is_connected or self.device_id != 'mount':
            return
            
        # 获取当前选中的设备信息
        current_index = self.combo.currentIndex()
        if current_index >= 0:
            device_data = self.combo.itemData(current_index)
            if device_data:
                device_number = device_data['DeviceNumber']
                # 获取位置信息
                longitude = self.client.get('telescope', device_number, 'sitelongitude')
                latitude = self.client.get('telescope', device_number, 'sitelatitude')
                elevation = self.client.get('telescope', device_number, 'siteelevation')
                
                if all(v is not None for v in [longitude, latitude, elevation]):
                    print(f"获取到位置信息：经度 {longitude}°, 纬度 {latitude}°, 海拔 {elevation}m")
                    # 发送信号更新位置信息
                    self.signals.location_updated.emit(longitude, latitude, elevation)
                    return True
        return False

    def toggle_connection(self):
        """切换连接状态"""
        if self.device_id not in ['mount', 'focuser', 'rotator', 'weather', 'cover', 'dome', 'cooler']:
            return
            
        self.is_connected = not self.is_connected
        self.connect_button.setText(i18n.get_text("connected") if self.is_connected else i18n.get_text("disconnected"))
        
        # 水冷机设备的特殊处理
        if self.device_id == 'cooler' and self.is_serial_device:
            if self.is_connected:
                self.connect_to_cooler()
            else:
                self.disconnect_from_cooler()
            return
            
        # 获取当前选中的设备信息
        current_index = self.combo.currentIndex()
        if current_index >= 0:
            device_data = self.combo.itemData(current_index)
            if device_data:
                device_number = device_data['DeviceNumber']
                if self.is_connected:
                    print(f"连接到设备: {device_data['DeviceName']}")
                    # 启动监控线程
                    if self.telescope_monitor:
                        self.telescope_monitor.set_device(device_number, self.device_id)
                        self.telescope_monitor.start()
                else:
                    print(f"断开设备: {device_data['DeviceName']}")
                    # 停止监控线程并标记为断开连接
                    if self.telescope_monitor:
                        self.telescope_monitor.disconnect_device()

    def connect_to_cooler(self):
        """连接到水冷机设备"""
        try:
            import serial
            # 获取选中的串口
            port = self.combo.currentData()
            if not port:
                print("错误: 未选择有效的串口")
                self.is_connected = False
                self.connect_button.setText(i18n.get_text("disconnected"))
                return
                
            # 保存选中的串口到配置文件
            config = load_config()
            if "devices" not in config:
                config["devices"] = {}
            if "cooler" not in config["devices"]:
                config["devices"]["cooler"] = {}
            config["devices"]["cooler"]["port"] = port
            
            # 获取或设置默认的串口参数
            baudrate = config["devices"]["cooler"].get("baudrate", 4800)
            bytesize = config["devices"]["cooler"].get("bytesize", 8)
            parity = config["devices"]["cooler"].get("parity", "N")
            stopbits = config["devices"]["cooler"].get("stopbits", 2)
            timeout = config["devices"]["cooler"].get("timeout", 1)
            
            # 将字符串转换为PySerial常量
            bytesize_map = {
                5: serial.FIVEBITS,
                6: serial.SIXBITS,
                7: serial.SEVENBITS,
                8: serial.EIGHTBITS
            }
            parity_map = {
                'N': serial.PARITY_NONE,
                'E': serial.PARITY_EVEN,
                'O': serial.PARITY_ODD,
                'M': serial.PARITY_MARK,
                'S': serial.PARITY_SPACE
            }
            stopbits_map = {
                1: serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2: serial.STOPBITS_TWO
            }
            
            # 保存配置
            config["devices"]["cooler"]["baudrate"] = baudrate
            config["devices"]["cooler"]["bytesize"] = bytesize
            config["devices"]["cooler"]["parity"] = parity
            config["devices"]["cooler"]["stopbits"] = stopbits
            config["devices"]["cooler"]["timeout"] = timeout
            
            import json
            with open("config.yaml", "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                
            # 连接串口 (使用MODBUS-RTU协议参数)
            print(f"连接到串口: {port}, 波特率: {baudrate}, 数据位: {bytesize}, 校验位: {parity}, 停止位: {stopbits}")
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize_map.get(bytesize, serial.EIGHTBITS),
                parity=parity_map.get(parity, serial.PARITY_NONE),
                stopbits=stopbits_map.get(stopbits, serial.STOPBITS_TWO),
                timeout=timeout
            )
            
            print(f"成功连接到水冷机设备: {port}")
            
            # 启动定时器，开始轮询设备状态
            self.cooler_timer.start()
            
        except ImportError:
            print("错误: 未安装PySerial库")
            self.is_connected = False
            self.connect_button.setText(i18n.get_text("disconnected"))
        except Exception as e:
            print(f"连接水冷机时出错: {e}")
            self.is_connected = False
            self.connect_button.setText(i18n.get_text("disconnected"))
            
    def disconnect_from_cooler(self):
        """断开与水冷机的连接"""
        # 停止定时器
        self.cooler_timer.stop()
        
        # 关闭串口连接
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("已断开与水冷机的连接")
            
    def poll_cooler_status(self):
        """轮询水冷机状态"""
        if not self.is_connected or not self.serial_connection or not self.serial_connection.is_open:
            return
            
        try:
            # 读取温度值 (参数码00H)
            temperature = self.read_modbus_register(1, 0x00)
            
            # 读取状态字 (参数码02H)
            status_bits = self.read_modbus_register(1, 0x02)
            
            # 发送状态更新信号
            status = {
                'temperature': temperature,
                'status_bits': status_bits
            }
            # 保存最后状态
            self.last_status = status
            # 发送信号通知UI更新
            self.signals.status_updated.emit(status)
            
        except Exception as e:
            print(f"读取水冷机状态时出错: {e}")
            
    def read_modbus_register(self, slave_addr, register_addr):
        """读取Modbus寄存器值"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return None
            
        try:
            # 构建Modbus RTU读寄存器请求（功能码03）
            request = bytearray([
                slave_addr,  # 从站地址
                0x03,        # 功能码 (03表示读保持寄存器)
                0x00,        # 寄存器地址高字节
                register_addr, # 寄存器地址低字节
                0x00,        # 寄存器数量高字节
                0x01,        # 寄存器数量低字节(读1个寄存器)
            ])
            
            # 计算CRC校验
            crc = self.calculate_crc(request)
            # Modbus RTU规范：先低字节，后高字节
            request.append(crc & 0xFF)         # CRC低字节
            request.append((crc >> 8) & 0xFF)  # CRC高字节
            
            # 打印请求内容，用于调试
            request_hex = ' '.join([f'{b:02X}' for b in request])
            print(f"发送Modbus请求: {request_hex}")
            
            # 清除接收缓冲区
            self.serial_connection.reset_input_buffer()
            
            # 发送请求
            self.serial_connection.write(request)
            
            # 读取响应（预期至少7个字节: 从站地址+功能码+字节数+数据(2字节)+CRC(2字节)）
            response = self.serial_connection.read(7)
            
            # 打印响应内容，用于调试
            if response:
                response_hex = ' '.join([f'{b:02X}' for b in response])
                print(f"收到Modbus响应: {response_hex}")
            
            # 检查响应长度
            if len(response) < 7:
                print(f"Modbus响应长度不足: {len(response)} bytes")
                return None
                
            # 检查从站地址和功能码
            if response[0] != slave_addr or response[1] != 0x03:
                print(f"Modbus响应错误: 从站地址或功能码不匹配")
                return None
                
            # 检查字节数
            if response[2] != 2:
                print(f"Modbus响应错误: 字节数不匹配")
                return None
                
            # 验证响应的CRC
            # Modbus RTU规范：先低字节，后高字节
            received_crc = (response[6] << 8) | response[5]
            calculated_crc = self.calculate_crc(response[0:5])
            if received_crc != calculated_crc:
                print(f"Modbus CRC校验错误: 收到 0x{received_crc:04X}, 计算值 0x{calculated_crc:04X}")
                # 考虑到某些设备可能不完全遵循标准，可以选择忽略CRC错误
                # return None
            
            # 提取并返回寄存器值（高字节在前，低字节在后）
            register_value = (response[3] << 8) | response[4]
            print(f"读取寄存器值: 0x{register_value:04X} ({register_value})")
            return register_value
            
        except Exception as e:
            print(f"读取Modbus寄存器时出错: {e}")
            return None
            
    def calculate_crc(self, data):
        """计算Modbus RTU的CRC-16校验值"""
        try:
            crc = 0xFFFF
            for byte in data:
                crc ^= byte
                for _ in range(8):
                    if crc & 0x0001:
                        crc = (crc >> 1) ^ 0xA001  # CRC-16 多项式 0xA001
                    else:
                        crc = crc >> 1
            return crc
        except Exception as e:
            print(f"计算CRC时出错: {e}")
            return 0

    def update_text(self):
        """更新文本"""
        self.label.setText(i18n.get_text(self.device_id))
        # 修改所有设备类型都更新按钮文本，不只是望远镜
        if self.device_id in ['mount', 'focuser', 'rotator', 'weather', 'cover', 'dome', 'cooler']:
            self.connect_button.setText(i18n.get_text("connected") if self.is_connected else i18n.get_text("disconnected"))

    def get_layout(self):
        """获取布局"""
        return self.layout

    def update_focuser_status(self, status):
        """更新电调焦状态显示"""
        # 更新位置
        if hasattr(self, 'focuser_status'):
            self.focuser_status.pairs['position'].set_value(f"{status['position']:.1f}°")
            
            # 更新移动状态
            moving_text = i18n.get_text('moving_yes') if status['ismoving'] else i18n.get_text('moving_no')
            self.focuser_status.pairs['moving'].set_value(moving_text)
            
            # 设置移动状态的样式
            style_class = 'medium-text ' + ('status-warning' if status['ismoving'] else 'status-success')
            self.focuser_status.pairs['moving'].value_label.setProperty('class', style_class)
            self.focuser_status.pairs['moving'].value_label.style().unpolish(self.focuser_status.pairs['moving'].value_label)
            self.focuser_status.pairs['moving'].value_label.style().polish(self.focuser_status.pairs['moving'].value_label)

    def update_rotator_status(self, status):
        """更新消旋器状态显示"""
        # 更新位置
        if hasattr(self, 'rotator_status'):
            self.rotator_status.pairs['position'].set_value(f"{status['position']:.1f}°")
            
            # 更新移动状态
            moving_text = i18n.get_text('moving_yes') if status['ismoving'] else i18n.get_text('moving_no')
            self.rotator_status.pairs['moving'].set_value(moving_text)
            
            # 设置移动状态的样式
            style_class = 'medium-text ' + ('status-warning' if status['ismoving'] else 'status-success')
            self.rotator_status.pairs['moving'].value_label.setProperty('class', style_class)
            self.rotator_status.pairs['moving'].value_label.style().unpolish(self.rotator_status.pairs['moving'].value_label)
            self.rotator_status.pairs['moving'].value_label.style().polish(self.rotator_status.pairs['moving'].value_label)

    def update_weather_info(self, weather_info):
        """更新气象站数据"""
        # 实现气象站数据更新逻辑
        pass

    def update_cover_status(self, status):
        """更新镜头盖状态"""
        # 实现镜头盖状态更新逻辑
        pass

    def update_dome_status(self, status):
        """更新圆顶状态"""
        if not status:
            return
        
        # 发送状态更新信号
        self.signals.status_updated.emit(status)

class InfoGroup:
    """信息组组件"""
    def __init__(self, title, items=None):
        self.title = title
        self.group = QGroupBox(i18n.get_text(title))
        self.layout = QVBoxLayout()
        self.pairs = {}
        
        if items:
            for key, value in items:
                pair = LabelPair(key, value)
                self.pairs[key] = pair
                self.layout.addLayout(pair.get_layout())
        
        self.group.setLayout(self.layout)
        
        # 设置布局属性
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

    def add_item(self, key, value, value_class='medium-text'):
        """添加项目"""
        pair = LabelPair(key, value, value_class)
        self.pairs[key] = pair
        self.layout.addLayout(pair.get_layout())

    def update_text(self):
        """更新文本"""
        self.group.setTitle(i18n.get_text(self.title))
        for pair in self.pairs.values():
            pair.update_text()

    def get_widget(self):
        """获取组件"""
        return self.group

class ThemeButton:
    """主题按钮组件"""
    def __init__(self, text, icon=None):
        self.button = QPushButton(text)
        self.button.setProperty('class', 'theme-button')
        self.button.setFixedHeight(32)
        if icon:
            self.button.setText(f"{icon} {text}")

    def get_widget(self):
        """获取组件"""
        return self.button

class AngleVisualizer(QWidget):
    """角度可视化组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dec_angle = 0  # 赤纬角度
        self.rotator_angle = 0  # 消旋器角度
        self.background_image = None  # 背景星图
        self.original_image = None  # 保存原始图片
        self.setMinimumSize(250, 250)  # 设置最小尺寸
        # 设置大小策略为扩展
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 设置内容边距，确保图片不会被边框遮挡
        self.setContentsMargins(10, 10, 10, 10)

    def set_background(self, image_path):
        """设置背景星图"""
        if image_path and os.path.exists(image_path):
            print(f"加载背景图片: {image_path}")
            self.original_image = QImage(image_path)  # 保存原始图片
            if not self.original_image.isNull():
                self.update_background_image()
                print(f"图片加载成功: 原始尺寸 {self.original_image.width()}x{self.original_image.height()}")
            else:
                print(f"图片加载失败")
            self.update()

    def update_background_image(self):
        """更新背景图片大小"""
        if self.original_image and not self.original_image.isNull():
            # 考虑内容边距计算可用空间
            margins = self.contentsMargins()
            available_width = self.width() - margins.left() - margins.right()
            available_height = self.height() - margins.top() - margins.bottom()
            
            # 取最小值确保图片完全显示且保持比例
            available_size = min(available_width, available_height)
            
            # 根据可用空间缩放图片
            self.background_image = self.original_image.scaled(
                available_size, available_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            print(f"图片已缩放至: {self.background_image.width()}x{self.background_image.height()}, 可用空间: {available_width}x{available_height}")

    def resizeEvent(self, event):
        """处理窗口大小变化事件"""
        super().resizeEvent(event)
        self.update_background_image()
        self.update()

    def set_angles(self, dec_angle, rotator_angle):
        """设置角度值"""
        self.dec_angle = dec_angle
        self.rotator_angle = rotator_angle
        self.update()

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 获取内容边距
        margins = self.contentsMargins()
        
        # 计算可用空间
        available_width = self.width() - margins.left() - margins.right()
        available_height = self.height() - margins.top() - margins.bottom()
        
        # 计算中心点（考虑边距）
        center_x = margins.left() + available_width / 2
        center_y = margins.top() + available_height / 2
        
        # 计算绘制尺寸（考虑边距）
        size = min(available_width, available_height)
        
        # 确保绘制尺寸不超过可用空间
        rect_size = int(size * 0.8)  # 稍微缩小一点，避免触及边缘

        # 绘制背景星图
        if self.background_image and not self.background_image.isNull():
            # 计算图片绘制位置，使其居中
            x = int(center_x - self.background_image.width() / 2)
            y = int(center_y - self.background_image.height() / 2)
            painter.drawImage(x, y, self.background_image)
        else:
            # 如果没有背景图，绘制灰色背景
            painter.fillRect(
                margins.left(), margins.top(),
                available_width, available_height,
                QColor(240, 240, 240)
            )

        # 设置半透明效果
        painter.setOpacity(0.7)

        # 绘制赤纬参考矩形（垂直）
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.dec_angle)
        pen = QPen(QColor(0, 0, 255))  # 蓝色
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(-20, -rect_size//2, 40, rect_size)
        # 绘制标记箭头
        arrow_y = -rect_size//2
        painter.drawLine(0, arrow_y-10, -10, arrow_y+10)
        painter.drawLine(0, arrow_y-10, 10, arrow_y+10)
        painter.restore()

        # 绘制画幅矩形（根据消旋器角度旋转）
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.rotator_angle)
        pen = QPen(QColor(255, 0, 0))  # 红色
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 200, 200, 50)))  # 淡红色半透明填充
        painter.drawRect(-30, -rect_size//2, 60, rect_size)
        # 绘制标记箭头
        arrow_y = -rect_size//2
        painter.drawLine(0, arrow_y-10, -10, arrow_y+10)
        painter.drawLine(0, arrow_y-10, 10, arrow_y+10)
        painter.restore()

        # 绘制夹角弧线
        painter.save()
        painter.translate(center_x, center_y)
        pen = QPen(QColor(0, 255, 0))  # 绿色
        pen.setWidth(2)
        painter.setPen(pen)
        radius = int(size * 0.15)  # 根据组件大小调整弧线半径
        start_angle = int(min(self.dec_angle, self.rotator_angle) * 16)
        span_angle = int((max(self.dec_angle, self.rotator_angle) - min(self.dec_angle, self.rotator_angle)) * 16)
        painter.drawArc(-radius, -radius, radius*2, radius*2, start_angle, span_angle)
        painter.restore() 