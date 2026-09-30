from collections.abc import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pygame
from matplotlib.backends.backend_agg import FigureCanvasAgg


def detection_chart(history: Sequence[tuple[float, float]], size: tuple[int, int] = (470, 230)) -> pygame.Surface:
    width, height = size
    figure = plt.Figure(figsize=(width / 100, height / 100), dpi=100, facecolor="#0b1014")
    axes = figure.add_axes((0.12, 0.2, 0.82, 0.68))
    values = list(history) or [(0.0, 0.0)]
    x_values = [item[0] for item in values]
    y_values = [item[1] for item in values]
    axes.plot(x_values, y_values, color="#5ee7a2", linewidth=2)
    axes.fill_between(x_values, y_values, color="#5ee7a2", alpha=0.12)
    axes.set_ylim(0, 100)
    axes.set_xlim(min(x_values), max(x_values) if max(x_values) > min(x_values) else min(x_values) + 1)
    axes.set_title("DETECTION TRACE", color="#d9f7e5", fontsize=9, loc="left")
    axes.set_xlabel("SECONDS", color="#71858a", fontsize=7)
    axes.set_ylabel("%", color="#71858a", fontsize=7)
    axes.tick_params(colors="#71858a", labelsize=7)
    axes.grid(color="#223037", linewidth=0.6, alpha=0.8)
    for spine in axes.spines.values():
        spine.set_color("#2a3b42")
    canvas = FigureCanvasAgg(figure)
    canvas.draw()
    canvas_width, canvas_height = canvas.get_width_height()
    raw = canvas.tostring_argb()
    surface = pygame.image.fromstring(raw, (canvas_width, canvas_height), "ARGB")
    plt.close(figure)
    return surface
