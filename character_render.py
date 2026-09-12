"""Character rendering for the two-player stickman arena.

This module owns the visual side of the characters.  It deliberately does not
simulate movement: ``draw_stickman`` only consumes the state produced by the
move module and translates it into animated line poses.

Expected player state fields
----------------------------
The move module can pass either a ``dict`` or any object with attributes:

- ``x``, ``y``: current foot-centre position on screen.
- ``vx``, ``vy``: horizontal and vertical velocity.
- ``facing``: ``1`` faces right, ``-1`` faces left.
- ``on_ground``: bool, used to choose jump/fall vs ground poses.
- ``standing_platform``: optional platform index maintained by ``move.py``.
- ``action``: optional explicit pose such as ``"idle"``, ``"run"``,
  ``"jump"``, ``"fall"``, ``"attack"``, ``"skill"``, ``"hit"`` or
  ``"block"``.
- ``anim_time``: seconds elapsed for the run cycle, defaulting to Pygame's
  own clock when omitted.
"""

import math

import pygame

from map import get_ground_y

PLAYER_COLORS = {
    0: (80, 200, 255),   # player 0 (cyan)
    1: (255, 120, 120),  # player 1 (light red)
}

SHADOW_COLOR = (73, 79, 76)

HEAD_RADIUS = 9
TORSO_LENGTH = 27
LEG_LENGTH = 28
LIMB_WIDTH = 3

SWORD_LENGTH = 66
SWORD_BLADE = (228, 234, 229)
SWORD_EDGE = (48, 54, 54)
SWORD_GUARD = (185, 192, 187)
SWORD_GRIP = (97, 102, 99)
SWORD_ANGLE_START = -1.4  # 前方头顶起劈(cos>0,全程位于面朝方向)
SWORD_ANGLE_END = 0.4     # 向前下方劈落

POSE_NAMES = (
    "idle",
    "run",
    "jump",
    "fall",
    "attack",
    "skill",
    "hit",
    "block",
)


def _state_get(state, key, default=None):
    """Read a value from either a dict or a move-module object."""
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def _resolve_action(state, vy, on_ground, moving):
    """Choose a pose from explicit state or from the motion itself."""
    action = _state_get(state, "action", "")

    if action == "move_left" or action == "move_right":
        action = "run"
    elif action == "gravity" or action == "falling":
        action = "fall"

    if action in POSE_NAMES:
        return action

    if not on_ground:
        return "jump" if vy < -1 else "fall"

    return "run" if moving else "idle"


def _build_pose(action, anim_time):
    """Return unscaled local pose points.

    Local coordinates use the foot centre as ``(0, 0)``.  Positive ``x`` points
    in the character's facing direction and negative ``y`` points upward.
    """
    hip = (0, -LEG_LENGTH)
    shoulder = (0, -LEG_LENGTH - TORSO_LENGTH)
    head = (0, shoulder[1] - HEAD_RADIUS - 2)

    if action == "run":
        phase = anim_time * 10.0
        swing = math.sin(phase)
        left_foot = (-8, -max(0.0, swing) * 11)
        right_foot = (8, -max(0.0, -swing) * 11)
        left_hand = (-11 + swing * 7, shoulder[1] + 13)
        right_hand = (11 - swing * 7, shoulder[1] + 13)

    elif action == "jump":
        hip = (0, -26)
        shoulder = (0, -53)
        head = (1, -63)
        left_foot = (-7, -8)
        right_foot = (10, -15)
        left_hand = (-14, -48)
        right_hand = (14, -48)

    elif action == "fall":
        hip = (0, -26)
        shoulder = (0, -53)
        head = (0, -63)
        left_foot = (-12, -6)
        right_foot = (12, -16)
        left_hand = (-16, -48)
        right_hand = (16, -48)

    elif action == "attack":
        hip = (-2, -27)
        shoulder = (5, -54)
        head = (10, -65)
        left_foot = (-13, 0)
        right_foot = (16, -4)
        left_hand = (-10, -41)
        right_hand = (28, -47)

    elif action == "skill":
        hip = (-3, -25)
        shoulder = (4, -52)
        head = (9, -63)
        left_foot = (-15, -2)
        right_foot = (18, -9)
        left_hand = (-9, -43)
        right_hand = (34, -50)

    elif action == "hit":
        hip = (0, -27)
        shoulder = (-3, -54)
        head = (-2, -64)
        left_foot = (-10, -2)
        right_foot = (10, 2)
        left_hand = (-8, -40)
        right_hand = (8, -44)

    elif action == "block":
        hip = (0, -27)
        shoulder = (0, -54)
        head = (0, -64)
        left_foot = (-11, 0)
        right_foot = (11, 0)
        left_hand = (-5, -50)
        right_hand = (5, -50)

    else:  # idle
        left_foot = (-9, 0)
        right_foot = (9, 0)
        left_hand = (-12, shoulder[1] + 13)
        right_hand = (12, shoulder[1] + 13)

    return {
        "hip": hip,
        "shoulder": shoulder,
        "head": head,
        "left_foot": left_foot,
        "right_foot": right_foot,
        "left_hand": left_hand,
        "right_hand": right_hand,
    }


def _to_screen(origin, point, facing, scale):
    """Convert a local pose point to a screen point."""
    x, y = origin
    lx, ly = point
    return (
        int(round(x + lx * facing * scale)),
        int(round(y + ly * scale)),
    )


def _draw_skill_effect(screen, origin, facing, scale, anim_time, color, progress=None):
    """Draw the sword slash and energy burst used by the skill pose."""
    x, y = origin
    centre = (
        int(round(x + facing * 28 * scale)),  # 光晕前移到前方
        int(round(y - (LEG_LENGTH + TORSO_LENGTH) * scale)),
    )
    radius = int(round((LEG_LENGTH + TORSO_LENGTH + 18) * scale))

    if progress is None:
        progress = (math.sin(anim_time * 6.0) + 1.0) / 2.0
    progress = min(1.0, max(0.0, float(progress)))
    eased = 0.5 - 0.5 * math.cos(math.pi * progress)

    pose = _build_pose("skill", anim_time)
    hand = _to_screen(origin, pose["right_hand"], facing, scale)

    # The blade starts raised behind the player and sweeps forward. Using
    # ``facing`` only on the x component mirrors the motion for both sides.
    angle = SWORD_ANGLE_START + (SWORD_ANGLE_END - SWORD_ANGLE_START) * eased
    direction = (facing * math.cos(angle), math.sin(angle))
    length = math.hypot(*direction)
    if length <= 1e-6:
        direction = (float(facing), 0.0)
    else:
        direction = (direction[0] / length, direction[1] / length)

    # A soft moving trail shows the path the blade just travelled.
    trail = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    blade_length = SWORD_LENGTH * scale
    for i in range(6):
        ghost_progress = progress - (i + 1) * 0.09
        if ghost_progress < 0.02:
            continue
        ghost_eased = 0.5 - 0.5 * math.cos(math.pi * ghost_progress)
        ghost_angle = SWORD_ANGLE_START + (
            SWORD_ANGLE_END - SWORD_ANGLE_START
        ) * ghost_eased
        ghost_dir = (facing * math.cos(ghost_angle), math.sin(ghost_angle))
        ghost_tip = (
            int(round(hand[0] + ghost_dir[0] * blade_length * 0.92)),
            int(round(hand[1] + ghost_dir[1] * blade_length * 0.92)),
        )
        alpha = max(20, int(150 - i * 24))
        ghost_color = (color[0], color[1], color[2], alpha)
        pygame.draw.line(
            trail, ghost_color, hand, ghost_tip, max(2, int(3 * scale))
        )
    screen.blit(trail, (0, 0))

    # Keep the existing energy ring as a readable magic aura behind the blade.
    pygame.draw.circle(screen, color, centre, max(1, int(radius * progress)), 2)
    for i in range(7):
        ring_angle = anim_time * 5.0 + i * math.tau / 7.0
        inner = radius * (0.48 + progress * 0.12)
        outer = radius * (0.82 + progress * 0.18)
        ring_start = (
            int(round(centre[0] + math.cos(ring_angle) * inner)),
            int(round(centre[1] + math.sin(ring_angle) * inner)),
        )
        ring_end = (
            int(round(centre[0] + math.cos(ring_angle) * outer)),
            int(round(centre[1] + math.sin(ring_angle) * outer)),
        )
        pygame.draw.line(screen, color, ring_start, ring_end, 2)

    # Sword geometry is built around the skill pose's extended right hand.
    grip_start = (
        int(round(hand[0] - direction[0] * 5 * scale)),
        int(round(hand[1] - direction[1] * 5 * scale)),
    )
    grip_end = (
        int(round(hand[0] + direction[0] * 6 * scale)),
        int(round(hand[1] + direction[1] * 6 * scale)),
    )
    blade_start = (
        int(round(hand[0] + direction[0] * 8 * scale)),
        int(round(hand[1] + direction[1] * 8 * scale)),
    )
    blade_end = (
        int(round(hand[0] + direction[0] * (8 * scale + blade_length))),
        int(round(hand[1] + direction[1] * (8 * scale + blade_length))),
    )
    perpendicular = (-direction[1], direction[0])

    pygame.draw.line(
        screen, SWORD_EDGE, blade_start, blade_end, max(3, int(6 * scale))
    )
    pygame.draw.line(
        screen, SWORD_BLADE, blade_start, blade_end, max(1, int(3 * scale))
    )
    pygame.draw.circle(screen, SWORD_BLADE, blade_end, max(1, int(2 * scale)))
    pygame.draw.line(
        screen, SWORD_GRIP, grip_start, grip_end, max(2, int(3 * scale))
    )

    guard_half = max(3, int(5 * scale))
    guard_left = (
        int(round(hand[0] + direction[0] * 5 * scale - perpendicular[0] * guard_half)),
        int(round(hand[1] + direction[1] * 5 * scale - perpendicular[1] * guard_half)),
    )
    guard_right = (
        int(round(hand[0] + direction[0] * 5 * scale + perpendicular[0] * guard_half)),
        int(round(hand[1] + direction[1] * 5 * scale + perpendicular[1] * guard_half)),
    )
    pygame.draw.line(
        screen, SWORD_GUARD, guard_left, guard_right, max(2, int(3 * scale))
    )
    pygame.draw.circle(screen, color, hand, max(2, int(4 * scale)))

    # Return a generous bounding rect for debug overlays and render tests.
    points = (centre, hand, grip_start, grip_end, blade_start, blade_end)
    min_x = min(point[0] for point in points) - radius
    min_y = min(point[1] for point in points) - radius
    max_x = max(point[0] for point in points) + radius
    max_y = max(point[1] for point in points) + radius
    return pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)


def draw_skill_effect(screen, skill_anim_info, player_state):
    """Draw a skill sword slash for ``player_state`` onto ``screen``.

    This renderer only reads state. It never mutates ``skill_anim_info`` or
    ``player_state``, so it can be called safely from the skill module after
    the normal stickman body has been drawn.

    ``skill_anim_info`` may be a dict or object and can provide:
    - ``progress``: 0.0 (wind-up) to 1.0 (slash complete).
    - ``player_id``: used when ``player_state`` does not carry it.
    - ``color``: optional RGB/RGBA tint for the effect.

    Returns:
        ``pygame.Rect`` covering the sword and aura, useful for tests.
    """
    if screen is None:
        raise ValueError("draw_skill_effect needs a screen surface")

    width, height = screen.get_size()
    raw_x = float(_state_get(player_state, "x", width * 0.5))
    x = max(8.0, min(width - 8.0, raw_x))
    ground_y = get_ground_y(screen, x)
    raw_y = _state_get(player_state, "y", None)
    y = float(ground_y if raw_y is None else raw_y)
    y = min(y, ground_y)

    facing = _state_get(player_state, "facing", 1)
    facing = 1 if float(facing) >= 0 else -1
    scale = max(0.5, min(2.0, float(_state_get(player_state, "scale", 1.0))))
    anim_time = float(
        _state_get(player_state, "anim_time", pygame.time.get_ticks() / 1000.0)
    )

    player_id = _state_get(
        skill_anim_info, "player_id", _state_get(player_state, "id", 0)
    )
    if player_id not in PLAYER_COLORS:
        player_id = 0

    color = _state_get(
        skill_anim_info, "color",
        _state_get(player_state, "color", PLAYER_COLORS[player_id]),
    )
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        color = (int(color[0]), int(color[1]), int(color[2]))

    progress = _state_get(skill_anim_info, "progress", None)
    return _draw_skill_effect(
        screen, (x, y), facing, scale, anim_time, color, progress
    )


def draw_stickman(screen, player_id, player_state):
    """Draw one animated stickman onto ``screen``.

    Args:
        screen: Target ``pygame.Surface``.
        player_id: ``1`` for the red player, ``2`` for the blue player.
        player_state: Move-module state, either a dict or an object.  See the
            module docstring for the supported fields.

    Returns:
        ``pygame.Rect`` bounding the rendered character.  The rect is useful
        for debug overlays and for tests that verify draw calls.
    """
    if player_id not in PLAYER_COLORS:
        raise ValueError(f"player_id must be 0 or 1, got {player_id!r}")

    width, height = screen.get_size()
    color = _state_get(player_state, "color", PLAYER_COLORS[player_id])

    raw_x = float(_state_get(player_state, "x", width * (0.22 if player_id == 0 else 0.78)))
    x = max(8.0, min(width - 8.0, raw_x))
    ground_y = float(_state_get(player_state, "ground_y", get_ground_y(screen, x)))

    raw_y = _state_get(player_state, "y", None)
    y = float(ground_y if raw_y is None else raw_y)
    on_ground_default = raw_y is None or float(raw_y) >= ground_y
    # The move module owns real physics; this only stops a bad state from
    # dropping a character below the visible ground surface.
    y = min(y, ground_y)

    vx = float(_state_get(player_state, "vx", 0.0))
    vy = float(_state_get(player_state, "vy", 0.0))
    on_ground = bool(_state_get(player_state, "on_ground", on_ground_default))
    moving = bool(_state_get(player_state, "moving", abs(vx) > 18.0))
    scale = max(0.5, min(2.0, float(_state_get(player_state, "scale", 1.0))))
    anim_time = float(_state_get(player_state, "anim_time", pygame.time.get_ticks() / 1000.0))

    facing = _state_get(player_state, "facing", 1 if player_id == 0 else -1)
    facing = 1 if float(facing) >= 0 else -1

    action = _resolve_action(player_state, vy, on_ground, moving)
    pose = _build_pose(action, anim_time)
    origin = (x, y)
    line_width = max(2, int(round(LIMB_WIDTH * scale)))

    # Faint ground contact shadow.  It stays on the ground during air poses.
    pygame.draw.line(
        screen,
        SHADOW_COLOR,
        (int(round(x - 12 * scale)), int(round(ground_y))),
        (int(round(x + 12 * scale)), int(round(ground_y))),
        max(2, int(round(2 * scale))),
    )

    if action == "skill":
        _draw_skill_effect(screen, origin, facing, scale, anim_time, color)

    points = {
        name: _to_screen(origin, local, facing, scale)
        for name, local in pose.items()
    }

    hip = points["hip"]
    shoulder = points["shoulder"]
    head = points["head"]
    left_foot = points["left_foot"]
    right_foot = points["right_foot"]
    left_hand = points["left_hand"]
    right_hand = points["right_hand"]

    segments = (
        (hip, shoulder),
        (hip, left_foot),
        (hip, right_foot),
        (shoulder, left_hand),
        (shoulder, right_hand),
    )

    for start, end in segments:
        pygame.draw.line(screen, color, start, end, line_width)

    head_radius = max(2, int(round(HEAD_RADIUS * scale)))
    pygame.draw.circle(screen, color, head, head_radius, max(2, int(round(2 * scale))))

    all_points = [head, hip, shoulder, left_foot, right_foot, left_hand, right_hand]
    min_x = min(p[0] for p in all_points) - head_radius
    min_y = min(p[1] for p in all_points) - head_radius
    max_x = max(p[0] for p in all_points) + head_radius
    max_y = max(p[1] for p in all_points) + head_radius

    return pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)


def get_player_hitbox(player_state):
    """Return the player's body hitbox as a ``pygame.Rect``.

    The skill module can use ``colliderect`` or point tests against this
    rect.  It follows the same pose logic as ``draw_stickman``, but it
    covers the head, torso, hips, and feet only.  Arms and skill effects are
    excluded so extended limbs do not accidentally enlarge the target.
    """
    x = float(_state_get(player_state, "x", 0.0))
    y = float(_state_get(player_state, "y", 0.0))
    vy = float(_state_get(player_state, "vy", 0.0))
    vx = float(_state_get(player_state, "vx", 0.0))
    on_ground = bool(_state_get(player_state, "on_ground", True))
    moving = bool(_state_get(player_state, "moving", abs(vx) > 18.0))
    scale = max(0.5, min(2.0, float(_state_get(player_state, "scale", 1.0))))
    anim_time = float(
        _state_get(player_state, "anim_time", pygame.time.get_ticks() / 1000.0)
    )

    facing = _state_get(player_state, "facing", 1)
    facing = 1 if float(facing) >= 0 else -1

    action = _resolve_action(player_state, vy, on_ground, moving)
    pose = _build_pose(action, anim_time)
    origin = (x, y)

    body_points = (
        _to_screen(origin, pose["head"], facing, scale),
        _to_screen(origin, pose["shoulder"], facing, scale),
        _to_screen(origin, pose["hip"], facing, scale),
        _to_screen(origin, pose["left_foot"], facing, scale),
        _to_screen(origin, pose["right_foot"], facing, scale),
    )

    head_radius = max(2, int(round(HEAD_RADIUS * scale)))
    min_x = min(point[0] for point in body_points) - head_radius
    min_y = min(point[1] for point in body_points) - head_radius
    max_x = max(point[0] for point in body_points) + head_radius
    max_y = max(point[1] for point in body_points) + head_radius

    return pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)


def initial_player_state(screen, player_id):
    """Return a sensible round-start state for one player.

    Red starts on the left side facing right; blue starts on the right side
    facing left.  This helper is mostly for the preview and for bootstrapping
    the move module.
    """
    if player_id not in PLAYER_COLORS:
        raise ValueError(f"player_id must be 0 or 1, got {player_id!r}")

    width, height = screen.get_size()
    x_ratio = 0.22 if player_id == 0 else 0.78
    x = width * x_ratio

    return {
        "x": x,
        "y": get_ground_y(screen, x),
        "vx": 0.0,
        "vy": 0.0,
        "facing": 1 if player_id == 0 else -1,
        "on_ground": True,
        "standing_platform": None,
        "moving": False,
        "action": "idle",
        "anim_time": 0.0,
        "scale": 1.0,
        "color": PLAYER_COLORS[player_id],
    }



def _preview():
    pygame.init()
    screen = pygame.display.set_mode((960, 540))
    pygame.display.set_caption("stickman render preview")
    clock = pygame.time.Clock()

    from map import draw_background, update_dynamic_obstacle
    from move.apply_gravity import apply_gravity
    from move.jump_logic import jump_logic
    from move.update_position import update_position

    def _step(state, direction, jump, screen, dt):
        state["vx"] = direction * 300.0
        if direction > 0:
            state["facing"] = 1
        elif direction < 0:
            state["facing"] = -1
        state["ground_y"] = get_ground_y(screen, state["x"])
        jump_logic(state, jump)
        apply_gravity(state, dt)
        update_position(state, dt)

    current_round = 1
    red = initial_player_state(screen, 0)
    blue = initial_player_state(screen, 1)
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        time_s = pygame.time.get_ticks() / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    current_round = current_round % 5 + 1
                    pygame.display.set_caption(
                        f"stickman render preview - round {current_round}"
                    )

        keys = pygame.key.get_pressed()
        red_direction = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        blue_direction = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        _step(red, red_direction, keys[pygame.K_w], screen, dt)
        _step(blue, blue_direction, keys[pygame.K_UP], screen, dt)

        # Demonstrate the skill pose on demand without touching the real
        # move/skill modules.
        if keys[pygame.K_f]:
            red["action"] = "skill"
        elif not red["on_ground"]:
            red["action"] = "jump" if red["vy"] < 0 else "fall"
        else:
            red["action"] = "run" if abs(red["vx"]) > 18 else "idle"

        if keys[pygame.K_l]:
            blue["action"] = "skill"
        elif not blue["on_ground"]:
            blue["action"] = "jump" if blue["vy"] < 0 else "fall"
        else:
            blue["action"] = "run" if abs(blue["vx"]) > 18 else "idle"

        draw_background(screen)
        update_dynamic_obstacle(current_round, screen, time_s)
        draw_stickman(screen, 0, red)
        draw_stickman(screen, 1, blue)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    _preview()
