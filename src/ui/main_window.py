"""
主窗口模块
"""
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel
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

        # 主题切换按钮布局
        theme_layout = QHBoxLayout()
        theme_layout.setContentsMargins(
            0, 0, 0, LAYOUT_CONFIG['header_margin']
        )
        theme_layout.addStretch()

        # 语言切换按钮
        self.lang_btn = ThemeButton(i18n.get_text('language')).get_widget()
        self.lang_btn.setFixedSize(60, 32)  # 设置固定大小
        self.lang_btn.clicked.connect(self.change_language)
        theme_layout.addWidget(self.lang_btn)

        # 主题切换按钮
        self.light_btn = ThemeButton(i18n.get_text('light_mode'), '☀️').get_widget()
        self.dark_btn = ThemeButton(i18n.get_text('dark_mode'), '🌙').get_widget()
        self.red_btn = ThemeButton(i18n.get_text('red_mode'), '🔴').get_widget()

        for btn, theme in [(self.light_btn, 'light'),
                          (self.dark_btn, 'dark'),
                          (self.red_btn, 'red')]:
            btn.setFixedSize(80, 32)  # 设置固定大小
            btn.clicked.connect(lambda checked, t=theme: self.change_theme(t))
            theme_layout.addWidget(btn)

        theme_layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        main_layout.addLayout(theme_layout)
        main_layout.addLayout(content_layout)

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
        self.device_group.layout.setSpacing(LAYOUT_CONFIG['group_spacing'])
        
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
            ('cooler', 'cooler')  # 新增水冷机设备
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
            self.device_controls.append(device_control)
            self.device_group.layout.addLayout(device_control.get_layout())
        
        left_layout.addWidget(self.device_group.get_widget())

        # 中间栏
        middle_layout = QVBoxLayout()
        middle_layout.setSpacing(LAYOUT_CONFIG['section_spacing'])

        # 望远镜状态组 (原消旋器角度组去掉)
        self.telescope_status = InfoGroup('telescope_status')
        self.telescope_status.layout.setSpacing(LAYOUT_CONFIG['group_spacing'])
        self.telescope_status.add_item('ra', '12:00:00', 'large-text')
        self.telescope_status.add_item('dec', '+30:00:00', 'large-text')
        self.telescope_status.add_item('alt', '60°', 'medium-text')
        self.telescope_status.add_item('az', '120°', 'medium-text')
        self.telescope_status.add_item('status', i18n.get_text('status_unknown'), 'medium-text')
        self.telescope_status.add_item('cover_status', i18n.get_text('cover_status_unknown'), 'medium-text')  # 添加镜头盖状态显示
        # 添加画幅与赤纬夹角数据
        self.telescope_status.add_item('frame_dec_angle', '0.0°', 'medium-text')  # 修改为medium-text
        middle_layout.addWidget(self.telescope_status.get_widget())

        # 圆顶状态组（原相机设置组）
        self.dome_status_group = InfoGroup('dome_status')
        self.dome_status_group.layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        self.dome_status_group.add_item('dome_azimuth', '0.0°', 'medium-text')  # 添加圆顶方位显示
        self.dome_status_group.add_item('dome_status', i18n.get_text('dome_status_unknown'), 'medium-text')  # 添加圆顶状态显示
        middle_layout.addWidget(self.dome_status_group.get_widget())

        # 调焦器状态组
        self.focuser_status = InfoGroup('focuser_status')
        self.focuser_status.layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        self.focuser_status.add_item('position', '34000/60000', 'medium-text')
        self.focuser_status.add_item('angle', '0.0°', 'medium-text')
        self.focuser_status.add_item('moving', i18n.get_text('moving_yes'))
        self.focuser_status.add_item('temperature', '-10.0°C', 'medium-text')
        self.focuser_status.add_item('last_focus', '2025-02-23 12:00:00')
        middle_layout.addWidget(self.focuser_status.get_widget())
        
        # 水冷机状态组
        self.cooler_status_group = InfoGroup('cooler_status')
        self.cooler_status_group.layout.setSpacing(LAYOUT_CONFIG['widget_spacing'])
        self.cooler_status_group.add_item('cooler_temperature', '--°C', 'medium-text')  # 水冷机温度显示，改为medium-text
        self.cooler_status_group.add_item('cooler_running', i18n.get_text('indicator_off'), 'medium-text')  # 运行指示灯
        self.cooler_status_group.add_item('cooler_heating', i18n.get_text('indicator_off'), 'medium-text')  # 加热指示灯
        self.cooler_status_group.add_item('cooler_cooling', i18n.get_text('indicator_off'), 'medium-text')  # 制冷指示灯
        self.cooler_status_group.add_item('cooler_flow_alarm', i18n.get_text('indicator_off'), 'medium-text')  # 流量报警
        self.cooler_status_group.add_item('cooler_pump', i18n.get_text('indicator_off'), 'medium-text')  # Pump循环指示灯
        self.cooler_status_group.add_item('cooler_temp_alarm', i18n.get_text('indicator_off'), 'medium-text')  # 温度报警
        self.cooler_status_group.add_item('cooler_level_alarm', i18n.get_text('indicator_off'), 'medium-text')  # 液位报警
        self.cooler_status_group.add_item('cooler_power', i18n.get_text('indicator_off'), 'medium-text')  # 电源指示灯
        middle_layout.addWidget(self.cooler_status_group.get_widget())

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
        camera_label = QLabel()
        camera_label.setText('<img src="C:/Users/90811/Downloads/cutout2.jpg"/>')
        camera_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.telescope_camera.layout.addWidget(camera_label)
        
        # 添加提示文本标签
        camera_tip_label = QLabel(i18n.get_text('telescope_camera_tip'))
        camera_tip_label.setProperty('class', 'small-text')
        camera_tip_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        camera_tip_label.setWordWrap(True)  # 允许文本换行
        self.telescope_camera.layout.addWidget(camera_tip_label)
        self.telescope_camera_tip_label = camera_tip_label
        
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

        # 设置布局比例
        content_layout.addLayout(left_layout, 2)    # 增加左侧栏比例
        content_layout.addLayout(middle_layout, 5)  # 减小中间栏比例
        content_layout.addLayout(right_layout, 3)   # 增加右侧栏比例

        # 设置中心部件的布局
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

    def init_timer(self):
        """初始化定时器"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_info)
        self.timer.start(1000)  # 每秒更新

    def change_theme(self, theme):
        """切换主题"""
        theme_manager.switch_theme(theme)
        self.setStyleSheet(theme_manager.get_theme_style())

    def change_language(self):
        """切换语言"""
        i18n.switch_language()
        self.update_all_texts()

        # 强制更新水冷机状态显示
        for device_control in self.device_controls:
            if hasattr(device_control, 'device_id') and device_control.device_id == 'cooler':
                if device_control.is_connected and hasattr(device_control, 'last_status') and device_control.last_status:
                    # 使用上次接收到的状态重新更新UI
                    self.update_cooler_status(device_control.last_status)

    def update_all_texts(self):
        """更新所有文本"""
        # 更新窗口标题
        self.setWindowTitle(i18n.get_text('telescope_monitor'))

        # 更新按钮文本
        self.lang_btn.setText(i18n.get_text('language'))
        self.light_btn.setText(f"☀️ {i18n.get_text('light_mode')}")
        self.dark_btn.setText(f"🌙 {i18n.get_text('dark_mode')}")
        self.red_btn.setText(f"🔴 {i18n.get_text('red_mode')}")

        # 更新所有组件的文本
        self.basic_info.update_text()
        self.device_group.update_text()
        
        # 更新消旋器示意图组
        self.rotator_visualizer_group.update_text()
        
        # 更新望远镜状态组的动态值
        self.telescope_status.update_text()
        self.telescope_status.pairs['status'].set_value(i18n.get_text('status_unknown'))
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
        self.telescope_camera_tip_label.setText(i18n.get_text('telescope_camera_tip'))
        
        # 更新水冷机状态组的文本
        self.cooler_status_group.update_text()
        # 更新水冷机各个指示灯的默认状态文本
        self.cooler_status_group.pairs['cooler_running'].set_value(i18n.get_text('indicator_off'))
        self.cooler_status_group.pairs['cooler_heating'].set_value(i18n.get_text('indicator_off'))
        self.cooler_status_group.pairs['cooler_cooling'].set_value(i18n.get_text('indicator_off'))
        self.cooler_status_group.pairs['cooler_flow_alarm'].set_value(i18n.get_text('alarm_off'))
        self.cooler_status_group.pairs['cooler_pump'].set_value(i18n.get_text('indicator_off'))
        self.cooler_status_group.pairs['cooler_temp_alarm'].set_value(i18n.get_text('alarm_off'))
        self.cooler_status_group.pairs['cooler_level_alarm'].set_value(i18n.get_text('alarm_off'))
        self.cooler_status_group.pairs['cooler_power'].set_value(i18n.get_text('indicator_off'))
        
        self.environment.update_text()
        self.time_group.update_text()

        # 更新设备控制组件
        for device_control in self.device_controls:
            device_control.update_text()

        # 更新时间信息
        self.update_time_info()

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
            
            # 计算框架赤纬角度
            frame_dec_angle = dec_deg
            self.frame_dec_angle = frame_dec_angle
            
            # 更新中间栏的角度显示
            self.telescope_status.pairs['frame_dec_angle'].set_value(f"{frame_dec_angle:.6f}°")
            
            # 更新角度可视化
            self.angle_visualizer.set_angles(0, frame_dec_angle)  # 使用0度作为赤纬参考线
            
        except Exception as e:
            print(f"计算框架赤纬角度失败: {e}")

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
            self.telescope_status.pairs['status'].set_value('Status Unknown')
            self.telescope_status.pairs['status'].value_label.setProperty('class', 'medium-text status-normal')
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
            self.telescope_status.pairs['status'].set_value('Status Unknown')
            self.telescope_status.pairs['status'].value_label.setProperty('class', 'medium-text status-normal')
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
        self.telescope_status.pairs['status'].set_value(', '.join(active_states))
        self.telescope_status.pairs['status'].value_label.setProperty('class', style_class)
        self.telescope_status.pairs['status'].value_label.style().unpolish(self.telescope_status.pairs['status'].value_label)
        self.telescope_status.pairs['status'].value_label.style().polish(self.telescope_status.pairs['status'].value_label)

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
        self.focuser_status.pairs['temperature'].set_value(f"{status['temperature']:.1f}°C")
        
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
        self.focuser_status.pairs['angle'].set_value(f"{status['position']:.1f}°")
        
        # 更新角度可视化
        self.angle_visualizer.set_angles(0, status['position'])

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
            self.environment.pairs['dew_point'].set_value(f"{weather_data['dewpoint']:.1f}°C")
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
            self.environment.pairs['sky_temperature'].set_value(f"{weather_data['skytemperature']:.1f}°C")
        else:
            self.environment.pairs['sky_temperature'].set_value("--")
            
        if 'starfwhm' in weather_data and weather_data['starfwhm'] is not None:
            self.environment.pairs['seeing'].set_value(f"{weather_data['starfwhm']:.1f}arcsec")
        else:
            self.environment.pairs['seeing'].set_value("--")
            
        if 'temperature' in weather_data and weather_data['temperature'] is not None:
            self.environment.pairs['air_temp'].set_value(f"{weather_data['temperature']:.1f}°C")
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
                self.dome_status_group.pairs['dome_azimuth'].set_value(f"{azimuth:.1f}°")
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
            return
            
        # 更新温度显示
        if 'temperature' in status and status['temperature'] is not None:
            try:
                # 检查是否为溢出值
                if status['temperature'] == 0x7FFF:  # 上溢出
                    self.cooler_status_group.pairs['cooler_temperature'].set_value(i18n.get_text("temperature_overflow"))
                elif status['temperature'] == 0x8001:  # 下溢出
                    self.cooler_status_group.pairs['cooler_temperature'].set_value(i18n.get_text("temperature_underflow"))
                else:
                    temp = float(status['temperature']) / 10.0  # 假设温度需要除以10显示
                    self.cooler_status_group.pairs['cooler_temperature'].set_value(f"{temp:.1f}°C")
                    
                    # 根据温度值设置不同的样式
                    style_class = 'medium-text '
                    if temp > 30:
                        style_class += 'status-error'  # 温度过高，显示红色
                    elif temp < 10:
                        style_class += 'status-info'   # 温度较低，显示蓝色
                    else:
                        style_class += 'status-success'  # 温度正常，显示绿色
                        
                    self.cooler_status_group.pairs['cooler_temperature'].value_label.setProperty('class', style_class)
                    self.cooler_status_group.pairs['cooler_temperature'].value_label.style().unpolish(self.cooler_status_group.pairs['cooler_temperature'].value_label)
                    self.cooler_status_group.pairs['cooler_temperature'].value_label.style().polish(self.cooler_status_group.pairs['cooler_temperature'].value_label)
            except (ValueError, TypeError):
                self.cooler_status_group.pairs['cooler_temperature'].set_value("--°C")
        
        # 更新状态指示灯显示
        if 'status_bits' in status and status['status_bits'] is not None:
            status_bits = status['status_bits']
            
            # 更新各个指示灯状态
            self.update_indicator('cooler_running', status_bits & 0x80, 'running')      # bit7 运行指示灯
            self.update_indicator('cooler_heating', status_bits & 0x40, 'heating')      # bit6 加热指示灯
            self.update_indicator('cooler_cooling', status_bits & 0x20, 'cooling')      # bit5 制冷指示灯
            self.update_indicator('cooler_flow_alarm', status_bits & 0x10, 'flow')      # bit4 流量报警
            self.update_indicator('cooler_pump', status_bits & 0x08, 'pump')            # bit3 Pump循环
            self.update_indicator('cooler_temp_alarm', status_bits & 0x04, 'temp')      # bit2 温度报警
            self.update_indicator('cooler_level_alarm', status_bits & 0x02, 'level')    # bit1 液位报警
            self.update_indicator('cooler_power', status_bits & 0x01, 'power')          # bit0 电源指示灯
    
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
        self.cooler_status_group.pairs[indicator_key].set_value(text)
        self.cooler_status_group.pairs[indicator_key].value_label.setProperty('class', f'medium-text {style}')
        self.cooler_status_group.pairs[indicator_key].value_label.style().unpolish(self.cooler_status_group.pairs[indicator_key].value_label)
        self.cooler_status_group.pairs[indicator_key].value_label.style().polish(self.cooler_status_group.pairs[indicator_key].value_label)
    
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