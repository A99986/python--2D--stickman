import math

import pygame

SKY_PAPER = (239, 241, 237)
INK_BLUE = (91, 112, 120)
INK_GRAY = (115, 125, 123)
GROUND_PAPER = (224, 223, 216)
GROUND_LINE = (55, 58, 57)
GROUND_ECHO = ((86, 89, 85), (126, 128, 121), (168, 169, 160))
HILL_FAR_FILL = (214, 217, 210)
HILL_FAR_LINE = (173, 177, 169)
HILL_NEAR_FILL = (201, 205, 198)
HILL_NEAR_LINE = (153, 158, 149)

PLATFORM_WIDTH = 5

GROUND_MARGIN = 120  # 地面距屏幕底部的预留空间(像素),需与 init_game_context 保持一致

# 悬浮平台:按「左外、左内、右内、右外」的对称顺序排列。
# 字段: x 中心比例, y 比例, 长度比例, 线条颜色。
# 高度依据跳跃能力设计: 起跳初速 800、重力 2000 -> 最大跳高 160px。
#   外台 y=520(离地 80,轻松跳上); 内台 y=485(离地 115,可直接跳上,
#   也可从外台二次起跳); 左右关于 x=0.5 严格镜像,保证双方公平。
PLATFORMS = (
    (0.16, 13 / 18, 9 / 64, INK_BLUE),
    (0.37, 97 / 144, 9 / 64, INK_GRAY),
    (0.63, 97 / 144, 9 / 64, INK_GRAY),
    (0.84, 13 / 18, 9 / 64, INK_BLUE),
)

# 漂移对称化: 镜像对(0<->3, 1<->2)共享相位; 水平方向右侧取负、垂直方向
# 两侧同步,确保任意时刻平台位置都关于中线对称。
_PAIR_PHASE_X = (0.0, 1.37, 1.37, 0.0)
_PAIR_PHASE_Y = (0.0, 0.90, 0.90, 0.0)
_MIRROR_X = (1.0, 1.0, -1.0, -1.0)


def _soft_ink_blob(surface, center, radius, color, max_alpha, steps=60):
    """Draw a radial ink wash with soft edges."""
    cx, cy = center
    for i in range(steps, 0, -1):
        t = i / steps
        r = max(1, int(radius * t))
        alpha = int(max_alpha * (1.0 - t * t))
        if alpha <= 0:
            continue
        pygame.draw.circle(
            surface,
            (color[0], color[1], color[2], alpha),
            (int(cx), int(cy)),
            r,
        )


def _draw_ink_sky(screen):
    """Draw a pale, softly diffused ink sky."""
    width, height = screen.get_size()
    wash = pygame.Surface((width, height), pygame.SRCALPHA)

    blobs = (
        (0.18, 0.20, 0.44, INK_BLUE, 8),
        (0.33, 0.10, 0.28, INK_GRAY, 7),
        (0.42, 0.34, 0.40, INK_BLUE, 6),
        (0.50, 0.15, 0.20, INK_GRAY, 7),
        (0.50, 0.56, 0.78, (129, 133, 126), 10),
    )

    for x_ratio, y_ratio, radius_ratio, color, max_alpha in blobs:
        x_positions = [x_ratio]
        if abs(x_ratio - 0.5) > 1e-3:
            x_positions.append(1.0 - x_ratio)
        for xr in x_positions:
            _soft_ink_blob(
                wash,
                (width * xr, height * y_ratio),
                max(width, height) * radius_ratio,
                color,
                max_alpha,
            )

    screen.blit(wash, (0, 0))


def _symmetric_wave(t):
    """Return a smooth terrain wave that is symmetric around t=0.5."""
    return (
        0.58 * math.cos(2.0 * math.pi * t)
        + 0.24 * math.cos(4.0 * math.pi * t)
        + 0.10 * math.cos(6.0 * math.pi * t)
        + 0.04 * math.cos(8.0 * math.pi * t)
    )


def _line_points(screen, base_ratio, amplitude_ratio, samples=180):
    """Build left-to-right points for one symmetric landscape layer."""
    width, height = screen.get_size()
    base_y = height * base_ratio
    amplitude = height * amplitude_ratio
    points = []

    for i in range(samples + 1):
        t = i / samples
        x = width * t
        y = base_y - _symmetric_wave(t) * amplitude
        points.append((x, y))

    return points


def _draw_hill_layer(screen, base_ratio, amplitude_ratio, fill_color, line_color, width):
    """Draw one distant hill layer behind the main terrain."""
    screen_width, screen_height = screen.get_size()
    points = _line_points(screen, base_ratio, amplitude_ratio)
    polygon = points + [(screen_width, screen_height), (0, screen_height)]

    pygame.draw.polygon(screen, fill_color, polygon)
    pygame.draw.lines(screen, line_color, False, points, width)


def _draw_hills(screen):
    _draw_hill_layer(screen, 0.63, 0.025, HILL_FAR_FILL, HILL_FAR_LINE, 1)
    _draw_hill_layer(screen, 0.68, 0.035, HILL_NEAR_FILL, HILL_NEAR_LINE, 2)


def _draw_ground(screen):
    """Draw the flat playable ground with one solid line and faint echoes."""
    screen_width, screen_height = screen.get_size()
    ground_y = screen_height - GROUND_MARGIN

    pygame.draw.rect(
        screen, GROUND_PAPER,
        (0, int(ground_y), screen_width, GROUND_MARGIN),
    )
    pygame.draw.line(screen, GROUND_LINE, (0, int(ground_y)), (screen_width, int(ground_y)), 3)

    for offset, color in zip((6, 13, 21), GROUND_ECHO):
        echo_y = int(ground_y + offset)
        pygame.draw.line(screen, color, (0, echo_y), (screen_width, echo_y), 1)


def draw_background(screen):
    """Draw the complete map background onto a pygame surface.

    Args:
        screen: A pygame.Surface, usually pygame.display.get_surface().
    """
    screen.fill(SKY_PAPER)
    _draw_ink_sky(screen)
    _draw_hills(screen)
    _draw_ground(screen)


def _platform_geometry(screen, current_round, time_s=None):
    """Return the collision geometry for the current round's platforms."""
    if time_s is None:
        time_s = pygame.time.get_ticks() / 1000.0

    width, height = screen.get_size()

    if current_round <= 3:
        horizontal_range = 0.0
        vertical_range = 0.0
    elif current_round == 4:
        horizontal_range = 0.035
        vertical_range = 0.0
    else:
        horizontal_range = 0.045
        vertical_range = 0.035

    platforms = []

    for index, (center_ratio, y_ratio, length_ratio, color) in enumerate(PLATFORMS):
        # 对称漂移: 镜像对共享相位,水平右侧取负、垂直两侧同步。
        phase_x = _PAIR_PHASE_X[index]
        phase_y = _PAIR_PHASE_Y[index]
        mirror_x = _MIRROR_X[index]

        if current_round <= 3:
            offset_x = 0.0
            offset_y = 0.0
        elif current_round == 4:
            offset_x = math.sin(time_s * 0.68 + phase_x) * width * horizontal_range * mirror_x
            offset_y = 0.0
        else:
            offset_x = math.sin(time_s * 0.78 + phase_x) * width * horizontal_range * mirror_x
            offset_y = math.sin(time_s * 0.92 + phase_y) * height * vertical_range

        half_length = length_ratio * width * 0.5
        center_x = center_ratio * width + offset_x
        center_y = y_ratio * height + offset_y

        # Keep every platform fully visible with a small screen margin.
        center_x = max(half_length + 2.0, min(width - half_length - 2.0, center_x))
        center_y = max(PLATFORM_WIDTH + 2.0, min(height - PLATFORM_WIDTH - 2.0, center_y))

        left = center_x - half_length
        right = center_x + half_length
        top = center_y - PLATFORM_WIDTH / 2.0

        platforms.append(
            {
                "index": index,
                "start": (int(round(left)), int(round(center_y))),
                "end": (int(round(right)), int(round(center_y))),
                "rect": pygame.Rect(
                    int(round(left)),
                    int(round(top)),
                    int(round(right - left)),
                    PLATFORM_WIDTH,
                ),
                "color": color,
                "thickness": PLATFORM_WIDTH,
            }
        )

    return platforms


def get_platforms(current_round, screen=None, time_s=None):
    """公开接口:返回当前帧悬浮平台的几何(渲染与碰撞共用同一份,保证一致)。"""
    if screen is None:
        screen = pygame.display.get_surface()
        if screen is None:
            raise RuntimeError("get_platforms needs a screen surface")
    return _platform_geometry(screen, current_round, time_s)


def update_dynamic_obstacle(current_round, screen=None, time_s=None, platforms=None):
    """Draw four minimal floating platforms for the current round.

    Rounds 1-3 use fixed platform positions. Round 4 adds a gentle horizontal
    drift, and round 5 adds a larger horizontal and vertical float. The
    motion is based on elapsed seconds so it remains smooth across frames.

    Args:
        current_round: Integer round number, expected to be 1 through 5.
        screen: Optional pygame.Surface. Defaults to the display surface.
        time_s: Optional elapsed time in seconds, useful for tests.
        platforms: Optional precomputed geometry shared with collision logic.
    """
    if platforms is None:
        if screen is None:
            screen = pygame.display.get_surface()
            if screen is None:
                raise RuntimeError("update_dynamic_obstacle needs a screen surface")
        platforms = _platform_geometry(screen, current_round, time_s)

    for platform in platforms:
        pygame.draw.line(
            screen,
            platform["color"],
            platform["start"],
            platform["end"],
            platform["thickness"],
        )


def draw_map(screen, current_round):
    """Draw the background and its current-round dynamic platforms."""
    draw_background(screen)
    update_dynamic_obstacle(current_round, screen)


def get_ground_y(screen, x):
    """Return the flat playable ground y (independent of x)."""
    return screen.get_size()[1] - GROUND_MARGIN


def get_map_bounds(screen=None, current_round=1, time_s=None):
    """Return collision regions used by the move module."""
    if screen is None:
        screen = pygame.display.get_surface()
        if screen is None:
            raise RuntimeError("get_map_bounds needs a screen surface")

    width, height = screen.get_size()
    ground_y = height - GROUND_MARGIN
    ground_points = [(0, ground_y), (width, ground_y)]
    ground_polygon = [(0, ground_y), (width, ground_y), (width, height), (0, height)]

    return {
        "screen": pygame.Rect(0, 0, width, height),
        "ground": {
            "surface": ground_points,
            "polygon": ground_polygon,
            "rect": pygame.Rect(
                0,
                int(ground_y),
                width,
                GROUND_MARGIN,
            ),
        },
        "platforms": _platform_geometry(screen, current_round, time_s),
    }


def _preview():
    pygame.init()
    screen = pygame.display.set_mode((960, 540))
    pygame.display.set_caption("map background preview")
    clock = pygame.time.Clock()
    running = True
    current_round = 1

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    current_round = current_round % 5 + 1
                    pygame.display.set_caption(f"map background preview - round {current_round}")

        draw_map(screen, current_round)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    _preview()
