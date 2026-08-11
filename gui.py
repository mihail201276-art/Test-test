from __future__ import annotations

import math
import random

import pygame

from logic import GameLogic, Rect


START_BALLS = 20
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 650
INVENTORY_PANEL_WIDTH = 160
FIELD_WIDTH = WINDOW_WIDTH - INVENTORY_PANEL_WIDTH
FIELD_HEIGHT = WINDOW_HEIGHT
DELETE_ZONE_HEIGHT = 80
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 60, 60)
GRAY = (120, 120, 120)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(a, b, t) -> tuple:
    return tuple(int(round(_lerp(a[i], b[i], t))) for i in range(3))


def _shade(color, factor: float) -> tuple:
    return tuple(min(255, int(color[i] * factor)) for i in range(3))


def draw_ball(surface, x: float, y: float, radius: float, color) -> None:
    cx, cy = int(x), int(y)
    r = max(int(radius), 1)
    pygame.draw.circle(surface, _shade(color, 0.65), (cx, cy), r)
    pygame.draw.circle(surface, color, (cx, cy), max(int(r * 0.82), 1))
    pygame.draw.circle(surface, _lerp_color(color, WHITE, 0.25), (cx, cy), max(int(r * 0.55), 1))
    highlight = _lerp_color(color, WHITE, 0.75)
    pygame.draw.circle(
        surface,
        highlight,
        (cx - int(r * 0.35), cy - int(r * 0.4)),
        max(int(r * 0.28), 1),
    )


class RingEffect:
    def __init__(self, x: float, y: float, color, max_radius: float, duration: float = 0.4) -> None:
        self.x = x
        self.y = y
        self.color = color
        self.max_radius = max_radius
        self.life = 0.0
        self.duration = duration

    @property
    def done(self) -> bool:
        return self.life >= self.duration

    def update(self, dt: float) -> None:
        self.life += dt

    def draw(self, surface) -> None:
        if self.done:
            return
        t = min(self.life / self.duration, 1.0)
        eased = 1.0 - (1.0 - t) ** 2
        radius = int(_lerp(6.0, self.max_radius, eased))
        alpha = int(220 * (1.0 - t))
        pygame.draw.circle(surface, (*self.color, alpha), (int(self.x), int(self.y)), radius, 3)


class Gui:
    def __init__(self) -> None:
        pygame.init()
        self.logic = GameLogic(FIELD_WIDTH, FIELD_HEIGHT)
        self.logic.delete_zone = Rect(0, FIELD_HEIGHT - DELETE_ZONE_HEIGHT, FIELD_WIDTH, DELETE_ZONE_HEIGHT)
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Balls")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("segoeui", 20)
        self.overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)

        self.carried = None
        self.effects: list[RingEffect] = []
        self.display_color: dict[int, list] = {}
        self.prev_color: dict[int, tuple] = {}
        self.running = True

        for _ in range(START_BALLS):
            self._spawn_random_ball()

    def _spawn_random_ball(self) -> None:
        radius = random.uniform(12.0, 18.0)
        x = random.uniform(radius, FIELD_WIDTH - radius)
        y = random.uniform(radius, FIELD_HEIGHT - DELETE_ZONE_HEIGHT - radius)
        self.logic.spawn_ball(x=x, y=y, radius=radius, speed=random.uniform(100.0, 160.0))

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_click(event.pos)

    def _on_click(self, pos) -> None:
        mx, my = pos
        if mx >= FIELD_WIDTH:
            return
        ball = self.logic.ball_at(mx, my)
        if ball is not None:
            if self.logic.try_suck(mx, my):
                self.carried = ball
            return
        if self.carried is not None:
            if self.logic.spit(mx, my):
                self.carried = None
        elif self.logic.inventory:
            self.logic.spit(mx, my)

    def _update(self, dt: float) -> None:
        for ball in self.logic.balls:
            key = id(ball)
            if key not in self.display_color:
                self.display_color[key] = list(ball.color)
                self.prev_color[key] = ball.color

        self.logic.update(dt)

        current_ids = {id(b) for b in self.logic.balls}
        if self.carried is not None:
            current_ids.add(id(self.carried))
        for key in list(self.display_color):
            if key not in current_ids:
                del self.display_color[key]
                del self.prev_color[key]

        for ball in self.logic.balls:
            key = id(ball)
            current = self.display_color[key]
            target = ball.color
            if self.prev_color[key] != target:
                self.effects.append(RingEffect(ball.x, ball.y, target, ball.radius * 2.6))
            for i in range(3):
                current[i] = _lerp(current[i], target[i], 0.25)
            self.display_color[key] = current
            self.prev_color[key] = target

        for effect in self.effects:
            effect.update(dt)
        self.effects = [e for e in self.effects if not e.done]

        if self.carried is not None:
            self.carried.x, self.carried.y = pygame.mouse.get_pos()

    def _draw(self) -> None:
        self.screen.fill(WHITE)

        for ball in self.logic.balls:
            draw_ball(self.screen, ball.x, ball.y, ball.radius, tuple(int(c) for c in self.display_color[id(ball)]))

        self.overlay.fill((0, 0, 0, 0))
        zone = self.logic.delete_zone
        pygame.draw.rect(self.overlay, (255, 90, 90, 40), (zone.x, zone.y, zone.width, zone.height))
        for effect in self.effects:
            effect.draw(self.overlay)
        self.screen.blit(self.overlay, (0, 0))

        pygame.draw.rect(self.screen, RED, (zone.x, zone.y, zone.width, zone.height), 2)
        label = self.font.render("Зона удаления", True, RED)
        self.screen.blit(label, (zone.x + 10, zone.y + zone.height - label.get_height() - 6))

        if self.carried is not None:
            mx, my = pygame.mouse.get_pos()
            ghost = pygame.Surface((int(self.carried.radius * 2.5) + 4, int(self.carried.radius * 2.5) + 4), pygame.SRCALPHA)
            draw_ball(ghost, ghost.get_width() / 2, ghost.get_height() / 2, self.carried.radius, self.carried.color)
            ghost.set_alpha(170)
            self.screen.blit(ghost, (mx - ghost.get_width() / 2, my - ghost.get_height() / 2))

        self._draw_inventory_panel()

        fps = int(self.clock.get_fps())
        info = f"Шарики: {len(self.logic.balls)} | Инвентарь: {len(self.logic.inventory)} | FPS: {fps}"
        pygame.display.set_caption(f"Balls — {info}")

    def _draw_inventory_panel(self) -> None:
        px = FIELD_WIDTH
        pygame.draw.rect(self.screen, (245, 245, 245), (px, 0, INVENTORY_PANEL_WIDTH, WINDOW_HEIGHT))
        pygame.draw.line(self.screen, GRAY, (px, 0), (px, WINDOW_HEIGHT), 2)

        title = self.font.render(f"Инвентарь ({len(self.logic.inventory)})", True, BLACK)
        self.screen.blit(title, (px + 10, 10))

        cell_size = 52
        margin = 10
        cols = 2
        for index, ball in enumerate(self.logic.inventory):
            col = index % cols
            row = index // cols
            cx = px + margin + col * (cell_size + margin) + cell_size / 2
            cy = 40 + row * (cell_size + margin) + cell_size / 2
            pygame.draw.circle(self.screen, GRAY, (int(cx), int(cy)), int(cell_size / 2), 1)
            draw_ball(self.screen, cx, cy, 16, ball.color)

        if not self.logic.inventory:
            hint = self.font.render("Пусто", True, GRAY)
            self.screen.blit(hint, (px + 10, 40))
            hint2 = self.font.render("Клик по шарику —", True, GRAY)
            hint3 = self.font.render("всасать его сюда", True, GRAY)
            self.screen.blit(hint2, (px + 10, 65))
            self.screen.blit(hint3, (px + 10, 88))

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
        pygame.quit()


def run() -> None:
    Gui().run()


if __name__ == "__main__":
    run()
