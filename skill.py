"""Skill trigger and collision logic for the two-player stickman arena.

The module deliberately keeps keyboard input, cooldown bookkeeping, and
attack-range generation separate from movement and rendering.  It expects to
be called once per frame for each player, in this order:

    red_skill = skill_trigger(0, keys, red_state, game_mode)
    blue_skill = skill_trigger(1, keys, blue_state, game_mode)

It mutates only the skill-related fields on ``player_state`` and the
``action`` field used by ``character_render.draw_stickman``.  Movement fields
such as ``x``, ``y``, ``vx``, ``vy`` and ``on_ground`` are left untouched, so
moving and air releases continue to work through the normal move module.

Integration notes
-----------------
``draw_stickman`` already renders the skill pose and sword effect whenever
``player_state["action"] == "skill"``.  For most games that is all you need:

    character_render.draw_stickman(screen, 0, red_state)
    character_render.draw_stickman(screen, 1, blue_state)

If you prefer to draw the slash effect separately, pass the returned
``anim_info`` to ``character_render.draw_skill_effect`` and do not also let
``draw_stickman`` draw the skill pose in the same frame.
"""

import math
import time

import pygame

import character_render as cr


SKILL_KEYS = {
    0: pygame.K_f,
    1: getattr(pygame, "K_BACKSLASH", 92),
}

# Base timings are shared by all standard game modes.  ``game_mode`` can be a
# dict to override one or more of these values without editing this module.
SKILL_DEFAULT_CONFIG = {
    # CD 与动画等长: 0.42s 动画播放结束时冷却同步转好,可立即再次释放。
    "cooldown": 0.42,
    "duration": 0.42,
    "active_start": 0.20,
    "active_end": 0.60,
    "reach_scale": 1.0,
    "height_scale": 1.0,
}


def _now():
    """Return elapsed seconds, preferring Pygame's clock when initialized."""
    try:
        if pygame.get_init():
            return pygame.time.get_ticks() / 1000.0
    except Exception:
        pass
    return time.monotonic()


def _state_get(state, key, default=None):
    """Read a field from a dict or a plain Python object."""
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def _state_set(state, key, value):
    """Write a field to a dict or a plain Python object."""
    if isinstance(state, dict):
        state[key] = value
    else:
        setattr(state, key, value)


def _normalize_player_id(player_id):
    """Accept 0/1 and the common red/blue string aliases."""
    if isinstance(player_id, str):
        name = player_id.strip().lower()
        if name in ("red", "0"):
            return 0
        if name in ("blue", "1"):
            return 1
    if player_id in (0, 1):
        return int(player_id)
    raise ValueError(f"player_id must be 0 or 1, got {player_id!r}")


def _key_is_down(key_state, key):
    """Return True when ``key_state`` reports ``key`` as held down.

    ``key_state`` is normally ``pygame.key.get_pressed()``, but dict and
    object styles are also accepted so the function is easy to test.
    """
    if key_state is None:
        return False

    if isinstance(key_state, dict):
        key_name = pygame.key.name(key)
        for candidate in (key, key_name, key_name.upper()):
            if key_state.get(candidate):
                return True
        return False

    try:
        return bool(key_state[key])
    except (KeyError, IndexError, TypeError):
        pass

    try:
        return bool(getattr(key_state, pygame.key.name(key), False))
    except AttributeError:
        return False


def _skill_config(game_mode):
    """Return the timing/range configuration for the current game mode."""
    config = dict(SKILL_DEFAULT_CONFIG)
    if isinstance(game_mode, dict):
        for key in config:
            if key in game_mode and game_mode[key] is not None:
                config[key] = game_mode[key]
    return config


def _build_skill_animation_info(player_id, config):
    """Build timing metadata from one skill configuration."""
    duration = float(config["duration"])
    active_start = float(config["active_start"])
    active_end = float(config["active_end"])
    cooldown = float(config["cooldown"])
    fps = 60.0

    return {
        "player_id": player_id,
        "action": "skill",
        "duration": duration,
        "cooldown": cooldown,
        "active_start": active_start,
        "active_end": active_end,
        "active_duration": max(0.0, active_end - active_start),
        "recovery_duration": max(0.0, duration - active_end),
        "fps": fps,
        "frame_count": max(1, int(round(duration * fps))),
        "timeline": (
            {"phase": "windup", "start": 0.0, "end": active_start},
            {"phase": "attack", "start": active_start, "end": active_end},
            {"phase": "recover", "start": active_end, "end": duration},
        ),
    }


def get_skill_animation_info(player_id):
    """Return skill action timing data for one player.

    This function performs no drawing and mutates no player state. It only
    exposes the timing values used by :func:`skill_trigger` so the renderer
    can animate the skill pose from data alone.
    """
    player_id = _normalize_player_id(player_id)
    return _build_skill_animation_info(player_id, dict(SKILL_DEFAULT_CONFIG))


def _clamp(value, low=0.0, high=1.0):
    return max(float(low), min(float(high), float(value)))


def _ease(progress):
    """Match the renderer's smooth sword sweep easing."""
    return 0.5 - 0.5 * math.cos(math.pi * progress)


def _player_geometry(player_state):
    """Return x, y, facing and scale in a form usable by the hitbox builder."""
    x = float(_state_get(player_state, "x", 0.0))
    y = float(_state_get(player_state, "y", 0.0))
    facing = float(_state_get(player_state, "facing", 1))
    facing = 1 if facing >= 0 else -1
    scale = _clamp(float(_state_get(player_state, "scale", 1.0)), 0.5, 2.0)
    return x, y, facing, scale


def get_skill_hitbox(player_state, progress=None, config=None):
    """Return the active skill damage rectangle, or ``None``.

    The hitbox lies STRICTLY IN FRONT of the player, along the facing
    direction: its near edge never crosses the body centre, so there is no
    damage behind the character. It tracks the forward sword slash rendered
    by ``character_render`` (the blade stays in front for the whole active
    window). Flip ``facing`` and the hitbox flips to the other side.

    ``progress`` should be the same normalized 0.0..1.0 skill progress passed
    to the renderer. When omitted, the function reads the active phase from
    ``player_state``.
    """
    if config is None:
        config = SKILL_DEFAULT_CONFIG

    now = _now()
    if progress is None:
        started_at = _state_get(player_state, "skill_started_at", None)
        if started_at is None:
            return None
        duration = float(config["duration"])
        if duration <= 0:
            return None
        progress = _clamp((now - float(started_at)) / duration)

    progress = _clamp(progress)
    if not (float(config["active_start"]) <= progress <= float(config["active_end"])):
        return None

    x, y, facing, scale = _player_geometry(player_state)
    eased = _ease(progress)
    angle = cr.SWORD_ANGLE_START + (
        cr.SWORD_ANGLE_END - cr.SWORD_ANGLE_START
    ) * eased
    dirx = math.cos(angle)
    diry = math.sin(angle)
    vec_len = math.hypot(dirx, diry)
    if vec_len <= 1e-6:
        dirx, diry = 1.0, 0.0
    else:
        dirx, diry = dirx / vec_len, diry / vec_len

    reach_scale = float(config["reach_scale"])

    # 技能姿态前伸的右手,局部坐标 (34, -50)。
    hand = (
        x + 34.0 * facing * scale,
        y - 50.0 * scale,
    )
    blade_start = (
        hand[0] + facing * dirx * 8.0 * scale,
        hand[1] + diry * 8.0 * scale,
    )
    blade_reach = 8.0 * scale + cr.SWORD_LENGTH * scale * reach_scale
    blade_end = (
        hand[0] + facing * dirx * blade_reach,
        hand[1] + diry * blade_reach,
    )

    # 判定只取前方武器轨迹点(不再纳入以身体为中心、向身后扩散的光环)。
    points = (hand, blade_start, blade_end)
    min_x = min(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_x = max(point[0] for point in points)
    max_y = max(point[1] for point in points)

    # 垂直方向适度放宽,覆盖前方敌人头到腰,保证命中稳定。
    min_y -= 6.0 * scale
    max_y = max(max_y, y - 12.0 * scale)

    padding = max(3.0, 4.0 * scale)
    min_x -= padding
    min_y -= padding
    max_x += padding
    max_y += padding

    # 关键: 严格朝前方 —— 近边不越过身体中心,身后零判定。
    front_guard = 4.0 * scale
    if facing > 0:
        min_x = max(min_x, x - front_guard)
    else:
        max_x = min(max_x, x + front_guard)

    return pygame.Rect(
        int(round(min_x)),
        int(round(min_y)),
        int(round(max_x - min_x)),
        int(round(max_y - min_y)),
    )


def skill_trigger(player_id, key_state, player_state, game_mode):
    """Process one frame of skill input for one player.

    Args:
        player_id: ``0`` for the red player (``F``), ``1`` for blue
            (``\\``).  The string aliases ``"red"`` and ``"blue"`` are also
            accepted.
        key_state: A pressed-key structure such as ``pygame.key.get_pressed()``,
            a dict keyed by Pygame key codes/names, or an object with key
            attributes.
        player_state: The mutable player state dict/object shared with the move
            and render modules.
        game_mode: Reserved game-mode selector.  Pass a dict to override
            ``cooldown``, ``duration``, ``active_start``, ``active_end``,
            ``reach_scale`` or ``height_scale``.

    Returns:
        A dict with ``triggered``, ``active``, ``progress``, ``hitboxes``,
        ``cooldown_remaining``, and ``anim_info``.  ``hitboxes`` is a list of
        one ``pygame.Rect`` while the slash can deal damage, otherwise empty.
    """
    player_id = _normalize_player_id(player_id)
    config = _skill_config(game_mode)
    now = _now()

    cooldown_until = float(_state_get(player_state, "skill_cooldown_until", 0.0))
    cooldown_remaining = max(0.0, cooldown_until - now)
    cooldown_ready = now >= cooldown_until

    key = SKILL_KEYS[player_id]
    key_down = _key_is_down(key_state, key)
    was_down = bool(_state_get(player_state, "skill_key_was_down", False))
    pressed = key_down and not was_down
    _state_set(player_state, "skill_key_was_down", key_down)

    started_at = _state_get(player_state, "skill_started_at", None)
    duration = float(config["duration"])
    active_until = _state_get(player_state, "skill_active_until", None)
    if active_until is None and started_at is not None:
        active_until = float(started_at) + duration
    active = active_until is not None and now < float(active_until)

    triggered = False
    if pressed and cooldown_ready:
        triggered = True
        started_at = now
        _state_set(player_state, "skill_started_at", started_at)
        _state_set(
            player_state,
            "skill_cooldown_until",
            now + float(config["cooldown"]),
        )
        active_until = now + duration
        _state_set(player_state, "skill_active_until", active_until)
        _state_set(player_state, "skill_hit_players", [])
        active = True
        cooldown_remaining = float(config["cooldown"])
        cooldown_ready = False

    progress = 0.0
    if active and started_at is not None and duration > 0:
        progress = _clamp((now - float(started_at)) / duration)

    # Keep the renderer in its skill pose for the whole active window.  When
    # the skill finishes, clear the explicit pose so draw_stickman can fall
    # back to idle/run/jump/fall from the movement state.
    if active:
        _state_set(player_state, "action", "skill")
    elif _state_get(player_state, "action", "") == "skill":
        _state_set(player_state, "action", "")

    hitboxes = []
    if active:
        box = get_skill_hitbox(player_state, progress, config)
        if box is not None:
            hitboxes.append(box)

    anim_info = _build_skill_animation_info(player_id, config)
    anim_info["progress"] = progress
    anim_info["color"] = cr.PLAYER_COLORS.get(player_id, cr.PLAYER_COLORS[0])

    return {
        "player_id": player_id,
        "key": key,
        "key_down": key_down,
        "pressed": pressed,
        "triggered": triggered,
        "active": active,
        "progress": progress,
        "hit_active": bool(hitboxes),
        "hitboxes": hitboxes,
        "cooldown_ready": cooldown_ready,
        "cooldown_remaining": cooldown_remaining,
        "cooldown_total": float(config["cooldown"]),
        "anim_info": anim_info,
    }

def _as_rect(box):
    """Return ``box`` as a pygame.Rect, or ``None`` for empty input."""
    if box is None:
        return None
    if isinstance(box, pygame.Rect):
        return box.copy()
    try:
        return pygame.Rect(box)
    except (TypeError, ValueError):
        return None


def _send_heal_interrupt(blood, defender_state, event):
    """Tell the blood module to interrupt the defender's healing.

    The blood module's ``interrupt_heal`` receives the defender's *state*
    (not an id), matching ``blood.interrupt_heal(player_state)``.
    """
    if blood is None:
        return

    interrupt = None
    if isinstance(blood, dict):
        interrupt = blood.get("interrupt_heal")
    else:
        interrupt = getattr(blood, "interrupt_heal", None)

    if callable(interrupt):
        interrupt(defender_state)
        return

    if callable(blood):
        blood(event)


def check_hit(attack_box, enemy_hitbox, attacker_id=None, defender_id=None,
              damage=1, blood=None, on_hit=None, hit_players=None,
              defender_state=None):
    """Check one skill attack box against an enemy body hitbox.

    The two required arguments are the attack rectangle produced by
    :func:`get_skill_hitbox` and the enemy's body rectangle produced by
    ``character_render.get_player_hitbox``.  Optional arguments let the
    caller connect damage to the rest of the game without making this
    module depend on the blood or scoreboard implementations.

    Behavior
    --------
    * No overlap returns ``None``.
    * ``attacker_id == defender_id`` is ignored, so a player can never
      damage themselves.
    * A second collision against the same defender can be suppressed by
      passing the ``skill_hit_players`` list stored on the attacker state.
    * On a valid hit, ``on_hit`` (if supplied) receives the damage event,
      ``blood.interrupt_heal(defender_state)`` is called when available, and
      the damage event is returned.
    """
    attack_rect = _as_rect(attack_box)
    enemy_rect = _as_rect(enemy_hitbox)

    if attack_rect is None or enemy_rect is None:
        return None
    if not attack_rect.colliderect(enemy_rect):
        return None

    # Prohibit self damage while still accepting int/string aliases such as
    # 1 versus "red".  If identities are not supplied, collision alone is
    # treated as a valid hit so this function remains easy to test.
    if attacker_id is not None and defender_id is not None:
        try:
            same_player = (
                _normalize_player_id(attacker_id)
                == _normalize_player_id(defender_id)
            )
        except (ValueError, TypeError):
            same_player = False
        if same_player:
            return {
                "hit": False,
                "reason": "self",
                "attacker_id": attacker_id,
                "defender_id": defender_id,
            }

    if hit_players is not None:
        try:
            if defender_id in hit_players:
                return {
                    "hit": False,
                    "reason": "already_hit",
                    "attacker_id": attacker_id,
                    "defender_id": defender_id,
                }
            hit_players.append(defender_id)
        except (AttributeError, TypeError):
            pass

    event = {
        "hit": True,
        "type": "skill_hit",
        "attacker_id": attacker_id,
        "defender_id": defender_id,
        "damage": int(damage),
        "attack_box": attack_rect,
        "enemy_hitbox": enemy_rect,
        "impact_point": (enemy_rect.centerx, enemy_rect.centery),
    }

    if callable(on_hit):
        on_hit(event)

    _send_heal_interrupt(blood, defender_state, event)
    return event
