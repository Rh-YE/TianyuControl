#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
内存诊断工具 - 用于检测和分析TianyuControl系统的内存问题
"""

import os
import sys
import gc
import time
import argparse
import datetime
import traceback

try:
    import psutil
except ImportError:
    print("未安装psutil库，请先运行: pip install psutil")
    sys.exit(1)

def memory_object_analysis():
    """分析内存中的对象"""
    import types
    import inspect
    from collections import defaultdict
    
    # 获取所有对象
    gc.collect()  # 先执行一次垃圾回收
    objects = gc.get_objects()
    
    # 按类型统计对象
    type_counts = defaultdict(int)
    total_size = 0
    
    for obj in objects:
        try:
            obj_type = type(obj).__name__
            type_counts[obj_type] += 1
            
            # 尝试获取对象大小（不适用于所有对象）
            if hasattr(obj, '__sizeof__'):
                total_size += obj.__sizeof__()
        except Exception:
            continue
    
    # 按数量排序
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    
    print("\n== 对象类型统计 ==")
    print(f"总计检测到 {len(objects)} 个对象, 估计大小: {total_size / (1024*1024):.2f} MB")
    print(f"{'类型':<20} {'数量':<10}")
    print("-" * 30)
    
    # 显示前20种最常见的对象类型
    for obj_type, count in sorted_types[:20]:
        print(f"{obj_type:<20} {count:<10}")
    
    return sorted_types

def find_memory_leaks(iterations=3, interval=1.0):
    """通过多次垃圾回收检测内存泄漏"""
    print("\n== 内存泄漏检测 ==")
    print(f"执行 {iterations} 次垃圾回收，间隔 {interval} 秒...")
    
    # 先执行一次完整的垃圾回收
    gc.collect()
    
    # 循环执行多次垃圾回收，检查是否每次都有新的不可达对象
    unreachable_counts = []
    
    for i in range(iterations):
        time.sleep(interval)
        count = gc.collect()
        unreachable_counts.append(count)
        print(f"第 {i+1} 次回收: 发现 {count} 个不可回收对象")
    
    # 分析结果
    if all(count > 0 for count in unreachable_counts):
        print("\n警告: 每次垃圾回收都发现不可回收对象，可能存在内存泄漏")
        print("建议检查循环引用或未正确关闭的资源")
    elif any(count > 10 for count in unreachable_counts):
        print("\n注意: 部分垃圾回收发现大量不可回收对象，需要关注")
    else:
        print("\n内存回收正常，未检测到明显的泄漏问题")
    
    return unreachable_counts

def check_process_memory(pid=None):
    """检查指定进程的内存使用情况"""
    if pid is None:
        # 如果未指定PID，使用当前进程
        pid = os.getpid()
    
    try:
        process = psutil.Process(pid)
        
        # 获取进程信息
        process_info = {
            'pid': process.pid,
            'name': process.name(),
            'create_time': datetime.datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S'),
            'status': process.status(),
            'cpu_percent': process.cpu_percent(interval=1.0),
            'memory_info': process.memory_info(),
            'memory_percent': process.memory_percent(),
            'threads': process.num_threads(),
            'open_files': len(process.open_files()),
            'connections': len(process.connections()),
        }
        
        # 打印进程信息
        print("\n== 进程信息 ==")
        print(f"PID: {process_info['pid']}")
        print(f"名称: {process_info['name']}")
        print(f"启动时间: {process_info['create_time']}")
        print(f"状态: {process_info['status']}")
        print(f"CPU使用率: {process_info['cpu_percent']}%")
        print(f"内存使用: {process_info['memory_info'].rss / (1024*1024):.2f} MB (RSS)")
        print(f"内存使用率: {process_info['memory_percent']:.2f}%")
        print(f"线程数: {process_info['threads']}")
        print(f"打开文件数: {process_info['open_files']}")
        print(f"网络连接数: {process_info['connections']}")
        
        return process_info
        
    except psutil.NoSuchProcess:
        print(f"错误: 未找到PID为 {pid} 的进程")
        return None
    except Exception as e:
        print(f"检查进程内存时出错: {str(e)}")
        traceback.print_exc()
        return None

def analyze_system_resources():
    """分析系统资源使用情况"""
    try:
        # 系统内存使用情况
        memory = psutil.virtual_memory()
        
        # CPU使用情况
        cpu_percent = psutil.cpu_percent(interval=1.0, percpu=True)
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        
        # 打印系统资源使用情况
        print("\n== 系统资源使用情况 ==")
        
        print("\n内存:")
        print(f"总内存: {memory.total / (1024*1024*1024):.2f} GB")
        print(f"可用内存: {memory.available / (1024*1024*1024):.2f} GB")
        print(f"内存使用率: {memory.percent:.2f}%")
        
        print("\nCPU:")
        for i, percent in enumerate(cpu_percent):
            print(f"CPU {i+1}: {percent}%")
        print(f"平均CPU使用率: {sum(cpu_percent) / len(cpu_percent):.2f}%")
        
        print("\n磁盘:")
        print(f"总空间: {disk.total / (1024*1024*1024):.2f} GB")
        print(f"可用空间: {disk.free / (1024*1024*1024):.2f} GB")
        print(f"磁盘使用率: {disk.percent:.2f}%")
        
        return {
            'memory': memory,
            'cpu_percent': cpu_percent,
            'disk': disk,
        }
        
    except Exception as e:
        print(f"分析系统资源时出错: {str(e)}")
        traceback.print_exc()
        return None

def check_memory_fragmentation():
    """检查内存碎片情况"""
    try:
        print("\n== 内存碎片分析 ==")
        
        # 强制执行一次完整的垃圾回收
        gc.collect()
        
        # 尝试分配一块大内存，然后释放，检查是否能够回收
        print("测试内存分配和释放...")
        try:
            # 尝试分配128MB内存
            large_data = bytearray(128 * 1024 * 1024)
            del large_data
            gc.collect()
            print("内存分配测试成功，未检测到明显的内存碎片问题")
        except MemoryError:
            print("警告: 无法分配大块内存，可能存在内存碎片问题或系统内存不足")
        
        # 获取当前内存使用情况
        if 'psutil' in sys.modules:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            print(f"当前进程内存: RSS={mem_info.rss / (1024*1024):.2f}MB, VMS={mem_info.vms / (1024*1024):.2f}MB")
            
            # 尝试估计碎片率
            if hasattr(mem_info, 'rss') and hasattr(mem_info, 'vms') and mem_info.vms > 0:
                fragmentation_ratio = mem_info.rss / mem_info.vms
                print(f"内存使用效率 (RSS/VMS): {fragmentation_ratio:.2f}")
                
                if fragmentation_ratio < 0.5:
                    print("警告: 内存使用效率较低，可能存在内存碎片问题")
                else:
                    print("内存使用效率正常")
            
    except Exception as e:
        print(f"检查内存碎片时出错: {str(e)}")
        traceback.print_exc()

def find_tianyucontrol_process():
    """查找正在运行的TianyuControl进程"""
    try:
        print("\n== 查找TianyuControl进程 ==")
        
        tianyucontrol_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 检查命令行或进程名是否包含关键字
                if proc.info['cmdline'] and any('tianyucontrol' in cmd.lower() for cmd in proc.info['cmdline'] if cmd):
                    tianyucontrol_processes.append(proc)
                elif proc.info['cmdline'] and any('main.py' in cmd for cmd in proc.info['cmdline'] if cmd):
                    tianyucontrol_processes.append(proc)
                elif proc.info['name'] and 'python' in proc.info['name'].lower() and proc.info['cmdline'] and any('main.py' in cmd for cmd in proc.info['cmdline'] if cmd):
                    tianyucontrol_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if tianyucontrol_processes:
            print(f"找到 {len(tianyucontrol_processes)} 个TianyuControl相关进程:")
            for i, proc in enumerate(tianyucontrol_processes):
                print(f"{i+1}. PID: {proc.pid}, 名称: {proc.name()}, 内存: {proc.memory_info().rss / (1024*1024):.2f}MB")
            
            return tianyucontrol_processes
        else:
            print("未找到正在运行的TianyuControl进程")
            return []
            
    except Exception as e:
        print(f"查找TianyuControl进程时出错: {str(e)}")
        traceback.print_exc()
        return []
        
def generate_diagnosis_report(output_file=None):
    """生成完整的诊断报告"""
    if output_file is None:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"memory_diagnosis_{timestamp}.txt"
    
    # 将输出重定向到文件
    original_stdout = sys.stdout
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            sys.stdout = f
            
            print("=" * 50)
            print("TianyuControl 内存诊断报告")
            print(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 50)
            
            # 系统资源分析
            analyze_system_resources()
            
            # 查找TianyuControl进程
            tianyucontrol_processes = find_tianyucontrol_process()
            
            # 如果找到了进程，分析第一个
            if tianyucontrol_processes:
                print("\n分析第一个找到的TianyuControl进程...")
                check_process_memory(tianyucontrol_processes[0].pid)
            
            # 当前进程的内存分析
            print("\n当前诊断进程内存分析:")
            check_process_memory()
            
            # 内存碎片分析
            check_memory_fragmentation()
            
            # 对象统计
            memory_object_analysis()
            
            # 内存泄漏检测
            find_memory_leaks()
            
            # 诊断建议
            print("\n== 诊断建议 ==")
            print("1. 确保使用最新版本的TianyuControl，已包含内存优化")
            print("2. 启动程序时启用内存优化: python main.py")
            print("3. 如果频繁发生内存问题，请定期重启应用程序")
            print("4. 检查系统资源使用情况，确保有足够的可用内存")
            print("5. 如有持续的内存问题，请联系开发团队并提供此诊断报告")
    
    except Exception as e:
        sys.stdout = original_stdout
        print(f"生成诊断报告时出错: {str(e)}")
        traceback.print_exc()
    
    # 恢复原始输出
    sys.stdout = original_stdout
    print(f"诊断报告已生成: {output_file}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TianyuControl 内存诊断工具')
    parser.add_argument('--report', action='store_true', help='生成完整诊断报告')
    parser.add_argument('--find-process', action='store_true', help='查找TianyuControl进程')
    parser.add_argument('--check-pid', type=int, help='检查特定PID的内存使用情况')
    parser.add_argument('--system', action='store_true', help='分析系统资源')
    parser.add_argument('--objects', action='store_true', help='分析内存中的对象')
    parser.add_argument('--leaks', action='store_true', help='检测内存泄漏')
    parser.add_argument('--fragmentation', action='store_true', help='检查内存碎片')
    parser.add_argument('--output', type=str, help='诊断报告输出文件')
    
    args = parser.parse_args()
    
    # 没有参数时，显示帮助信息
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # 生成完整诊断报告
    if args.report:
        generate_diagnosis_report(args.output)
        return
    
    # 查找TianyuControl进程
    if args.find_process:
        find_tianyucontrol_process()
    
    # 检查特定PID
    if args.check_pid:
        check_process_memory(args.check_pid)
    
    # 分析系统资源
    if args.system:
        analyze_system_resources()
    
    # 分析内存中的对象
    if args.objects:
        memory_object_analysis()
    
    # 检测内存泄漏
    if args.leaks:
        find_memory_leaks()
    
    # 检查内存碎片
    if args.fragmentation:
        check_memory_fragmentation()

if __name__ == "__main__":
    main() 