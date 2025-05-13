import pygame, sys
from settings import *
from level import Level
import os  # Import os để xử lý đường dẫn


class Game:
    def __init__(self):
        # General setup
        pygame.init()
        # Sử dụng HEIGHT từ settings.py nếu có, nếu bạn đã định nghĩa HEIGTH ở đó thì giữ nguyên
        # Giả sử settings.py có HEIGHT, nếu không thì HEIGTH bạn dùng vẫn được giữ
        try:
            display_height = HEIGHT
        except NameError:
            display_height = HEIGTH  # Giữ lại HEIGTH nếu HEIGHT không tồn tại trong settings

        self.screen = pygame.display.set_mode((WIDTH, display_height))
        pygame.display.set_caption('Game Đánh Quái')
        self.clock = pygame.time.Clock()

        # --- Trạng thái game ---
        self.game_state = 'menu'
        self.level = None

        # --- Tải tài nguyên cho Menu ---
        # === Đường dẫn đến các tài nguyên ===
        base_path = os.path.dirname(__file__)  # Lấy thư mục chứa file main.py
        # Đường dẫn này giả định thư mục 'graphics' và 'audio' nằm cùng cấp với thư mục chứa 'code'
        # Ví dụ: Game/graphics, Game/audio, Game/code/main.py
        # Nếu cấu trúc của bạn là Game/code/main.py và Game/graphics (tức là graphics ngang hàng với code)
        # thì graphics_path và audio_path cần là os.path.join(base_path, '..', 'graphics')
        # Giả sử cấu trúc là Game/graphics và Game/code

        # Điều chỉnh đường dẫn dựa trên vị trí tương đối của graphics và audio so với thư mục chứa main.py
        # Nếu 'graphics' và 'audio' nằm trong thư mục 'Game' và 'main.py' nằm trong 'Game/code',
        # thì bạn cần đi lên một cấp ('..') từ 'code' để đến 'Game', rồi vào 'graphics' hoặc 'audio'.
        graphics_folder_path = os.path.join(base_path, '..', 'graphics')
        audio_folder_path = os.path.join(base_path, '..', 'audio')

        menu_bg_path = os.path.join(graphics_folder_path, 'tilemap', 'menu.png')
        font_path = os.path.join(graphics_folder_path, 'font', 'joystix.ttf')
        sound_path = os.path.join(audio_folder_path, 'main.ogg')

        try:
            # Tải ảnh nền menu
            self.menu_bg = pygame.image.load(menu_bg_path).convert()
            # Scale ảnh nền cho vừa màn hình
            self.menu_bg = pygame.transform.scale(self.menu_bg, (WIDTH, display_height))
        except pygame.error as e:
            print(f"Lỗi tải ảnh nền menu '{menu_bg_path}': {e}")
            self.menu_bg = pygame.Surface((WIDTH, display_height))  # Tạo nền đen dự phòng
            self.menu_bg.fill('black')

        try:
            # Font cho nút
            self.menu_font_button = pygame.font.Font(font_path, 40)
        except pygame.error as e:
            print(f"Lỗi tải font '{font_path}': {e}. Sử dụng font mặc định.")
            self.menu_font_button = pygame.font.Font(None, 50)  # Font mặc định dự phòng

        # Tạo Text Surface và Rect cho nút "CHƠI NGAY"
        self.play_button_text = 'CHƠI NGAY'
        try:
            self.play_button_surf = self.menu_font_button.render(self.play_button_text, False, TEXT_COLOR)
        except pygame.error as e:
            print(f"Lỗi render text '{self.play_button_text}' với font đã chọn: {e}")
            fallback_font = pygame.font.Font(None, 50)
            self.play_button_surf = fallback_font.render("PLAY", False, TEXT_COLOR)

        # Kích thước và vị trí nút
        button_width = self.play_button_surf.get_width() + 80
        button_height = self.play_button_surf.get_height() + 15
        self.play_button_rect = pygame.Rect(
            (WIDTH - button_width) // 2,
            int(display_height * 0.7 - 15),
            button_width,
            button_height
        )
        # Vị trí text bên trong nút
        self.play_text_rect = self.play_button_surf.get_rect(center=self.play_button_rect.center)

        # Màu sắc nút
        self.button_bg_color = '#b8560e'
        self.button_border_color_outer = '#5c2505'
        self.button_border_color_inner = '#ffd700'

        # Âm thanh
        try:
            self.main_sound = pygame.mixer.Sound(sound_path)
            self.main_sound.set_volume(0.5)
        except pygame.error as e:
            print(f"Lỗi tải âm thanh '{sound_path}': {e}")
            self.main_sound = None
        # Không play nhạc ngay khi init

    def start_game(self):
        """Khởi tạo level và chuyển trạng thái sang playing"""
        self.level = Level()  # Tạo một đối tượng Level mới
        self.game_state = 'playing'
        if self.main_sound:
            self.main_sound.play(loops=-1)  # Bắt đầu nhạc game

    def draw_menu(self):
        """Vẽ các thành phần của menu"""
        self.screen.blit(self.menu_bg, (0, 0))

        border_outer_thickness = 4
        border_inner_thickness = 2

        outer_rect = self.play_button_rect.inflate(border_outer_thickness * 2, border_outer_thickness * 2)
        pygame.draw.rect(self.screen, self.button_border_color_outer, outer_rect, border_radius=8)

        pygame.draw.rect(self.screen, self.button_bg_color, self.play_button_rect, border_radius=8)

        pygame.draw.rect(self.screen, self.button_border_color_inner, self.play_button_rect, border_inner_thickness,
                         border_radius=8)

        self.screen.blit(self.play_button_surf, self.play_text_rect)

    def handle_menu_events(self):
        """Xử lý input khi đang ở menu"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Chuột trái
                    mouse_pos = pygame.mouse.get_pos()
                    if self.play_button_rect.collidepoint(mouse_pos):
                        self.start_game()

    def run(self):
        while True:
            if self.game_state == 'menu':
                self.handle_menu_events()
                self.draw_menu()
            elif self.game_state == 'playing':
                # --- ĐIỂM THAY ĐỔI CHÍNH ---
                # Xử lý tất cả sự kiện và chuyển tiếp cho Level xử lý
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

                    # Chuyển tiếp sự kiện cho self.level (nếu level đã được tạo)
                    if self.level:
                        self.level.handle_input(event)
                # --- KẾT THÚC THAY ĐỔI ---

                self.screen.fill(WATER_COLOR)
                if self.level:
                    self.level.run()  # Cập nhật và vẽ màn chơi
                else:
                    # Trường hợp này không nên xảy ra nếu start_game() hoạt động đúng
                    print("Lỗi: Trạng thái 'playing' nhưng self.level là None.")
                    self.game_state = 'menu'  # Quay lại menu để tránh crash
                    if self.main_sound:
                        self.main_sound.stop()

            pygame.display.update()
            self.clock.tick(FPS)


if __name__ == '__main__':
    game = Game()
    game.run()