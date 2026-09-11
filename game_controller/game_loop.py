"""游戏控制模块 —— 主循环。

实现 ``game_loop`` 函数,驱动游戏的完整运行:初始化 pygame、逐帧处理
输入、更新玩家(移动 + 回血)、渲染场景与血条,直到退出。

当前已整合的能力:
    - 双人移动 / 跳跃 / 重力 / 边界(move 模块)。
    - 生存模式计时回血、受击打断(blood 模块)。
    - 实时血条(``draw_health_bar``)。
    - 极简线条地面 + 火柴人渲染。

尚未实现(后续模块接入时补全,预留在此说明):
    - 技能系统(攻击范围 / 冷却 / 命中伤害,届时在事件处理与更新阶段接入
      ``update_hp`` 与 ``interrupt_heal``)。
    - 五局三胜计分与单局结算、快速下一局。
    - 第五局动态悬空障碍。
    - 双模式选择界面(当前模式由 ``init_game_context`` 的 ``mode`` 参数决定)。
"""

import pygame

from move.apply_gravity import apply_gravity
from move.update_position import update_position
from move.jump_logic import jump_logic
from blood.update_heal_timer import update_heal_timer
from blood.draw_health_bar import draw_health_bar

from game_controller.get_global_context import get_global_context
from game_controller.init_game_context import init_game_context

# ---- 常量(极简线条风格,按需调整) ----
FPS = 60
MOVE_SPEED = 300.0                 # 水平移动速度(像素 / 秒)
BG_COLOR = (24, 24, 28)            # 背景色
GROUND_COLOR = (255, 255, 255)     # 地面线颜色
STICK_HEIGHT = 70.0                # 火柴人总高(脚底到头顶)
HEAD_RADIUS = 10.0                 # 头部半径

# 控制键映射:玩家0 / 玩家1 的 左 / 右 / 跳。
KEYMAP = {
    0: {'left': pygame.K_a, 'right': pygame.K_d, 'jump': pygame.K_w},
    1: {'left': pygame.K_LEFT, 'right': pygame.K_RIGHT, 'jump': pygame.K_UP},
}


def update_players(context, dt):
    """推进一帧:对所有玩家执行重力、位移与回血计时。

    水平速度 ``vx`` 与起跳指令需在调用本函数之前由输入处理写入;本函数
    不依赖 pygame 显示,可独立测试。

    Args:
        context: 全局游戏上下文。
        dt: 本帧耗时(秒)。

    Returns:
        None,直接原地修改 ``context['players']``。
    """
    for p in context['players']:
        apply_gravity(p, dt)
        update_position(p, dt)
        update_heal_timer(p, dt)


def _draw_ground(screen, context):
    """绘制地面线。"""
    pygame.draw.line(screen, GROUND_COLOR,
                     (0, context['ground_y']),
                     (context['screen_width'], context['ground_y']), 2)


def _draw_stickman(screen, player):
    """以脚底 ``(x, y)`` 为基准绘制火柴人(极简线条风格)。"""
    x = player['x']
    y = player['y']
    color = player['color']
    pygame.draw.circle(screen, color, (int(x), int(y - 60)), int(HEAD_RADIUS), 2)  # 头
    pygame.draw.line(screen, color, (x, y - 50), (x, y - 25), 2)                    # 躯干
    pygame.draw.line(screen, color, (x, y - 45), (x - 15, y - 32), 2)               # 左臂
    pygame.draw.line(screen, color, (x, y - 45), (x + 15, y - 32), 2)               # 右臂
    pygame.draw.line(screen, color, (x, y - 25), (x - 13, y), 2)                    # 左腿
    pygame.draw.line(screen, color, (x, y - 25), (x + 13, y), 2)                    # 右腿


def game_loop(context=None, fps=FPS):
    """运行游戏主循环,直到退出。

    Args:
        context: 全局游戏上下文;为 ``None`` 时依次尝试读取全局上下文,
            若仍未初始化则用默认参数新建。
        fps: 目标帧率。

    Returns:
        退出时的全局上下文 ``dict``。
    """
    ctx = context if context is not None else get_global_context()
    if not ctx:
        ctx = init_game_context()

    pygame.init()
    screen = pygame.display.set_mode((ctx['screen_width'], ctx['screen_height']))
    pygame.display.set_caption('2D 火柴人对战')
    clock = pygame.time.Clock()

    running = True
    while running:
        dt = clock.tick(fps) / 1000.0

        # --- 事件处理 ---
        jump_pressed = {0: False, 1: False}
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                for pid, keys in KEYMAP.items():
                    if event.key == keys['jump']:
                        jump_pressed[pid] = True

        # --- 输入 -> 水平速度 / 起跳 ---
        pressed = pygame.key.get_pressed()
        for pid, p in enumerate(ctx['players']):
            keys = KEYMAP[pid]
            if pressed[keys['left']]:
                p['vx'] = -MOVE_SPEED
            elif pressed[keys['right']]:
                p['vx'] = MOVE_SPEED
            else:
                p['vx'] = 0.0
            jump_logic(p, jump_pressed[pid])

        # --- 推进一帧(重力 / 位移 / 回血) ---
        update_players(ctx, dt)

        # --- 渲染 ---
        screen.fill(BG_COLOR)
        _draw_ground(screen, ctx)
        for p in ctx['players']:
            _draw_stickman(screen, p)
            draw_health_bar(screen, (p['x'], p['y'] - STICK_HEIGHT / 2),
                            p['hp'], p['max_hp'])
        pygame.display.flip()

    pygame.quit()
    return ctx
