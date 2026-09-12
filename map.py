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

GROUND_BASE_RATIO = 0.70
GROUND_AMPLITUDE_RATIO = 0.08

# Each platform is a simple horizontal line.
# Fields: x-center ratio, y ratio, length ratio, line color.
PLATFORMS = (
    (0.18, 0.36, 0.14, INK_BLUE),
    (0.42, 0.44, 0.22, INK_GRAY),
    (0.63, 0.52, 0.17, INK_BLUE),
    (0.84, 0.59, 0.26, INK_GRAY),
)


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
    """Draw the playable ground with one solid line and faint echo contours."""
    screen_width, screen_height = screen.get_size()
    points = _line_points(screen, GROUND_BASE_RATIO, GROUND_AMPLITUDE_RATIO)
    polygon = points + [(screen_width, screen_height), (0, screen_height)]

    pygame.draw.polygon(screen, GROUND_PAPER, polygon)
    pygame.draw.lines(screen, GROUND_LINE, False, points, 3)

    for offset, color in zip((6, 13, 21), GROUND_ECHO):
        echo = [(x, min(screen_height, y + offset)) for x, y in points]
        pygame.draw.lines(screen, color, False, echo, 1)


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
        phase = index * 1.37

        if current_round <= 3:
            offset_x = 0.0
            offset_y = 0.0
        elif current_round == 4:
            offset_x = math.sin(time_s * 0.68 + phase) * width * horizontal_range
            offset_y = 0.0
        else:
            offset_x = math.sin(time_s * 0.78 + phase * 1.7) * width * horizontal_range
            offset_y = math.sin(time_s * 0.92 + phase * 1.3) * height * vertical_range

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


def update_dynamic_obstacle(current_round, screen=None, time_s=None):
    """Draw four minimal floating platforms for the current round.

    Rounds 1-3 use fixed platform positions. Round 4 adds a gentle horizontal
    drift, and round 5 adds a larger horizontal and vertical float. The
    motion is based on elapsed seconds so it remains smooth across frames.

    Args:
        current_round: Integer round number, expected to be 1 through 5.
        screen: Optional pygame.Surface. Defaults to the display surface.
        time_s: Optional elapsed time in seconds, useful for tests.
    """
    if screen is None:
        screen = pygame.display.get_surface()
        if screen is None:
            raise RuntimeError("update_dynamic_obstacle needs a screen surface")

    for platform in _platform_geometry(screen, current_round, time_s):
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
    """Return the top ground surface y at a given screen x coordinate."""
    width, height = screen.get_size()
    points = _line_points(screen, GROUND_BASE_RATIO, GROUND_AMPLITUDE_RATIO)

    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]

    span = points[-1][0] - points[0][0]
    if span <= 0:
        return points[0][1]

    position = (x - points[0][0]) / span * (len(points) - 1)
    index = min(int(position), len(points) - 2)
    fraction = position - index

    x0, y0 = points[index]
    x1, y1 = points[index + 1]
    return y0 + (y1 - y0) * fraction


def get_map_bounds(screen=None, current_round=1, time_s=None):
    """Return collision regions used by the move module.

    The returned dict contains:

    - screen: a pygame.Rect for the full playable window.
    - ground: the uneven terrain as its top surface points, a filled polygon,
      and a bounding rect.
    - platforms: the current round's platform segments as pygame.Rect objects
      plus their line start and end points.

    Pass the same current_round and time_s values used by draw_map() so the
    collision platforms exactly match the visible platforms.
    """
    if screen is None:
        screen = pygame.display.get_surface()
        if screen is None:
            raise RuntimeError("get_map_bounds needs a screen surface")

    width, height = screen.get_size()
    ground_points = _line_points(screen, GROUND_BASE_RATIO, GROUND_AMPLITUDE_RATIO)
    ground_top = min(point[1] for point in ground_points)
    ground_polygon = ground_points + [(width, height), (0, height)]

    return {
        "screen": pygame.Rect(0, 0, width, height),
        "ground": {
            "surface": ground_points,
            "polygon": ground_polygon,
            "rect": pygame.Rect(
                0,
                int(ground_top),
                width,
                max(1, int(height - ground_top)),
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
