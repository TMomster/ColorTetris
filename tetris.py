# Tetris 使用 Pygame 实现
import pygame
import sys
import random
import math

# --- 常量设置 ---
GRID_SIZE = 30  # 单位网格尺寸（可缩放）
GRID_WIDTH = 10  # 游戏区域列数（宽度）
GRID_HEIGHT = 20  # 游戏区域行数（高度）
FPS = 60  # 帧数

# --- 方块形状设置 ---
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1], [1, 1]],  # O
    [[0, 1, 0], [1, 1, 1]],  # T
    [[1, 0], [1, 0], [1, 1]],  # L
    [[0, 1], [0, 1], [1, 1]],  # J
    [[1, 1, 0], [0, 1, 1]],  # S
    [[0, 1, 1], [1, 1, 0]]  # Z
]

# --- 解析度设置 ---
RESOLUTIONS = [
    (800, 600),  # 600p
    (1280, 720),  # 720p
    (1600, 900),  # 900p
    (1920, 1080)  # 1080p
]


# --- 游戏状态枚举 ---
class GameState:
    MAIN_MENU = 0  # 主菜单
    LEVEL_SELECT = 1  # 关卡选择
    OPTIONS = 2  # 设置菜单
    GAME = 3  # 游戏
    GAME_OVER = 4  # 游戏结束
    PAUSED = 5  # 暂停菜单


# --- 颜色方案 ---
class ColorScheme:
    BACKGROUND = pygame.Color("#1A237E")  # 主要背景颜色
    TEXT = pygame.Color("#FFFFFF")  # 文字颜色
    BUTTON = pygame.Color("#3F51B5")  # 按钮颜色
    BUTTON_HOVER = pygame.Color("#5C6BC0")  # 按钮高亮颜色
    GRID_LINE = pygame.Color("#303F9F")  # 网格线颜色
    SHAPE_COLORS = [  # 方块颜色
        pygame.Color("#00BCD4"),  # I
        pygame.Color("#FFEB3B"),  # O
        pygame.Color("#E91E63"),  # T
        pygame.Color("#FF9800"),  # L
        pygame.Color("#2196F3"),  # J
        pygame.Color("#4CAF50"),  # S
        pygame.Color("#F44336")  # Z
    ]


# --- 模糊处理 ---
def apply_blur(surface, factor=4):
    """ 通过平均采样实现模糊效果 """
    small = pygame.transform.smoothscale(surface,
                                         (surface.get_width() // factor, surface.get_height() // factor))
    return pygame.transform.smoothscale(small, surface.get_size())


# --- 按钮 ---
class Button:
    def __init__(self, text, x, y, width, height, action=None):
        """ 游戏界面按钮组件 """
        self.rect = pygame.Rect(x, y, width, height)  # 按钮的矩形
        self.text = text  # 按钮文本
        self.action = action  # 点击事件
        self.hovered = False  # 是否高亮

    def draw(self, surface):
        """ 按钮绘制 """
        color = ColorScheme.BUTTON_HOVER if self.hovered else ColorScheme.BUTTON  # 按钮颜色
        pygame.draw.rect(surface, color, self.rect)  # 绘制按钮
        font = pygame.font.Font(None, 36)  # 设置字体
        text_surf = font.render(self.text, True, ColorScheme.TEXT)  # 创建文本
        text_rect = text_surf.get_rect(center=self.rect.center)  # 创建文本的位置
        surface.blit(text_surf, text_rect)  # 绘制文本


class Tetris:
    def __init__(self, level):
        self.game = None  # 初始化game为None

        # 游戏区域相关
        self.grid = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]  # 二维列表网格表示游戏区域

        # 形状相关
        self.current_shape = None  # 当前形状
        self.shape_color = 0  # 当前形状颜色
        self.next_shape = self.choose_shape()  # 下个形状
        self.next_color = self.choose_next_color()  # 下个形状的颜色

        # 信息记录与规则控制相关
        self.score = 0  # 分数
        self.level = level  # 当前关卡（难度等级）
        self.last_fall = pygame.time.get_ticks()  # 上次下落时间
        self.fall_speed = max(50, 1000 - (level - 1) * 100)  # 下落速度
        self.new_shape()  # 控制下落速度
        self.game_over = False  # 游戏结束标志

        # 特效相关
        self.hard_drop_triggered = False  # 硬下落触发标志
        self.ghost_effect_active = False  # 幽灵方块特效激活标志
        self.ghost_effect_frames = 0  # 幽灵方块特效帧数
        self.ghost_effect_position = (0, 0)  # 幽灵方块特效的位置
        self.hard_drop_shape = None  # 硬下落时的方块形状
        self.score_effect = None  # 加分特效
        self.score_effect_frames = 0  # 加分特效持续时间
        self.score_effect_position = (0, 0)  # 加分特效的位置
        self.particles = []  # 存储粒子效果

    class Particle:
        def __init__(self, x, y, color):
            self.x = x
            self.y = y
            self.color = color
            self.size = random.randint(2, 4)
            self.life = 60  # 粒子存活时间（帧数）
            self.vx = random.uniform(-3, 3)
            self.vy = random.uniform(-5, -2)
            self.gravity = 0.25

    def update_particles(self):
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += p.gravity
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def choose_shape(self):
        """ 根据设置选择下一个形状 """
        if self.game and self.game.disable_sz_shapes:  # 过滤掉S和Z型方块（SHAPES[5]和SHAPES[6]）
            available_shapes = [shape for i, shape in enumerate(SHAPES) if i not in [5, 6]]
            return random.choice(available_shapes)
        return random.choice(SHAPES)

    def new_shape(self):
        """ 生成新方块并检查结束条件 """
        self.current_shape = self.next_shape  # 交换形状
        self.shape_color = self.next_color  # 交换颜色
        self.next_shape = self.choose_shape()  # 预选下个形状
        self.next_color = self.choose_next_color()  # 预选下个形状颜色
        self.shape_x = GRID_WIDTH // 2 - len(self.current_shape[0]) // 2  # 生成位置在水平中央
        self.shape_y = 0  # 生成位置在顶部
        if self.check_collision(self.shape_x, self.shape_y, self.current_shape):  # 检查是否与底部或顶部发生碰撞
            self.game_over = True  # 游戏结束

    def check_collision(self, x, y, shape):
        """ 检测碰撞 """
        for row in range(len(shape)):
            for col in range(len(shape[row])):
                if shape[row][col]:
                    if x + col < 0 or x + col >= GRID_WIDTH or \
                            y + row >= GRID_HEIGHT or \
                            (y + row >= 0 and self.grid[y + row][x + col]):
                        return True
        return False

    def rotate(self):
        """ 旋转方块 """
        rotated = list(zip(*self.current_shape[::-1]))  # 矩阵转置
        if not self.check_collision(self.shape_x, self.shape_y, rotated):  # 检查旋转后是否与上下边缘碰撞
            self.current_shape = rotated  # 更新形状

    def move(self, dx):
        """ 水平移动方块 """
        if not self.check_collision(self.shape_x + dx, self.shape_y, self.current_shape):  # 检查移动后是否与左右边缘碰撞
            self.shape_x += dx  # 更新位置

    def drop(self):
        """ 软下落 """
        self.shape_y += 1  # 尝试向下移动
        if self.check_collision(self.shape_x, self.shape_y, self.current_shape):  # 如果碰撞上下边缘，退回此前位置
            self.shape_y -= 1  # 退回
            self.lock_shape()  # 锁定形状

    def hard_drop(self):
        """ 硬下落 """
        self.hard_drop_shape = self.current_shape  # 记录硬下落时的方块形状

        # 计算幽灵方块位置
        ghost_y = self.shape_y
        while not self.check_collision(self.shape_x, ghost_y + 1, self.current_shape):
            ghost_y += 1
        self.ghost_effect_position = (self.shape_x, ghost_y)  # 记录幽灵方块的位置

        while not self.check_collision(self.shape_x, self.shape_y + 1, self.current_shape):
            self.shape_y += 1
        self.lock_shape()
        self.hard_drop_triggered = True  # 触发震动

        # 仅在 ghost_shape_enabled 为 True 时启用消散特效
        if self.game.ghost_shape_enabled:
            self.ghost_effect_active = True
            self.ghost_effect_frames = 30  # 设置特效持续帧数

    def lock_shape(self):
        """ 锁定形状 """
        for row in range(len(self.current_shape)):
            for col in range(len(self.current_shape[row])):
                if self.current_shape[row][col]:
                    self.grid[self.shape_y + row][self.shape_x + col] = self.shape_color + 1

        lines = 0
        for row in range(len(self.grid)):
            if all(self.grid[row]):
                del self.grid[row]
                self.grid.insert(0, [0] * GRID_WIDTH)
                lines += 1

        # 消除积分计算 = 每行基础分 10 * 行数
        if lines > 0:
            # 生成破裂粒子
            for y in range(len(self.grid)):
                for x in range(GRID_WIDTH):
                    if self.grid[y][x]:
                        # 生成5-8个粒子
                        for _ in range(random.randint(5, 8)):
                            px = (x + 0.5) * self.game.grid_size + self.game.game_area_x
                            py = (y + 0.5) * self.game.grid_size + self.game.game_area_y
                            self.particles.append(self.Particle(px, py,
                                                                ColorScheme.SHAPE_COLORS[self.grid[y][x] - 1]))
            base_score = 10 * lines
            multiplier = lines
            self.score += base_score * multiplier
            self.score_effect = f"+{base_score * multiplier}"
            self.score_effect_frames = 45  # 增加特效持续时间
            self.score_effect_position = (self.shape_x, self.shape_y)
            self.score_effect_scale = 1.0  # 缩放比例
            self.score_effect_color = (0, 255, 0)  # 初始颜色

        self.new_shape()
        self.hard_drop_triggered = False  # 重置震动触发标志

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_fall > self.fall_speed:
            self.drop()
            self.last_fall = now

    def choose_next_color(self):
        """选择下一个方块的颜色"""
        return random.randint(0, len(ColorScheme.SHAPE_COLORS) - 1)

    def get_shape_color(self):
        """获取当前方块的颜色"""
        return ColorScheme.SHAPE_COLORS[self.shape_color]


class Game:
    def __init__(self):
        pygame.init()
        self.resolution = RESOLUTIONS[0]
        self.fullscreen = False
        self.ghost_shape_enabled = True
        self.screen_shake_enabled = True
        self.shake_intensity = 5  # 震动强度
        self.disable_sz_shapes = False  # 禁用S和Z型方块
        self.temp_settings = {
            "fullscreen": self.fullscreen,
            "resolution": self.resolution,
            "ghost_shape": self.ghost_shape_enabled,
            "screen_shake": self.screen_shake_enabled,
            "shake_intensity": self.shake_intensity,  # 震动强度
            "disable_sz_shapes": self.disable_sz_shapes  # 禁用S和Z型方块
        }
        self.screen_shake_enabled = self.temp_settings["screen_shake"]
        self.grid_size = GRID_SIZE
        self.scale_factor = 1.0  # 缩放比例
        self.init_display()
        self.state = GameState.MAIN_MENU
        self.prev_state = GameState.MAIN_MENU
        self.clock = pygame.time.Clock()
        self.paused_surface = None
        self.paused_selected = 0
        self.update_layout()
        self.title_letters = ['T', 'E', 'T', 'R', 'I', 'S']
        self.title_positions = [
            {
                'x': 0,
                'y': 0,
                'base_y': 0,
                'char': char
            } for i, char in enumerate(self.title_letters)
        ]
        self.title_center = (self.resolution[0] // 2, 150)
        self.title_speed = 0.02
        self.background_shapes = []
        self.last_background_update = pygame.time.get_ticks()
        self.background_update_interval = 500
        self.init_background_shapes()
        self.showing_dropdown = False
        self.dropdown_rect = None
        self.dropdown_options = []
        self.dropdown_selected = 0
        self.arrow_buttons = []
        self.update_layout()
        self.shake_offset = (0, 0)  # 震动偏移量
        self.shake_duration = 0  # 震动持续时间
        self.shake_intensity = 5  # 震动强度

    def init_display(self):
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.screen = pygame.display.set_mode(self.resolution, flags)
        pygame.display.set_caption("Tetris")

        # 计算缩放比例
        base_resolution = (800, 600)  # 将基础分辨率设置为800x600
        self.scale_factor = min(self.resolution[0] / base_resolution[0],
                                self.resolution[1] / base_resolution[1])

        # 根据缩放比例调整网格大小，缩小游戏区域和边框
        self.grid_size = int(GRID_SIZE * self.scale_factor * 0.9)  # 缩小10%

        self.update_layout()

    def init_background_shapes(self):
        """初始化背景形状"""
        self.background_shapes = []
        max_shapes = 20  # 最大背景方块数量
        shape_size = self.grid_size  # 使用当前网格大小

        # 计算每行可以容纳的方块数量
        columns = self.resolution[0] // (shape_size * 4)  # 每个方块占用4倍网格宽度
        rows = self.resolution[1] // (shape_size * 4)  # 每个方块占用4倍网格高度

        # 计算总方块数量，确保不超过最大数量且不重叠
        total_shapes = min(max_shapes, columns * rows)

        # 生成不重叠的初始位置
        occupied_positions = set()
        for _ in range(total_shapes):
            while True:
                x = random.randint(0, columns - 1) * shape_size * 4
                y = random.randint(-rows, 0) * shape_size * 4
                if (x, y) not in occupied_positions:
                    occupied_positions.add((x, y))
                    break

            shape = random.choice(SHAPES)
            color = random.choice(ColorScheme.SHAPE_COLORS)
            speed = 3.0  # 采用游戏3级速度（700ms/格）
            self.background_shapes.append({
                'shape': shape,
                'color': color,
                'x': x,
                'y': y,
                'speed': speed
            })

    def update_background_shapes(self):
        """更新背景方块的位置"""
        now = pygame.time.get_ticks()
        if now - self.last_background_update > 700:  # 3级速度，700ms/格
            for shape in self.background_shapes:
                shape['y'] += shape['speed'] * self.grid_size
                # 如果方块超出屏幕底部，则重置到顶部
                if shape['y'] > self.resolution[1]:
                    shape['y'] = -len(shape['shape']) * self.grid_size
                    # 重新随机x位置，确保不重叠
                    columns = self.resolution[0] // (self.grid_size * 4)
                    shape['x'] = random.randint(0, columns - 1) * self.grid_size * 4
            self.last_background_update = now

    def draw_background_shapes(self):
        """绘制背景形状"""
        for shape in self.background_shapes:
            for y, row in enumerate(shape['shape']):
                for x, cell in enumerate(row):
                    if cell:
                        # 绘制黑色描边
                        pygame.draw.rect(self.screen, pygame.Color("#000000"), (
                            shape['x'] + x * self.grid_size - 2,
                            shape['y'] + y * self.grid_size - 2,
                            self.grid_size + 3, self.grid_size + 3
                        ))
                        # 绘制实际颜色的方块
                        pygame.draw.rect(self.screen, shape['color'], (
                            shape['x'] + x * self.grid_size,
                            shape['y'] + y * self.grid_size,
                            self.grid_size - 1, self.grid_size - 1
                        ))

    def draw_current_shape(self):
        color = self.tetris.get_shape_color()

        # 使用self.grid_size代替GRID_SIZE
        if self.ghost_shape_enabled:
            ghost_y = self.tetris.shape_y
            while not self.tetris.check_collision(self.tetris.shape_x, ghost_y + 1, self.tetris.current_shape):
                ghost_y += 1

            # 正常绘制幽灵方块
            for y, row in enumerate(self.tetris.current_shape):
                for x, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(self.screen, pygame.Color("#FFFFFF"), (
                            self.game_area_x + (self.tetris.shape_x + x) * self.grid_size,
                            self.game_area_y + (ghost_y + y) * self.grid_size,
                            self.grid_size - 1, self.grid_size - 1
                        ), 2)

        # 绘制幽灵方块消散特效
        if self.tetris.ghost_effect_active and self.ghost_shape_enabled:  # 仅在 ghost_shape_enabled 为 True 时显示消散特效
            for y, row in enumerate(self.tetris.hard_drop_shape):  # 使用硬下落时的方块形状
                for x, cell in enumerate(row):
                    if cell:
                        alpha = 255 * (self.tetris.ghost_effect_frames / 30)
                        size = self.grid_size * (1 + (1 - self.tetris.ghost_effect_frames / 30))
                        ghost_surface = pygame.Surface((size, size), pygame.SRCALPHA)
                        pygame.draw.rect(ghost_surface, (255, 255, 255, alpha), (0, 0, size, size), 2)
                        self.screen.blit(ghost_surface, (
                            self.game_area_x + (self.tetris.ghost_effect_position[0] + x) * self.grid_size - (
                                    size - self.grid_size) / 2,
                            self.game_area_y + (self.tetris.ghost_effect_position[1] + y) * self.grid_size - (
                                    size - self.grid_size) / 2
                        ))

        # 使用self.grid_size代替GRID_SIZE
        for y, row in enumerate(self.tetris.current_shape):
            for x, cell in enumerate(row):
                if cell:
                    # 先绘制黑色轮廓，增强描边效果
                    pygame.draw.rect(self.screen, pygame.Color("#000000"), (
                        self.game_area_x + (self.tetris.shape_x + x) * self.grid_size - 2,
                        self.game_area_y + (self.tetris.shape_y + y) * self.grid_size - 2,
                        self.grid_size + 3, self.grid_size + 3
                    ))
                    # 再绘制实际颜色的方块
                    pygame.draw.rect(self.screen, color, (
                        self.game_area_x + (self.tetris.shape_x + x) * self.grid_size,
                        self.game_area_y + (self.tetris.shape_y + y) * self.grid_size,
                        self.grid_size - 1, self.grid_size - 1
                    ))

    def update_layout(self):
        screen_width, screen_height = self.resolution

        # 重新计算游戏区域位置
        self.game_area_x = (screen_width - GRID_WIDTH * self.grid_size) // 2
        self.game_area_y = (screen_height - GRID_HEIGHT * self.grid_size) // 2

        # 根据分辨率调整按钮大小和位置
        btn_width = int(200 * self.scale_factor)
        btn_height = int(50 * self.scale_factor)
        btn_spacing = int(100 * self.scale_factor)

        # 调整主菜单按钮位置
        self.main_menu_buttons = [
            Button("Start", (screen_width - btn_width) // 2, screen_height // 2 - btn_spacing, btn_width, btn_height,
                   self.show_levels),
            Button("Options", (screen_width - btn_width) // 2, screen_height // 2, btn_width, btn_height,
                   self.show_options),
            Button("Exit", (screen_width - btn_width) // 2, screen_height // 2 + btn_spacing, btn_width, btn_height,
                   sys.exit)
        ]

        # 根据分辨率调整关卡按钮大小和位置
        self.level_buttons = []
        for i in range(1, 11):
            x = (screen_width - int(500 * self.scale_factor)) // 2 + ((i - 1) % 5) * int(100 * self.scale_factor)
            y = screen_height // 2 - int(50 * self.scale_factor) + ((i - 1) // 5) * int(60 * self.scale_factor)
            self.level_buttons.append(Button(str(i), x, y, int(50 * self.scale_factor), int(30 * self.scale_factor),
                                             lambda l=i: self.start_game(l)))

        # 根据分辨率调整选项界面布局
        option_x = int(50 * self.scale_factor)
        option_y = int(150 * self.scale_factor)  # 将初始值从100调整为150，增加与标题的距离
        option_spacing = int(60 * self.scale_factor)

        # 根据分辨率调整箭头按钮大小和位置
        arrow_width = int(30 * self.scale_factor)
        self.arrow_buttons = [
            Button("<", screen_width - int(250 * self.scale_factor) - arrow_width - int(10 * self.scale_factor),
                   option_y, arrow_width, int(30 * self.scale_factor), lambda: self.cycle_setting(0, -1)),
            Button(">", screen_width - int(250 * self.scale_factor) + int(200 * self.scale_factor) + int(
                10 * self.scale_factor), option_y, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(0, 1)),
            Button("<", screen_width - int(250 * self.scale_factor) - arrow_width - int(10 * self.scale_factor),
                   option_y + option_spacing, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(1, -1)),
            Button(">", screen_width - int(250 * self.scale_factor) + int(200 * self.scale_factor) + int(
                10 * self.scale_factor), option_y + option_spacing, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(1, 1)),
            Button("<", screen_width - int(250 * self.scale_factor) - arrow_width - int(10 * self.scale_factor),
                   option_y + 2 * option_spacing, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(2, -1)),
            Button(">", screen_width - int(250 * self.scale_factor) + int(200 * self.scale_factor) + int(
                10 * self.scale_factor), option_y + 2 * option_spacing, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(2, 1)),
            Button("<", screen_width - int(250 * self.scale_factor) - arrow_width - int(10 * self.scale_factor),
                   option_y + 3 * option_spacing, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(3, -1)),
            Button(">", screen_width - int(250 * self.scale_factor) + int(200 * self.scale_factor) + int(
                10 * self.scale_factor), option_y + 3 * option_spacing, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(3, 1)),
            Button("<", screen_width - int(250 * self.scale_factor) - arrow_width - int(10 * self.scale_factor),
                   option_y + 4 * option_spacing, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(4, -1)),
            Button(">", screen_width - int(250 * self.scale_factor) + int(200 * self.scale_factor) + int(
                10 * self.scale_factor), option_y + 4 * option_spacing, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(4, 1)),
            Button("<", screen_width - int(250 * self.scale_factor) - arrow_width - int(10 * self.scale_factor),
                   option_y + 5 * option_spacing, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(5, -1)),
            Button(">", screen_width - int(250 * self.scale_factor) + int(200 * self.scale_factor) + int(
                10 * self.scale_factor), option_y + 5 * option_spacing, arrow_width, int(30 * self.scale_factor),
                   lambda: self.cycle_setting(5, 1)),
        ]

        # 更新选项标签和按钮
        self.option_labels = [
            ("Fullscreen", option_x, option_y),
            ("Resolution", option_x, option_y + option_spacing),
            ("Ghost Shape", option_x, option_y + 2 * option_spacing),
            ("Screen Shake", option_x, option_y + 3 * option_spacing),
            ("Shake Intensity", option_x, option_y + 4 * option_spacing),
            ("Disable S/Z Shapes", option_x, option_y + 5 * option_spacing)  # 禁用S/Z型方块选项
        ]

        self.options_buttons = [
            Button("On" if self.temp_settings["fullscreen"] else "Off",
                   screen_width - int(250 * self.scale_factor), option_y, int(200 * self.scale_factor),
                   int(30 * self.scale_factor), self.toggle_fullscreen),
            Button(f"{self.temp_settings['resolution'][0]}x{self.temp_settings['resolution'][1]}",
                   screen_width - int(250 * self.scale_factor), option_y + option_spacing, int(200 * self.scale_factor),
                   int(30 * self.scale_factor), self.cycle_resolution),
            Button("On" if self.temp_settings["ghost_shape"] else "Off",
                   screen_width - int(250 * self.scale_factor), option_y + 2 * option_spacing,
                   int(200 * self.scale_factor), int(30 * self.scale_factor), self.toggle_ghost_shape),
            Button("On" if self.temp_settings["screen_shake"] else "Off",
                   screen_width - int(250 * self.scale_factor), option_y + 3 * option_spacing,
                   int(200 * self.scale_factor), int(30 * self.scale_factor), self.toggle_screen_shake),
            Button(str(self.temp_settings["shake_intensity"]),
                   screen_width - int(250 * self.scale_factor), option_y + 4 * option_spacing,
                   int(200 * self.scale_factor), int(30 * self.scale_factor), self.adjust_shake_intensity),
            Button("On" if self.temp_settings["disable_sz_shapes"] else "Off",  # 新增：禁用S/Z型方块按钮
                   screen_width - int(250 * self.scale_factor), option_y + 5 * option_spacing,
                   int(200 * self.scale_factor), int(30 * self.scale_factor), self.toggle_disable_sz_shapes),
            Button("Apply", screen_width - int(250 * self.scale_factor), option_y + 6 * option_spacing,
                   int(200 * self.scale_factor), int(30 * self.scale_factor), self.apply_settings),
        ]

    def cycle_setting(self, index, direction):
        """循环设置选项"""
        if index == 0:  # 全屏模式
            self.temp_settings["fullscreen"] = not self.temp_settings["fullscreen"]
            self.options_buttons[0].text = "On" if self.temp_settings["fullscreen"] else "Off"
        elif index == 1:  # 分辨率
            current = RESOLUTIONS.index(self.temp_settings["resolution"])
            new_index = (current + direction) % len(RESOLUTIONS)
            self.temp_settings["resolution"] = RESOLUTIONS[new_index]
            self.options_buttons[
                1].text = f"{self.temp_settings['resolution'][0]}x{self.temp_settings['resolution'][1]}"
        elif index == 2:  # 幽灵方块
            self.temp_settings["ghost_shape"] = not self.temp_settings["ghost_shape"]
            self.options_buttons[2].text = "On" if self.temp_settings["ghost_shape"] else "Off"
        elif index == 3:  # 屏幕震动效果
            self.temp_settings["screen_shake"] = not self.temp_settings["screen_shake"]
            self.options_buttons[3].text = "On" if self.temp_settings["screen_shake"] else "Off"
        elif index == 4:  # 震动强度
            new_intensity = self.temp_settings["shake_intensity"] + direction
            if new_intensity < 1:
                new_intensity = 1
            elif new_intensity > 10:
                new_intensity = 10
            self.temp_settings["shake_intensity"] = new_intensity
            self.options_buttons[4].text = str(new_intensity)
        elif index == 5:  # 禁用S/Z型方块
            self.temp_settings["disable_sz_shapes"] = not self.temp_settings["disable_sz_shapes"]
            self.options_buttons[5].text = "On" if self.temp_settings["disable_sz_shapes"] else "Off"

    def toggle_screen_shake(self):
        """切换屏幕震动效果"""
        self.temp_settings["screen_shake"] = not self.temp_settings["screen_shake"]

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEMOTION:
                pos = pygame.mouse.get_pos()
                if hasattr(self, 'buttons'):
                    for btn in self.buttons:
                        btn.hovered = btn.rect.collidepoint(pos)
                # 处理箭头按钮的hover状态
                for btn in self.arrow_buttons:
                    btn.hovered = btn.rect.collidepoint(pos)

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                # 处理箭头按钮点击
                for btn in self.arrow_buttons:
                    if btn.rect.collidepoint(pos) and btn.action:
                        btn.action()
                # 处理普通按钮点击
                for btn in self.buttons:
                    if btn.rect.collidepoint(pos) and btn.action:
                        btn.action()

            # 统一处理所有按键事件
            if event.type == pygame.KEYDOWN:
                # 游戏进行中的按键处理
                if self.state == GameState.GAME and not self.tetris.game_over:
                    if event.key == pygame.K_LEFT:
                        self.tetris.move(-1)
                    elif event.key == pygame.K_RIGHT:
                        self.tetris.move(1)
                    elif event.key == pygame.K_UP:
                        self.tetris.rotate()
                    elif event.key == pygame.K_DOWN:
                        self.tetris.drop()
                    elif event.key == pygame.K_SPACE:
                        self.tetris.hard_drop()
                        self.shake_duration = 10 if self.screen_shake_enabled else 0
                    elif event.key == pygame.K_ESCAPE:  # 游戏内按下ESC暂停
                        self.state = GameState.PAUSED
                        self.paused_surface = apply_blur(self.screen.copy())

                # 暂停菜单的按键处理
                elif self.state == GameState.PAUSED:
                    if event.key == pygame.K_UP:
                        self.paused_selected = (self.paused_selected - 1) % 3
                    elif event.key == pygame.K_DOWN:
                        self.paused_selected = (self.paused_selected + 1) % 3
                    elif event.key == pygame.K_RETURN:
                        if self.paused_selected == 0:  # Continue
                            self.state = GameState.GAME
                        elif self.paused_selected == 1:  # Reset
                            self.start_game(self.tetris.level)
                            self.state = GameState.GAME
                        elif self.paused_selected == 2:  # Main Menu
                            self.state = GameState.MAIN_MENU
                    elif event.key == pygame.K_ESCAPE:  # 暂停时ESC恢复游戏
                        self.state = GameState.GAME

                # 非游戏状态的ESC返回逻辑
                elif self.state in [GameState.LEVEL_SELECT, GameState.OPTIONS]:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.MAIN_MENU

                # 游戏结束时的空格键返回逻辑
                elif self.state == GameState.GAME and self.tetris.game_over:
                    if event.key == pygame.K_SPACE:
                        self.state = GameState.LEVEL_SELECT

    def update_title_positions(self):
        """更新标题字母位置"""
        time = pygame.time.get_ticks() / 1000
        mouse_pos = pygame.mouse.get_pos()

        # 计算标题总宽度（6个字母，每个字母占60像素）
        total_width = 6 * 60

        # 计算标题起始位置，确保完全居中，并向右移动20像素
        title_start_x = (self.resolution[0] - total_width) // 2 + 20

        for i, pos in enumerate(self.title_positions):
            # 基础浮动
            y_offset = math.sin(time * 2 + i * 0.5) * 15

            # 鼠标斥力
            dx = title_start_x + i * 60 - mouse_pos[0]
            dy = self.title_center[1] + y_offset - mouse_pos[1]
            distance = math.hypot(dx, dy)

            if distance < 100:
                angle = math.atan2(dy, dx)
                push_force = (100 - distance) * 0.3
                x = title_start_x + i * 60 + math.cos(angle) * push_force
                y = self.title_center[1] + y_offset + math.sin(angle) * push_force
            else:
                x = title_start_x + i * 60
                y = self.title_center[1] + y_offset

            pos['x'] = x
            pos['y'] = y

    def draw_title(self):
        """绘制动态标题"""
        self.update_title_positions()
        font = pygame.font.Font(None, 120)

        # 定义标题字母颜色
        title_colors = [
            pygame.Color("#FF0000"),  # T - 红色
            pygame.Color("#00FF00"),  # E - 绿色
            pygame.Color("#0000FF"),  # T - 蓝色
            pygame.Color("#FF00FF"),  # R - 品红
            pygame.Color("#FFFF00"),  # I - 黄色
            pygame.Color("#00FFFF")  # S - 青色
        ]

        for i, pos in enumerate(self.title_positions):
            # 先绘制黑色轮廓
            text = font.render(pos['char'], True, pygame.Color("#000000"))
            # 绘制轮廓的四个偏移位置
            for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                text_rect = text.get_rect(center=(pos['x'] + dx, pos['y'] + dy))
                self.screen.blit(text, text_rect)

            # 再绘制实际颜色的字母
            text = font.render(pos['char'], True, title_colors[i])
            text_rect = text.get_rect(center=(pos['x'], pos['y']))
            self.screen.blit(text, text_rect)

    def draw_main_menu(self):
        self.screen.fill(ColorScheme.BACKGROUND)
        self.update_background_shapes()
        self.draw_background_shapes()
        self.draw_title()
        self.buttons = self.main_menu_buttons
        for btn in self.buttons:
            btn.draw(self.screen)  # 使用新的绘制按钮方法
        pygame.display.flip()

    def draw_paused_menu(self):
        # 绘制模糊背景
        self.screen.blit(self.paused_surface, (0, 0))

        # 绘制半透明遮罩
        overlay = pygame.Surface(self.resolution, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        # 绘制菜单选项
        font = pygame.font.Font(None, 72)
        text = font.render("PAUSED", True, ColorScheme.TEXT)
        text_rect = text.get_rect(center=(self.resolution[0] // 2, self.resolution[1] // 2 - 100))
        self.screen.blit(text, text_rect)

        options = ["Continue", "Restart", "Main Menu"]
        option_rects = []
        for i, option in enumerate(options):
            color = ColorScheme.TEXT if i == self.paused_selected else ColorScheme.BUTTON
            font = pygame.font.Font(None, 48)
            text = font.render(option, True, color)
            text_rect = text.get_rect(center=(self.resolution[0] // 2, self.resolution[1] // 2 + i * 50))
            self.screen.blit(text, text_rect)
            option_rects.append(text_rect)

        # 处理鼠标选择
        mouse_pos = pygame.mouse.get_pos()
        for i, rect in enumerate(option_rects):
            if rect.collidepoint(mouse_pos):
                self.paused_selected = i
                if pygame.mouse.get_pressed()[0]:  # 左键点击
                    if self.paused_selected == 0:  # Continue
                        self.state = GameState.GAME
                    elif self.paused_selected == 1:  # Reset
                        self.start_game(self.tetris.level)
                        self.state = GameState.GAME
                    elif self.paused_selected == 2:  # Main Menu
                        self.state = GameState.MAIN_MENU

        pygame.display.flip()

    def draw_levels(self):
        self.screen.fill(ColorScheme.BACKGROUND)
        self.update_background_shapes()
        self.draw_background_shapes()
        font = pygame.font.Font(None, 48)
        text = font.render("Select Level", True, ColorScheme.TEXT)
        # 计算标题居中位置
        text_rect = text.get_rect(center=(self.resolution[0] // 2, 100))
        self.screen.blit(text, text_rect)
        self.buttons = self.level_buttons
        for btn in self.buttons:
            btn.draw(self.screen)  # 使用新的绘制按钮方法
        pygame.display.flip()

    def prepare_dropdown_options(self, option_type):
        if option_type in ["On", "Off"]:
            self.dropdown_options = ["On", "Off"]
        elif "x" in option_type:
            self.dropdown_options = [f"{w}x{h}" for w, h in RESOLUTIONS]

    def update_selected_option(self):
        selected_option = self.dropdown_options[self.dropdown_selected]
        # 获取当前鼠标点击的按钮
        pos = pygame.mouse.get_pos()
        for btn in self.options_buttons:
            if btn.rect.collidepoint(pos):
                if btn.text in ["On", "Off"]:
                    # 根据按钮的位置判断是修改全屏还是幽灵方块
                    if btn == self.options_buttons[0]:  # 全屏模式
                        self.temp_settings["fullscreen"] = selected_option == "On"
                        self.options_buttons[0].text = selected_option
                    elif btn == self.options_buttons[2]:  # 幽灵方块
                        self.temp_settings["ghost_shape"] = selected_option == "On"
                        self.options_buttons[2].text = selected_option
                elif "x" in btn.text:  # 分辨率
                    # 仅在处理分辨率选项时执行字符串分割
                    if "x" in selected_option:
                        w, h = map(int, selected_option.split("x"))
                        self.temp_settings["resolution"] = (w, h)
                        self.options_buttons[1].text = selected_option
                break

    def draw_options(self):
        self.screen.fill(ColorScheme.BACKGROUND)
        self.update_background_shapes()
        self.draw_background_shapes()

        # 添加深色蒙版
        overlay = pygame.Surface(self.resolution, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # 半透明黑色（RGBA：0,0,0,128）
        self.screen.blit(overlay, (0, 0))

        # 绘制标题在左上角
        font = pygame.font.Font(None, 48)
        text = font.render("Options", True, ColorScheme.TEXT)
        self.screen.blit(text, (50, 50))

        # 绘制选项名
        font = pygame.font.Font(None, 36)
        for label, x, y in self.option_labels:
            text = font.render(label, True, ColorScheme.TEXT)
            self.screen.blit(text, (x, y))

        # 根据screen shake的状态设置震动强度选项的颜色
        if not self.temp_settings["screen_shake"]:
            color = pygame.Color("#808080")  # 灰色
        else:
            color = ColorScheme.BUTTON

        # 将Apply按钮固定在右下角
        apply_btn = self.options_buttons[-1]
        apply_btn.rect.x = self.resolution[0] - apply_btn.rect.width - 50
        apply_btn.rect.y = self.resolution[1] - apply_btn.rect.height - 50

        self.buttons = self.options_buttons
        self.buttons[4].color = color  # 设置震动强度按钮的颜色

        # 绘制选项值按钮
        for btn in self.buttons:
            btn.hovered = btn.rect.collidepoint(pygame.mouse.get_pos())
            btn.draw(self.screen)

        # 绘制箭头按钮
        for btn in self.arrow_buttons:
            btn.hovered = btn.rect.collidepoint(pygame.mouse.get_pos())
            btn.draw(self.screen)

        pygame.display.flip()

    def draw_next_shape(self):
        screen_width = self.resolution[0]
        # 调整信息栏位置，增加与游戏区域的间距
        info_panel_x = self.game_area_x + GRID_WIDTH * self.grid_size + int(100 * self.scale_factor)
        if info_panel_x + 200 > screen_width:
            info_panel_x = screen_width - 200

        # 根据缩放比例调整字体大小
        font = pygame.font.Font(None, int(36 * self.scale_factor))
        text = font.render("Next Shape:", True, ColorScheme.TEXT)
        self.screen.blit(text, (info_panel_x, int(100 * self.scale_factor)))

        start_x = info_panel_x
        start_y = int(150 * self.scale_factor)
        for y, row in enumerate(self.tetris.next_shape):
            for x, cell in enumerate(row):
                if cell:
                    pygame.draw.rect(self.screen, ColorScheme.SHAPE_COLORS[self.tetris.next_color], (
                        start_x + x * self.grid_size,
                        start_y + y * self.grid_size,
                        self.grid_size - 1, self.grid_size - 1
                    ))

    def draw_game_info(self):
        screen_width = self.resolution[0]
        # 调整信息栏位置，增加与游戏区域的间距
        info_panel_x = self.game_area_x + GRID_WIDTH * self.grid_size + int(100 * self.scale_factor)
        if info_panel_x + 200 > screen_width:
            info_panel_x = screen_width - 200

        # 根据缩放比例调整字体大小
        font = pygame.font.Font(None, int(36 * self.scale_factor))
        text = font.render(f"Score: {self.tetris.score}", True, ColorScheme.TEXT)
        self.screen.blit(text, (info_panel_x, int(300 * self.scale_factor)))

        # 绘制改进后的加分特效
        if self.tetris.score_effect_frames > 0:
            # 计算渐变色
            r = min(255, self.tetris.score_effect_color[0] + int(255 * (1 - self.tetris.score_effect_frames / 45)))
            g = max(0, self.tetris.score_effect_color[1] - int(255 * (1 - self.tetris.score_effect_frames / 45)))
            b = self.tetris.score_effect_color[2]
            color = (r, g, b)

            # 计算缩放比例
            self.tetris.score_effect_scale = 1.0 + (1 - self.tetris.score_effect_frames / 45) * 0.5

            # 创建渐变文本表面
            effect_font = pygame.font.Font(None, int(48 * self.scale_factor * self.tetris.score_effect_scale))
            effect_text = effect_font.render(self.tetris.score_effect, True, color)

            # 绘制主文本
            effect_rect = effect_text.get_rect(center=(info_panel_x + 100, int(280 * self.scale_factor)))
            self.screen.blit(effect_text, effect_rect)

            self.tetris.score_effect_frames -= 1

        text = font.render(f"Level: {self.tetris.level}", True, ColorScheme.TEXT)
        self.screen.blit(text, (info_panel_x, int(350 * self.scale_factor)))

    def toggle_fullscreen(self):
        self.temp_settings["fullscreen"] = not self.temp_settings["fullscreen"]

    def cycle_resolution(self):
        current = RESOLUTIONS.index(self.temp_settings["resolution"])
        self.temp_settings["resolution"] = RESOLUTIONS[(current + 1) % len(RESOLUTIONS)]

    def toggle_ghost_shape(self):
        self.temp_settings["ghost_shape"] = not self.temp_settings["ghost_shape"]

    def adjust_shake_intensity(self):
        """调整震动强度"""
        self.temp_settings["shake_intensity"] = (self.temp_settings["shake_intensity"] + 1) % 11

    def toggle_disable_sz_shapes(self):
        """切换禁用S和Z型方块状态"""
        self.temp_settings["disable_sz_shapes"] = not self.temp_settings["disable_sz_shapes"]

    def apply_settings(self):
        self.fullscreen = self.temp_settings["fullscreen"]
        self.resolution = self.temp_settings["resolution"]
        self.ghost_shape_enabled = self.temp_settings["ghost_shape"]
        self.screen_shake_enabled = self.temp_settings["screen_shake"]
        self.shake_intensity = self.temp_settings["shake_intensity"]
        self.disable_sz_shapes = self.temp_settings["disable_sz_shapes"]  # 应用禁用S/Z型方块设置
        self.init_display()
        # 清除背景方块并重新初始化
        self.background_shapes = []
        self.init_background_shapes()

    def start_game(self, level):
        self.tetris = Tetris(level)
        self.tetris.game = self  # 设置game属性
        # 重新生成下一个形状确保应用过滤条件
        self.tetris.next_shape = self.tetris.choose_shape()
        self.tetris.next_color = self.tetris.choose_next_color()
        self.state = GameState.GAME

    def show_main_menu(self):
        self.state = GameState.MAIN_MENU

    def show_options(self):
        self.state = GameState.OPTIONS

    def show_levels(self):
        self.state = GameState.LEVEL_SELECT

    def draw_grid(self):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.tetris.grid[y][x]:
                    color = ColorScheme.SHAPE_COLORS[self.tetris.grid[y][x] - 1]
                    # 仅在screen_shake_enabled为True时应用震动偏移量
                    shake_offset_x = int(self.shake_offset[0]) if self.screen_shake_enabled else 0
                    shake_offset_y = int(self.shake_offset[1]) if self.screen_shake_enabled else 0
                    pygame.draw.rect(self.screen, pygame.Color("#000000"), (
                        self.game_area_x + x * self.grid_size - 2 + shake_offset_x,
                        self.game_area_y + y * self.grid_size - 2 + shake_offset_y,
                        self.grid_size + 3, self.grid_size + 3
                    ))
                    pygame.draw.rect(self.screen, color, (
                        self.game_area_x + x * self.grid_size + shake_offset_x,
                        self.game_area_y + y * self.grid_size + shake_offset_y,
                        self.grid_size - 1, self.grid_size - 1
                    ))

    def draw_game(self):
        """绘制游戏画面，应用震动效果"""
        if self.screen_shake_enabled:
            self.apply_shake()
        self.screen.fill(ColorScheme.BACKGROUND)
        self.draw_grid()
        self.draw_current_shape()
        self.draw_next_shape()
        self.draw_game_info()

        # 绘制粒子效果
        for p in self.tetris.particles:
            alpha = int(255 * (p.life / 60))
            size = int(p.size * (p.life / 60))
            color = (*p.color[:3], alpha)  # 转换为RGBA格式
            # 添加随机偏移增强破碎感
            offset_x = random.randint(-2, 2)
            offset_y = random.randint(-2, 2)
            pygame.draw.circle(self.screen, color,
                               (int(p.x) + offset_x, int(p.y) + offset_y),
                               max(1, size))

        # 更新幽灵方块特效
        if self.tetris.ghost_effect_active:
            self.tetris.ghost_effect_frames -= 1
            if self.tetris.ghost_effect_frames <= 0:
                self.tetris.ghost_effect_active = False

        # 仅在screen_shake_enabled为True时应用震动偏移量
        shake_offset_x = int(self.shake_offset[0]) if self.screen_shake_enabled else 0
        shake_offset_y = int(self.shake_offset[1]) if self.screen_shake_enabled else 0
        border_rect = pygame.Rect(
            self.game_area_x - 2 + shake_offset_x,
            self.game_area_y - 2 + shake_offset_y,
            GRID_WIDTH * self.grid_size + 4,
            GRID_HEIGHT * self.grid_size + 4
        )
        pygame.draw.rect(self.screen, ColorScheme.GRID_LINE, border_rect, 2)

        if self.tetris.game_over:
            self.draw_game_over()

        pygame.display.flip()

    def draw_game_over(self):
        """绘制游戏结束界面"""
        # 绘制半透明遮罩
        overlay = pygame.Surface(self.resolution, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        # 绘制游戏结束文本
        font = pygame.font.Font(None, 72)
        text = font.render("Game Over", True, ColorScheme.TEXT)
        text_rect = text.get_rect(center=(self.resolution[0] // 2, self.resolution[1] // 2 - 50))
        self.screen.blit(text, text_rect)

        # 绘制得分信息
        font = pygame.font.Font(None, 48)
        text = font.render(f"Final Score: {self.tetris.score}", True, ColorScheme.TEXT)
        text_rect = text.get_rect(center=(self.resolution[0] // 2, self.resolution[1] // 2 + 50))
        self.screen.blit(text, text_rect)

        # 绘制返回主菜单的提示
        font = pygame.font.Font(None, 36)
        text = font.render("Press Space to return to Level Select", True, ColorScheme.TEXT)
        text_rect = text.get_rect(center=(self.resolution[0] // 2, self.resolution[1] // 2 + 150))
        self.screen.blit(text, text_rect)

    def apply_shake(self):
        """应用震动效果"""
        if self.shake_duration > 0 and self.screen_shake_enabled:
            # 随机生成震动偏移量
            self.shake_offset = (
                random.randint(-self.shake_intensity, self.shake_intensity),
                random.randint(-self.shake_intensity, self.shake_intensity)
            )
            self.shake_duration -= 1
        else:
            self.shake_offset = (0, 0)
            self.shake_duration = 0

    def run(self):
        while True:
            self.handle_events()
            self.clock.tick(FPS)

            if self.state == GameState.MAIN_MENU:
                self.draw_main_menu()
            elif self.state == GameState.LEVEL_SELECT:
                self.draw_levels()
            elif self.state == GameState.OPTIONS:
                self.draw_options()
            elif self.state == GameState.GAME:
                if not self.tetris.game_over:
                    self.tetris.update()
                    self.tetris.update_particles()  # 粒子更新
                self.draw_game()
            elif self.state == GameState.PAUSED:
                self.draw_paused_menu()


if __name__ == "__main__":
    game = Game()
    game.run()
