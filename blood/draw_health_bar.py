"""血条反馈模块 —— 血条绘制。

实现 ``draw_health_bar`` 函数,在火柴人角色头顶绘制实时血条 UI。

接口与《调整后的接口文档》3.5 节保持一致:
    draw_health_bar(screen, player_pos, hp, max_hp)

血条样式遵循小组调研结论(竞品「火柴人对决」可借鉴设计):
    - 底色红色(表示已损失血量)
    - 剩余血量绿色
    - 白色细边框,贴合项目「极简线条」整体风格
"""

import pygame


# ---- 血条样式常量(极简线条风格,按需调整) ----
BAR_WIDTH = 50        # 血条总宽度(像素)
BAR_HEIGHT = 8        # 血条总高度(像素)
BAR_OFFSET_Y = 34     # 血条底边相对角色中心点上移的距离,使血条悬于头顶上方
BORDER_COLOR = (255, 255, 255)   # 边框:白色细线
BG_COLOR = (220, 60, 60)         # 底色:红(已损失血量)
FILL_COLOR = (80, 200, 90)       # 剩余血量:绿


def draw_health_bar(screen, player_pos, hp, max_hp):
    """在角色头顶绘制实时血条。

    Args:
        screen: ``pygame.Surface``,目标绘制表面(通常为游戏主窗口)。
        player_pos: 角色中心坐标 ``(x, y)``,由 ``move.get_player_state`` 提供;
            兼容 tuple / list / ``pygame.math.Vector2`` 等可解包对象。
        hp: 当前血量。
        max_hp: 最大血量。

    Returns:
        None,直接绘制到 ``screen`` 上,不返回任何值。
    """
    # 防御:最大血量为 0 或负值时无法计算占比,直接返回避免除零。
    if max_hp <= 0:
        return

    # 解包角色中心坐标。
    x, y = player_pos

    # 当前血量钳位到 [0, max_hp],避免负数或越界。
    hp = max(0.0, min(float(hp), float(max_hp)))
    ratio = hp / float(max_hp)

    # 血条矩形:以角色中心 x 居中,顶边位于头顶上方。
    left = int(x - BAR_WIDTH / 2)
    top = int(y - BAR_OFFSET_Y)
    bar_rect = pygame.Rect(left, top, BAR_WIDTH, BAR_HEIGHT)

    # 1) 底色层:红色铺满整条血条,表示已损失的血量。
    pygame.draw.rect(screen, BG_COLOR, bar_rect)

    # 2) 剩余血量层:绿色按占比填充,与边框保留 1px 内边距,更显线条感。
    if ratio > 0.0:
        fill_width = int((BAR_WIDTH - 2) * ratio)
        if fill_width > 0:
            fill_rect = pygame.Rect(left + 1, top + 1, fill_width, BAR_HEIGHT - 2)
            pygame.draw.rect(screen, FILL_COLOR, fill_rect)

    # 3) 边框层:白色细边框,勾勒血条轮廓(极简线条风格)。
    pygame.draw.rect(screen, BORDER_COLOR, bar_rect, width=1)
