"""
UI组件模块
"""
from PyQt5.QtWidgets import (QLabel, QGroupBox, QVBoxLayout, QHBoxLayout,
                           QPushButton, QComboBox, QWidget, QSizePolicy, QGridLayout, QSpacerItem)
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
    # UPS状态相关的key列表和对应的中英文标签
    ups_status_labels = {
        'utility_status': {'cn': '市电状态：', 'en': 'Utility Status:'},
        'battery_status': {'cn': '电池电压状态：', 'en': 'Battery Status:'},
        'ups_health': {'cn': 'UPS状态：', 'en': 'UPS Health:'},
        'selftest_status': {'cn': '自检中：', 'en': 'Self-test:'},
        'running_status': {'cn': '运行中：', 'en': 'Running:'}
    }
    
    def __init__(self, key, value=None, value_class='status-text'):
        self.layout = QHBoxLayout()
        self.key = key
        
        # 确定标签文本
        if key in self.ups_status_labels:
            # 根据当前语言设置标签文本
            current_lang = i18n.current_language  # 直接使用当前语言
            label_text = self.ups_status_labels[key][current_lang]
        else:
            label_text = f"{i18n.get_text(key)}:"
        
        self.label = QLabel(label_text)
        self.label.setProperty('class', 'label-title')
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label.setMinimumWidth(120)
            
        self.value_label = QLabel(value if value else '')
        self.value_label.setProperty('class', value_class)
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # 构建布局
        if key in self.ups_status_labels:
            # 使用网格布局来对齐UPS状态显示
            grid_layout = QGridLayout()
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.setSpacing(0)
            
            # 在第0列放置标签
            grid_layout.addWidget(self.label, 0, 0)
            
            # 在第1列添加弹性空间
            spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
            grid_layout.addItem(spacer, 0, 1)
            
            # 在第2列放置值标签
            grid_layout.addWidget(self.value_label, 0, 2)
            
            # 设置列拉伸因子
            grid_layout.setColumnStretch(0, 0)
            grid_layout.setColumnStretch(1, 1)
            grid_layout.setColumnStretch(2, 0)
            
            # 将网格布局添加到主布局
            container = QWidget()
            container.setLayout(grid_layout)
            self.layout.addWidget(container)
            
            # 设置布局属性
            self.layout.setContentsMargins(0, 0, 0, 0)
            self.layout.setSpacing(0)
        else:
            # 常规项目布局
            self.layout.addWidget(self.label, 1)
            self.layout.addWidget(self.value_label, 2)
            self.layout.setContentsMargins(0, 0, 0, 0)
            self.layout.setSpacing(15)

    def set_value(self, value):
        """设置值"""
        self.value_label.setText(str(value))

    def update_text(self):
        """更新文本"""
        if self.key in self.ups_status_labels:
            # 根据当前语言更新标签文本
            current_lang = i18n.current_language  # 直接使用当前语言
            self.label.setText(self.ups_status_labels[self.key][current_lang])
        else:
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
        self.label.setFixedWidth(80)  # 增加标签宽度以便更好地显示
        
        # 使用统一的下拉菜单和连接按钮界面
        if device_id in ['mount', 'focuser', 'rotator', 'weather', 'cover', 'dome', 'cooler', 'ups']:
            self.combo = QComboBox()
            self.combo.setMinimumWidth(220)  # 增加最小宽度以便显示设备名称
            self.combo.setMaximumWidth(320)  # 增加最大宽度，避免过长
            self.combo.setStyleSheet("QComboBox { min-height: 28px; }")  # 增加高度以便更好地显示
            
            self.connect_button = QPushButton(i18n.get_text("connected") if self.is_connected else i18n.get_text("disconnected"))
            self.connect_button.setProperty('class', 'error-button')  # 默认使用红色按钮（未连接状态）
            self.connect_button.clicked.connect(self.toggle_connection)
            self.connect_button.setMinimumWidth(120)  # 增加按钮宽度
            self.connect_button.setFixedWidth(120)  # 设置固定宽度
            
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
                btn.setFixedSize(35, 35)  # 增加按钮大小
                self.buttons.append(btn)
            
            self.layout.addWidget(self.label)
            self.layout.addWidget(self.combo)
            for btn in self.buttons:
                self.layout.addWidget(btn)
            
        # 设置布局属性
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(15)  # 增加组件间距
        
        # 存储设备列表
        self.devices = []
        
        # 创建定时器用于水冷机状态轮询
        if device_id == 'cooler':
            from PyQt5.QtCore import QTimer
            self.cooler_timer = QTimer()
            self.cooler_timer.timeout.connect(self.poll_cooler_status)
            self.cooler_timer.setInterval(1000)  # 1秒轮询一次
        
        # 创建定时器用于UPS电源状态轮询
        elif device_id == 'ups':
            from PyQt5.QtCore import QTimer
            self.ups_timer = QTimer()
            self.ups_timer.timeout.connect(self.poll_ups_status)
            self.ups_timer.setInterval(1000)  # 1秒轮询一次

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
        """切换设备连接状态"""
        if self.is_connected:
            # 断开连接
            if self.device_id == 'cooler':
                self.disconnect_from_cooler()
            elif self.device_id == 'ups':
                self.disconnect_from_ups()
            else:
                self.is_connected = False
            
            # 更新按钮样式
            self.connect_button.setText(i18n.get_text("disconnected"))
            self.connect_button.setProperty('class', 'error-button')
            # 刷新样式
            self.connect_button.style().unpolish(self.connect_button)
            self.connect_button.style().polish(self.connect_button)
        else:
            # 连接设备
            if self.device_id == 'cooler':
                if self.connect_to_cooler():
                    self.is_connected = True
                    # 更新按钮样式
                    self.connect_button.setText(i18n.get_text("connected"))
                    self.connect_button.setProperty('class', 'success-button')
                    # 刷新样式
                    self.connect_button.style().unpolish(self.connect_button)
                    self.connect_button.style().polish(self.connect_button)
            elif self.device_id == 'ups':
                if self.connect_to_ups():
                    self.is_connected = True
                    # 更新按钮样式
                    self.connect_button.setText(i18n.get_text("connected"))
                    self.connect_button.setProperty('class', 'success-button')
                    # 刷新样式
                    self.connect_button.style().unpolish(self.connect_button)
                    self.connect_button.style().polish(self.connect_button)
            else:
                # 获取当前选中的设备信息
                current_index = self.combo.currentIndex()
                if current_index >= 0:
                    device_data = self.combo.itemData(current_index)
                    if device_data:
                        self.is_connected = True
                        
                        # 设置设备号，用于后续API调用
                        if self.telescope_monitor:
                            device_type = {
                                'mount': 'telescope',
                                'focuser': 'focuser',
                                'rotator': 'rotator',
                                'weather': 'observingconditions',
                                'cover': 'covercalibrator',
                                'dome': 'dome'
                            }[self.device_id]
                            self.telescope_monitor.set_device(device_data['DeviceNumber'], device_type)
                            self.telescope_monitor.start()
                            
                            # 针对特定设备类型的额外处理
                            if self.device_id == 'mount':
                                # 获取并发送望远镜位置信息
                                self.get_telescope_location()
                                
                        # 更新按钮样式
                        self.connect_button.setText(i18n.get_text("connected"))
                        self.connect_button.setProperty('class', 'success-button')
                        # 刷新样式
                        self.connect_button.style().unpolish(self.connect_button)
                        self.connect_button.style().polish(self.connect_button)

    def connect_to_cooler(self):
        """连接到水冷机"""
        try:
            # 导入串口模块
            import serial
            import serial.tools.list_ports
            
            # 获取当前选择的串口
            port = self.combo.currentText()
            if not port or port == "请安装PySerial":
                print(f"无效的串口选择: {port}")
                return False
            
            # 关闭之前的连接
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            # 连接串口
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            
            if self.serial_connection.is_open:
                print(f"已成功连接到水冷机，串口: {port}")
                # 启动状态监控定时器
                self.cooler_timer.start()
                # 立即执行一次轮询，不等待定时器
                print("立即执行一次水冷机状态轮询")
                self.poll_cooler_status()
                
                # 延迟500ms后再执行一次轮询，确保UI更新
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(500, self.poll_cooler_status)
                
                return True
            else:
                print(f"连接水冷机失败，串口: {port}")
                return False
        except Exception as e:
            import traceback
            print(f"连接水冷机时发生错误: {str(e)}")
            traceback.print_exc()
            return False
            
    def connect_to_ups(self):
        """连接到UPS电源"""
        try:
            # 导入串口模块
            import serial
            import serial.tools.list_ports
            
            # 获取当前选择的串口
            port = self.combo.currentText()
            if not port or port == "请安装PySerial":
                print(f"无效的串口选择: {port}")
                return False
            
            # 关闭之前的连接
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            # 连接串口 - 根据UPS要求设置参数
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=2400,  # 波特率2400
                bytesize=serial.EIGHTBITS,  # 8位数据位
                parity=serial.PARITY_NONE,  # 无校验
                stopbits=serial.STOPBITS_ONE,  # 1位停止位
                timeout=1
            )
            
            if self.serial_connection.is_open:
                print(f"已成功连接到UPS电源，串口: {port}")
                # 创建UPS状态轮询定时器
                from PyQt5.QtCore import QTimer
                self.ups_timer.start()
                return True
            else:
                print(f"连接UPS电源失败，串口: {port}")
                return False
        except Exception as e:
            import traceback
            print(f"连接UPS电源时发生错误: {str(e)}")
            traceback.print_exc()
            return False
            
    def disconnect_from_cooler(self):
        """断开与水冷机的连接"""
        # 停止状态轮询
        if hasattr(self, 'cooler_timer'):
            self.cooler_timer.stop()
        
        # 关闭串口连接
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        
        self.is_connected = False
        print("已断开水冷机连接")
        
    def disconnect_from_ups(self):
        """断开与UPS电源的连接"""
        # 停止状态轮询
        if hasattr(self, 'ups_timer'):
            self.ups_timer.stop()
        
        # 关闭串口连接
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        
        self.is_connected = False
        print("已断开UPS电源连接")
            
    def poll_cooler_status(self):
        """轮询水冷机状态"""
        if not self.is_connected or not self.serial_connection or not self.serial_connection.is_open:
            return
            
        try:
            # 清空缓冲区
            self.serial_connection.reset_input_buffer()
            
            # 创建MODBUS-RTU读取请求（读取多个寄存器）
            # 查询温度值（地址00H）和指示灯状态（地址02H）
            # MODBUS功能码03H用于读取保持寄存器
            # 格式：地址(1字节) + 功能码(1字节) + 寄存器起始地址(2字节) + 寄存器数量(2字节) + CRC校验(2字节)
            
            # 使用文档中给出的默认地址：Ad=1（地址为1）
            device_address = 1
            function_code = 3  # 功能码03H：读取寄存器
            register_address = 0  # 起始寄存器地址00H（温度值）
            register_count = 3    # 读取3个寄存器（温度、时间运行值、指示灯状态）
            
            # 构建请求数据
            request = bytearray([
                device_address,   # 设备地址
                function_code,    # 功能码
                register_address >> 8,    # 寄存器地址高字节
                register_address & 0xFF,  # 寄存器地址低字节
                register_count >> 8,      # 寄存器数量高字节
                register_count & 0xFF     # 寄存器数量低字节
            ])
            
            # 计算CRC校验码
            crc = self.calculate_crc(request)
            request.append(crc & 0xFF)        # CRC低字节
            request.append((crc >> 8) & 0xFF) # CRC高字节
            
            # 发送请求
            self.serial_connection.write(request)
            
            # 等待响应
            import time
            time.sleep(0.1)
            
            # 读取响应
            # 预期响应格式: 地址(1) + 功能码(1) + 字节数(1) + 数据(2*寄存器数) + CRC(2)
            # 即3+寄存器数量*2个字节的响应
            expected_response_length = 3 + register_count * 2 + 2
            response = self.serial_connection.read(expected_response_length)
            
            if len(response) < expected_response_length:
                print(f"接收到的水冷机响应数据不完整: 预期{expected_response_length}字节，实际接收{len(response)}字节")
                print(f"接收的数据: {' '.join([f'{b:02X}' for b in response])}")
                return
            
            # 验证响应
            if response[0] != device_address or response[1] != function_code:
                print(f"水冷机响应格式错误: 设备地址或功能码不匹配")
                return
            
            # 解析响应数据
            temp_raw = (response[3] << 8) | response[4]  # 温度原始值
            status_bits = (response[7] << 8) | response[8]  # 指示灯状态
            
            # 温度异常值处理
            # 注1*：7FFFH:上溢出；8001H:下溢出。
            if temp_raw == 0x7FFF:
                temperature = float('inf')  # 上溢出
                temp_status = "上溢出"
            elif temp_raw == 0x8001:
                temperature = float('-inf')  # 下溢出
                temp_status = "下溢出"
            else:
                # 假设温度值为实际温度的10倍（需要根据设备文档确认）
                temperature = temp_raw / 10.0
                temp_status = "正常"
            
            # 解析状态位：根据文档
            # bit7: Run 运行指示灯 
            # bit6: OUT 加热指示灯 
            # bit5: Cool 制冷指示灯 
            # bit4: Flow 流量报警指示灯
            # bit3: Pump 循环指示灯 
            # bit2: Temp 温度报警指示灯 
            # bit1: LEVEL 液位报警指示灯 
            # bit0: Power
            
            status = {
                'temperature': float(temperature),     # 温度，确保是浮点数
                'temp_status': str(temp_status),     # 温度状态，确保是字符串
                'raw_value': int(status_bits),       # 原始状态值，确保是整数
                'status_bits': int(status_bits),     # 状态位，确保是整数
                # 解析各个状态位，确保是布尔值
                'running': bool(status_bits & 0x80),     # bit7: 运行指示灯
                'heating': bool(status_bits & 0x40),     # bit6: 加热指示灯
                'cooling': bool(status_bits & 0x20),     # bit5: 制冷指示灯
                'flow_alarm': bool(status_bits & 0x10),  # bit4: 流量报警指示灯
                'pump': bool(status_bits & 0x08),        # bit3: 循环指示灯
                'temp_alarm': bool(status_bits & 0x04),  # bit2: 温度报警指示灯
                'level_alarm': bool(status_bits & 0x02), # bit1: 液位报警指示灯
                'power': bool(status_bits & 0x01)        # bit0: 电源指示灯
            }
            
            # 打印状态信息以便调试
            print(f"水冷机状态: 温度={temperature}°C, 状态位={status_bits:08b}")
            print(f"水冷机解析后的状态: {status}")
            
            # 保存最后的状态信息，以便在语言切换时重新更新UI
            self.last_status = status
            
            # 发送状态更新信号
            try:
                # 使用深拷贝确保状态对象不会被修改
                import copy
                status_copy = copy.deepcopy(status)
                
                # 直接发送信号
                print("发送水冷机状态更新信号")
                self.signals.status_updated.emit(status_copy)
                
                # 延迟发送备份信号以确保UI更新
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(200, lambda: self.update_cooler_status_ui(None))
            except Exception as e:
                print(f"发送状态更新信号时出错: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            import traceback
            print(f"轮询水冷机状态时发生错误: {str(e)}")
            traceback.print_exc()
            
    def calculate_crc(self, data):
        """计算MODBUS-RTU的CRC校验码"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc = crc >> 1
        return crc

    def poll_ups_status(self):
        """轮询UPS电源状态"""
        if not self.is_connected or not self.serial_connection or not self.serial_connection.is_open:
            return
            
        try:
            # 清空缓冲区
            self.serial_connection.reset_input_buffer()
            
            # 发送Q1查询命令
            query_cmd = b'Q1\r'
            self.serial_connection.write(query_cmd)
            
            # 等待并读取响应
            import time
            time.sleep(0.2)  # 等待UPS响应
            
            response = self.serial_connection.read_until(b'\r')
            response_str = response.decode('ascii', errors='ignore').strip()
            
            # 检查响应格式是否正确 - 应以(开头
            if not response_str or not response_str.startswith('('):
                print(f"UPS响应格式不正确: {response_str}")
                return
                
            # 解析响应数据
            try:
                # 格式: (MMM.M NNN.N PPP.P QQQ RR.R S.SS TT.T b7b6b5b4b3b2b1b0<cr>
                parts = response_str[1:].strip().split()
                if len(parts) < 8:
                    print(f"UPS响应数据不完整: {response_str}")
                    return
                    
                input_voltage = float(parts[0])    # 输入电压
                fault_voltage = float(parts[1])    # 故障电压
                output_voltage = float(parts[2])   # 输出电压
                load_percentage = int(parts[3])    # 负载百分比，例如"034"代表34%
                input_frequency = float(parts[4])  # 输入频率
                battery_voltage = float(parts[5])  # 电池单体电压
                temperature = float(parts[6])      # 温度
                status_byte = parts[7]             # 状态字节
                
                # 解析状态字节 (b7b6b5b4b3b2b1b0)
                if len(status_byte) == 8:
                    status_bits = [int(bit) for bit in status_byte]
                    
                    # 确定UPS运行状态
                    ups_status = self.parse_ups_status(status_bits)
                    
                    # 计算电池电量百分比 - 这是个估算，需要根据实际UPS调整
                    battery_percentage = self.calculate_battery_percentage(battery_voltage)
                    
                    # 准备状态信息
                    status = {
                        'input_voltage': input_voltage,
                        'output_voltage': output_voltage,
                        'load': load_percentage,
                        'battery': battery_percentage,
                        'temperature': temperature,
                        'input_frequency': input_frequency,
                        'status': ups_status,
                        'raw_value': response_str,  # 保存原始响应
                        'status_bits': status_bits  # 状态位
                    }
                    
                    # 保存最后的状态信息，以便在语言切换时重新更新UI
                    self.last_status = status
                    
                    # 打印状态信息以便调试
                    print(f"UPS状态: 状态={ups_status}, 输入电压={input_voltage}V, "
                          f"输出电压={output_voltage}V, 负载={load_percentage}%, "
                          f"电池电量={battery_percentage}%, 温度={temperature}°C")
                    print(f"状态位: {status_byte} -> {status_bits} (类型: {type(status_bits)}, 长度: {len(status_bits)})")
                    print(f"UPS状态原始信息: {status}")
                    
                    # 发送状态更新信号
                    self.signals.status_updated.emit(status)
                else:
                    print(f"UPS状态字节格式不正确: {status_byte}")
            except Exception as e:
                print(f"解析UPS响应时发生错误: {str(e)}, 响应: {response_str}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            import traceback
            print(f"轮询UPS电源状态时发生错误: {str(e)}")
            traceback.print_exc()
    
    def parse_ups_status(self, status_bits):
        """解析UPS状态位"""
        # 状态位含义:
        # b7: 0=市电正常, 1=市电失败
        # b6: 0=电池电压不低, 1=电池电压低
        # b5: 0=非旁路/电池工作模式, 1=旁路/正在升压或降压
        # b4: 0=UPS正常, 1=UPS有故障
        # b3: 0=在线式UPS, 1=后备式或互动式UPS
        # b2: 0=非自检过程中, 1=正在自检
        # b1: 0=正常运行状态, 1=正在关机或已关机
        # b0: 0=蜂鸣器关闭, 1=蜂鸣器打开
        
        is_online_ups = status_bits[3] == 0
        
        if status_bits[4] == 1:  # UPS有故障
            return "故障"
        
        if is_online_ups:  # 在线式UPS
            if status_bits[7] == 0:  # 市电正常
                if status_bits[5] == 1:  # 旁路状态
                    return "旁路供电"
                else:
                    return "市电正常"
            else:  # 市电失败
                return "电池供电"
        else:  # 后备式/互动式UPS
            if status_bits[5] == 1:  # 使用市电
                return "市电正常"
            else:  # 使用电池
                return "电池供电"
    
    def calculate_battery_percentage(self, battery_voltage):
        """根据电池电压估算电量百分比"""
        # 这个函数需要根据实际UPS类型和电池规格进行调整
        # 下面的计算只是一个示例
        
        try:
            # 假设是标准12V UPS
            min_voltage = 10.5  # 最低电压
            max_voltage = 13.5  # 最高电压
            
            if battery_voltage <= min_voltage:
                return 0
            elif battery_voltage >= max_voltage:
                return 100
            else:
                # 线性映射电压到百分比
                percentage = int((battery_voltage - min_voltage) / (max_voltage - min_voltage) * 100)
                return max(0, min(100, percentage))
        except:
            return 50  # 默认返回50%

    def update_text(self):
        """更新文本"""
        self.label.setText(i18n.get_text(self.device_id))
        # 修改所有设备类型都更新按钮文本，不只是望远镜
        if self.device_id in ['mount', 'focuser', 'rotator', 'weather', 'cover', 'dome', 'cooler', 'ups']:
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

    def update_cooler_status_ui(self, main_window):
        """直接更新水冷机状态UI(仅在轮询时使用)"""
        if not self.last_status or not main_window:
            return
            
        try:
            # 直接调用主窗口的状态更新方法
            main_window.update_cooler_status(self.last_status)
            print(f"直接更新水冷机状态UI: {self.last_status}")
        except Exception as e:
            print(f"直接更新水冷机状态UI时出错: {e}")
            import traceback
            traceback.print_exc()

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
        self.layout.setContentsMargins(15, 15, 15, 15)  # 增加内边距
        self.layout.setSpacing(12)  # 增加行间距

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
        
        # 标记中心点
        painter.save()
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.setPen(QPen(Qt.NoPen))
        painter.drawEllipse(int(center_x - 3), int(center_y - 3), 6, 6)
        painter.restore()

        # 绘制赤纬参考线（蓝色垂直线）
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.dec_angle)  # 赤纬角度
        pen = QPen(QColor(0, 0, 255))  # 蓝色
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(-20, -rect_size//2, 40, rect_size)
        # 绘制标记箭头
        arrow_y = -rect_size//2
        painter.drawLine(0, arrow_y-10, -10, arrow_y+10)
        painter.drawLine(0, arrow_y-10, 10, arrow_y+10)
        # 添加赤纬标记文字
        painter.drawText(-20, -rect_size//2 - 15, "Dec")
        painter.restore()

        # 绘制画幅矩形（根据消旋器角度旋转）
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.rotator_angle)  # 消旋器角度
        pen = QPen(QColor(255, 0, 0))  # 红色
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 200, 200, 50)))  # 淡红色半透明填充
        painter.drawRect(-30, -rect_size//2, 60, rect_size)
        # 绘制标记箭头
        arrow_y = -rect_size//2
        painter.drawLine(0, arrow_y-10, -10, arrow_y+10)
        painter.drawLine(0, arrow_y-10, 10, arrow_y+10)
        # 添加画幅标记文字
        painter.drawText(-20, -rect_size//2 - 15, "Rot")
        painter.restore()

        # 计算实际夹角
        angle_diff = abs(self.rotator_angle - self.dec_angle) % 360
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        # 绘制夹角弧线和角度标记
        painter.save()
        painter.translate(center_x, center_y)
        
        # 确定起始角和跨度角
        start_angle = min(self.dec_angle, self.rotator_angle)
        end_angle = max(self.dec_angle, self.rotator_angle)
        
        # 确保选择最小的角弧
        if end_angle - start_angle > 180:
            start_angle, end_angle = end_angle, start_angle + 360
        
        # 绘制夹角弧线
        pen = QPen(QColor(0, 255, 0))  # 绿色
        pen.setWidth(2)
        painter.setPen(pen)
        radius = int(size * 0.2)  # 根据组件大小调整弧线半径
        
        # 转换角度到Qt坐标系（Qt中角度是顺时针的，从3点钟方向开始）
        qt_start_angle = (90 - start_angle) % 360 * 16  # 转换为1/16度单位
        qt_span_angle = -((end_angle - start_angle) % 360) * 16  # 负值表示逆时针
        
        painter.drawArc(-radius, -radius, radius*2, radius*2, int(qt_start_angle), int(qt_span_angle))
        
        # 在弧线中间绘制角度文本
        mid_angle = start_angle + (end_angle - start_angle) / 2
        mid_angle_rad = math.radians(mid_angle)
        text_radius = radius * 1.2
        text_x = math.cos(mid_angle_rad) * text_radius
        text_y = -math.sin(mid_angle_rad) * text_radius  # 注意y轴是向下的，所以需要取负
        
        painter.save()
        painter.translate(text_x, text_y)
        painter.rotate(-mid_angle)  # 旋转文本使其易读
        painter.drawText(-20, 0, f"{angle_diff:.1f}°")
        painter.restore()
        
        painter.restore() 