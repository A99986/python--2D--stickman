"""游戏控制模块 —— 初始化游戏上下文。

实现 ``init_game_context`` 函数,构建一个完整的全局游戏上下文(含两个玩家的
移动 + 血量状态、游戏模式、计分与回合信息),并通过 ``set_global_context``
保存,供 ``get_global_context`` 在其它模块中读取。

上下文结构(``dict``):
    - ``mode``: 游戏模式,``'quick'``(快速,不可回血)或 ``'survival'``(生存,可回血)。
    - ``round``: 当前局数(1 ~ 5),五局三胜。
    - ``score``: ``[玩家0局分, 玩家1局分]``。
    - ``players``: 两个玩家状态的 ``list``,每个是移动 + 血量字段的 ``dict``。
    - ``screen_width`` / ``screen_height``: 屏幕尺寸。
    - ``ground_y``: 地面线纵坐标(同时存在于各玩家状态中,供移动模块使用)。

玩家状态字段(与 move / blood 模块约定一致):
    - 移动:``x`` / ``y`` / ``vx`` / ``vy`` / ``on_ground`` / ``ground_y`` /
      ``gravity`` / ``jump_speed`` / ``min_x`` / ``max_x``。
    - 血量:``hp`` / ``max_hp`` / ``heal_timer`` / ``heal_interval`` / ``heal_amount``。
    - 标识:``id`` / ``color``。
"""

from move.apply_gravity import DEFAULT_GRAVITY
from move.jump_logic import DEFAULT_JUMP_SPEED

from .get_global_context import set_global_context

# ---- 默认参数(极简线条风格,按需调整) ----
DEFAULT_SCREEN_WIDTH = 1280
DEFAULT_SCREEN_HEIGHT = 720
DEFAULT_MAX_HP = 100.0
DEFAULT_HEAL_INTERVAL = 5.0    # 生存模式回血间隔(秒)
DEFAULT_HEAL_AMOUNT = 10.0     # 生存模式每次回血量

GROUND_MARGIN = 120            # 地面距屏幕底部的预留空间(像素)

# 两个玩家的默认颜色(极简线条,用于区分,按需调整)。
PLAYER_COLORS = [(80, 200, 255), (255, 120, 120)]


def init_game_context(mode='survival', screen_width=DEFAULT_SCREEN_WIDTH,
                      screen_height=DEFAULT_SCREEN_HEIGHT, max_hp=DEFAULT_MAX_HP,
                      heal_interval=DEFAULT_HEAL_INTERVAL,
                      heal_amount=DEFAULT_HEAL_AMOUNT):
    """初始化全局游戏上下文并保存。

    Args:
        mode: 游戏模式,``'quick'`` 或 ``'survival'``(非法值回退为 survival)。
        screen_width: 屏幕宽度(像素)。
        screen_height: 屏幕高度(像素)。
        max_hp: 玩家最大血量。
        heal_interval: 生存模式回血间隔(秒);快速模式强制为 0(关闭回血)。
        heal_amount: 生存模式每次回血量。

    Returns:
        构建好的全局上下文 ``dict``(同时已保存到全局,可经
        ``get_global_context`` 读取)。
    """
    if mode not in ('quick', 'survival'):
        mode = 'survival'

    if max_hp <= 0:
        max_hp = DEFAULT_MAX_HP

    ground_y = float(screen_height - GROUND_MARGIN)

    # 快速模式不开启回血,把回血间隔置 0(move/blood 约定:<=0 即关闭)。
    if mode == 'quick':
        heal_interval = 0.0

    def _make_player(pid, x):
        """按玩家 id 与初始横坐标构造一个完整的玩家状态。"""
        return {
            # 移动字段
            'x': float(x),
            'y': ground_y,
            'vx': 0.0,
            'vy': 0.0,
            'on_ground': True,
            'facing': 1 if pid == 0 else -1,
            'ground_y': ground_y,
            'gravity': DEFAULT_GRAVITY,
            'jump_speed': DEFAULT_JUMP_SPEED,
            'min_x': 0.0,
            'max_x': float(screen_width),
            # 血量字段
            'hp': float(max_hp),
            'max_hp': float(max_hp),
            'heal_timer': float(heal_interval),
            'heal_interval': float(heal_interval),
            'heal_amount': float(heal_amount),
            # 标识
            'id': pid,
            'color': PLAYER_COLORS[pid],
        }

    players = [
        _make_player(0, screen_width * 0.25),
        _make_player(1, screen_width * 0.75),
    ]

    context = {
        'mode': mode,
        'round': 1,
        'score': [0, 0],
        'players': players,
        'screen_width': screen_width,
        'screen_height': screen_height,
        'ground_y': ground_y,
    }

    set_global_context(context)
    return context
