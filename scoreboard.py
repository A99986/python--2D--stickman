"""计分板模块 —— 五局三胜计分、单局 / 整场结算与双模式选择。

实现整场比赛的计分与回合流转,并把分数、局数、单局 / 整场结算画面与
双模式选择界面渲染到屏幕上:

    - 计分规则:五局三胜(先赢 ``WIN_SCORE`` 局者获胜),局分记录在
      ``context['score']``(``[玩家0局分, 玩家1局分]``)。
    - 单局结算:某方血量归零即本局结束,展示获胜方并等待按键进入下一局。
    - 整场结算:某方先到 ``WIN_SCORE`` 分即整场结束,可重开或退出。
    - 常驻计分板:对局进行中在屏幕顶部显示局数与双方比分。
    - 模式选择:启动时进入「快速 / 生存」双模式选择界面。

本模块中,``check_round_end`` / ``award_round`` / ``check_match_end`` /
``reset_round`` / ``reset_match`` 为纯逻辑函数,不依赖显示,可独立测试;
``draw_*`` 与 ``select_mode`` 需要已初始化的 ``pygame`` 显示表面。
"""

import pygame

from character_render import PLAYER_COLORS

# ---- 计分规则常量 ----
WIN_SCORE = 3        # 五局三胜:先赢得 3 局者获胜
TOTAL_ROUNDS = 5     # 单场最多 5 局(先到 3 分即提前结束)

# ---- 玩家显示名(与 PLAYER_COLORS 顺序一致:0 青蓝 / 1 红) ----
PLAYER_NAMES = {0: "蓝方", 1: "红方"}

# ---- UI 常量(极简线条风格,按需调整) ----
PAPER_BG = (239, 241, 237)     # 与 map.SKY_PAPER 一致的浅纸色
INK = (55, 58, 57)             # 与 map.GROUND_LINE 一致的深墨色
HINT = (95, 101, 101)          # 次要提示文字颜色
SCORE_FONT_SIZE = 26
RESULT_FONT_SIZE = 60
TITLE_FONT_SIZE = 44
OPTION_FONT_SIZE = 30
SMALL_FONT_SIZE = 22

# 常见中文字体路径(Windows),按优先级依次尝试,均不存在时回退默认字体。
_FONT_PATHS = (
    "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
    "C:/Windows/Fonts/simhei.ttf",    # 黑体
    "C:/Windows/Fonts/simsun.ttc",    # 宋体
    "C:/Windows/Fonts/Deng.ttf",      # 等线
)

# 字体缓存:按 (size, bold) 复用,避免每帧重复加载 / 渲染字体。
_FONT_CACHE = {}


def _get_font(size, bold=False):
    """返回支持中文的字体,找不到时回退到 pygame 默认字体。

    直接加载字体文件而非 ``pygame.font.SysFont``,以规避 SysFont 在部分
    Windows 环境扫描字体注册表时的兼容性问题,同时用缓存降低开销。
    """
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    font = None
    for path in _FONT_PATHS:
        try:
            font = pygame.font.Font(path, size)
            font.set_bold(bold)
            break
        except Exception:
            continue

    if font is None:
        font = pygame.font.Font(None, size)
        font.set_bold(bold)

    _FONT_CACHE[key] = font
    return font


def _draw_text(screen, text, size, color, center, bold=False):
    """在 ``screen`` 上绘制一条居中文本,返回其 ``pygame.Rect``。"""
    font = _get_font(size, bold)
    surface = font.render(text, True, color)
    rect = surface.get_rect(center=(int(center[0]), int(center[1])))
    screen.blit(surface, rect)
    return rect


def _draw_overlay(screen, alpha=170):
    """在屏幕上叠一层半透明深色遮罩,用于结算画面。"""
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((20, 24, 26, alpha))
    screen.blit(overlay, (0, 0))


# ---- 纯逻辑:回合 / 整场流转 ----

def check_round_end(context):
    """检测单局是否结束。

    Args:
        context: 全局游戏上下文(含 ``players``)。

    Returns:
        ``None`` 表示局内继续;``0`` / ``1`` 表示获胜玩家;
        ``'draw'`` 表示双方同时阵亡(平局,不产生局分)。
    """
    if not context:
        return None
    players = context.get('players', [])
    if len(players) < 2:
        return None

    dead = [p.get('hp', 0) <= 0 for p in players[:2]]
    if dead[0] and dead[1]:
        return 'draw'
    if dead[0]:
        return 1
    if dead[1]:
        return 0
    return None


def award_round(context, winner_id):
    """给获胜玩家加一局分,并推进到下一局。

    平局(``'draw'``)不调用本函数;``winner_id`` 非法时不做任何修改。
    """
    if not context:
        return
    score = context.setdefault('score', [0, 0])
    if 0 <= winner_id < len(score):
        score[winner_id] += 1
    context['round'] = min(context.get('round', 1) + 1, TOTAL_ROUNDS)


def check_match_end(context):
    """检测是否已有玩家率先赢得整场比赛。

    Returns:
        获胜玩家 ``0`` / ``1``;尚未结束时返回 ``None``。
    """
    if not context:
        return None
    score = context.get('score', [0, 0])
    for pid in (0, 1):
        if pid < len(score) and score[pid] >= WIN_SCORE:
            return pid
    return None


def _reset_player(context, player):
    """把单个玩家状态恢复到每局开局(保留 ``max_hp`` / 回血等配置)。"""
    width = context.get('screen_width', 1280)
    ground_y = context.get('ground_y', 600.0)
    pid = player.get('id', 0)

    player['x'] = width * (0.25 if pid == 0 else 0.75)
    player['y'] = ground_y
    player['vx'] = 0.0
    player['vy'] = 0.0
    player['on_ground'] = True
    player['facing'] = 1 if pid == 0 else -1
    player['ground_y'] = ground_y
    player['hp'] = player.get('max_hp', 100.0)
    player['heal_timer'] = player.get('heal_interval', 0.0)
    player['moving'] = False
    player['action'] = 'idle'
    player['anim_time'] = 0.0

    # 清空技能残留状态(冷却 / 命中记录),避免跨局继承。
    for key in ('skill_started_at', 'skill_active_until',
                'skill_cooldown_until', 'skill_key_was_down',
                'skill_hit_players'):
        player.pop(key, None)


def reset_round(context):
    """把双方玩家恢复到开局位置 / 血量,准备下一局(不改变比分与局数)。"""
    if not context:
        return
    for player in context.get('players', []):
        _reset_player(context, player)


def reset_match(context):
    """重置整场比赛:比分归零、局数回到第 1 局、玩家复位。"""
    if not context:
        return
    context['score'] = [0, 0]
    context['round'] = 1
    reset_round(context)


# ---- 绘制:常驻计分板 ----

def draw_scoreboard(screen, context):
    """在屏幕顶部绘制局数与双方比分(每帧调用)。

    Args:
        screen: 目标 ``pygame.Surface``。
        context: 全局游戏上下文。

    Returns:
        None,直接绘制到 ``screen`` 上。
    """
    if not screen or not context:
        return
    width, _ = screen.get_size()
    score = context.get('score', [0, 0])
    round_no = context.get('round', 1)

    _draw_text(screen, f"蓝方 {score[0]}", SCORE_FONT_SIZE,
               PLAYER_COLORS[0], (width * 0.18, 26), bold=True)
    _draw_text(screen, f"第 {round_no} 局 / 五局三胜", SCORE_FONT_SIZE,
               INK, (width * 0.5, 26))
    _draw_text(screen, f"红方 {score[1]}", SCORE_FONT_SIZE,
               PLAYER_COLORS[1], (width * 0.82, 26), bold=True)


# ---- 绘制:结算画面 ----

def draw_round_result(screen, context, result):
    """展示单局结算画面,阻塞等待玩家按键。

    Args:
        screen: 目标 ``pygame.Surface``。
        context: 全局游戏上下文。
        result: ``0`` / ``1`` 表示获胜玩家,``'draw'`` 表示平局。

    Returns:
        ``True`` 表示进入下一局;``False`` 表示退出(ESC / 关闭窗口)。
    """
    clock = pygame.time.Clock()
    width, height = screen.get_size()
    score = context.get('score', [0, 0])

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    return True

        _draw_overlay(screen)

        if result == 'draw':
            title = "平局!"
            title_color = (240, 240, 240)
        else:
            title = f"{PLAYER_NAMES[result]}获胜!"
            title_color = PLAYER_COLORS[result]

        _draw_text(screen, title, RESULT_FONT_SIZE, title_color,
                   (width * 0.5, height * 0.38), bold=True)
        _draw_text(screen, f"当前比分    蓝方 {score[0]} : {score[1]} 红方",
                   OPTION_FONT_SIZE, (240, 240, 240),
                   (width * 0.5, height * 0.52))
        _draw_text(screen, "按 空格 / 回车 进入下一局", SMALL_FONT_SIZE,
                   HINT, (width * 0.5, height * 0.68))

        pygame.display.flip()
        clock.tick(60)


def draw_match_result(screen, context, winner_id):
    """展示整场结算画面,阻塞等待玩家选择重开或退出。

    Returns:
        ``'restart'`` 表示重新开始一场比赛,``'quit'`` 表示退出。
    """
    clock = pygame.time.Clock()
    width, height = screen.get_size()
    score = context.get('score', [0, 0])

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'quit'
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return 'quit'
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    return 'restart'

        _draw_overlay(screen)

        _draw_text(screen, f"{PLAYER_NAMES[winner_id]}赢得比赛!",
                   RESULT_FONT_SIZE, PLAYER_COLORS[winner_id],
                   (width * 0.5, height * 0.34), bold=True)
        _draw_text(screen, f"最终比分    蓝方 {score[0]} : {score[1]} 红方",
                   OPTION_FONT_SIZE, (240, 240, 240),
                   (width * 0.5, height * 0.48))
        _draw_text(screen, "按 空格 / 回车 重新开始", SMALL_FONT_SIZE,
                   HINT, (width * 0.5, height * 0.62))
        _draw_text(screen, "按 ESC 退出", SMALL_FONT_SIZE,
                   HINT, (width * 0.5, height * 0.68))

        pygame.display.flip()
        clock.tick(60)


# ---- 模式选择 ----

def select_mode(screen):
    """双模式选择界面,阻塞等待玩家选择。

    Returns:
        ``'quick'``(快速模式,不可回血)或 ``'survival'``(生存模式,可计时回血);
        玩家按 ESC 或关闭窗口时返回 ``None``。
    """
    clock = pygame.time.Clock()
    width, height = screen.get_size()
    cx = width * 0.5

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_1, pygame.K_q):
                    return 'quick'
                if event.key in (pygame.K_2, pygame.K_s):
                    return 'survival'

        screen.fill(PAPER_BG)

        _draw_text(screen, "2D 火柴人对战", TITLE_FONT_SIZE, INK,
                   (cx, height * 0.16), bold=True)
        _draw_text(screen, "选择游戏模式", OPTION_FONT_SIZE, INK,
                   (cx, height * 0.28))

        _draw_text(screen, "[ 1 ]  快速模式   ——   不可回血",
                   OPTION_FONT_SIZE, PLAYER_COLORS[0],
                   (cx, height * 0.42), bold=True)
        _draw_text(screen, "[ 2 ]  生存模式   ——   可计时回血",
                   OPTION_FONT_SIZE, PLAYER_COLORS[1],
                   (cx, height * 0.52), bold=True)

        _draw_text(screen, "蓝方: A / D 移动    W 跳    F 技能",
                   SMALL_FONT_SIZE, HINT, (cx, height * 0.68))
        _draw_text(screen, "红方: ← / → 移动    ↑ 跳    \\ 技能",
                   SMALL_FONT_SIZE, HINT, (cx, height * 0.75))
        _draw_text(screen, "按 1 / 2 选择, ESC 退出",
                   SMALL_FONT_SIZE, HINT, (cx, height * 0.86))

        pygame.display.flip()
        clock.tick(60)
