"""游戏控制模块 —— 主循环。

实现 ``game_loop`` 函数,驱动游戏的完整运行:初始化 pygame、双模式选择、
逐帧处理输入、更新玩家(移动 + 平台碰撞 + 回血 + 技能)、渲染场景 / 血条 /
计分板,并在单局 / 整场结束后进入结算,直到退出。

已整合的能力:
    - 双模式选择(快速 / 生存,``scoreboard.select_mode``)。
    - 双人移动 / 跳跃 / 重力 / 边界(move 模块)。
    - 悬浮平台碰撞:可跳上站立、左右对称(move.platform_collision + map)。
    - 生存模式计时回血、受击打断(blood 模块)。
    - 技能系统:技能触发 / 冷却 / 攻击范围 / 命中伤害(skill 模块)。
    - 实时血条(``draw_health_bar``)与常驻计分板(``scoreboard.draw_scoreboard``)。
    - 极简线条背景 + 悬浮平台(map 模块)。
    - 火柴人渲染(``character_render.draw_stickman``)。
    - 五局三胜计分、单局 / 整场结算、快速下一局(scoreboard 模块)。
"""

import pygame

from move.apply_gravity import apply_gravity
from move.update_position import update_position
from move.jump_logic import jump_logic
from move.platform_collision import resolve_platform_collision
from blood.update_heal_timer import update_heal_timer
from blood.update_hp import update_hp
from blood.interrupt_heal import interrupt_heal
from blood.draw_health_bar import draw_health_bar

import character_render
import map as map_module
import skill as skill_module
import scoreboard as scoreboard_module

from game_controller.get_global_context import get_global_context
from game_controller.init_game_context import (
    init_game_context,
    DEFAULT_SCREEN_WIDTH,
    DEFAULT_SCREEN_HEIGHT,
)

# ---- 常量(极简线条风格,按需调整) ----
FPS = 60
MOVE_SPEED = 300.0                 # 水平移动速度(像素 / 秒)
HEALTH_BAR_Y_OFFSET = 40.0         # 血条中心相对脚底的上移量(像素)
SKILL_DAMAGE = 25.0                # 技能单次命中造成的伤害

# 控制键映射:玩家0 / 玩家1 的 左 / 右 / 跳。
KEYMAP = {
    0: {'left': pygame.K_a, 'right': pygame.K_d, 'jump': pygame.K_w},
    1: {'left': pygame.K_LEFT, 'right': pygame.K_RIGHT, 'jump': pygame.K_UP},
}


def update_players(context, dt, platforms=None):
    """推进一帧:对所有玩家执行重力、位移、平台碰撞与回血计时。

    水平速度 ``vx`` 与起跳指令需在调用本函数之前由输入处理写入;本函数
    不依赖 pygame 显示,可独立测试。

    Args:
        context: 全局游戏上下文。
        dt: 本帧耗时(秒)。
        platforms: 当前帧悬浮平台几何(由 ``map.get_platforms`` 提供)。

    Returns:
        None,直接原地修改 ``context['players']``。
    """
    for p in context['players']:
        # 记录垂直积分前的脚底高度,供平台碰撞判断本帧是否越过台面。
        p['y_prev'] = p.get('y', 0.0)
        apply_gravity(p, dt)
        update_position(p, dt)
        resolve_platform_collision(p, platforms if platforms is not None else [])
        update_heal_timer(p, dt)


def _process_skills(context, held_keys):
    """处理本帧双方技能的触发与命中结算。

    对每个玩家依次:触发技能(冷却 / 攻击范围) -> 用攻击范围与对方身体
    命中框做碰撞 -> 命中则通过 ``update_hp`` 扣血。``skill.check_hit`` 会
    借助攻击者状态上的 ``skill_hit_players`` 抑制单次技能对同一目标的重复命中。

    Args:
        context: 全局游戏上下文。
        held_keys: 当前被按住按键的 ``set``(由 KEYDOWN / KEYUP 事件维护)。

    Returns:
        None,直接原地修改玩家血量 / 技能状态。
    """
    players = context['players']
    # skill._key_is_down 接受 dict(按键码 -> 布尔),由 held 集合构造。
    key_state = {key: True for key in held_keys}
    skill_results = {}
    for pid, p in enumerate(players):
        skill_results[pid] = skill_module.skill_trigger(
            pid, key_state, p, context['mode']
        )

    for pid in (0, 1):
        other = 1 - pid
        attacker = players[pid]
        defender = players[other]
        enemy_hitbox = character_render.get_player_hitbox(defender)
        for box in skill_results[pid]['hitboxes']:
            event = skill_module.check_hit(
                box, enemy_hitbox,
                attacker_id=pid,
                defender_id=other,
                damage=SKILL_DAMAGE,
                blood={'interrupt_heal': interrupt_heal},
                hit_players=attacker.get('skill_hit_players'),
                defender_state=defender,
            )
            if event and event.get('hit'):
                update_hp(defender, -event['damage'])


def game_loop(context=None, fps=FPS):
    """运行游戏主循环,直到退出。

    Args:
        context: 全局游戏上下文;为 ``None`` 时依次尝试读取全局上下文,
            若仍未初始化则先进入双模式选择界面再新建。
        fps: 目标帧率。

    Returns:
        退出时的全局上下文 ``dict``(若在模式选择阶段退出则返回 ``None``)。
    """
    ctx = context if context is not None else get_global_context()

    pygame.init()

    if not ctx:
        # 双模式选择界面:先建立窗口让玩家选择模式,再据此初始化上下文。
        # 注意:这里只创建一次窗口,后续直接复用同一 surface。避免再次调用
        # set_mode 重建窗口,否则新窗口会失去键盘焦点,导致方向 / 技能按键
        # (依赖 pygame.key.get_pressed)无响应。
        screen = pygame.display.set_mode((DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT))
        pygame.display.set_caption('2D 火柴人对战')
        mode = scoreboard_module.select_mode(screen)
        if mode is None:
            pygame.quit()
            return None
        ctx = init_game_context(mode=mode, screen_width=DEFAULT_SCREEN_WIDTH,
                                screen_height=DEFAULT_SCREEN_HEIGHT)
    else:
        screen = pygame.display.set_mode((ctx['screen_width'], ctx['screen_height']))
        pygame.display.set_caption('2D 火柴人对战')

    clock = pygame.time.Clock()

    # 当前被按住的按键集合:由 KEYDOWN / KEYUP 事件维护,比
    # pygame.key.get_pressed() 更可靠(后者在部分 Windows 环境下可能因窗口
    # 焦点等问题恒返回 0,导致方向 / 技能无响应)。
    held_keys = set()

    running = True
    while running:
        # --- 单局对战:循环到有一方阵亡 ---
        round_result = None
        while round_result is None and running:
            dt = clock.tick(fps) / 1000.0
            time_s = pygame.time.get_ticks() / 1000.0

            # --- 事件处理 ---
            jump_pressed = {0: False, 1: False}
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    held_keys.add(event.key)
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    for pid, keys in KEYMAP.items():
                        if event.key == keys['jump']:
                            jump_pressed[pid] = True
                elif event.type == pygame.KEYUP:
                    held_keys.discard(event.key)
            if not running:
                break

            # --- 输入 -> 水平速度 / 朝向 / 起跳 ---
            for pid, p in enumerate(ctx['players']):
                keys = KEYMAP[pid]
                if keys['left'] in held_keys:
                    p['vx'] = -MOVE_SPEED
                    p['facing'] = -1
                elif keys['right'] in held_keys:
                    p['vx'] = MOVE_SPEED
                    p['facing'] = 1
                else:
                    p['vx'] = 0.0
                jump_logic(p, jump_pressed[pid])

            # 当前帧平台几何:更新(碰撞)与渲染共用同一份,保证所见即所碰。
            platforms = map_module.get_platforms(ctx['round'], screen, time_s)

            # --- 推进一帧(重力 / 位移 / 平台碰撞 / 回血) ---
            update_players(ctx, dt, platforms)

            # --- 技能触发与命中结算 ---
            _process_skills(ctx, held_keys)

            # --- 渲染 ---
            map_module.draw_background(screen)
            map_module.update_dynamic_obstacle(ctx['round'], screen, time_s,
                                               platforms=platforms)
            for pid, p in enumerate(ctx['players']):
                character_render.draw_stickman(screen, pid, p)
                draw_health_bar(screen, (p['x'], p['y'] - HEALTH_BAR_Y_OFFSET),
                                p['hp'], p['max_hp'])
            scoreboard_module.draw_scoreboard(screen, ctx)
            pygame.display.flip()

            # --- 单局结束判定 ---
            round_result = scoreboard_module.check_round_end(ctx)

        if not running:
            break

        # 结算画面会消费此期间的按键事件,清空 held 状态避免带入下一局
        # (否则结算时松开的按键会被误判为仍处于按住状态)。
        held_keys.clear()

        # --- 单局结算:计分并展示 ---
        if round_result != 'draw':
            scoreboard_module.award_round(ctx, round_result)
        if not scoreboard_module.draw_round_result(screen, ctx, round_result):
            running = False
            break

        # --- 整场判定 ---
        match_winner = scoreboard_module.check_match_end(ctx)
        if match_winner is not None:
            action = scoreboard_module.draw_match_result(screen, ctx, match_winner)
            if action == 'quit':
                running = False
            else:
                scoreboard_module.reset_match(ctx)
        else:
            scoreboard_module.reset_round(ctx)

    pygame.quit()
    return ctx
