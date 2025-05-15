"""
内存监控工具

这个模块提供了跟踪应用程序内存使用的功能，
可以帮助检测内存泄漏问题并执行定期垃圾回收
"""
import os
import gc
import time
import psutil
import logging
import weakref
import sys
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from typing import Callable, Optional, Dict, List, Any, Set

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='memory_usage.log'
)
logger = logging.getLogger('memory_monitor')

class MemoryMonitor(QObject):
    """内存监控类，追踪应用程序内存使用情况并提供垃圾回收"""
    
    # 信号，当内存使用变化时发出
    memory_usage_changed = pyqtSignal(dict)
    
    def __init__(self, 
                 check_interval: int = 5000,  # 默认每5秒检查一次
                 gc_interval: int = 60000,    # 默认每60秒进行一次垃圾回收
                 warning_threshold: float = 80.0,  # 内存使用率警告阈值（百分比）
                 critical_threshold: float = 90.0,  # 内存使用率临界阈值（百分比）
                 parent: Optional[QObject] = None):
        """
        初始化内存监控器
        
        Args:
            check_interval: 检查内存使用的间隔（毫秒）
            gc_interval: 进行垃圾回收的间隔（毫秒）
            warning_threshold: 内存使用警告阈值（百分比）
            critical_threshold: 内存使用临界阈值（百分比）
            parent: 父QObject
        """
        super().__init__(parent)
        
        self.check_interval = check_interval
        self.gc_interval = gc_interval
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        
        # 创建当前进程的psutil进程对象
        self.process = psutil.Process(os.getpid())
        
        # 收集基准内存使用数据
        self.baseline_memory = self.get_memory_usage()
        
        # 存储内存使用历史（使用弱引用存储，避免内存监控器本身引起内存泄漏）
        self._memory_history: List[Dict[str, Any]] = []
        self.max_history_size = 100  # 最多保存100个历史记录点
        
        # 标记是否已经发出过警告
        self.warning_issued = False
        self.critical_issued = False
        
        # 记录潜在循环引用对象
        self.circular_refs: List[Set[int]] = []
        
        # 创建定时器用于检查内存使用
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_memory_usage)
        
        # 创建定时器用于垃圾回收
        self.gc_timer = QTimer(self)
        self.gc_timer.timeout.connect(self.force_garbage_collection)
        
        # 创建定时器用于检测循环引用（消耗资源较多，较长时间运行一次）
        self.cycle_timer = QTimer(self)
        self.cycle_timer.timeout.connect(self.detect_cycles)
        self.cycle_timer.setInterval(300000)  # 默认5分钟检测一次
        
        # 记录启动信息
        logger.info(f"内存监控启动 - 基准内存使用: {self.baseline_memory}")
        logger.info(f"检查间隔: {check_interval}ms, 垃圾回收间隔: {gc_interval}ms")
        logger.info(f"警告阈值: {warning_threshold}%, 临界阈值: {critical_threshold}%")
        
        # 在初始化时主动执行一次垃圾回收
        self.force_garbage_collection()
    
    def start(self):
        """启动内存监控"""
        self.check_timer.start(self.check_interval)
        self.gc_timer.start(self.gc_interval)
        self.cycle_timer.start()
        logger.info("内存监控服务已启动")
    
    def stop(self):
        """停止内存监控"""
        self.check_timer.stop()
        self.gc_timer.stop()
        self.cycle_timer.stop()
        logger.info("内存监控服务已停止")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取当前内存使用情况"""
        # 获取进程信息
        process_info = self.process.memory_info()
        
        # 获取系统内存信息
        system_memory = psutil.virtual_memory()
        
        # 计算当前时间
        current_time = time.time()
        
        # 尝试获取更多内存使用数据
        try:
            if hasattr(self.process, 'memory_maps'):
                memory_maps = self.process.memory_maps()
                private_bytes = sum(m.private for m in memory_maps if hasattr(m, 'private'))
            else:
                private_bytes = 0
        except Exception:
            private_bytes = 0
            
        # 尝试获取pagefile使用情况
        try:
            if hasattr(psutil, 'swap_memory'):
                swap = psutil.swap_memory()
                swap_used = swap.used
                swap_total = swap.total
                swap_percent = swap.percent
            else:
                swap_used = swap_total = swap_percent = 0
        except Exception:
            swap_used = swap_total = swap_percent = 0
            
        return {
            'timestamp': current_time,
            'formatted_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time)),
            'rss': process_info.rss,  # 常驻内存大小 (字节)
            'rss_mb': process_info.rss / (1024 * 1024),  # 常驻内存大小 (MB)
            'vms': process_info.vms,  # 虚拟内存大小 (字节)
            'vms_mb': process_info.vms / (1024 * 1024),  # 虚拟内存大小 (MB)
            'private_bytes': private_bytes,  # 私有内存 (字节)
            'private_mb': private_bytes / (1024 * 1024) if private_bytes > 0 else 0,  # 私有内存 (MB)
            'percent': self.process.memory_percent(),  # 进程内存使用百分比
            'system_total': system_memory.total,  # 系统总内存 (字节)
            'system_total_mb': system_memory.total / (1024 * 1024),  # 系统总内存 (MB)
            'system_available': system_memory.available,  # 系统可用内存 (字节)
            'system_available_mb': system_memory.available / (1024 * 1024),  # 系统可用内存 (MB)
            'system_percent': system_memory.percent,  # 系统内存使用百分比
            'swap_used_mb': swap_used / (1024 * 1024) if swap_used > 0 else 0,  # 交换文件使用 (MB)
            'swap_percent': swap_percent,  # 交换文件使用百分比
            'gc_objects': len(gc.get_objects()),  # 垃圾回收器跟踪的对象数量
            'gc_collected': 0,  # 最近一次垃圾回收收集的对象数量 (初始为0)
            'circular_refs': len(self.circular_refs)  # 检测到的循环引用数
        }
    
    def check_memory_usage(self):
        """检查当前内存使用情况，记录日志并在必要时发出警告"""
        try:
            memory_info = self.get_memory_usage()
            
            # 添加到历史记录
            self._memory_history.append(memory_info)
            
            # 如果历史记录过长，删除最早的记录
            if len(self._memory_history) > self.max_history_size:
                self._memory_history.pop(0)
            
            # 检查是否超过警告阈值
            if memory_info['system_percent'] > self.warning_threshold and not self.warning_issued:
                logger.warning(f"系统内存使用率超过警告阈值: {memory_info['system_percent']:.2f}%")
                self.warning_issued = True
                
                # 主动尝试释放一些内存
                self.cleanup_memory()
                
            elif memory_info['system_percent'] < self.warning_threshold and self.warning_issued:
                # 如果内存使用率恢复到阈值以下，重置警告标志
                self.warning_issued = False
            
            # 检查是否超过临界阈值
            if memory_info['system_percent'] > self.critical_threshold and not self.critical_issued:
                logger.critical(f"系统内存使用率超过临界阈值: {memory_info['system_percent']:.2f}%")
                self.critical_issued = True
                
                # 在临界情况下立即执行垃圾回收和内存清理
                self.cleanup_memory(aggressive=True)
                
            elif memory_info['system_percent'] < self.critical_threshold and self.critical_issued:
                # 如果内存使用率恢复到阈值以下，重置警告标志
                self.critical_issued = False
            
            # 每10次检查记录一次详细信息
            if len(self._memory_history) % 10 == 0:
                logger.info(f"内存使用: {memory_info['rss_mb']:.2f}MB (RSS), "
                           f"系统内存: {memory_info['system_percent']:.2f}%, "
                           f"进程内存: {memory_info['percent']:.2f}%")
                
                # 每10次检查检测一次未引用对象
                self.cleanup_unreachable()
            
            # 发送信号
            self.memory_usage_changed.emit(memory_info)
            
        except Exception as e:
            logger.error(f"检查内存使用时出错: {str(e)}")
    
    def force_garbage_collection(self):
        """强制执行垃圾回收"""
        try:
            # 记录回收前的对象数量
            before_count = len(gc.get_objects())
            
            # 禁用GC以防止在收集过程中创建新对象
            was_enabled = gc.isenabled()
            if was_enabled:
                gc.disable()
            
            # 保存并临时关闭GC调试标志，避免大量输出
            old_debug = gc.get_debug()
            gc.set_debug(0)
            
            try:
                # 执行完整的垃圾回收
                gc.collect(0)  # 收集第0代对象
                gc.collect(1)  # 收集第1代对象
                gc.collect(2)  # 收集第2代对象
            finally:
                # 恢复GC状态和调试标志
                if was_enabled:
                    gc.enable()
                gc.set_debug(old_debug)
            
            # 记录回收后的对象数量
            after_count = len(gc.get_objects())
            collected = before_count - after_count if before_count > after_count else 0
            
            # 记录在内存信息中
            if self._memory_history:
                self._memory_history[-1]['gc_collected'] = collected
            
            # 记录日志
            logger.info(f"执行垃圾回收: 收集了 {collected} 个对象")
            
        except Exception as e:
            logger.error(f"执行垃圾回收时出错: {str(e)}")
    
    def cleanup_memory(self, aggressive=False):
        """清理内存，尝试释放更多资源"""
        try:
            logger.info(f"开始清理内存 (aggressive={aggressive})")
            
            # 清理会话级对象池
            cleanup_session_pools()
            
            # 保存GC调试标志
            old_debug = gc.get_debug()
            
            # 关闭调试标志，避免产生大量输出
            gc.set_debug(0)
            
            # 主动执行垃圾回收
            self.force_garbage_collection()
            
            # 如果是激进模式，尝试更强力的清理
            if aggressive:
                # 尝试清理Python内部缓存
                cleanup_python_caches()
                
                # 尝试回收未引用但循环引用的对象
                self.detect_cycles()
                
                # 再次执行垃圾回收
                self.force_garbage_collection()
                
                # 记录已保存但可能消耗内存的历史数据大小
                history_size = len(self._memory_history)
                if history_size > 20:  # 保留最近20条记录
                    # 丢弃旧记录以节省内存
                    self._memory_history = self._memory_history[-20:]
                    logger.info(f"内存压力大，丢弃了{history_size - 20}条历史记录")
            
            # 释放历史循环引用记录
            self.circular_refs = []
            
            # 在Windows上尝试降低工作集大小
            try:
                if sys.platform == 'win32':
                    import ctypes
                    # 导入Windows API函数
                    if hasattr(ctypes, 'windll') and hasattr(ctypes.windll, 'kernel32'):
                        kernel32 = ctypes.windll.kernel32
                        if hasattr(kernel32, 'SetProcessWorkingSetSize'):
                            # 尝试设置工作集大小为最小值
                            pid = os.getpid()
                            handle = kernel32.OpenProcess(0x1F0FFF, False, pid)
                            result = kernel32.SetProcessWorkingSetSize(handle, -1, -1)
                            kernel32.CloseHandle(handle)
                            logger.info(f"尝试降低工作集大小，结果: {result}")
            except Exception as e:
                logger.error(f"尝试降低工作集大小时出错: {str(e)}")
                
            # 恢复GC调试标志
            gc.set_debug(old_debug)
        
        except Exception as e:
            logger.error(f"清理内存时出错: {str(e)}")
    
    def cleanup_unreachable(self):
        """清理已经不可达但由于引用循环而未被回收的对象"""
        try:
            # 使用gc.collect()显式收集这些对象
            unreachable = gc.collect()
            if unreachable > 0:
                logger.info(f"清理了 {unreachable} 个不可达对象")
        except Exception as e:
            logger.error(f"清理不可达对象时出错: {str(e)}")
    
    def detect_cycles(self):
        """检测和记录循环引用"""
        try:
            logger.info("开始检测循环引用...")
            
            # 重置循环引用计数
            self.circular_refs = []
            
            # 保存GC调试标志
            old_debug = gc.get_debug()
            
            # 关闭调试标志，避免产生大量输出
            gc.set_debug(0)
            
            # 获取所有对象
            gc.collect()  # 首先执行一次收集，确保之前可以回收的对象已被回收
            objects = gc.get_objects()
            
            # 限制检查的对象数量，以避免过高的CPU使用
            max_to_check = min(10000, len(objects))
            objects = objects[:max_to_check]
            
            # 查找循环引用
            cycles = []
            for obj in objects:
                # 安全地获取对象的引用
                try:
                    # 保存已检查过的对象的ID
                    seen = {id(obj)}
                    # 查找内存泄漏的路径
                    path = [obj]
                    self._find_cycle(obj, seen, path, cycles)
                except Exception:
                    # 忽略检查过程中的错误
                    pass
            
            # 记录结果
            self.circular_refs = cycles[:100]  # 限制记录的循环引用数量
            
            if cycles:
                logger.warning(f"检测到 {len(cycles)} 个潜在的循环引用")
                
                # 尝试中断一些循环引用
                self._break_cycles()
            else:
                logger.info("未检测到循环引用")
                
            # 恢复GC调试标志
            gc.set_debug(old_debug)
                
        except Exception as e:
            logger.error(f"检测循环引用时出错: {str(e)}")
    
    def _find_cycle(self, obj, seen, path, cycles, depth=0, max_depth=3):
        """递归查找对象的循环引用"""
        if depth >= max_depth:
            return
        
        # 尝试获取对象的引用
        try:
            refs = gc.get_referents(obj)
        except Exception:
            return
            
        for ref in refs:
            # 跟踪引用ID
            ref_id = id(ref)
            
            # 如果已经在路径中，发现了一个循环
            if ref_id in seen:
                # 找到循环的起点
                cycle_start = path.index(ref)
                # 记录循环中的对象ID
                cycle = set(id(o) for o in path[cycle_start:])
                # 如果这是一个新的循环，添加到列表中
                if cycle not in cycles:
                    cycles.append(cycle)
                continue
                
            # 继续搜索
            seen.add(ref_id)
            path.append(ref)
            self._find_cycle(ref, seen, path, cycles, depth + 1, max_depth)
            path.pop()
            seen.remove(ref_id)
    
    def _break_cycles(self):
        """尝试中断一些循环引用"""
        try:
            # 只有在循环引用很多的情况下才执行
            if len(self.circular_refs) < 10:
                return
                
            logger.info(f"尝试中断 {len(self.circular_refs)} 个循环引用")
            
            # 保存GC调试标志
            old_debug = gc.get_debug()
            
            # 关闭调试标志，避免产生大量输出
            gc.set_debug(0)
            
            # 对一些特定类型的对象执行引用清理
            count = 0
            for obj in gc.get_objects():
                try:
                    # 清理可能包含循环引用的字典
                    if isinstance(obj, dict) and len(obj) > 0:
                        obj.clear()
                        count += 1
                    # 清理可能包含循环引用的列表
                    elif isinstance(obj, list) and len(obj) > 0:
                        obj.clear()
                        count += 1
                    # 最多清理1000个对象
                    if count >= 1000:
                        break
                except Exception:
                    pass
            
            # 执行垃圾回收
            gc.collect()
            logger.info(f"清理了 {count} 个可能包含循环引用的容器对象")
            
            # 恢复GC调试标志
            gc.set_debug(old_debug)
            
        except Exception as e:
            logger.error(f"中断循环引用时出错: {str(e)}")
    
    def get_memory_history(self) -> List[Dict[str, Any]]:
        """获取内存使用历史"""
        return self._memory_history
    
    def get_memory_leak_analysis(self) -> Dict[str, Any]:
        """分析可能的内存泄漏"""
        if len(self._memory_history) < 10:
            return {"status": "insufficient_data", "message": "数据点不足，无法进行泄漏分析"}
        
        # 计算增长率
        first_rss = self._memory_history[0]['rss']
        last_rss = self._memory_history[-1]['rss']
        time_diff = self._memory_history[-1]['timestamp'] - self._memory_history[0]['timestamp']
        
        if time_diff <= 0:
            return {"status": "error", "message": "时间数据无效"}
        
        growth_rate = (last_rss - first_rss) / time_diff  # 每秒字节增长率
        
        # 临时关闭调试标志，避免大量输出
        old_debug = gc.get_debug()
        gc.set_debug(0)
        
        # 检查未被引用但未被回收的对象
        unreachable = gc.collect()
        
        # 进行更深入的泄漏分析
        type_counts = {}
        try:
            # 获取所有对象的类型统计
            for obj in gc.get_objects():
                obj_type = type(obj).__name__
                type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
            
            # 筛选出数量最多的10种对象类型
            top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        except Exception:
            top_types = []
        
        # 恢复GC调试标志
        gc.set_debug(old_debug)
        
        return {
            "status": "analyzed",
            "start_memory_mb": first_rss / (1024 * 1024),
            "current_memory_mb": last_rss / (1024 * 1024),
            "memory_growth_mb": (last_rss - first_rss) / (1024 * 1024),
            "time_period_seconds": time_diff,
            "growth_rate_kb_per_sec": growth_rate / 1024,
            "unreachable_objects": unreachable,
            "circular_references": len(self.circular_refs),
            "top_object_types": dict(top_types),
            "is_leaking": growth_rate > 1024 * 10,  # 如果每秒增长超过10KB，可能存在泄漏
            "message": f"内存增长速率: {growth_rate / 1024:.2f}KB/秒, 检测到{len(self.circular_refs)}个循环引用"
        }
    
    def print_stats(self):
        """打印内存使用统计信息"""
        if not self._memory_history:
            print("没有可用的内存使用历史数据")
            return
        
        latest = self._memory_history[-1]
        print("\n----- 内存使用统计 -----")
        print(f"时间: {latest['formatted_time']}")
        print(f"进程内存: {latest['rss_mb']:.2f}MB (RSS)")
        print(f"系统内存: {latest['system_percent']:.1f}% 使用中")
        print(f"可用系统内存: {latest['system_available_mb']:.2f}MB")
        print(f"GC跟踪的对象: {latest['gc_objects']}")
        
        if 'gc_collected' in latest:
            print(f"最近回收的对象: {latest['gc_collected']}")
        
        if 'circular_refs' in latest:
            print(f"检测到的循环引用: {latest['circular_refs']}")
        
        if len(self._memory_history) > 1:
            first = self._memory_history[0]
            growth = latest['rss'] - first['rss']
            time_diff = latest['timestamp'] - first['timestamp']
            if time_diff > 0:
                rate = growth / time_diff
                print(f"内存增长: {growth/(1024*1024):.2f}MB 在 {time_diff:.0f}秒内")
                print(f"增长率: {rate/1024:.2f}KB/秒")
                
                if rate > 1024 * 10:  # 如果增长率超过10KB/秒
                    print("警告: 可能存在内存泄漏!")
        
        print("------------------------\n")
        
    def get_memory_status_text(self) -> str:
        """获取内存状态文本，用于显示在UI或日志中"""
        if not self._memory_history:
            return "没有可用的内存使用历史数据"
        
        latest = self._memory_history[-1]
        status_text = f"内存: {latest['rss_mb']:.2f}MB (RSS) | 系统: {latest['system_percent']:.1f}% | GC对象: {latest['gc_objects']}"
        
        if len(self._memory_history) > 1:
            first = self._memory_history[0]
            growth = latest['rss'] - first['rss']
            time_diff = latest['timestamp'] - first['timestamp']
            if time_diff > 0:
                rate = growth / time_diff
                status_text += f" | 增长率: {rate/1024:.2f}KB/秒"
                
                if rate > 1024 * 10:  # 如果增长率超过10KB/秒
                    status_text += " [警告: 可能存在内存泄漏!]"
        
        return status_text
        
    def get_memory_statistics(self) -> str:
        """获取详细的内存统计信息，格式化为文本字符串"""
        if not self._memory_history:
            return "没有可用的内存使用历史数据"
        
        latest = self._memory_history[-1]
        stats = [
            "----- 内存使用统计详情 -----",
            f"时间: {latest['formatted_time']}",
            f"进程内存: {latest['rss_mb']:.2f}MB (RSS)",
            f"系统内存: {latest['system_percent']:.1f}% 使用中",
            f"可用系统内存: {latest['system_available_mb']:.2f}MB",
            f"GC跟踪的对象: {latest['gc_objects']}"
        ]
        
        if 'gc_collected' in latest:
            stats.append(f"最近回收的对象: {latest['gc_collected']}")
        
        if 'circular_refs' in latest:
            stats.append(f"检测到的循环引用: {latest['circular_refs']}")
        
        if len(self._memory_history) > 1:
            first = self._memory_history[0]
            growth = latest['rss'] - first['rss']
            time_diff = latest['timestamp'] - first['timestamp']
            if time_diff > 0:
                rate = growth / time_diff
                stats.append(f"内存增长: {growth/(1024*1024):.2f}MB 在 {time_diff:.0f}秒内")
                stats.append(f"增长率: {rate/1024:.2f}KB/秒")
                
                if rate > 1024 * 10:  # 如果增长率超过10KB/秒
                    stats.append("警告: 可能存在内存泄漏!")
                    
        stats.append("------------------------")
        return "\n".join(stats)


def cleanup_session_pools():
    """清理会话级对象池和缓存"""
    try:
        # 强制清理PyQt的事件队列和缓存
        # 注意：在实际应用中，这可能需要根据具体的应用设计进行调整
        QObject.receivers = {}  # 尝试清理信号接收器缓存
    except Exception:
        pass


def cleanup_python_caches():
    """清理Python内部缓存"""
    try:
        # 尝试清理sys模块的各种缓存
        if hasattr(sys, 'gettotalrefcount'):  # 只在debug build中可用
            sys.gettotalrefcount()  # 触发一次引用计数更新
        
        # 清理sys.modules中未使用的模块
        # 注意：这是一个激进的操作，可能会导致一些问题
        # 所以我们只移除非必要的模块
        non_essential_modules = []
        for module_name in list(sys.modules.keys()):
            if not any(module_name.startswith(prefix) for prefix in ['PyQt5', 'sys', 'os', 'gc', 'builtins']):
                non_essential_modules.append(module_name)
        
        # 从后向前移除，以避免遍历过程中的修改问题
        for module_name in non_essential_modules[:100]:  # 限制最多移除100个模块
            try:
                if module_name in sys.modules:
                    del sys.modules[module_name]
            except Exception:
                pass
    except Exception:
        pass


# 不再在模块级别创建实例，改为提供创建实例的函数
def get_memory_monitor(check_interval=5000, gc_interval=60000, 
                     warning_threshold=80.0, critical_threshold=90.0, 
                     parent=None):
    """
    获取内存监控器实例，如果不存在则创建一个新的
    
    Args:
        check_interval: 检查内存使用的间隔（毫秒）
        gc_interval: 进行垃圾回收的间隔（毫秒）
        warning_threshold: 内存使用警告阈值（百分比）
        critical_threshold: 内存使用临界阈值（百分比）
        parent: 父QObject
        
    Returns:
        MemoryMonitor: 内存监控器实例
    """
    # 使用全局变量存储单例
    global _memory_monitor_instance
    if '_memory_monitor_instance' not in globals() or _memory_monitor_instance is None:
        _memory_monitor_instance = MemoryMonitor(
            check_interval=check_interval,
            gc_interval=gc_interval,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            parent=parent
        )
    return _memory_monitor_instance

# 初始化全局变量
_memory_monitor_instance = None 