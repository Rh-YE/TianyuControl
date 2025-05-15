"""
主程序入口
"""
import sys
import os
import argparse
import gc
import time
import tracemalloc  # 用于内存分配跟踪，发现泄漏源
import logging
import traceback
from datetime import datetime
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QFile, QIODevice, QTextStream
from src.ui.main_window import MainWindow
from device_manager import Telescope, Focuser, Rotator, ObservingConditions, Dome, Cooler, UPS

# 添加全局变量用于存储主窗口内存引用
_window_ref = None
_app_ref = None
_cleanup_timers = []
_last_devices = None

# 导入内存监控器
from src.utils.memory_monitor import get_memory_monitor

# 创建日志目录
def ensure_log_directory():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir

# GC输出重定向器
class GCRedirector:
    def __init__(self, filename):
        self.log_file = open(filename, 'a', encoding='utf-8')
        self.original_stderr = sys.stderr
        
    def write(self, text):
        if 'gc: ' in text or 'GC: ' in text:
            # 只将GC相关输出写入日志文件
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.log_file.write(f"[{timestamp}] {text}")
            self.log_file.flush()
        else:
            # 其他输出正常显示
            self.original_stderr.write(text)
            
    def flush(self):
        self.log_file.flush()
        self.original_stderr.flush()
        
    def close(self):
        self.log_file.close()
        
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
    
    # 将设备列表保存在全局变量中，以便后续清理引用
    global _last_devices
    _last_devices = all_devices
    
    return all_devices

def cleanup_image_caches():
    """清理图像缓存以防止内存泄漏"""
    try:
        from PyQt5.QtGui import QPixmapCache
        # 清理QPixmap缓存
        QPixmapCache.clear()
        
        # 从主窗口中获取并清理状态图像
        global _window_ref
        if _window_ref and hasattr(_window_ref, 'camera_image'):
            _window_ref.camera_image = None
        
        print("已清理图像缓存")
    except Exception as e:
        print(f"清理图像缓存失败: {e}")

def restart_timers():
    """重启所有定时器，防止定时器堆积"""
    global _window_ref, _cleanup_timers
    
    try:
        if _window_ref:
            # 重启主窗口中的定时器
            if hasattr(_window_ref, 'restart_timers') and callable(_window_ref.restart_timers):
                _window_ref.restart_timers()
            
            # 重启全局清理定时器
            for timer in _cleanup_timers:
                if timer.isActive():
                    timer.stop()
                timer.start()
                
        print("已重启所有定时器")
    except Exception as e:
        print(f"重启定时器失败: {e}")

def perform_deep_cleanup():
    """执行深度清理，防止长时间运行时的资源耗尽"""
    print("开始执行深度清理...")
    
    # 清理图像缓存
    cleanup_image_caches()
    
    # 清理Python内部缓存
    try:
        sys.intern_cache.clear()  # Python 3.11+
    except (AttributeError, Exception):
        pass
    
    # 重启所有定时器
    restart_timers()
    
    # 强制执行垃圾回收
    collected = gc.collect()
    print(f"垃圾回收释放了 {collected} 个对象")
    
    # 尝试从主窗口获取控件并清理它们的缓存
    global _window_ref
    if _window_ref:
        try:
            for widget in _window_ref.findChildren(QObject):
                if hasattr(widget, 'clear'):
                    widget.clear()
                if hasattr(widget, 'clearMask'):
                    widget.clearMask()
        except Exception:
            pass
    
    # 尝试释放未使用的内存返回给操作系统
    try:
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1)
    except Exception:
        pass
    
    print("深度清理完成")

def main():
    parser = argparse.ArgumentParser(description='天语总控')
    parser.add_argument('--monitor-memory', action='store_false', help='禁用内存监控')
    parser.add_argument('--optimize-memory', action='store_false', help='禁用内存优化')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--check-interval', type=int, default=30, help='内存检查间隔(秒)')
    parser.add_argument('--gc-interval', type=int, default=60, help='垃圾回收间隔(秒)')
    parser.add_argument('--no-gc-log', action='store_true', help='禁用垃圾回收日志')
    
    args = parser.parse_args()
    
    # 默认启用内存监控和优化
    enable_memory_monitoring = not args.monitor_memory
    enable_memory_optimization = not args.optimize_memory
    
    # 创建日志目录
    log_dir = ensure_log_directory()
    
    # 设置垃圾回收日志
    if not args.no_gc_log:
        gc_log_file = os.path.join(log_dir, f"gc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        gc_redirector = GCRedirector(gc_log_file)
        sys.stderr = gc_redirector
        print(f"垃圾回收日志重定向到: {gc_log_file}")
    
    # 设置调试日志
    if args.debug:
        debug_log_file = os.path.join(log_dir, f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        logging.basicConfig(
            filename=debug_log_file,
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        print(f"调试日志输出到: {debug_log_file}")
    
    # 启用内存优化
    if enable_memory_optimization:
        # 调整垃圾回收阈值，使其更频繁地进行回收
        # 参数说明: (阈值0, 阈值1, 阈值2)，数值越小，回收越频繁
        gc.set_threshold(100, 5, 5)
        print("已启用内存优化模式")
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 创建内存监控定时器
    memory_monitor = None
    mem_timer = None
    
    # 创建垃圾回收定时器
    gc_timer = None
    
    if enable_memory_monitoring:
        try:
            # 初始化内存监控器 - 注意：将秒转换为毫秒
            memory_monitor = get_memory_monitor(check_interval=args.check_interval * 1000, 
                                           gc_interval=args.gc_interval * 1000,
                                           warning_threshold=70)
            
            # 开始监控
            memory_monitor.start()
            print(f"已启用内存监控，检查间隔: {args.check_interval}秒，GC间隔: {args.gc_interval}秒")
            
            # 定时打印内存统计信息
            mem_timer = QTimer()
            mem_timer.timeout.connect(lambda: print(memory_monitor.get_memory_status_text()))
            mem_timer.start(args.check_interval * 1000)  # 每隔check_interval秒打印一次
            
        except Exception as e:
            print(f"初始化内存监控器时出错: {str(e)}")
            traceback.print_exc()
    
    # 即使不启用完整的内存监控，也设置定期垃圾回收
    if enable_memory_optimization:
        gc_timer = QTimer()
        gc_timer.timeout.connect(lambda: gc.collect())
        gc_timer.start(60 * 1000)  # 每60秒强制执行一次垃圾回收
    
    # 创建主窗口
    window = MainWindow(telescope_devices=search_telescope())
    
    # 存储全局引用，以便在清理函数中使用
    global _window_ref, _app_ref
    _window_ref = window
    _app_ref = app
    
    # 应用退出时清理
    def cleanup():
        if memory_monitor:
            memory_monitor.stop()
            print(memory_monitor.get_memory_statistics())
        
        if mem_timer:
            mem_timer.stop()
        
        if gc_timer:
            gc_timer.stop()
        
        # 恢复原始stderr
        if not args.no_gc_log and 'gc_redirector' in locals():
            sys.stderr = gc_redirector.original_stderr
            gc_redirector.close()
    
    # 连接退出信号
    app.aboutToQuit.connect(cleanup)
    
    # 显示主窗口并启动应用程序
    window.show()
    
    # 在启动应用程序前进行一次全面清理
    perform_deep_cleanup()
    
    sys.exit(app.exec_())

def print_memory_traces():
    """打印内存分配追踪信息"""
    if not tracemalloc.is_tracing():
        return
        
    print("\n----- 内存分配追踪 -----")
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("[ 前10个内存分配源 ]")
    for stat in top_stats[:10]:
        print(f"{stat.count} 个对象: {stat.size / 1024:.1f} KB")
        print(f"  {stat.traceback.format()[0]}")
    print("-------------------------\n")

if __name__ == '__main__':
    main()    