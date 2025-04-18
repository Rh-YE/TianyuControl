"""
主窗口模块
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QGroupBox, QLabel, QPushButton, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QImage, QPixmap
from src.ui.components import LabelPair, DeviceControl, InfoGroup, ThemeButton, AngleVisualizer
from src.utils.i18n import i18n
from src.utils.theme_manager import theme_manager
from src.services.astronomy_service import astronomy_service
from src.services.device_service import device_service
from src.services.dss_image_fetcher import DSSImageFetcher
from src.config.settings import TELESCOPE_CONFIG, DEVICES, LAYOUT_CONFIG
from utils import load_config
import os
import time

class MainWindow(QMainWindow):
    def __init__(self, telescope_devices=None):
        super().__init__()
        # 创建中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建DSS图像获取线程
        self.dss_fetcher = DSSImageFetcher()
        self.dss_fetcher.image_ready.connect(self.update_dss_image)
        
        self.init_ui(telescope_devices)
        self.init_timer()

    def init_ui(self, telescope_devices):
        """初始化UI"""
        self.setWindowTitle(i18n.get_text('telescope_monitor'))
        self.setGeometry(100, 100, 1920, 1080)

        # 创建菜单栏
        self.menubar = self.menuBar()
        
        # 创建设置菜单
        self.settings_menu = self.menubar.addMenu('设置')
        
        # 创建主题子菜单
        self.theme_menu = self.settings_menu.addMenu('主题')
        
        # 创建主题菜单项
        self.light_action = self.theme_menu.addAction('☀️ ' + i18n.get_text('light_mode'))
        self.dark_action = self.theme_menu.addAction('🌙 ' + i18n.get_text('dark_mode'))
        self.red_action = self.theme_menu.addAction('🔴 ' + i18n.get_text('red_mode'))
        
        # 设置菜单项为可勾选
        self.light_action.setCheckable(True)
        self.dark_action.setCheckable(True)
        self.red_action.setCheckable(True)
        
        # 默认选中日间模式
        self.light_action.setChecked(True)
        
        # 连接主题菜单项的信号
        self.light_action.triggered.connect(lambda: self.change_theme('light'))
        self.dark_action.triggered.connect(lambda: self.change_theme('dark'))
        self.red_action.triggered.connect(lambda: self.change_theme('red'))
        
        # 添加语言切换菜单项
        self.language_action = self.settings_menu.addAction(i18n.get_text('language'))
        self.language_action.triggered.connect(self.change_language)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(
            LAYOUT_CONFIG['window_margin'],
            LAYOUT_CONFIG['window_margin'],
            LAYOUT_CONFIG['window_margin'],
            LAYOUT_CONFIG['window_margin']
        )
        main_layout.setSpacing(LAYOUT_CONFIG['content_spacing'])

        content_layout = QHBoxLayout()
        content_layout.setSpacing(LAYOUT_CONFIG['section_spacing'])
        
        # 左侧栏
        left_layout = QVBoxLayout()
        left_layout.setSpacing(LAYOUT_CONFIG['group_spacing'])
        
        # 基本信息组
        self.basic_info = InfoGroup('basic_info')
        self.basic_info.layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        self.basic_info.add_item('aperture', TELESCOPE_CONFIG['aperture'])
        self.basic_info.add_item('fov', TELESCOPE_CONFIG['field_of_view'])
        self.basic_info.add_item('longitude', f"{TELESCOPE_CONFIG['longitude']}°")
        self.basic_info.add_item('latitude', f"{TELESCOPE_CONFIG['latitude']}°")
        self.basic_info.add_item('altitude_text', f"{TELESCOPE_CONFIG['altitude']}m")
        left_layout.addWidget(self.basic_info.get_widget())

        # 设备控制组件列表
        self.device_controls = []
        
        # 设备连接状态组
        self.device_group = InfoGroup('device_connection')
        self.device_group.layout.setSpacing(int(LAYOUT_CONFIG['group_spacing'] * 1.5))  # 增加设备控制组件之间的间距，确保是整数
        
        # 添加望远镜设备控制组件（新的带下拉菜单的版本）
        self.mount_control = DeviceControl('mount', i18n.get_text('mount'))
        if telescope_devices:  # 如果有设备列表，更新到下拉菜单
            self.mount_control.update_devices(telescope_devices)
        # 连接位置更新信号
        self.mount_control.signals.location_updated.connect(self.update_location_info)
        # 连接坐标更新信号
        self.mount_control.signals.coordinates_updated.connect(self.update_coordinates)
        # 连接状态更新信号
        self.mount_control.signals.status_updated.connect(self.update_telescope_status)
        # 连接设备列表更新信号
        self.mount_control.telescope_monitor.devices_updated.connect(self.mount_control.update_devices)
        self.device_group.layout.addLayout(self.mount_control.get_layout())
        self.device_controls.append(self.mount_control)
        
        # 添加其他设备控制组件
        other_devices = [
            ('focuser', 'focuser'),
            ('rotator', 'rotator'),
            ('weather', 'weather'),
            ('cover', 'cover'),
            ('dome', 'dome'),  # 圆顶设备
            ('cooler', 'cooler'),  # 新增水冷机设备
            ('ups', 'ups')  # 新增UPS电源设备
        ]
        for device_id, name in other_devices:
            device_control = DeviceControl(device_id, i18n.get_text(device_id))
            if device_id == 'focuser':
                # 连接电调焦状态更新信号
                device_control.telescope_monitor.focuser_updated.connect(self.update_focuser_status)
                # 连接设备列表更新信号
                device_control.telescope_monitor.devices_updated.connect(device_control.update_devices)
                # 如果有设备列表，更新到下拉菜单
                if telescope_devices:
                    device_control.update_devices(telescope_devices)
            elif device_id == 'rotator':
                # 连接消旋器状态更新信号
                device_control.telescope_monitor.rotator_updated.connect(self.update_rotator_status)
                # 连接设备列表更新信号
                device_control.telescope_monitor.devices_updated.connect(device_control.update_devices)
                # 如果有设备列表，更新到下拉菜单
                if telescope_devices:
                    device_control.update_devices(telescope_devices)
            elif device_id == 'weather':
                # 连接气象站数据更新信号
                if device_control.telescope_monitor:
                    device_control.telescope_monitor.weather_updated.connect(self.update_weather_info)
                    # 连接设备列表更新信号
                    device_control.telescope_monitor.devices_updated.connect(device_control.update_devices)
                    # 如果有设备列表，更新到下拉菜单
                    if telescope_devices:
                        device_control.update_devices(telescope_devices)
                    else:
                        # 如果没有设备列表，添加一个默认设备
                        default_devices = [{
                            'DeviceName': 'ASCOM Observing Conditions Simulator',
                            'DeviceType': 'ObservingConditions',
                            'DeviceNumber': 0,
                            'ApiVersion': '1.0'
                        }]
                        device_control.update_devices(default_devices)
            elif device_id == 'cover':
                # 连接镜头盖状态更新信号
                if device_control.telescope_monitor:
                    device_control.telescope_monitor.cover_updated.connect(self.update_cover_status)
                    # 连接设备列表更新信号
                    device_control.telescope_monitor.devices_updated.connect(device_control.update_devices)
                    # 如果有设备列表，更新到下拉菜单
                    if telescope_devices:
                        device_control.update_devices(telescope_devices)
                    else:
                        # 如果没有设备列表，添加一个默认设备
                        default_devices = [{
                            'DeviceName': 'ASCOM CoverCalibrator Simulator',
                            'DeviceType': 'CoverCalibrator',
                            'DeviceNumber': 0,
                            'ApiVersion': '1.0'
                        }]
                        device_control.update_devices(default_devices)
            elif device_id == 'dome':
                # 连接圆顶状态更新信号
                if device_control.telescope_monitor:
                    device_control.telescope_monitor.dome_updated.connect(self.update_dome_status)
                    # 连接设备列表更新信号
                    device_control.telescope_monitor.devices_updated.connect(device_control.update_devices)
                    # 如果有设备列表，更新到下拉菜单
                    if telescope_devices:
                        device_control.update_devices([d for d in telescope_devices if d.get('DeviceType') == 'Dome'])
                    else:
                        # 如果没有设备列表，添加一个默认设备
                        default_devices = [{
                            'DeviceName': 'ASCOM Dome Simulator',
                            'DeviceType': 'Dome',
                            'DeviceNumber': 0,
                            'ApiVersion': '1.0'
                        }]
                        device_control.update_devices(default_devices)
                    # 启动圆顶监控
                    device_control.telescope_monitor.start_dome_monitoring()
            elif device_id == 'cooler':
                # 特殊处理水冷机设备（使用串口连接）
                # 创建水冷机设备控制器（不使用 telescope_monitor）
                device_control.is_serial_device = True
                # 连接水冷机状态更新信号
                device_control.signals.status_updated.connect(self.update_cooler_status)
                # 获取可用串口列表并更新到下拉菜单
                self.update_serial_ports(device_control)
            elif device_id == 'ups':
                # 特殊处理UPS电源设备（使用串口连接）
                # 创建UPS电源设备控制器（不使用 telescope_monitor）
                device_control.is_serial_device = True
                # 连接UPS电源状态更新信号
                device_control.signals.status_updated.connect(self.update_ups_status)
                # 获取可用串口列表并更新到下拉菜单
                self.update_serial_ports(device_control)
            self.device_controls.append(device_control)
            self.device_group.layout.addLayout(device_control.get_layout())
        
        left_layout.addWidget(self.device_group.get_widget())

        # 中间栏
        middle_layout = QVBoxLayout()
        middle_layout.setSpacing(LAYOUT_CONFIG['section_spacing'])

        # 创建主内容区水平布局（左右两栏）
        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(LAYOUT_CONFIG['section_spacing'])
        
        # 左侧内容区（放置望远镜状态、圆顶状态和调焦器状态）
        left_content_layout = QVBoxLayout()
        left_content_layout.setSpacing(LAYOUT_CONFIG['section_spacing'])
        
        # 望远镜状态组
        self.telescope_status = InfoGroup('telescope_status')
        self.telescope_status.layout.setSpacing(LAYOUT_CONFIG['group_spacing'])
        self.telescope_status.add_item('ra', '12:00:00', 'large-text')
        self.telescope_status.add_item('dec', '+30:00:00', 'large-text')
        self.telescope_status.add_item('alt', '60°', 'medium-text')
        self.telescope_status.add_item('az', '120°', 'medium-text')
        self.telescope_status.add_item('telescope_state', i18n.get_text('status_unknown'), 'medium-text')
        self.telescope_status.add_item('motor_enable', i18n.get_text('motor_disabled'), 'medium-text')
        self.telescope_status.add_item('cover_status', i18n.get_text('cover_status_unknown'), 'medium-text')
        self.telescope_status.add_item('frame_dec_angle', '0.0°', 'medium-text')
        
        # 圆顶和调焦器状态水平布局
        dome_focuser_layout = QHBoxLayout()
        dome_focuser_layout.setSpacing(LAYOUT_CONFIG['widget_spacing'] * 2)  # 增加间距
        
        # 圆顶状态组
        self.dome_status_group = InfoGroup('dome_status')
        self.dome_status_group.layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        self.dome_status_group.add_item('dome_azimuth', '0.0°', 'medium-text')
        self.dome_status_group.add_item('dome_status', i18n.get_text('dome_status_unknown'), 'medium-text')
        
        # 调焦器状态组 - 增加宽度
        self.focuser_status = InfoGroup('focuser_status')
        self.focuser_status.layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        self.focuser_status.add_item('position', '34000/60000', 'medium-text')
        self.focuser_status.add_item('angle', '0.0°', 'medium-text')
        self.focuser_status.add_item('moving', i18n.get_text('moving_yes'))
        self.focuser_status.add_item('temperature', '-10.0°C', 'medium-text')
        
        # 设置最小宽度，确保文字显示完整
        focuser_widget = self.focuser_status.get_widget()
        focuser_widget.setMinimumWidth(220)  # 进一步增加最小宽度
        
        # 为调焦器状态框设置左右外边距，确保文字不被遮挡
        focuser_widget.setContentsMargins(10, 5, 10, 5)
        
        # 设置圆顶状态框的最小宽度
        dome_widget = self.dome_status_group.get_widget()
        dome_widget.setMinimumWidth(200)
        dome_widget.setContentsMargins(10, 5, 10, 5)
        
        # 添加圆顶和调焦器到水平布局，使用不同的比例
        dome_focuser_layout.addWidget(dome_widget, 1)  # 圆顶状态比例为1
        dome_focuser_layout.addWidget(focuser_widget, 1)  # 调焦器状态比例为1
        
        # 添加望远镜状态和圆顶/调焦器布局到左侧内容区
        left_content_layout.addWidget(self.telescope_status.get_widget())
        left_content_layout.addLayout(dome_focuser_layout)
        
        # 右侧内容区（放置水冷机和UPS电源状态）
        right_content_layout = QVBoxLayout()
        right_content_layout.setSpacing(LAYOUT_CONFIG['section_spacing'])
        
        # 水冷机状态组
        self.expanded_cooler_status_group = InfoGroup('cooler_status')
        self.expanded_cooler_status_group.layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        self.expanded_cooler_status_group.add_item('cooler_temperature', '--°C')
        self.expanded_cooler_status_group.add_item('cooler_running', i18n.get_text('indicator_off'))
        self.expanded_cooler_status_group.add_item('cooler_heating', i18n.get_text('indicator_off'))
        self.expanded_cooler_status_group.add_item('cooler_cooling', i18n.get_text('indicator_off'))
        self.expanded_cooler_status_group.add_item('cooler_flow_alarm', i18n.get_text('indicator_off'))
        self.expanded_cooler_status_group.add_item('cooler_pump', i18n.get_text('indicator_off'))
        self.expanded_cooler_status_group.add_item('cooler_temp_alarm', i18n.get_text('indicator_off'))
        self.expanded_cooler_status_group.add_item('cooler_level_alarm', i18n.get_text('indicator_off'))
        self.expanded_cooler_status_group.add_item('cooler_power', i18n.get_text('indicator_off'))
        
        # UPS状态组
        self.expanded_ups_status_group = InfoGroup('ups_status')
        self.expanded_ups_status_group.layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        self.expanded_ups_status_group.add_item('ups_status', i18n.get_text('ups_status_unknown'))
        self.expanded_ups_status_group.add_item('ups_input_voltage', '0.0V')
        self.expanded_ups_status_group.add_item('ups_output_voltage', '0.0V')
        self.expanded_ups_status_group.add_item('ups_battery', '0%')
        self.expanded_ups_status_group.add_item('ups_load', '0%')
        self.expanded_ups_status_group.add_item('ups_input_frequency', '0.0Hz')
        self.expanded_ups_status_group.add_item('ups_temperature', '0.0°C')
        
        # 添加UPS状态位
        self.expanded_ups_status_group.add_item('utility_status', i18n.get_text('ups_utility_normal'))
        self.expanded_ups_status_group.add_item('battery_status', i18n.get_text('ups_battery_normal'))
        self.expanded_ups_status_group.add_item('ups_health', i18n.get_text('ups_health_normal'))
        self.expanded_ups_status_group.add_item('selftest_status', i18n.get_text('ups_selftest_inactive'))
        self.expanded_ups_status_group.add_item('running_status', i18n.get_text('ups_running_normal'))
        
        # 添加水冷机和UPS状态到右侧内容区
        right_content_layout.addWidget(self.expanded_cooler_status_group.get_widget())
        right_content_layout.addWidget(self.expanded_ups_status_group.get_widget())
        
        # 将左右内容区添加到主内容区布局
        main_content_layout.addLayout(left_content_layout, 5)  # 左侧占更多空间
        main_content_layout.addLayout(right_content_layout, 4)  # 右侧占较少空间
        
        # 将主内容区布局添加到中间栏
        middle_layout.addLayout(main_content_layout)
        
        # 右侧栏
        right_layout = QVBoxLayout()
        right_layout.setSpacing(LAYOUT_CONFIG['section_spacing'])

        # 创建上部布局（两个框并排）
        top_right_layout = QHBoxLayout()
        top_right_layout.setSpacing(LAYOUT_CONFIG['section_spacing'])
        
        # 创建消旋器示意图框
        self.rotator_visualizer_group = InfoGroup('rotator_visualizer')
        self.rotator_visualizer_group.layout.setSpacing(LAYOUT_CONFIG['group_spacing'])
        
        # 添加DSS图像和角度可视化组件
        visualizer_layout = QVBoxLayout()  # 改为垂直布局
        
        # 角度可视化组件
        self.angle_visualizer = AngleVisualizer()
        self.angle_visualizer.setMinimumSize(200, 200)  # 设置最小尺寸
        visualizer_layout.addWidget(self.angle_visualizer)
        
        self.rotator_visualizer_group.layout.addLayout(visualizer_layout)
        
        # 望远镜监控相机组
        self.telescope_camera = InfoGroup('telescope_monitor_camera')
        self.telescope_camera.layout.setSpacing(LAYOUT_CONFIG['group_spacing'])
        self.telescope_camera_label = QLabel()
        self.telescope_camera_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.telescope_camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许标签扩展填充可用空间
        # 设置更大的最小尺寸，确保图片有足够显示空间
        self.telescope_camera_label.setMinimumSize(300, 300)
        self.telescope_camera.layout.addWidget(self.telescope_camera_label)
        
        # 加载全天相机图片
        self.update_telescope_camera_image()
        
        # 添加两个框到顶部布局（等宽）
        top_right_layout.addWidget(self.rotator_visualizer_group.get_widget(), 1)
        top_right_layout.addWidget(self.telescope_camera.get_widget(), 1)
        
        # 将顶部布局添加到右侧布局
        right_layout.addLayout(top_right_layout)

        # 环境监测组
        self.environment = InfoGroup('environment')
        self.environment.layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        self.environment.add_item('cloud_cover', '30%', 'medium-text')
        self.environment.add_item('dew_point', '-15.0°C', 'medium-text')
        self.environment.add_item('humidity', '50%', 'medium-text')
        self.environment.add_item('pressure', '1000hPa', 'medium-text')
        self.environment.add_item('rain', '10mm/h', 'medium-text')
        self.environment.add_item('sky_brightness', '10lux', 'medium-text')
        self.environment.add_item('sky_temperature', '-10.0°C', 'medium-text')
        self.environment.add_item('seeing', '0.5arcsec', 'medium-text')
        self.environment.add_item('air_temp', '-10.0°C', 'medium-text')
        self.environment.add_item('wind_direction', '70°', 'medium-text')
        self.environment.add_item('wind_speed', '10m/s', 'medium-text')
        self.environment.add_item('avg_wind_speed', '10m/s', 'medium-text')
        right_layout.addWidget(self.environment.get_widget())

        # 时间显示组
        self.time_group = InfoGroup('current_time')
        self.time_group.layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        self.time_group.add_item('utc8', '', 'medium-text')
        self.time_group.add_item('sunrise_sunset', '', 'medium-text')
        self.time_group.add_item('twilight', '', 'medium-text')
        self.time_group.add_item('moon_phase', '', 'medium-text')
        self.time_group.add_item('sun_altitude', '', 'medium-text')
        right_layout.addWidget(self.time_group.get_widget())

        # 将左侧栏添加到内容布局
        content_layout.addLayout(left_layout, 3)  # 左侧栏比例
        
        # 将中间栏和右侧栏添加到内容布局
        content_layout.addLayout(middle_layout, 6)  # 中间栏比例
        content_layout.addLayout(right_layout, 3)  # 右侧栏比例
        
        # 确保将内容布局添加到主布局
        main_layout.addLayout(content_layout)
        
        # 设置中央部件的布局
        self.central_widget.setLayout(main_layout)

        # 设置默认主题
        self.change_theme('light')

        # 连接设备监控线程信号
        if self.mount_control.telescope_monitor:
            self.mount_control.telescope_monitor.coordinates_updated.connect(self.update_coordinates)
            self.mount_control.telescope_monitor.status_updated.connect(self.update_telescope_status)
            self.mount_control.telescope_monitor.devices_updated.connect(self.mount_control.update_devices)
            
            # 连接气象站数据信号
            self.mount_control.telescope_monitor.weather_updated.connect(self.update_weather_info)
            
        # 创建一个定时器，用于强制更新水冷机状态
        self.cooler_refresh_timer = QTimer(self)
        self.cooler_refresh_timer.timeout.connect(self.force_refresh_cooler_status)
        self.cooler_refresh_timer.start(5000)  # 每5秒强制刷新一次

    def init_timer(self):
        """初始化定时器"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_info)
        self.timer.start(1000)  # 每秒更新
        
        # 初始化全天相机定时刷新
        self.telescope_camera_timer = QTimer(self)
        self.telescope_camera_timer.timeout.connect(self.update_telescope_camera_image)
        
        # 从配置中读取刷新间隔
        config = load_config()
        refresh_interval = config.get("devices", {}).get("allsky_camera", {}).get("refresh_interval", 5)
        self.telescope_camera_timer.start(refresh_interval * 1000)  # 转换为毫秒

    def change_theme(self, theme):
        """切换主题"""
        # 更新主题
        theme_manager.switch_theme(theme)
        self.setStyleSheet(theme_manager.get_theme_style())
        
        # 更新菜单项选中状态
        self.light_action.setChecked(theme == 'light')
        self.dark_action.setChecked(theme == 'dark')
        self.red_action.setChecked(theme == 'red')

    def change_language(self):
        """切换语言"""
        i18n.switch_language()
        self.update_all_texts()

    def update_all_texts(self):
        """更新所有文本"""
        # 更新窗口标题
        self.setWindowTitle(i18n.get_text('telescope_monitor'))

        # 更新菜单文本
        self.settings_menu.setTitle('设置' if i18n.get_current_language() == 'cn' else 'Settings')
        self.theme_menu.setTitle('主题' if i18n.get_current_language() == 'cn' else 'Theme')
        self.light_action.setText('☀️ ' + i18n.get_text('light_mode'))
        self.dark_action.setText('🌙 ' + i18n.get_text('dark_mode'))
        self.red_action.setText('🔴 ' + i18n.get_text('red_mode'))
        self.language_action.setText(i18n.get_text('language'))
        
        # 更新消旋器示意图组
        self.rotator_visualizer_group.update_text()
        
        # 更新望远镜状态组的动态值
        self.telescope_status.update_text()
        self.telescope_status.pairs['telescope_state'].set_value(i18n.get_text('status_unknown'))
        self.telescope_status.pairs['motor_enable'].set_value(i18n.get_text('motor_disabled'))
        self.telescope_status.pairs['cover_status'].set_value(i18n.get_text('cover_status_unknown'))
        
        # 更新圆顶状态组的动态值
        self.dome_status_group.update_text()
        self.dome_status_group.pairs['dome_azimuth'].set_value("--")
        self.dome_status_group.pairs['dome_status'].set_value(i18n.get_text('dome_status_unknown'))
        
        # 更新调焦器状态组的动态值
        self.focuser_status.update_text()
        self.focuser_status.pairs['moving'].set_value(i18n.get_text('moving_yes'))
        
        # 更新望远镜监控相机组的动态值
        self.telescope_camera.update_text()
        
        # 更新水冷机状态组的动态值
        self.expanded_cooler_status_group.update_text()
        
        # 更新UPS状态组的默认值
        self.expanded_ups_status_group.update_text()
        # 更新UPS状态的默认值
        self.expanded_ups_status_group.pairs['ups_status'].set_value(i18n.get_text('ups_status_unknown'))
        self.expanded_ups_status_group.pairs['ups_input_voltage'].set_value('0.0V')
        self.expanded_ups_status_group.pairs['ups_output_voltage'].set_value('0.0V')
        self.expanded_ups_status_group.pairs['ups_battery'].set_value('0%')
        self.expanded_ups_status_group.pairs['ups_load'].set_value('0%')
        self.expanded_ups_status_group.pairs['ups_input_frequency'].set_value('0.0Hz')
        self.expanded_ups_status_group.pairs['ups_temperature'].set_value('0.0°C')
        
        # 重置UPS状态位显示
        self.expanded_ups_status_group.pairs['utility_status'].set_value(i18n.get_text('ups_utility_normal'))
        self.expanded_ups_status_group.pairs['battery_status'].set_value(i18n.get_text('ups_battery_normal'))
        self.expanded_ups_status_group.pairs['ups_health'].set_value(i18n.get_text('ups_health_normal'))
        self.expanded_ups_status_group.pairs['selftest_status'].set_value(i18n.get_text('ups_selftest_inactive'))
        self.expanded_ups_status_group.pairs['running_status'].set_value(i18n.get_text('ups_running_normal'))
                
        # 更新环境监测组
        self.environment.update_text()
        
        # 更新时间显示组
        self.time_group.update_text()
        
        # 强制更新设备状态显示
        for device_control in self.device_controls:
            device_control.update_text()
            
            # 强制更新水冷机状态
            if hasattr(device_control, 'device_id') and device_control.device_id == 'cooler':
                if device_control.is_connected and hasattr(device_control, 'last_status') and device_control.last_status:
                    # 使用上次接收到的状态重新更新UI
                    print(f"强制更新水冷机状态: {device_control.last_status}")
                    self.update_cooler_status(device_control.last_status)

    def calculate_frame_dec_angle(self):
        """计算框架赤纬角度"""
        try:
            # 获取当前坐标
            ra_text = self.telescope_status.pairs['ra'].value_label.text()
            dec_text = self.telescope_status.pairs['dec'].value_label.text()
            
            # 转换坐标为度数
            ra_deg = astronomy_service._parse_time_format(ra_text)
            dec_deg = astronomy_service._parse_time_format(dec_text)
            
            # 只有当坐标变化超过阈值时才更新DSS图像
            if not hasattr(self, 'last_coords') or self.last_coords is None:
                self.last_coords = (ra_deg, dec_deg)
                self.dss_fetcher.set_coordinates(ra_text, dec_text)
            else:
                last_ra, last_dec = self.last_coords
                # 如果坐标变化超过0.5度才更新
                if abs(ra_deg - last_ra) > 0.5 or abs(dec_deg - last_dec) > 0.5:
                    self.last_coords = (ra_deg, dec_deg)
                    self.dss_fetcher.set_coordinates(ra_text, dec_text)
            
            # 获取当前消旋器角度
            rotator_angle = 0
            try:
                # 从调焦器状态组的angle字段获取消旋器角度
                angle_text = self.focuser_status.pairs['angle'].value_label.text()
                # 移除度数符号并转换为浮点数
                if angle_text and '°' in angle_text:
                    rotator_angle = float(angle_text.replace('°', ''))
            except (ValueError, KeyError) as e:
                print(f"获取消旋器角度失败: {e}")
            
            # 计算画幅与赤纬的夹角 (Parallactic angle)
            pa = astronomy_service.calculate_parallactic_angle(ra_text, dec_text, rotator_angle)
            if pa is None:
                pa = 0  # 计算失败时使用默认值
            
            self.frame_dec_angle = pa
            
            # 更新中间栏的角度显示
            self.telescope_status.pairs['frame_dec_angle'].set_value(f"{pa:.6f}°")
            
            # 更新角度可视化 - 用赤纬角度作为第一个参数，消旋器角度作为第二个参数
            self.angle_visualizer.set_angles(dec_deg, rotator_angle)
            
            print(f"已更新旁行角(PA): {pa:.6f}°, 赤纬: {dec_deg}°, 消旋器角度: {rotator_angle}°")
            
        except Exception as e:
            print(f"计算框架赤纬角度失败: {e}")
            import traceback
            traceback.print_exc()

    def update_dss_image(self, image_path):
        """更新DSS图像"""
        self.angle_visualizer.set_background(image_path)

    def update_time_info(self):
        """更新时间信息"""
        # 更新时间
        time_info = astronomy_service.get_current_time()
        self.time_group.pairs['utc8'].set_value(time_info['utc8'])
        
        # 更新太阳信息
        sun_info = astronomy_service.get_sun_info()
        self.time_group.pairs['sunrise_sunset'].set_value(
            f"{sun_info['sunrise']} / {sun_info['sunset']}"
        )
        self.time_group.pairs['sun_altitude'].set_value(sun_info['altitude'])

        # 更新晨昏信息
        twilight_info = astronomy_service.get_twilight_info()
        self.time_group.pairs['twilight'].set_value(
            f"{twilight_info['morning']} / {twilight_info['evening']}"
        )

        # 更新月相
        moon_phase = astronomy_service.calculate_moon_phase()
        self.time_group.pairs['moon_phase'].set_value(str(moon_phase))
        
        # 每30秒更新一次角度计算和星图
        if int(time.time()) % 30 == 0:
            self.calculate_frame_dec_angle() 

    def update_location_info(self, longitude, latitude, elevation):
        """更新位置信息"""
        self.basic_info.pairs['longitude'].set_value(f"{longitude:.6f}°")
        self.basic_info.pairs['latitude'].set_value(f"{latitude:.6f}°")
        self.basic_info.pairs['altitude_text'].set_value(f"{elevation:.1f}m")

    def update_coordinates(self, ra, dec, alt, az):
        """更新望远镜坐标信息"""
        # 将赤经转换为时分秒格式
        ra_h = int(ra)
        ra_m = int((ra - ra_h) * 60)
        ra_s = int(((ra - ra_h) * 60 - ra_m) * 60)
        ra_str = f"{ra_h:02d}:{ra_m:02d}:{ra_s:02d}"
        
        # 将赤纬转换为度分秒格式
        dec_sign = '+' if dec >= 0 else '-'
        dec_abs = abs(dec)
        dec_d = int(dec_abs)
        dec_m = int((dec_abs - dec_d) * 60)
        dec_s = int(((dec_abs - dec_d) * 60 - dec_m) * 60)
        dec_str = f"{dec_sign}{dec_d:02d}:{dec_m:02d}:{dec_s:02d}"
        
        # 更新界面显示
        self.telescope_status.pairs['ra'].set_value(ra_str)
        self.telescope_status.pairs['dec'].set_value(dec_str)
        self.telescope_status.pairs['alt'].set_value(f"{alt:.1f}°")
        self.telescope_status.pairs['az'].set_value(f"{az:.1f}°") 

    def update_telescope_status(self, status):
        """更新望远镜状态"""
        if not status:
            self.telescope_status.pairs['telescope_state'].set_value('Status Unknown')
            self.telescope_status.pairs['telescope_state'].value_label.setProperty('class', 'medium-text status-normal')
            self.telescope_status.pairs['motor_enable'].set_value(i18n.get_text('motor_disabled'))
            self.telescope_status.pairs['motor_enable'].value_label.setProperty('class', 'medium-text status-normal')
            return

        # 收集所有激活的状态
        active_states = []
        if status.get('slewing'):
            active_states.append('Slewing')
        if status.get('ispulseguiding'):
            active_states.append('Guiding')
        if status.get('tracking'):
            active_states.append('Tracking')
        if status.get('atpark'):
            active_states.append('AtPark')
        if status.get('athome'):
            active_states.append('AtHome')

        # 如果没有任何状态激活，显示未知状态
        if not active_states:
            self.telescope_status.pairs['telescope_state'].set_value('Status Unknown')
            self.telescope_status.pairs['telescope_state'].value_label.setProperty('class', 'medium-text status-normal')
            self.telescope_status.pairs['motor_enable'].set_value(i18n.get_text('motor_disabled'))
            self.telescope_status.pairs['motor_enable'].value_label.setProperty('class', 'medium-text status-normal')
            return

        # 根据状态设置样式类
        style_class = 'medium-text '  # 使用 medium-text 替代 status-text
        if 'Slewing' in active_states:
            style_class += 'status-warning'
        elif 'Guiding' in active_states or 'Tracking' in active_states:
            style_class += 'status-success'
        elif 'AtHome' in active_states or 'AtPark' in active_states:
            style_class += 'status-info'
        else:
            style_class += 'status-normal'

        # 更新状态显示
        self.telescope_status.pairs['telescope_state'].set_value(', '.join(active_states))
        self.telescope_status.pairs['telescope_state'].value_label.setProperty('class', style_class)
        self.telescope_status.pairs['telescope_state'].value_label.style().unpolish(self.telescope_status.pairs['telescope_state'].value_label)
        self.telescope_status.pairs['telescope_state'].value_label.style().polish(self.telescope_status.pairs['telescope_state'].value_label)
        
        # 更新电机使能状态
        # 如果望远镜在AtPark状态，则电机未使能；否则电机已使能
        is_enabled = not status.get('atpark', False)
        motor_status_text = i18n.get_text('motor_enabled') if is_enabled else i18n.get_text('motor_disabled')
        motor_style_class = 'medium-text ' + ('status-success' if is_enabled else 'status-info')
        
        self.telescope_status.pairs['motor_enable'].set_value(motor_status_text)
        self.telescope_status.pairs['motor_enable'].value_label.setProperty('class', motor_style_class)
        self.telescope_status.pairs['motor_enable'].value_label.style().unpolish(self.telescope_status.pairs['motor_enable'].value_label)
        self.telescope_status.pairs['motor_enable'].value_label.style().polish(self.telescope_status.pairs['motor_enable'].value_label)

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止DSS图像获取线程
        self.dss_fetcher.stop()
        self.dss_fetcher.wait()
        
        # 停止所有设备的监控线程
        for device_control in self.device_controls:
            if hasattr(device_control, 'telescope_monitor') and device_control.telescope_monitor:
                device_control.telescope_monitor.stop()
                device_control.telescope_monitor.wait()
        
        super().closeEvent(event) 

    def update_focuser_status(self, status):
        """更新电调焦状态显示"""
        # 更新位置
        self.focuser_status.pairs['position'].set_value(f"{status['position']}/{status['maxstep']}")
        
        # 更新温度
        self.focuser_status.pairs['temperature'].set_value(f"{status['temperature']:.2f}°C")
        
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
        # 更新调焦器状态组中的消旋器角度
        self.focuser_status.pairs['angle'].set_value(f"{status['position']:.2f}°")
        
        # 获取当前坐标用于计算PA
        try:
            ra_text = self.telescope_status.pairs['ra'].value_label.text()
            dec_text = self.telescope_status.pairs['dec'].value_label.text()
            
            # 计算画幅与赤纬的夹角 (Parallactic angle)
            pa = astronomy_service.calculate_parallactic_angle(ra_text, dec_text, status['position'])
            
            if pa is not None:
                # 将PA值更新到界面
                self.telescope_status.pairs['frame_dec_angle'].set_value(f"{pa:.6f}°")
                
                # 更新角度可视化
                dec_deg = astronomy_service._parse_time_format(dec_text)
                self.angle_visualizer.set_angles(dec_deg, status['position'])
                
                print(f"已更新旁行角(PA): {pa:.6f}°, 赤纬: {dec_deg}°, 消旋器角度: {status['position']}°")
            else:
                # 如果计算PA失败，只使用消旋器角度更新可视化
                self.angle_visualizer.set_angles(0, status['position'])
                print(f"消旋器角度更新(无法计算旁行角): 位置={status['position']}°")
        except Exception as e:
            # 如果出错，只使用消旋器角度更新可视化
            self.angle_visualizer.set_angles(0, status['position'])
            print(f"更新消旋器状态和旁行角计算时出错: {e}")

    def update_weather_info(self, weather_data):
        """更新气象站信息"""
        # 打印完整的气象站数据到控制台
        #print("\n气象站数据更新:")
        for key, value in weather_data.items():
            print(f"  {key}: {value}")
        
        # 更新环境监测组中的气象数据
        if 'cloudcover' in weather_data and weather_data['cloudcover'] is not None:
            self.environment.pairs['cloud_cover'].set_value(f"{weather_data['cloudcover']:.0f}%")
        else:
            self.environment.pairs['cloud_cover'].set_value("--")
        
        if 'dewpoint' in weather_data and weather_data['dewpoint'] is not None:
            self.environment.pairs['dew_point'].set_value(f"{weather_data['dewpoint']:.2f}°C")
        else:
            self.environment.pairs['dew_point'].set_value("--")
            
        if 'humidity' in weather_data and weather_data['humidity'] is not None:
            self.environment.pairs['humidity'].set_value(f"{weather_data['humidity']:.0f}%")
        else:
            self.environment.pairs['humidity'].set_value("--")
            
        if 'pressure' in weather_data and weather_data['pressure'] is not None:
            self.environment.pairs['pressure'].set_value(f"{weather_data['pressure']:.0f}hPa")
        else:
            self.environment.pairs['pressure'].set_value("--")
            
        if 'rainrate' in weather_data and weather_data['rainrate'] is not None:
            self.environment.pairs['rain'].set_value(f"{weather_data['rainrate']:.1f}mm/h")
        else:
            self.environment.pairs['rain'].set_value("--")
            
        if 'skybrightness' in weather_data and weather_data['skybrightness'] is not None:
            self.environment.pairs['sky_brightness'].set_value(f"{weather_data['skybrightness']:.1f}lux")
        else:
            self.environment.pairs['sky_brightness'].set_value("--")
            
        if 'skytemperature' in weather_data and weather_data['skytemperature'] is not None:
            self.environment.pairs['sky_temperature'].set_value(f"{weather_data['skytemperature']:.2f}°C")
        else:
            self.environment.pairs['sky_temperature'].set_value("--")
            
        if 'starfwhm' in weather_data and weather_data['starfwhm'] is not None:
            self.environment.pairs['seeing'].set_value(f"{weather_data['starfwhm']:.1f}arcsec")
        else:
            self.environment.pairs['seeing'].set_value("--")
            
        if 'temperature' in weather_data and weather_data['temperature'] is not None:
            self.environment.pairs['air_temp'].set_value(f"{weather_data['temperature']:.2f}°C")
        else:
            self.environment.pairs['air_temp'].set_value("--")
            
        if 'winddirection' in weather_data and weather_data['winddirection'] is not None:
            self.environment.pairs['wind_direction'].set_value(f"{weather_data['winddirection']:.0f}°")
        else:
            self.environment.pairs['wind_direction'].set_value("--")
            
        if 'windspeed' in weather_data and weather_data['windspeed'] is not None:
            self.environment.pairs['wind_speed'].set_value(f"{weather_data['windspeed']:.1f}m/s")
        else:
            self.environment.pairs['wind_speed'].set_value("--")
            
        if 'windgust' in weather_data and weather_data['windgust'] is not None:
            self.environment.pairs['avg_wind_speed'].set_value(f"{weather_data['windgust']:.1f}m/s")
        else:
            self.environment.pairs['avg_wind_speed'].set_value("--")

    def update_cover_status(self, status):
        """更新镜头盖状态显示"""
        if not status:
            self.telescope_status.pairs['cover_status'].set_value(i18n.get_text('cover_status_unknown'))
            self.telescope_status.pairs['cover_status'].value_label.setProperty('class', 'medium-text status-normal')
            return

        # 获取镜头盖状态的原始值
        raw_value = status.get('raw_value', 4)  # 默认为Unknown(4)
        
        # 如果状态没有变化，不更新UI
        if hasattr(self, '_last_cover_state') and self._last_cover_state == raw_value:
            return
            
        # 保存当前状态
        self._last_cover_state = raw_value
        
        # 设置状态文本和样式
        style_class = 'medium-text '
        if raw_value == 0:  # NotPresent
            status_text = i18n.get_text('cover_status_unknown')
            style_class += 'status-normal'
        elif raw_value == 1:  # Closed
            status_text = i18n.get_text('cover_status_closed')
            style_class += 'status-info'
        elif raw_value == 2:  # Moving
            status_text = i18n.get_text('cover_status_moving')
            style_class += 'status-warning'
        elif raw_value == 3:  # Open
            status_text = i18n.get_text('cover_status_open')
            style_class += 'status-success'
        elif raw_value == 5:  # Error
            status_text = i18n.get_text('cover_status_error')
            style_class += 'status-error'
        else:  # Unknown (4) or any other state
            status_text = i18n.get_text('cover_status_unknown')
            style_class += 'status-normal'

        # 更新状态显示
        self.telescope_status.pairs['cover_status'].set_value(status_text)
        self.telescope_status.pairs['cover_status'].value_label.setProperty('class', style_class)
        self.telescope_status.pairs['cover_status'].value_label.style().unpolish(self.telescope_status.pairs['cover_status'].value_label)
        self.telescope_status.pairs['cover_status'].value_label.style().polish(self.telescope_status.pairs['cover_status'].value_label)

    def update_dome_status(self, status):
        """更新圆顶状态显示"""
        if not status:
            # 如果没有状态数据，显示未知状态
            self.dome_status_group.pairs['dome_azimuth'].set_value("--")
            self.dome_status_group.pairs['dome_status'].set_value(i18n.get_text('dome_status_unknown'))
            self.dome_status_group.pairs['dome_status'].value_label.setProperty('class', 'medium-text status-normal')
            return

        # 更新圆顶方位角显示
        if 'azimuth' in status and status['azimuth'] is not None:
            try:
                azimuth = float(status['azimuth'])
                self.dome_status_group.pairs['dome_azimuth'].set_value(f"{azimuth:.2f}°")
            except (ValueError, TypeError):
                self.dome_status_group.pairs['dome_azimuth'].set_value("--")
        else:
            self.dome_status_group.pairs['dome_azimuth'].set_value("--")
            
        # 更新圆顶状态文本
        status_text = []
        style_class = 'medium-text '
        
        # 检查各种状态
        if status.get('athome'):
            status_text.append(i18n.get_text('dome_at_home'))
            style_class += 'status-info'
        if status.get('atpark'):
            status_text.append(i18n.get_text('dome_at_park'))
            style_class += 'status-info'
        if status.get('slewing'):
            status_text.append(i18n.get_text('dome_slewing'))
            style_class += 'status-warning'
            
        # 更新天窗状态
        shutter_status = status.get('shutter_status')
        if shutter_status is not None:
            if shutter_status == 0:  # shutterOpen
                status_text.append(i18n.get_text('dome_shutter_open'))
                if not style_class.endswith('status-warning'):
                    style_class += 'status-success'
            elif shutter_status == 1:  # shutterClosed
                status_text.append(i18n.get_text('dome_shutter_closed'))
                if not style_class.endswith('status-warning'):
                    style_class += 'status-info'
            elif shutter_status == 2:  # shutterOpening
                status_text.append(i18n.get_text('dome_shutter_opening'))
                style_class += 'status-warning'
            elif shutter_status == 3:  # shutterClosing
                status_text.append(i18n.get_text('dome_shutter_closing'))
                style_class += 'status-warning'
            elif shutter_status == 4:  # shutterError
                status_text.append(i18n.get_text('dome_shutter_error'))
                style_class += 'status-error'
                
        # 如果没有任何状态，显示未知状态
        if not status_text:
            status_text.append(i18n.get_text('dome_status_unknown'))
            style_class += 'status-normal'

        # 更新状态显示和样式
        self.dome_status_group.pairs['dome_status'].set_value(', '.join(status_text))
        self.dome_status_group.pairs['dome_status'].value_label.setProperty('class', style_class)
        self.dome_status_group.pairs['dome_status'].value_label.style().unpolish(self.dome_status_group.pairs['dome_status'].value_label)
        self.dome_status_group.pairs['dome_status'].value_label.style().polish(self.dome_status_group.pairs['dome_status'].value_label)

    def update_cooler_status(self, status):
        """更新水冷机状态显示"""
        if not status:
            print("水冷机状态更新：收到空状态")
            return
            
        print(f"水冷机状态更新接收：{status}")
            
        # 更新温度显示
        if 'temperature' in status and status['temperature'] is not None:
            try:
                # 检查是否为溢出值
                if status['temperature'] == float('inf'):  # 上溢出
                    self.expanded_cooler_status_group.pairs['cooler_temperature'].set_value(i18n.get_text("temperature_overflow"))
                elif status['temperature'] == float('-inf'):  # 下溢出
                    self.expanded_cooler_status_group.pairs['cooler_temperature'].set_value(i18n.get_text("temperature_underflow"))
                else:
                    temp = float(status['temperature'])  # 直接使用温度值，模块中已处理
                    self.expanded_cooler_status_group.pairs['cooler_temperature'].set_value(f"{temp:.2f}°C")
                    
                    # 根据温度值设置不同的样式
                    style_class = 'medium-text '
                    if temp > 30:
                        style_class += 'status-error'  # 温度过高，显示红色
                    elif temp < 10:
                        style_class += 'status-info'   # 温度较低，显示蓝色
                    else:
                        style_class += 'status-success'  # 温度正常，显示绿色
                        
                    self.expanded_cooler_status_group.pairs['cooler_temperature'].value_label.setProperty('class', style_class)
                    self.expanded_cooler_status_group.pairs['cooler_temperature'].value_label.style().unpolish(self.expanded_cooler_status_group.pairs['cooler_temperature'].value_label)
                    self.expanded_cooler_status_group.pairs['cooler_temperature'].value_label.style().polish(self.expanded_cooler_status_group.pairs['cooler_temperature'].value_label)
            except (ValueError, TypeError) as e:
                print(f"更新水冷机温度时出错: {e}")
                self.expanded_cooler_status_group.pairs['cooler_temperature'].set_value("--°C")
        
        # 更新状态指示灯显示
        try:
            # 从单独的状态字段获取而不是从原始状态位解析
            self.update_indicator('cooler_running', status.get('running', False), 'running')      # 运行指示灯
            self.update_indicator('cooler_heating', status.get('heating', False), 'heating')      # 加热指示灯
            self.update_indicator('cooler_cooling', status.get('cooling', False), 'cooling')      # 制冷指示灯
            self.update_indicator('cooler_flow_alarm', status.get('flow_alarm', False), 'flow')   # 流量报警
            self.update_indicator('cooler_pump', status.get('pump', False), 'pump')               # Pump循环
            self.update_indicator('cooler_temp_alarm', status.get('temp_alarm', False), 'temp')   # 温度报警
            self.update_indicator('cooler_level_alarm', status.get('level_alarm', False), 'level') # 液位报警
            self.update_indicator('cooler_power', status.get('power', False), 'power')            # 电源指示灯
            print("水冷机状态更新完成")
        except Exception as e:
            print(f"更新水冷机状态指示灯时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def update_indicator(self, indicator_key, bit_value, indicator_type):
        """更新指示灯状态"""
        # 设置指示灯显示文本
        if bit_value:
            # 根据指示灯类型设置不同的开启状态文本
            if indicator_type in ['flow', 'temp', 'level']:  # 报警类指示灯
                text = i18n.get_text('alarm_on')
                style = 'status-error'  # 报警状态使用红色
            else:  # 正常指示灯
                text = i18n.get_text('indicator_on')
                
                # 根据不同指示灯状态设置不同颜色
                if indicator_type == 'running':
                    style = 'status-success'  # 运行状态使用绿色
                elif indicator_type == 'heating':
                    style = 'status-warning'  # 加热状态使用黄色
                elif indicator_type == 'cooling':
                    style = 'status-info'     # 制冷状态使用蓝色
                elif indicator_type == 'pump':
                    style = 'status-success'  # 泵循环状态使用绿色
                elif indicator_type == 'power':
                    style = 'status-success'  # 电源指示灯使用绿色
                else:
                    style = 'status-normal'   # 其他状态使用默认颜色
        else:
            # 所有指示灯的关闭状态文本
            if indicator_type in ['flow', 'temp', 'level']:  # 报警类指示灯
                text = i18n.get_text('alarm_off')
            else:
                text = i18n.get_text('indicator_off')
            style = 'status-normal'  # 关闭状态使用灰色
        
        # 更新指示灯状态显示
        self.expanded_cooler_status_group.pairs[indicator_key].set_value(text)
        self.expanded_cooler_status_group.pairs[indicator_key].value_label.setProperty('class', f'medium-text {style}')
        self.expanded_cooler_status_group.pairs[indicator_key].value_label.style().unpolish(self.expanded_cooler_status_group.pairs[indicator_key].value_label)
        self.expanded_cooler_status_group.pairs[indicator_key].value_label.style().polish(self.expanded_cooler_status_group.pairs[indicator_key].value_label)
    
    def update_serial_ports(self, device_control):
        """更新可用串口列表"""
        try:
            import serial.tools.list_ports
            # 获取所有可用串口
            ports = [p.device for p in serial.tools.list_ports.comports()]
            
            if not ports:
                print("未找到可用串口设备")
                device_control.combo.clear()
                device_control.combo.addItem("无可用串口", None)
                return
                
            print(f"找到可用串口: {ports}")
            
            # 清空下拉菜单
            device_control.combo.clear()
            
            # 读取配置文件中上次使用的串口
            config = load_config()
            last_port = config.get("devices", {}).get("cooler", {}).get("port", "")
            
            # 填充下拉菜单
            index_to_select = 0
            for i, port in enumerate(ports):
                device_control.combo.addItem(port, port)
                # 如果找到上次使用的串口，选中它
                if port == last_port:
                    index_to_select = i
            
            # 选择上次使用的串口或第一个可用串口
            if device_control.combo.count() > 0:
                device_control.combo.setCurrentIndex(index_to_select)
                
        except ImportError:
            print("警告: 缺少PySerial库，无法列出串口设备")
            device_control.combo.clear()
            device_control.combo.addItem("请安装PySerial", None)

    def update_ups_status(self, status):
        """更新UPS状态显示"""
        if not status:
            self.expanded_ups_status_group.pairs['ups_status'].set_value(i18n.get_text('ups_status_unknown'))
            self.expanded_ups_status_group.pairs['ups_status'].value_label.setProperty('class', 'medium-text status-normal')
            self.expanded_ups_status_group.pairs['ups_input_voltage'].set_value('0.0V')
            self.expanded_ups_status_group.pairs['ups_output_voltage'].set_value('0.0V')
            self.expanded_ups_status_group.pairs['ups_battery'].set_value('0%')
            self.expanded_ups_status_group.pairs['ups_load'].set_value('0%')
            self.expanded_ups_status_group.pairs['ups_input_frequency'].set_value('0.0Hz')
            self.expanded_ups_status_group.pairs['ups_temperature'].set_value('0.0°C')
            
            # 重置UPS状态位显示
            self.expanded_ups_status_group.pairs['utility_status'].set_value(i18n.get_text('ups_utility_normal'))
            self.expanded_ups_status_group.pairs['battery_status'].set_value(i18n.get_text('ups_battery_normal'))
            self.expanded_ups_status_group.pairs['ups_health'].set_value(i18n.get_text('ups_health_normal'))
            self.expanded_ups_status_group.pairs['selftest_status'].set_value(i18n.get_text('ups_selftest_inactive'))
            self.expanded_ups_status_group.pairs['running_status'].set_value(i18n.get_text('ups_running_normal'))
            return

        # 获取UPS状态信息
        # UPS状态位 b0: 0=蜂鸣器关闭, 1=蜂鸣器打开
        #           b1: 0=正常运行状态, 1=正在关机或已关机
        #           b2: 0=非自检过程中, 1=正在自检
        #           b3: 0=在线式UPS, 1=后备式或互动式UPS
        #           b4: 0=UPS正常, 1=UPS有故障
        #           b5: 0=非旁路/电池工作模式, 1=旁路/正在升压或降压
        #           b6: 0=电池电压不低, 1=电池电压低
        #           b7: 0=市电正常, 1=市电失败
        status_text = status.get('status', '状态未知')
        input_voltage = status.get('input_voltage', 0.0)
        output_voltage = status.get('output_voltage', 0.0)
        battery = status.get('battery', 0)      # 电池电量
        load = status.get('load', 0)            # 负载
        input_frequency = status.get('input_frequency', 0.0)
        temperature = status.get('temperature', 0.0)
        
        # 确定状态样式和显示文本
        style_class = 'medium-text '
        if status_text == "市电正常":
            display_text = i18n.get_text('ups_status_normal')
            style_class += 'status-success'
        elif status_text == "电池供电":
            display_text = i18n.get_text('ups_status_battery')
            style_class += 'status-warning'
        elif status_text == "旁路供电":
            display_text = i18n.get_text('ups_status_bypass')
            style_class += 'status-info'
        elif status_text == "故障":
            display_text = i18n.get_text('ups_status_fault')
            style_class += 'status-error'
        else:  # 未知状态
            display_text = i18n.get_text('ups_status_unknown')
            style_class += 'status-normal'

        # 更新状态显示
        self.expanded_ups_status_group.pairs['ups_status'].set_value(display_text)
        self.expanded_ups_status_group.pairs['ups_status'].value_label.setProperty('class', style_class)
        self.expanded_ups_status_group.pairs['ups_status'].value_label.style().unpolish(self.expanded_ups_status_group.pairs['ups_status'].value_label)
        self.expanded_ups_status_group.pairs['ups_status'].value_label.style().polish(self.expanded_ups_status_group.pairs['ups_status'].value_label)
        
        # 更新电压、频率和温度显示
        self.expanded_ups_status_group.pairs['ups_input_voltage'].set_value(f"{input_voltage:.1f}V")
        self.expanded_ups_status_group.pairs['ups_output_voltage'].set_value(f"{output_voltage:.1f}V")
        self.expanded_ups_status_group.pairs['ups_battery'].set_value(f"{battery}%")
        self.expanded_ups_status_group.pairs['ups_load'].set_value(f"{load}%")
        self.expanded_ups_status_group.pairs['ups_input_frequency'].set_value(f"{input_frequency:.1f}Hz")
        self.expanded_ups_status_group.pairs['ups_temperature'].set_value(f"{temperature:.2f}°C")

        # 设置电池电量显示样式
        battery_style = 'medium-text '
        if battery <= 20:
            battery_style += 'status-error'  # 电量过低，显示红色
        elif battery <= 50:
            battery_style += 'status-warning'  # 电量较低，显示黄色
        else:
            battery_style += 'status-success'  # 电量正常，显示绿色
        
        self.expanded_ups_status_group.pairs['ups_battery'].value_label.setProperty('class', battery_style)
        self.expanded_ups_status_group.pairs['ups_battery'].value_label.style().unpolish(self.expanded_ups_status_group.pairs['ups_battery'].value_label)
        self.expanded_ups_status_group.pairs['ups_battery'].value_label.style().polish(self.expanded_ups_status_group.pairs['ups_battery'].value_label)

        # 设置负载显示样式
        load_style = 'medium-text '
        if load >= 90:
            load_style += 'status-error'  # 负载过高，显示红色
        elif load >= 70:
            load_style += 'status-warning'  # 负载较高，显示黄色
        else:
            load_style += 'status-success'  # 负载正常，显示绿色
        
        self.expanded_ups_status_group.pairs['ups_load'].value_label.setProperty('class', load_style)
        self.expanded_ups_status_group.pairs['ups_load'].value_label.style().unpolish(self.expanded_ups_status_group.pairs['ups_load'].value_label)
        self.expanded_ups_status_group.pairs['ups_load'].value_label.style().polish(self.expanded_ups_status_group.pairs['ups_load'].value_label)
        
        # 更新UPS状态位显示
        if 'status_bits' in status and len(status['status_bits']) >= 8:
            status_bits = status['status_bits']
            
            # 更新各状态位显示
            self.update_ups_status_bit('utility_status', status_bits[0], 'status-error' if status_bits[0] == 1 else 'status-success')
            self.update_ups_status_bit('battery_status', status_bits[1], 'status-error' if status_bits[1] == 1 else 'status-success')
            self.update_ups_status_bit('ups_health', status_bits[3], 'status-error' if status_bits[3] == 1 else 'status-success')
            self.update_ups_status_bit('selftest_status', status_bits[5], 'status-info' if status_bits[5] == 1 else 'status-success')
            self.update_ups_status_bit('running_status', status_bits[6], 'status-error' if status_bits[6] == 1 else 'status-success')

    def update_ups_status_bit(self, key, bit_value, style_class):
        """更新UPS状态位显示"""
        if key not in self.expanded_ups_status_group.pairs:
            return
            
        # 根据不同状态位设置显示文本
        if key == 'utility_status':
            text = i18n.get_text('ups_utility_fail') if bit_value == 1 else i18n.get_text('ups_utility_normal')
        elif key == 'battery_status':
            text = i18n.get_text('ups_battery_low') if bit_value == 1 else i18n.get_text('ups_battery_normal')
        elif key == 'ups_health':
            text = i18n.get_text('ups_health_fault') if bit_value == 1 else i18n.get_text('ups_health_normal')
        elif key == 'selftest_status':
            text = i18n.get_text('ups_selftest_active') if bit_value == 1 else i18n.get_text('ups_selftest_inactive')
        elif key == 'running_status':
            text = i18n.get_text('ups_running_shutdown') if bit_value == 1 else i18n.get_text('ups_running_normal')
        else:
            text = f"{bit_value}"
            
        # 更新显示文本
        self.expanded_ups_status_group.pairs[key].set_value(text)
        
        # 更新样式
        self.expanded_ups_status_group.pairs[key].value_label.setProperty('class', f'medium-text {style_class}')
        self.expanded_ups_status_group.pairs[key].value_label.style().unpolish(self.expanded_ups_status_group.pairs[key].value_label)
        self.expanded_ups_status_group.pairs[key].value_label.style().polish(self.expanded_ups_status_group.pairs[key].value_label)

    def force_refresh_cooler_status(self):
        """强制刷新水冷机状态"""
        for device_control in self.device_controls:
            if hasattr(device_control, 'device_id') and device_control.device_id == 'cooler':
                if device_control.is_connected and hasattr(device_control, 'last_status') and device_control.last_status:
                    # 如果已连接且有状态数据，强制更新UI
                    print(f"强制刷新水冷机状态: {device_control.last_status}")
                    self.update_cooler_status(device_control.last_status)

    def update_telescope_camera_image(self):
        """更新望远镜监控相机（全天相机）图片"""
        try:
            # 从配置中获取全天相机配置
            config = load_config()
            allsky_config = config.get("devices", {}).get("allsky_camera", {})
            
            if not allsky_config.get("enabled", False):
                print("全天相机功能已禁用")
                return
                
            # 获取图片路径
            image_path = allsky_config.get("image_path", "")
            image_name = allsky_config.get("image_name", "test001")
            image_ext = allsky_config.get("image_extension", ".png")
            
            # 构建完整的图片路径
            full_image_path = os.path.join(image_path, image_name + image_ext)
            
            # 检查文件是否存在
            if not os.path.exists(full_image_path):
                print(f"全天相机图片不存在: {full_image_path}")
                return
                
            # 加载图片
            original_pixmap = QPixmap(full_image_path)
            if original_pixmap.isNull():
                print(f"无法加载全天相机图片: {full_image_path}")
                return
                
            # 获取原始图片尺寸
            orig_width = original_pixmap.width()
            orig_height = original_pixmap.height()
            
            # 获取容器尺寸
            container = self.telescope_camera.get_widget()
            container_width = container.width() - 20  # 减去边距
            container_height = container.height() - 40  # 减去标题和边距
            
            # 如果容器尺寸不可用，使用标签尺寸
            if container_width <= 10 or container_height <= 10:
                container_width = self.telescope_camera_label.width()
                container_height = self.telescope_camera_label.height()
            
            # 如果尺寸仍不可用，使用默认尺寸
            if container_width <= 10 or container_height <= 10:
                container_width = 260
                container_height = 260
            
            # 计算缩放比例
            width_ratio = container_width / orig_width
            height_ratio = container_height / orig_height
            
            # 使用较小的比例来确保图片完全显示
            scale_ratio = min(width_ratio, height_ratio)
            
            # 计算新尺寸
            new_width = int(orig_width * scale_ratio)
            new_height = int(orig_height * scale_ratio)
            
            # 缩放图片
            scaled_pixmap = original_pixmap.scaled(
                new_width, 
                new_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # 将图像设置到标签
            self.telescope_camera_label.setPixmap(scaled_pixmap)
            
            print(f"望远镜监控相机图片已更新: {full_image_path}")
            print(f"容器尺寸: {container_width}x{container_height}, 图像尺寸: {new_width}x{new_height}, 缩放比例: {scale_ratio:.2f}")
            
        except Exception as e:
            print(f"更新望远镜监控相机图片失败: {e}")
            import traceback
            traceback.print_exc()
            
    def resizeEvent(self, event):
        """窗口大小改变事件处理"""
        super().resizeEvent(event)
        # 使用单次计时器延迟更新，确保在布局调整完成后更新图像
        QTimer.singleShot(100, self.update_telescope_camera_image)