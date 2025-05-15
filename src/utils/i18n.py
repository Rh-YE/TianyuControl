"""
国际化支持模块
"""

class I18nManager:
    def __init__(self):
        self.current_language = 'cn'
        self.translations = {
            'telescope_monitor': {'cn': '天语望远镜总监控视', 'en': 'Tianyu Telescope Monitor'},
            'basic_info': {'cn': '基本信息', 'en': 'Basic Info'},
            'rotator_angle_group': {'cn': '消旋器角度', 'en': 'Rotator Angle'},
            'frame_dec_angle': {'cn': '旁行角', 'en': 'Parallactic Angle'},
            'current_angle': {'cn': '当前角度', 'en': 'Current Angle'},
            'telescope_status': {'cn': '望远镜状态', 'en': 'Telescope Status'},
            'camera_settings': {'cn': '相机设置', 'en': 'Camera Settings'},
            'focuser_status': {'cn': '调焦器状态', 'en': 'Focuser Status'},
            'all_sky_camera': {'cn': '望远镜监控相机', 'en': 'Telescope Monitor Camera'},
            'environment': {'cn': '环境监测', 'en': 'Environment'},
            'current_time': {'cn': '当前时间', 'en': 'Current Time'},
            'light_mode': {'cn': '日间', 'en': 'Light'},
            'dark_mode': {'cn': '夜间', 'en': 'Dark'},
            'red_mode': {'cn': '红光', 'en': 'Red'},
            'language': {'cn': '中文', 'en': 'EN'},
            'device_connection': {'cn': '设备连接状态', 'en': 'Device Connection'},
            'mount': {'cn': '赤道仪', 'en': 'Mount'},
            'focuser': {'cn': '电调焦', 'en': 'Focuser'},
            'rotator': {'cn': '消旋器', 'en': 'Rotator'},
            'rotator_visualizer': {'cn': '旁行角模拟', 'en': 'Parallactic Angle Visualizer'},
            'telescope_monitor_camera': {'cn': '望远镜监控相机', 'en': 'Telescope Monitor Camera'},
            'weather': {'cn': '气象站', 'en': 'Weather Station'},
            'dome': {'cn': '圆顶', 'en': 'Dome'},
            'dome_altitude': {'cn': '圆顶高度', 'en': 'Altitude'},
            'dome_azimuth': {'cn': '圆顶方位', 'en': 'Azimuth'},
            'dome_status': {'cn': '圆顶状态', 'en': 'Status'},
            'dome_status_unknown': {'cn': '状态未知', 'en': 'Unknown'},
            'dome_at_home': {'cn': '圆顶在原位', 'en': 'AtHome'},
            'dome_at_park': {'cn': '圆顶已停泊', 'en': 'Parked'},
            'dome_slewing': {'cn': '圆顶转动中', 'en': 'Slewing'},
            'dome_shutter_closed': {'cn': '天窗已关闭', 'en': 'Shutter Closed'},
            'dome_shutter_opening': {'cn': '天窗打开中', 'en': 'Shutter Opening'},
            'dome_shutter_open': {'cn': '天窗已打开', 'en': 'Shutter Open'},
            'dome_shutter_closing': {'cn': '天窗关闭中', 'en': 'Shutter Closing'},
            'dome_shutter_error': {'cn': '天窗错误', 'en': 'Shutter Error'},
            'camera_temp': {'cn': '相机温度', 'en': 'Camera Temperature'},
            'readout_mode': {'cn': '读出模式', 'en': 'Readout Mode'},
            'filter_position': {'cn': '滤光片位置', 'en': 'Filter Position'},
            'position': {'cn': '当前位置', 'en': 'Current Position'},
            'angle': {'cn': '消旋器角度', 'en': 'Rotator Angle'},
            'moving': {'cn': '是否移动', 'en': 'Is Moving'},
            'temperature': {'cn': '温度', 'en': 'Temperature'},
            'cloud_cover': {'cn': '红外云量', 'en': 'Cloud Cover'},
            'dew_point': {'cn': '露点', 'en': 'Dew Point'},
            'humidity': {'cn': '湿度', 'en': 'Humidity'},
            'pressure': {'cn': '气压', 'en': 'Pressure'},
            'rain': {'cn': '雨量', 'en': 'Precipitation'},
            'sky_brightness': {'cn': '天空亮度', 'en': 'Sky Brightness'},
            'sky_temperature': {'cn': '天空温度', 'en': 'Sky Temperature'},
            'seeing': {'cn': '视宁度', 'en': 'Seeing'},
            'air_temp': {'cn': '气温', 'en': 'Air Temperature'},
            'wind_direction': {'cn': '风向', 'en': 'Wind Direction'},
            'wind_speed': {'cn': '瞬时风速', 'en': 'Wind Speed'},
            'avg_wind_speed': {'cn': '5分钟平均风速', 'en': '5-min Avg Wind Speed'},
            'fullscreen': {'cn': '全屏显示', 'en': 'Fullscreen'},
            'status': {'cn': '状态', 'en': 'Status'},
            'telescope_state': {'cn': '望远镜状态', 'en': 'Telescope State'},
            'running': {'cn': '运行中', 'en': 'Running'},
            'ra': {'cn': '赤经', 'en': 'RA'},
            'dec': {'cn': '赤纬', 'en': 'Dec'},
            'alt': {'cn': '高度角', 'en': 'Altitude'},
            'az': {'cn': '方位角', 'en': 'Azimuth'},
            'aperture': {'cn': '口径', 'en': 'Aperture'},
            'fov': {'cn': '视场', 'en': 'Field of View'},
            'longitude': {'cn': '经度', 'en': 'Longitude'},
            'latitude': {'cn': '纬度', 'en': 'Latitude'},
            'altitude_text': {'cn': '海拔', 'en': 'Altitude'},
            'utc8': {'cn': 'UTC+8', 'en': 'UTC+8'},
            'sunrise_sunset': {'cn': '日出/日落', 'en': 'Sunrise/Sunset'},
            'twilight': {'cn': '天文晨光/昏影', 'en': 'Astronomical Twilight'},
            'moon_phase': {'cn': '月相', 'en': 'Moon Phase'},
            'sun_altitude': {'cn': '太阳高度', 'en': 'Sun Altitude'},
            'yes': {'cn': '是', 'en': 'Yes'},
            'no': {'cn': '否', 'en': 'No'},
            'high_dynamic_range': {'cn': '高动态范围模式', 'en': 'High Dynamic Range Mode'},
            'device_status': {'cn': '设备连接状态', 'en': 'Device Connection Status'},
            'all_sky_camera_history': {'cn': '全天相机历史图片，右下角全屏放大查看', 'en': 'All Sky Camera History, Click Bottom-Right to Fullscreen'},
            'current_position': {'cn': '当前位置', 'en': 'Current Position'},
            'connected': {'cn': '断开设备', 'en': 'Disconnect'},
            'disconnected': {'cn': '连接设备', 'en': 'Connect'},
            'connecting': {'cn': '连接中', 'en': 'Connecting'},
            'error': {'cn': '错误', 'en': 'Error'},
            'tracking': {'cn': '跟踪中', 'en': 'Tracking'},
            'slewing': {'cn': '转动中', 'en': 'Slewing'},
            'parked': {'cn': '复位', 'en': 'Parked'},
            'high_dynamic_range_mode': {'cn': '高动态范围模式', 'en': 'High Dynamic Range Mode'},
            'normal_mode': {'cn': '普通模式', 'en': 'Normal Mode'},
            'fast_mode': {'cn': '快速模式', 'en': 'Fast Mode'},
            'filter_r': {'cn': 'R滤光片', 'en': 'R-band'},
            'filter_g': {'cn': 'G滤光片', 'en': 'G-band'},
            'filter_b': {'cn': 'B滤光片', 'en': 'B-band'},
            'filter_l': {'cn': 'L滤光片', 'en': 'L-band'},
            'moving_yes': {'cn': '是', 'en': 'Yes'},
            'moving_no': {'cn': '否', 'en': 'No'},
            'all_sky_camera_tip': {'cn': '望远镜监控相机图片，右下角全屏放大查看', 'en': 'Telescope Monitor Camera, Click Bottom-Right to Fullscreen'},
            'telescope_camera_tip': {'cn': '望远镜监控相机图片，右下角全屏放大查看', 'en': 'Telescope Monitor Camera, Click Bottom-Right to Fullscreen'},
            'status_unknown': {'cn': '状态未知', 'en': 'Unknown'},
            '望远镜转动中': {'cn': '望远镜转动中', 'en': 'Slewing'},
            '导星中': {'cn': '导星中', 'en': 'Guiding'},
            '跟踪中': {'cn': '跟踪中', 'en': 'Tracking'},
            '望远镜已复位': {'cn': '已复位', 'en': 'Parked'},
            '望远镜在原位': {'cn': '在原位', 'en': 'AtHome'},
            'cover': {'cn': '镜头盖', 'en': 'Cover'},
            'cover_status': {'cn': '镜头盖状态', 'en': 'Cover Status'},
            'cover_status_unknown': {'cn': '状态未知', 'en': 'Unknown'},
            'cover_status_open': {'cn': '已打开', 'en': 'Open'},
            'cover_status_closed': {'cn': '已关闭', 'en': 'Closed'},
            'cover_status_moving': {'cn': '移动中', 'en': 'Moving'},
            'cover_status_error': {'cn': '错误', 'en': 'Error'},
            'motor_enable': {'cn': '望远镜使能', 'en': 'Telescope Enable'},
            'motor_enabled': {'cn': '已使能', 'en': 'Enabled'},
            'motor_disabled': {'cn': '未使能', 'en': 'Disabled'},
            'cooler': {'cn': '水冷机', 'en': 'Cooler'},
            'cooler_status': {'cn': '水冷机状态', 'en': 'Cooler Status'},
            'cooler_temperature': {'cn': '水冷机温度', 'en': 'Cooler Temperature'},
            'cooler_running': {'cn': '运行状态', 'en': 'Running Status'},
            'cooler_heating': {'cn': '加热状态', 'en': 'Heating Status'},
            'cooler_cooling': {'cn': '制冷状态', 'en': 'Cooling Status'},
            'cooler_flow_alarm': {'cn': '流量报警', 'en': 'Flow Alarm'},
            'cooler_pump': {'cn': '循环泵状态', 'en': 'Pump Status'},
            'cooler_temp_alarm': {'cn': '温度报警', 'en': 'Temperature Alarm'},
            'cooler_level_alarm': {'cn': '液位报警', 'en': 'Level Alarm'},
            'cooler_power': {'cn': '电源状态', 'en': 'Power Status'},
            'temperature_overflow': {'cn': '上溢出', 'en': 'Overflow'},
            'temperature_underflow': {'cn': '下溢出', 'en': 'Underflow'},
            'indicator_on': {'cn': '已开启', 'en': 'ON'},
            'indicator_off': {'cn': '已关闭', 'en': 'OFF'},
            'alarm_on': {'cn': '报警', 'en': 'ALARM'},
            'alarm_off': {'cn': '正常', 'en': 'NORMAL'},
            'ups': {'cn': 'UPS电源', 'en': 'UPS'},
            'ups_status': {'cn': 'UPS电源状态', 'en': 'UPS Status'},
            'ups_battery': {'cn': '电池电量', 'en': 'Battery Level'},
            'ups_load': {'cn': '负载', 'en': 'Load'},
            'ups_status_normal': {'cn': '市电正常', 'en': 'Utility Normal'},
            'ups_status_battery': {'cn': '电池供电', 'en': 'On Battery'},
            'ups_status_bypass': {'cn': '旁路供电', 'en': 'On Bypass'},
            'ups_status_fault': {'cn': '故障', 'en': 'Fault'},
            'ups_status_unknown': {'cn': '状态未知', 'en': 'Status Unknown'},
            'ups_input_voltage': {'cn': '输入电压', 'en': 'Input Voltage'},
            'ups_output_voltage': {'cn': '输出电压', 'en': 'Output Voltage'},
            'ups_input_frequency': {'cn': '输入频率', 'en': 'Input Frequency'},
            'ups_temperature': {'cn': 'UPS温度', 'en': 'UPS Temperature'},
            'ups_status_detail': {'cn': 'UPS状态详情', 'en': 'UPS Status Detail'},
            'ups_utility_fail': {'cn': '失败', 'en': 'Failed'},
            'ups_utility_normal': {'cn': '正常', 'en': 'Normal'},
            'ups_battery_low': {'cn': '偏低', 'en': 'Low'},
            'ups_battery_normal': {'cn': '正常', 'en': 'Normal'},
            'ups_health_fault': {'cn': '故障', 'en': 'Fault'},
            'ups_health_normal': {'cn': '正常', 'en': 'Normal'},
            'ups_selftest_active': {'cn': '是', 'en': 'Yes'},
            'ups_selftest_inactive': {'cn': '否', 'en': 'No'},
            'ups_running_shutdown': {'cn': '否', 'en': 'No'},
            'ups_running_normal': {'cn': '是', 'en': 'Yes'},
            'ups_bit7_0': {'cn': '市电正常', 'en': 'Utility Normal'},
            'ups_bit7_1': {'cn': '市电失败', 'en': 'Utility Failure'},
            'ups_bit6_0': {'cn': '电池电压正常', 'en': 'Battery Normal'},
            'ups_bit6_1': {'cn': '电池电压低', 'en': 'Battery Low'},
            'ups_bit5_0': {'cn': '非旁路模式', 'en': 'Not Bypass'},
            'ups_bit5_1': {'cn': '旁路模式', 'en': 'Bypass Mode'},
            'ups_bit4_0': {'cn': 'UPS正常', 'en': 'UPS Normal'},
            'ups_bit4_1': {'cn': 'UPS故障', 'en': 'UPS Fault'},
            'ups_bit3_0': {'cn': '在线式UPS', 'en': 'Online UPS'},
            'ups_bit3_1': {'cn': '后备式UPS', 'en': 'Standby UPS'},
            'ups_bit2_0': {'cn': '非自检状态', 'en': 'Not Self-testing'},
            'ups_bit2_1': {'cn': '自检中', 'en': 'Self-testing'},
            'ups_bit1_0': {'cn': '正常运行', 'en': 'Normal Running'},
            'ups_bit1_1': {'cn': '关机状态', 'en': 'Shutdown'},
            'ups_bit0_0': {'cn': '蜂鸣器关闭', 'en': 'Buzzer Off'},
            'ups_bit0_1': {'cn': '蜂鸣器开启', 'en': 'Buzzer On'},
            'connect': {'cn': '连接', 'en': 'Connect'},
            'refresh_devices': {'cn': '刷新设备列表', 'en': 'Refresh Devices'},
            'no_devices': {'cn': '未发现设备', 'en': 'No Devices Found'},
            'no_serial_ports': {'cn': '未发现串口设备', 'en': 'No Serial Ports Found'},
            'serial_port': {'cn': '串口', 'en': 'Serial Port'},
            'cover_control': {'cn': '镜头盖控制', 'en': 'Cover Control'},
            'dome_control': {'cn': '圆顶控制', 'en': 'Dome Control'},
            '调焦座控制': {'cn': '调焦座控制', 'en': 'Focuser Control'},
            '输入位置值': {'cn': '输入位置值', 'en': 'Enter Position'},
            '移动': {'cn': '移动', 'en': 'Move'},
            '停止': {'cn': '停止', 'en': 'Halt'},
            'settings': {'cn': '设置', 'en': 'Settings'},
            'theme': {'cn': '主题', 'en': 'Theme'},
            'dome_open': {'cn': '圆顶开', 'en': 'Open Dome'},
            'dome_close': {'cn': '圆顶关', 'en': 'Close Dome'},
            'cover_open': {'cn': '打开镜头盖', 'en': 'Open Cover'},
            'cover_close': {'cn': '关闭镜头盖', 'en': 'Close Cover'},
            'refresh_cover_device': {'cn': '刷新镜头盖设备', 'en': 'Refresh Cover Device'},
            'manual_added': {'cn': '手动添加', 'en': 'Manually Added'},
            'connection': {'cn': '连接', 'en': 'Connect'}
        }

    def get_text(self, key, with_unit=None):
        """
        获取翻译文本
        :param key: 翻译键
        :param with_unit: 带单位的值，如果提供则会自动添加单位
        :return: 翻译后的文本
        """
        if key is None:
            return with_unit if with_unit is not None else ''
            
        text = self.translations.get(key, {}).get(self.current_language, key)
        
        if with_unit is not None:
            # 处理带单位的文本
            units = {
                '°C': {'cn': '°C', 'en': '°C'},
                '°': {'cn': '°', 'en': '°'},
                'm': {'cn': '米', 'en': 'm'},
                'hPa': {'cn': '百帕', 'en': 'hPa'},
                'mm/h': {'cn': '毫米/小时', 'en': 'mm/h'},
                'lux': {'cn': '勒克斯', 'en': 'lux'},
                'm/s': {'cn': '米/秒', 'en': 'm/s'},
                '%': {'cn': '%', 'en': '%'},
                'arcsec': {'cn': '角秒', 'en': 'arcsec'},
                'deg': {'cn': '度', 'en': 'deg'}
            }
            
            # 分离数值和单位
            value = str(with_unit)
            unit = None
            for u in units.keys():
                if value.endswith(u):
                    unit = u
                    value = value[:-len(u)].strip()
                    break
            
            if unit:
                unit_text = units[unit][self.current_language]
                return f"{value}{unit_text}"
            
            return with_unit
            
        return text

    def switch_language(self):
        """切换语言"""
        self.current_language = 'en' if self.current_language == 'cn' else 'cn'

    def get_current_language(self):
        """获取当前语言"""
        return self.current_language

# 创建全局实例
i18n = I18nManager() 