# threading.Thread 是Python标准库中用于创建和管理线程的核心类，它提供了多线程编程的基础功能。
import threading

# 创建线程
thread = threading.Thread(
    target=callable,  # 要在线程中执行的函数
    args=tuple,  # 传递给目标函数的参数元组
    kwargs=dict,  # 传递给目标函数的关键字参数字典
    name=str,  # 线程名称
    daemon=bool,  # 是否为守护线程
    group=None,  # 线程组（通常为None）
)

# 启动线程
thread.start()

# 等待线程完成
thread.join()
