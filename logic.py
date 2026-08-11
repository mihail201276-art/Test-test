from __future__ import annotations

import colorsys
import math
import random
from dataclasses import dataclass, field
from typing import Optional, Tuple


Color = Tuple[int, int, int]


def _rgb_to_hsv(color: Color) -> Tuple[float, float, float]:
    r, g, b = (c / 255.0 for c in color)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h, s, v


def _hsv_to_rgb(h: float, s: float, v: float) -> Color:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, min(max(s, 0.0), 1.0), min(max(v, 0.0), 1.0))
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))


def mix_colors(a: Color, b: Color) -> Color:
    ha, sa, va = _rgb_to_hsv(a)
    hb, sb, vb = _rgb_to_hsv(b)

    signed = (hb - ha + 0.5) % 1.0 - 0.5
    mixed_h = (ha + signed / 2) % 1.0
    hue_gap = abs(signed)
    saturation = max(0.0, min(sa, sb) - hue_gap * 0.5)
    value = max(va, vb)

    return _hsv_to_rgb(mixed_h, saturation, value)


@dataclass
class Rect:
    x: float
    y: float
    width: float
    height: float

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    color: Color

    def move(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt

    def distance_to(self, px: float, py: float) -> float:
        return math.hypot(self.x - px, self.y - py)

    def overlaps(self, other: "Ball") -> bool:
        return self.distance_to(other.x, other.y) < self.radius + other.radius


class GameLogic:
    def __init__(
        self,
        width: float = 800,
        height: float = 600,
        delete_zone: Optional[Rect] = None,
    ) -> None:
        self.width = width
        self.height = height
        self.balls: list[Ball] = []
        self.inventory: list[Ball] = []
        self.delete_zone = delete_zone or Rect(0, height - 80, width, 80)

    def spawn_ball(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        color: Optional[Color] = None,
        radius: float = 14.0,
        speed: float = 120.0,
    ) -> Ball:
        x = x if x is not None else random.uniform(radius, self.width - radius)
        y = y if y is not None else random.uniform(radius, self.height - radius)
        color = color if color is not None else self._random_color()
        angle = random.uniform(0, math.tau)
        ball = Ball(
            x=x,
            y=y,
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            radius=radius,
            color=color,
        )
        self.balls.append(ball)
        return ball

    @staticmethod
    def _random_color() -> Color:
        h = random.random()
        s = random.uniform(0.7, 1.0)
        v = random.uniform(0.6, 1.0)
        return _hsv_to_rgb(h, s, v)

    def update(self, dt: float) -> list[Ball]:
        merged = []
        for ball in self.balls:
            ball.move(dt)
            self._bounce_off_walls(ball)

        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                a, b = self.balls[i], self.balls[j]
                if a.overlaps(b):
                    a.color = b.color = mix_colors(a.color, b.color)
                    merged.append(a)

        removed = [b for b in self.balls if self.delete_zone.contains(b.x, b.y)]
        for ball in removed:
            self.delete_ball(ball)
        return removed

    def _bounce_off_walls(self, ball: Ball) -> None:
        if ball.x - ball.radius < 0:
            ball.x = ball.radius
            ball.vx = abs(ball.vx)
        elif ball.x + ball.radius > self.width:
            ball.x = self.width - ball.radius
            ball.vx = -abs(ball.vx)
        if ball.y - ball.radius < 0:
            ball.y = ball.radius
            ball.vy = abs(ball.vy)
        elif ball.y + ball.radius > self.height:
            ball.y = self.height - ball.radius
            ball.vy = -abs(ball.vy)

    def try_suck(self, x: float, y: float) -> bool:
        ball = self.ball_at(x, y)
        if ball is None:
            return False
        self.balls.remove(ball)
        self.inventory.append(ball)
        return True

    def spit(self, x: float, y: float) -> bool:
        if not self.inventory:
            return False
        ball = self.inventory.pop()
        ball.x = min(max(x, ball.radius), self.width - ball.radius)
        ball.y = min(max(y, ball.radius), self.height - ball.radius)
        angle = random.uniform(0, math.tau)
        ball.vx = math.cos(angle) * 150.0
        ball.vy = math.sin(angle) * 150.0
        self.balls.append(ball)
        return True

    def ball_at(self, x: float, y: float) -> Optional[Ball]:
        for ball in reversed(self.balls):
            if ball.distance_to(x, y) <= ball.radius:
                return ball
        return None

    def delete_ball(self, ball: Ball) -> None:
        if ball in self.balls:
            self.balls.remove(ball)

    def get_state(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "delete_zone": {
                "x": self.delete_zone.x,
                "y": self.delete_zone.y,
                "width": self.delete_zone.width,
                "height": self.delete_zone.height,
            },
            "balls": [
                {
                    "x": b.x,
                    "y": b.y,
                    "radius": b.radius,
                    "color": list(b.color),
                }
                for b in self.balls
            ],
            "inventory": [list(b.color) for b in self.inventory],
        }
