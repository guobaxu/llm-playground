import asyncio
import time


# 1. async def
# async def用于定义异步函数，这种函数可以在执行过程中暂停和恢复。
# -异步函数必须用async def定义
# -调用异步函数会返回一个协程对象，需要用await或asyncio.run()来执行
# -异步函数内部可以使用await关键字
async def async_function():
    # 异步函数体
    pass


# 2. await
# await用于等待异步操作完成，只能在async def函数内使用。

# 3. 执行异步函数的三种方式
# 方式1: 使用 asyncio.run() (推荐用于主程序)
asyncio.run(async_function())


# 方式2: 使用 await (在async函数内)
async def main():
    await async_function()


# 方式3: 使用 asyncio.create_task() (创建任务)
async def example_with_task():
    task = asyncio.create_task(async_function())
    await task


# 4. 示例——并发执行多个异步函数
async def task(name, delay):
    print(f"任务 {name} 开始")
    await asyncio.sleep(delay)
    print(f"任务 {name} 完成")
    return f"结果 {name}"


async def main():
    # 方法1: 使用 asyncio.gather() 并发执行
    results = await asyncio.gather(task("A", 2), task("B", 1), task("C", 3))
    print("所有结果:", results)


asyncio.run(main())

"""
output:
任务 A 开始
任务 B 开始
任务 C 开始
任务 B 完成
任务 A 完成
任务 C 完成
所有结果: ['结果 A', '结果 B', '结果 C']    # 结果顺序保持
"""
