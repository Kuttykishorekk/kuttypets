"""
OmniPet - High-Performance Particle System with Memory Reuse Pool.
"""

from __future__ import annotations
import math
import random
from typing import List, Optional

class Particle:
    """Lightweight reusable particle."""
    def __init__(self):
        self.alive: bool = False
        self.x: float = 0.0
        self.y: float = 0.0
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.life: float = 0.0
        self.max_life: float = 1.0
        self.ptype: str = "sparkle"
        self.text: str = ""
        self.angle: float = 0.0
        self.v_rot: float = 0.0
        self.alpha: float = 1.0
        self.alpha_mul: float = 1.0

    def spawn(self, x: float, y: float, ptype: str = "sparkle", text: str = "") -> None:
        self.alive = True
        self.x = x
        self.y = y
        self.ptype = ptype
        self.text = text
        self.angle = random.uniform(0, math.pi * 2)

        if ptype == "spark":
            self.vx = random.uniform(-65, 65)
            self.vy = random.uniform(-140, -40)
            self.max_life = random.uniform(0.35, 0.70)
            self.v_rot = random.uniform(-8.0, 8.0)
            self.alpha_mul = 1.0
        elif ptype == "sparkle":
            self.vx = random.uniform(-25, 25)
            self.vy = random.uniform(-35, -5)
            self.max_life = random.uniform(0.5, 0.9)
            self.v_rot = random.uniform(-3.0, 3.0)
            self.alpha_mul = 0.85
        elif ptype == "bubble":
            self.vx = random.uniform(-8, 8)
            self.vy = -18.0
            self.max_life = 3.2
            self.v_rot = 0.0
            self.alpha_mul = 1.0
        elif ptype == "butterfly":
            self.vx = random.uniform(-25, 25)
            self.vy = random.uniform(-35, -10)
            self.max_life = 1.4
            self.v_rot = random.uniform(-2.0, 2.0)
            self.alpha_mul = 0.9
        elif ptype == "clover":
            self.vx = random.uniform(-20, 20)
            self.vy = random.uniform(-25, -5)
            self.max_life = 1.2
            self.v_rot = random.uniform(-4.0, 4.0)
            self.alpha_mul = 0.9
        elif ptype == "sakura":
            self.vx = random.uniform(-30, 30)
            self.vy = random.uniform(15, 45)
            self.max_life = 1.8
            self.v_rot = random.uniform(-1.5, 1.5)
            self.alpha_mul = 0.8
        elif ptype == "feather":
            self.vx = random.uniform(-15, 15)
            self.vy = random.uniform(-20, 10)
            self.max_life = 1.5
            self.v_rot = random.uniform(-1.0, 1.0)
            self.alpha_mul = 0.85
        else:
            self.vx = random.uniform(-20, 20)
            self.vy = random.uniform(-30, -10)
            self.max_life = 0.8
            self.v_rot = 0.0
            self.alpha_mul = 0.8

        self.life = self.max_life
        self.alpha = self.alpha_mul

    def update(self, dt: float) -> bool:
        if not self.alive:
            return False
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return False
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.v_rot * dt
        if self.ptype == "spark":
            self.vy += 220.0 * dt
        progress = self.life / self.max_life
        self.alpha = progress * self.alpha_mul
        return True


class ParticlePool:
    """Zero-allocation memory pool for particles."""

    def __init__(self, capacity: int = 32):
        self.pool: List[Particle] = [Particle() for _ in range(capacity)]

    def emit(self, count: int, x: float, y: float, ptype: str = "sparkle", text: str = "") -> None:
        emitted = 0
        for p in self.pool:
            if not p.alive:
                p.spawn(x, y, ptype, text)
                emitted += 1
                if emitted >= count:
                    break

    def update(self, dt: float) -> None:
        for p in self.pool:
            if p.alive:
                p.update(dt)

    def active_particles(self) -> List[Particle]:
        return [p for p in self.pool if p.alive]
