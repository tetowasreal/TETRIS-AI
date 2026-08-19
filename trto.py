import pygame
import random
import copy

# -------------------- Config --------------------
WIDTH, HEIGHT = 300, 600
PANEL_WIDTH = 250
GRID_SIZE = 30
COLS, ROWS = WIDTH // GRID_SIZE, HEIGHT // GRID_SIZE

BLACK = (0, 0, 0)
GRAY = (40, 40, 40)
CYAN = (0, 255, 255)
YELLOW = (255, 255, 0)
PURPLE = (160, 0, 240)
ORANGE = (255, 165, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 60, 60)
WHITE = (240, 240, 240)

MAX_POINTS = 150

SHAPES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
}

COLORS = {
    "I": CYAN,
    "O": YELLOW,
    "T": PURPLE,
    "L": ORANGE,
    "J": BLUE,
    "S": GREEN,
    "Z": RED,
}

# -------------------- Piece --------------------
class Piece:
    def __init__(self):
        self.type = random.choice(list(SHAPES.keys()))
        self.shape = copy.deepcopy(SHAPES[self.type])
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

# -------------------- AI --------------------
class AI:
    def __init__(self):
        self.w_line_clear = 1.0
        self.w_center_hole = -1.0
        self.w_edge_hole = 0.5
        self.w_gameover = -10.0
        self.w_height_penalty = -0.3

        self.lr = 0.0005

        self.hist_center = []
        self.hist_edge = []
        self.hist_line = []

    def compute_features(self, board):
        heights = [0] * COLS
        holes_center = 0
        holes_edge = 0

        for x in range(COLS):
            found = False

            for y in range(ROWS):
                if board[y][x]:
                    if not found:
                        heights[x] = ROWS - y
                        found = True

                elif found:
                    # 블록 아래 빈칸 = hole
                    if x == 0 or x == COLS - 1:
                        holes_edge += 1
                    else:
                        holes_center += 1

        danger = sum(h * h for h in heights)

        bumpiness = 0
        for i in range(COLS - 1):
            bumpiness += abs(heights[i] - heights[i + 1])

        return {
            "height": sum(heights),
            "danger": danger,
            "center": holes_center,
            "edge": holes_edge,
            "bumpiness": bumpiness
        }

    def evaluate(self, board):
        f = self.compute_features(board)

        score = -(
            f["danger"] * 0.08 +
            f["center"] * 3.0 +
            f["edge"] * 1.0 +
            f["bumpiness"] * 0.6
        )

        return score, f

    def learn(self, board, cleared):
        _, f = self.evaluate(board)

        # 줄 제거 보상
        self.w_line_clear += cleared * 0.01

        # 위험하면 height 패널티 강화
        self.w_height_penalty -= self.lr * f["danger"] * 0.0001

        self.hist_center.append(f["center"])
        self.hist_edge.append(f["edge"])
        self.hist_line.append(cleared)

    def learn_gameover(self, board):
        f = self.compute_features(board)
        self.w_center_hole += self.lr * (-5) * f["center"]
        self.w_edge_hole += self.lr * (-5) * f["edge"]

    def collision(self, board, piece, x, y, shape):
        for py, row in enumerate(shape):
            for px, cell in enumerate(row):
                if not cell:
                    continue
                nx, ny = x + px, y + py
                if nx < 0 or nx >= COLS or ny >= ROWS:
                    return True
                if ny >= 0 and board[ny][nx]:
                    return True
        return False

    def drop(self, board, piece, x, shape):
        y = 0
        while not self.collision(board, piece, x, y + 1, shape):
            y += 1
        return y

    def best_move(self, game):
        best_score = -1e9
        best_x, best_shape = game.piece.x, game.piece.shape

        base = game.piece.shape

        for r in range(4):
            shape = base
            for _ in range(r):
                shape = [list(row) for row in zip(*shape[::-1])]

            for x in range(-2, COLS):
                y = self.drop(game.board, game.piece, x, shape)

                if self.collision(game.board, game.piece, x, y, shape):
                    continue

                temp = copy.deepcopy(game.board)
                for py, row in enumerate(shape):
                    for px, cell in enumerate(row):
                        if cell:
                            ny, nx = y + py, x + px
                            if 0 <= ny < ROWS and 0 <= nx < COLS:
                                temp[ny][nx] = 1

                score, _ = self.evaluate(temp)
                if score > best_score:
                    best_score = score
                    best_x, best_shape = x, shape

        return best_x, best_shape

# -------------------- Game --------------------
class Game:
    def __init__(self, ai):
        self.ai = ai
        self.reset()
        self.clock = pygame.time.Clock()
        self.drop_time = 0
        self.font = pygame.font.SysFont("consolas", 16)

    def reset(self):
        self.board = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.piece = Piece()
        x, shape = self.ai.best_move(self)
        self.piece.shape = shape
        self.piece.x = x
    def collision(self, piece, dx=0, dy=0):
        for y, row in enumerate(piece.shape):
            for x, cell in enumerate(row):
                if not cell:
                    continue
                nx = piece.x + x + dx
                ny = piece.y + y + dy
                if nx < 0 or nx >= COLS or ny >= ROWS:
                    return True
                if ny >= 0 and self.board[ny][nx]:
                    return True
        return False
    def spawn_piece(self):
        self.piece = Piece()

        x, shape = self.ai.best_move(self)
        self.piece.shape = shape
        self.piece.x = x
    def lock(self):
        for y, row in enumerate(self.piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    self.board[self.piece.y + y][self.piece.x + x] = 1

        cleared = self.clear()
        self.ai.learn(self.board, cleared)

        self.spawn_piece()
        if self.collision(self.piece):
            self.ai.learn_gameover(self.board)
            self.reset()

    def clear(self):
        new = [r for r in self.board if any(c is None for c in r)]
        cleared = ROWS - len(new)
        for _ in range(cleared):
            new.insert(0, [None] * COLS)
        self.board = new
        return cleared

    def update(self):

        while not self.collision(self.piece, dy=1):
            self.piece.y += 1

        self.lock()

    def draw(self, screen):
        screen.fill(BLACK)
        features = self.ai.compute_features(self.board)
        for y in range(ROWS):
            for x in range(COLS):
                if self.board[y][x]:
                    pygame.draw.rect(screen, GRAY,
                        (x*GRID_SIZE, y*GRID_SIZE, GRID_SIZE, GRID_SIZE))

        for y, row in enumerate(self.piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    pygame.draw.rect(screen, CYAN,
                        ((self.piece.x+x)*GRID_SIZE,
                         (self.piece.y+y)*GRID_SIZE,
                         GRID_SIZE, GRID_SIZE))

        ui_x = WIDTH + 10
        texts = [
            f"danger: {features['danger']:.1f}",
            f"center holes: {features['center']}",
            f"edge holes: {features['edge']}",
            f"bumpiness: {features['bumpiness']:.1f}"
            ]

        for i, t in enumerate(texts):
            screen.blit(self.font.render(t, True, WHITE), (ui_x, 20 + i * 20))

# -------------------- Manager --------------------
class GameManager:
    def __init__(self, n=5):
        self.ai = AI()
        self.games = [Game(self.ai) for _ in range(n)]

    def update(self):
        for g in self.games:
            g.update()

    def draw(self, screen):
        self.games[0].draw(screen)

# -------------------- Main --------------------

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH + PANEL_WIDTH, HEIGHT))
    pygame.display.set_caption("Tetris AI Multi Fixed")

    manager = GameManager(5)

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

        manager.update()
        manager.draw(screen)
        pygame.display.update()

    pygame.quit()

if __name__ == "__main__":
    main()