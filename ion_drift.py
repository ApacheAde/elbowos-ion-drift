#!/usr/bin/env python3
"""ION DRIFT — neon asteroids-harvest arcade. Python 3 + pygame. ElbowOS."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
if RECORD:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

W, H, FPS = 1080, 1920, 30
TITLE = "ION DRIFT"
HANDLE = "x.com/ElbowOS"
OUT = os.environ.get("ELBOWOS_MP4", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ION_DRIFT_ElbowOS.mp4"))
BG = (8, 4, 22)
MAG = (255, 48, 196)
CYAN = (48, 255, 230)
GOLD = (255, 214, 70)
AMBER = (255, 156, 32)
LIME = (140, 255, 70)
VIO = (170, 90, 255)
WHITE = (240, 244, 255)


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def ang_diff(a, b):
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    return d


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, col):
        a = random.uniform(0, 6.283)
        sp = random.uniform(40, 380)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * sp, math.sin(a) * sp
        self.life = random.uniform(0.25, 0.7)
        self.col = col
        self.r = random.randint(2, 6)

    def tick(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, s):
        if self.life <= 0:
            return
        pygame.draw.circle(s, self.col, (int(self.x), int(self.y)), max(1, self.r))


class Shard:
    def __init__(self, x, y, r, tier=2):
        self.x, self.y, self.r, self.tier = x, y, r, tier
        a = random.uniform(0, 6.283)
        sp = random.uniform(40, 110 + 30 * (3 - tier))
        self.vx, self.vy = math.cos(a) * sp, math.sin(a) * sp
        self.spin = random.uniform(-2.4, 2.4)
        self.rot = random.uniform(0, 6.283)
        n = random.randint(5, 7)
        self.pts = [
            (math.cos(i * 6.283 / n + random.uniform(-0.2, 0.2)) * random.uniform(0.62, 1.0),
             math.sin(i * 6.283 / n + random.uniform(-0.2, 0.2)) * random.uniform(0.62, 1.0))
            for i in range(n)
        ]
        self.col = random.choice((AMBER, LIME, VIO, CYAN))

    def tick(self, dt):
        self.x = (self.x + self.vx * dt) % W
        self.y = (self.y + self.vy * dt) % H
        self.rot += self.spin * dt

    def poly(self):
        ca, sa = math.cos(self.rot), math.sin(self.rot)
        out = []
        for px, py in self.pts:
            x = px * self.r
            y = py * self.r
            out.append((self.x + x * ca - y * sa, self.y + x * sa + y * ca))
        return out

    def draw(self, s):
        pts = self.poly()
        pygame.draw.polygon(s, self.col, pts, 3)
        inner = [(self.x + (p[0] - self.x) * 0.35, self.y + (p[1] - self.y) * 0.35) for p in pts]
        pygame.draw.polygon(s, WHITE, inner, 1)


class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "life")

    def __init__(self, x, y, a):
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * 920, math.sin(a) * 920
        self.life = 0.85

    def tick(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return 0 < self.x < W and 0 < self.y < H and self.life > 0

    def draw(self, s):
        pygame.draw.circle(s, GOLD, (int(self.x), int(self.y)), 5)
        pygame.draw.circle(s, WHITE, (int(self.x), int(self.y)), 2)


class Game:
    def __init__(self):
        self.ship = pygame.Vector2(W / 2, H * 0.62)
        self.vel = pygame.Vector2(0, 0)
        self.ang = -math.pi / 2
        self.cool = 0.0
        self.score = 0
        self.combo = 0
        self.alive = True
        self.t = 0.0
        self.shards = []
        self.bullets = []
        self.parts = []
        self.stars = [(random.randrange(W), random.randrange(H), random.randint(1, 3),
                       random.choice((WHITE, VIO, CYAN))) for _ in range(90)]
        for _ in range(7):
            self.spawn(2)

    def spawn(self, tier=2):
        r = {2: 78, 1: 46, 0: 24}[tier]
        side = random.choice((0, 1, 2, 3))
        if side == 0:
            x, y = random.uniform(0, W), -r
        elif side == 1:
            x, y = random.uniform(0, W), H + r
        elif side == 2:
            x, y = -r, random.uniform(0, H)
        else:
            x, y = W + r, random.uniform(0, H)
        if math.hypot(x - self.ship.x, y - self.ship.y) < 220:
            x = (x + W * 0.4) % W
        self.shards.append(Shard(x, y, r, tier))

    def boom(self, x, y, col, n=14):
        for _ in range(n):
            self.parts.append(Particle(x, y, col))

    def shoot(self):
        if self.cool > 0 or not self.alive:
            return
        nose = self.ship + pygame.Vector2(math.cos(self.ang), math.sin(self.ang)) * 34
        self.bullets.append(Bullet(nose.x, nose.y, self.ang))
        self.cool = 0.14
        self.boom(nose.x, nose.y, GOLD, 4)

    def split(self, sh):
        self.score += (3 - sh.tier) * 50 + 40 + self.combo * 8
        self.combo = min(self.combo + 1, 24)
        self.boom(sh.x, sh.y, sh.col, 18)
        if sh.tier > 0:
            for _ in range(2):
                kid = Shard(sh.x, sh.y, {1: 46, 0: 24}[sh.tier - 1], sh.tier - 1)
                kid.col = sh.col
                self.shards.append(kid)

    def tick(self, dt, keys, auto):
        self.t += dt
        self.cool = max(0.0, self.cool - dt)
        rot = 0
        thrust = False
        fire = False
        if auto:
            rot, thrust, fire = self.ai()
        else:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                rot = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                rot = 1
            thrust = keys[pygame.K_UP] or keys[pygame.K_w]
            fire = keys[pygame.K_SPACE] or keys[pygame.K_k]
        if self.alive:
            self.ang += rot * 3.6 * dt
            if thrust:
                self.vel.x += math.cos(self.ang) * 420 * dt
                self.vel.y += math.sin(self.ang) * 420 * dt
                tail = self.ship - pygame.Vector2(math.cos(self.ang), math.sin(self.ang)) * 22
                self.boom(tail.x, tail.y, random.choice((CYAN, MAG)), 2)
            if fire:
                self.shoot()
            self.vel *= 0.992
            if self.vel.length() > 520:
                self.vel.scale_to_length(520)
            self.ship.x = (self.ship.x + self.vel.x * dt) % W
            self.ship.y = (self.ship.y + self.vel.y * dt) % H
        for sh in self.shards:
            sh.tick(dt)
        self.bullets = [b for b in self.bullets if b.tick(dt)]
        self.parts = [p for p in self.parts if p.tick(dt)]
        keep = []
        for sh in self.shards:
            hit = False
            for b in list(self.bullets):
                if (b.x - sh.x) ** 2 + (b.y - sh.y) ** 2 < (sh.r + 8) ** 2:
                    self.bullets.remove(b)
                    self.split(sh)
                    hit = True
                    break
            if not hit:
                if self.alive and (self.ship.x - sh.x) ** 2 + (self.ship.y - sh.y) ** 2 < (sh.r + 16) ** 2:
                    self.alive = False
                    self.boom(self.ship.x, self.ship.y, MAG, 40)
                    self.combo = 0
                else:
                    keep.append(sh)
        self.shards = keep
        while len(self.shards) < 6:
            self.spawn(random.choice((2, 2, 1)))
        if not self.alive and auto and self.t > 0.4:
            self.ship.update(W / 2, H * 0.62)
            self.vel.update(0, 0)
            self.ang = -math.pi / 2
            self.alive = True
            self.shards = [s for s in self.shards
                           if math.hypot(s.x - self.ship.x, s.y - self.ship.y) > 260]
            self.t = 0.0

    def ai(self):
        if not self.shards:
            return 0, False, False
        def wrap_d(ax, ay, bx, by):
            dx = bx - ax
            dy = by - ay
            if dx > W / 2:
                dx -= W
            if dx < -W / 2:
                dx += W
            if dy > H / 2:
                dy -= H
            if dy < -H / 2:
                dy += H
            return dx, dy, math.hypot(dx, dy)

        nearest = min(self.shards, key=lambda s: wrap_d(self.ship.x, self.ship.y, s.x, s.y)[2] - s.r)
        dx, dy, dist = wrap_d(self.ship.x, self.ship.y, nearest.x, nearest.y)
        want = math.atan2(dy, dx)
        d = ang_diff(self.ang, want)
        rot = 1 if d > 0.08 else -1 if d < -0.08 else 0
        danger = dist < nearest.r + 140
        if danger:
            flee = math.atan2(-dy, -dx)
            d2 = ang_diff(self.ang, flee)
            rot = 1 if d2 > 0.1 else -1 if d2 < -0.1 else 0
            return rot, True, abs(d) < 0.35
        thrust = dist > 280 or self.vel.length() < 60
        fire = abs(d) < 0.22 and dist < 720
        return rot, thrust, fire

    def draw(self, s, font, big, tiny):
        s.fill(BG)
        pulse = 18 + int(10 * math.sin(self.t * 1.7))
        pygame.draw.circle(s, (28, 8, 48), (W // 2, int(H * 0.38)), 420 + pulse)
        pygame.draw.circle(s, (16, 6, 36), (W // 2, int(H * 0.38)), 260 + pulse // 2)
        for x, y, r, c in self.stars:
            yy = (y + int(self.t * (8 + r * 6))) % H
            pygame.draw.circle(s, c, (x, yy), r)
        for p in self.parts:
            p.draw(s)
        for sh in self.shards:
            sh.draw(s)
        for b in self.bullets:
            b.draw(s)
        if self.alive:
            ca, sa = math.cos(self.ang), math.sin(self.ang)
            nose = (self.ship.x + ca * 36, self.ship.y + sa * 36)
            lft = (self.ship.x + math.cos(self.ang + 2.5) * 24, self.ship.y + math.sin(self.ang + 2.5) * 24)
            rgt = (self.ship.x + math.cos(self.ang - 2.5) * 24, self.ship.y + math.sin(self.ang - 2.5) * 24)
            pygame.draw.polygon(s, MAG, [nose, lft, rgt])
            pygame.draw.polygon(s, CYAN, [nose, lft, rgt], 3)
            pygame.draw.circle(s, WHITE, (int(self.ship.x), int(self.ship.y)), 5)
        bar = pygame.Surface((W, 168), pygame.SRCALPHA)
        bar.fill((6, 2, 18, 210))
        s.blit(bar, (0, 0))
        s.blit(big.render(TITLE, True, MAG), (40, 22))
        s.blit(font.render(f"SCORE  {self.score:06d}   COMBO x{self.combo}", True, GOLD), (40, 100))
        s.blit(tiny.render(HANDLE, True, CYAN), (W - 340, 36))
        s.blit(tiny.render("ARROWS steer   SPACE fire   W thrust", True, (180, 170, 210)), (40, H - 70))
        pygame.draw.line(s, MAG, (0, 168), (W, 168), 3)
        pygame.draw.line(s, CYAN, (0, H - 96), (W, H - 96), 2)


def record_reel(game, surf, font, big, tiny):
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "fast", "-movflags", "+faststart", OUT,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    frames = FPS * 15
    dt = 1.0 / FPS
    try:
        for i in range(frames):
            game.tick(dt, None, auto=True)
            game.draw(surf, font, big, tiny)
            proc.stdin.write(pygame.image.tostring(surf, "RGB"))
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "ignore") if proc.stderr else ""
        rc = proc.wait(timeout=60)
        if rc != 0:
            raise RuntimeError(err[-2000:])
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        raise


def main():
    pygame.init()
    pygame.font.init()
    if RECORD:
        screen = pygame.Surface((W, H))
    else:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(f"{TITLE} — {HANDLE}")
    font = pygame.font.SysFont("DejaVu Sans Mono", 36, bold=True)
    big = pygame.font.SysFont("DejaVu Sans", 64, bold=True)
    tiny = pygame.font.SysFont("DejaVu Sans Mono", 28, bold=True)
    game = Game()
    if RECORD:
        record_reel(game, screen, font, big, tiny)
        print("WROTE", OUT)
        pygame.quit()
        return
    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r and not game.alive:
                game.__init__()
        game.tick(dt, pygame.key.get_pressed(), auto=False)
        game.draw(screen, font, big, tiny)
        if not game.alive:
            msg = big.render("DRIFT LOST  —  R to retry", True, GOLD)
            screen.blit(msg, msg.get_rect(center=(W // 2, H // 2)))
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
