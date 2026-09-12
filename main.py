"""程序入口。

轻量启动脚本:直接调用 ``game_controller.game_loop.game_loop``,由主循环
负责初始化 pygame、展示双模式选择界面并驱动整场对战。

    python main.py
"""

from game_controller.game_loop import game_loop


if __name__ == "__main__":
    game_loop()
