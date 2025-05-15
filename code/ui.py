import pygame
from settings import *
from pathfinding_algorithms import ALGORITHM_NAMES, \
    PATHFINDING_ALGORITHMS
from npc import NPC  # Cần thiết nếu UI tương tác trực tiếp với kiểu NPC


class UI:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(UI_FONT, UI_FONT_SIZE)
        self.small_font = pygame.font.Font(UI_FONT, UI_FONT_SIZE - 4)
        # --- THÊM FONT CHO THÔNG BÁO CHIẾN THẮNG ---
        self.victory_font = pygame.font.Font(UI_FONT, 40)  # Font lớn hơn, bạn có thể điều chỉnh
        self.victory_message_color = TEXT_COLOR_SELECTED  # Hoặc một màu nổi bật khác
        self.pathfinding_alert_font = pygame.font.Font(UI_FONT, UI_FONT_SIZE)  # Hoặc kích thước khác
        self.show_algo_menu_due_to_error = False
        # --- KẾT THÚC THÊM FONT ---

        self.health_bar_rect = pygame.Rect(10, 10, HEALTH_BAR_WIDTH, BAR_HEIGHT)
        self.energy_bar_rect = pygame.Rect(10, 34, ENERGY_BAR_WIDTH, BAR_HEIGHT)

        self.weapon_graphics = []
        for weapon in weapon_data.values():
            path = weapon['graphic']
            weapon_img = pygame.image.load(path).convert_alpha()
            self.weapon_graphics.append(weapon_img)

        self.magic_graphics = []
        for magic in magic_data.values():
            magic_img = pygame.image.load(magic['graphic']).convert_alpha()
            self.magic_graphics.append(magic_img)

        self.show_algo_menu = False
        self.selected_algo_index = ALGORITHM_NAMES.index('A*') if 'A*' in ALGORITHM_NAMES else 0
        self.algo_button_rect = None
        self.algo_menu_rects = []
        self.algo_menu_visible_items = 5
        self.algo_menu_scroll_offset = 0

        self.po_toggle_button_rect = None
        self.aggro_mode_display_rect = None

        # --- CHO THÔNG BÁO CHIẾN THẮNG ---
        self._victory_message_surf = None  # Cache surface để không render mỗi frame
        self._victory_message_rect = None
        self._current_victory_text = ""  # Để biết khi nào cần render lại
        # --- KẾT THÚC ---

    def show_bar(self, current, max_amount, bg_rect, color):
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect)
        ratio = current / max_amount
        current_width = bg_rect.width * ratio
        current_rect = bg_rect.copy()
        current_rect.width = current_width
        pygame.draw.rect(self.display_surface, color, current_rect)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_rect, 3)

    def show_exp(self, exp):
        text_surf = self.font.render(str(int(exp)), False, TEXT_COLOR)
        x = self.display_surface.get_size()[0] - 20
        y = self.display_surface.get_size()[1] - 20
        text_rect = text_surf.get_rect(bottomright=(x, y))
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, text_rect.inflate(20, 20))
        self.display_surface.blit(text_surf, text_rect)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, text_rect.inflate(20, 20), 3)

    def selection_box(self, left, top, has_switched):
        bg_rect = pygame.Rect(left, top, ITEM_BOX_SIZE, ITEM_BOX_SIZE)
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect)
        border_color = UI_BORDER_COLOR_ACTIVE if has_switched else UI_BORDER_COLOR
        pygame.draw.rect(self.display_surface, border_color, bg_rect, 3)
        return bg_rect

    def weapon_overlay(self, weapon_index, has_switched):
        if 0 <= weapon_index < len(self.weapon_graphics):
            bg_rect = self.selection_box(10, self.display_surface.get_height() - ITEM_BOX_SIZE - 10, has_switched)
            weapon_surf = self.weapon_graphics[weapon_index]
            weapon_rect = weapon_surf.get_rect(center=bg_rect.center)
            self.display_surface.blit(weapon_surf, weapon_rect)

    def magic_overlay(self, magic_index, has_switched):
        if 0 <= magic_index < len(self.magic_graphics):
            bg_rect = self.selection_box(ITEM_BOX_SIZE + 20, self.display_surface.get_height() - ITEM_BOX_SIZE - 10,
                                         has_switched)
            magic_surf = self.magic_graphics[magic_index]
            magic_rect = magic_surf.get_rect(center=bg_rect.center)
            self.display_surface.blit(magic_surf, magic_rect)

    def display_algorithm_selection(self, current_algorithm_name):
        button_text = f"NPC Algo: {current_algorithm_name}"
        try:
            text_surf = self.font.render(button_text, False, TEXT_COLOR)
        except Exception:
            text_surf = self.font.render("Algo: Error", False, TEXT_COLOR)

        if self.algo_button_rect:
            pygame.draw.rect(self.display_surface, UI_BG_COLOR, self.algo_button_rect)
            border_color = UI_BORDER_COLOR_ACTIVE if self.show_algo_menu else UI_BORDER_COLOR
            pygame.draw.rect(self.display_surface, border_color, self.algo_button_rect, 3)
            text_rect = text_surf.get_rect(center=self.algo_button_rect.center)
            self.display_surface.blit(text_surf, text_rect)

        if self.show_algo_menu and self.algo_button_rect:
            self.algo_menu_rects = []
            menu_item_height = self.small_font.get_height() + 8
            menu_width = self.algo_button_rect.width
            num_displayable_items = min(len(ALGORITHM_NAMES) - self.algo_menu_scroll_offset,
                                        self.algo_menu_visible_items)
            num_displayable_items = max(0, num_displayable_items)
            menu_height = num_displayable_items * menu_item_height + 10
            if num_displayable_items == 0: menu_height = 0

            menu_x = self.algo_button_rect.left
            menu_y = self.algo_button_rect.bottom + 5

            if menu_height > 0:
                menu_bg_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
                pygame.draw.rect(self.display_surface, UI_BG_COLOR, menu_bg_rect)
                pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, menu_bg_rect, 3)

                start_index = self.algo_menu_scroll_offset
                end_index = start_index + num_displayable_items
                if not ALGORITHM_NAMES: return

                for i in range(start_index, end_index):
                    if 0 <= i < len(ALGORITHM_NAMES) and ALGORITHM_NAMES[i] != 'RTAA*':
                        algo_name = ALGORITHM_NAMES[i]
                        item_y_offset = (i - start_index) * menu_item_height
                        item_rect = pygame.Rect(menu_x + 5, menu_y + 5 + item_y_offset, menu_width - 10,
                                                menu_item_height)
                        self.algo_menu_rects.append({'rect': item_rect, 'index': i, 'name': algo_name})

                        is_selected = (i == self.selected_algo_index)
                        bg_color = UPGRADE_BG_COLOR_SELECTED if is_selected else UI_BG_COLOR
                        text_color = TEXT_COLOR_SELECTED if is_selected else TEXT_COLOR

                        pygame.draw.rect(self.display_surface, bg_color, item_rect)
                        if is_selected:
                            pygame.draw.rect(self.display_surface, UI_BORDER_COLOR_ACTIVE, item_rect, 2)
                        try:
                            item_text_surf = self.small_font.render(algo_name, False, text_color)
                        except Exception:
                            item_text_surf = self.small_font.render("Error", False, text_color)
                        item_text_rect = item_text_surf.get_rect(centery=item_rect.centery, left=item_rect.left + 10)
                        self.display_surface.blit(item_text_surf, item_text_rect)

                if len(ALGORITHM_NAMES) > self.algo_menu_visible_items and menu_height > 0:
                    if self.algo_menu_scroll_offset > 0:
                        pygame.draw.polygon(self.display_surface, TEXT_COLOR,
                                            [(menu_x + menu_width // 2, menu_y + 4),
                                             (menu_x + menu_width // 2 - 5, menu_y + 9),
                                             (menu_x + menu_width // 2 + 5, menu_y + 9)])
                    if end_index < len(ALGORITHM_NAMES):
                        down_arrow_y = menu_y + menu_height - 4
                        pygame.draw.polygon(self.display_surface, TEXT_COLOR,
                                            [(menu_x + menu_width // 2, down_arrow_y),
                                             (menu_x + menu_width // 2 - 5, down_arrow_y - 5),
                                             (menu_x + menu_width // 2 + 5, down_arrow_y - 5)])

    # Trong lớp UI
    def display_pathfinding_alert(self, npc_name, algo_name, time_taken):
        message1 = f"Loi: NPC '{npc_name}' voi '{algo_name}'"
        message2 = f"xu ly qua lau ({time_taken}ms) hoac khong tim duoc duong."
        message3 = "Vui long chon thuat toan khac (M)."

        text_surf1 = self.pathfinding_alert_font.render(message1, False, (255, 100, 100))  # Màu đỏ nhạt
        text_surf2 = self.pathfinding_alert_font.render(message2, False, (255, 100, 100))
        text_surf3 = self.pathfinding_alert_font.render(message3, False, TEXT_COLOR)

        screen_w = self.display_surface.get_width()
        screen_h = self.display_surface.get_height()

        padding = 10
        bg_rect_w = max(text_surf1.get_width(), text_surf2.get_width(), text_surf3.get_width()) + padding * 2
        line_h = text_surf1.get_height()
        bg_rect_h = (line_h * 3) + (padding * 4)

        bg_rect = pygame.Rect((screen_w - bg_rect_w) / 2, screen_h * 0.4, bg_rect_w, bg_rect_h)  # Vị trí giữa màn hình

        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR_ACTIVE, bg_rect, 3)

        self.display_surface.blit(text_surf1, (bg_rect.x + padding, bg_rect.y + padding))
        self.display_surface.blit(text_surf2, (bg_rect.x + padding, bg_rect.y + padding + line_h + padding // 2))
        self.display_surface.blit(text_surf3, (bg_rect.x + padding, bg_rect.y + padding + (line_h + padding // 2) * 2))

        # Tùy chọn: Tự động mở menu chọn thuật toán
        if self.show_algo_menu_due_to_error and not self.show_algo_menu:
            self.show_algo_menu = True
            self.show_algo_menu_due_to_error = False  # Reset cờ sau khi mở menu

    # --- THÊM PHƯƠNG THỨC HIỂN THỊ THÔNG BÁO CHIẾN THẮNG ---
    def display_victory_notification(self, message_text="Tất cả quái đã bị tiêu diệt!"):
        if self._current_victory_text != message_text or self._victory_message_surf is None:
            self._current_victory_text = message_text
            text_surf = self.victory_font.render(message_text, True, self.victory_message_color)

            padding = 20
            bg_width = text_surf.get_width() + padding * 2
            bg_height = text_surf.get_height() + padding * 2

            self._victory_message_surf = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)

            # --- THAY ĐỔI Ở ĐÂY ---
            # Dòng cũ gây lỗi:
            # self._victory_message_surf.fill(UI_BG_COLOR + (230,))

            # Giải pháp 1: Nếu UI_BG_COLOR là một tuple (R, G, B)
            if isinstance(UI_BG_COLOR, tuple) and len(UI_BG_COLOR) == 3:
                victory_bg_color_rgba = (UI_BG_COLOR[0], UI_BG_COLOR[1], UI_BG_COLOR[2], 230)
            # Giải pháp 2: Hoặc định nghĩa một màu nền riêng cho thông báo này
            else:  # Nếu UI_BG_COLOR là string hoặc không phải RGB tuple, dùng màu mặc định
                victory_bg_color_rgba = (50, 50, 50, 230)  # Ví dụ: màu xám đậm trong suốt

            self._victory_message_surf.fill(victory_bg_color_rgba)
            # --- KẾT THÚC THAY ĐỔI ---

            text_rect_on_surf = text_surf.get_rect(center=(bg_width // 2, bg_height // 2))
            self._victory_message_surf.blit(text_surf, text_rect_on_surf)

            pygame.draw.rect(self._victory_message_surf, UI_BORDER_COLOR_ACTIVE, (0, 0, bg_width, bg_height), 5,
                             border_radius=5)

            screen_center_x = self.display_surface.get_width() // 2
            screen_center_y = self.display_surface.get_height() // 2
            self._victory_message_rect = self._victory_message_surf.get_rect(center=(screen_center_x, screen_center_y))

        if self._victory_message_surf and self._victory_message_rect:
            self.display_surface.blit(self._victory_message_surf, self._victory_message_rect)

    # --- KẾT THÚC PHƯƠNG THỨC ---

    # --- CẬP NHẬT CHỮ KÝ display() ĐỂ NHẬN CỜ THÔNG BÁO ---
    def display(self, player, current_algorithm_name, po_is_enabled, enemy_aggression_enabled,
                show_victory_message_flag=False,pathfinding_alert_data=None):
        self.show_bar(player.health, player.stats['health'], self.health_bar_rect, HEALTH_COLOR)
        self.show_bar(player.energy, player.stats['energy'], self.energy_bar_rect, ENERGY_COLOR)
        self.show_exp(player.exp)
        self.weapon_overlay(player.weapon_index, not player.can_switch_weapon)
        self.magic_overlay(player.magic_index, not player.can_switch_magic)

        next_button_y_offset = 10

        try:
            algo_button_text_surf = self.font.render(f"NPC Algo: {current_algorithm_name}", False, TEXT_COLOR)
        except Exception:
            algo_button_text_surf = self.font.render(f"NPC Algo: Error", False, TEXT_COLOR)

        algo_button_width = algo_button_text_surf.get_width() + 20
        algo_button_height = algo_button_text_surf.get_height() + 10
        algo_button_x = self.display_surface.get_width() - algo_button_width - 10
        algo_button_y = next_button_y_offset
        self.algo_button_rect = pygame.Rect(algo_button_x, algo_button_y, algo_button_width, algo_button_height)

        self.display_algorithm_selection(current_algorithm_name)

        po_text = f"PO: {'On' if po_is_enabled else 'Off'}"
        po_surf = self.font.render(po_text, False, TEXT_COLOR)
        algo_btn_bottom = self.algo_button_rect.bottom if self.algo_button_rect else (10 + algo_button_height)
        po_button_x = self.display_surface.get_width() - (po_surf.get_width() + 20) - 10
        po_button_y = algo_btn_bottom + 5
        self.po_toggle_button_rect = pygame.Rect(po_button_x, po_button_y, po_surf.get_width() + 20,
                                                 po_surf.get_height() + 10)
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, self.po_toggle_button_rect)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, self.po_toggle_button_rect, 3)
        self.display_surface.blit(po_surf, po_surf.get_rect(center=self.po_toggle_button_rect.center))

        aggro_text = f"Aggro: {'ON' if enemy_aggression_enabled else 'Off'}"
        aggro_surf = self.font.render(aggro_text, False,
                                      TEXT_COLOR_SELECTED if enemy_aggression_enabled else TEXT_COLOR)
        po_btn_bottom = self.po_toggle_button_rect.bottom if self.po_toggle_button_rect else (
                algo_btn_bottom + 5 + po_surf.get_height() + 10)
        aggro_display_x = self.display_surface.get_width() - (aggro_surf.get_width() + 20) - 10
        aggro_display_y = po_btn_bottom + 5
        self.aggro_mode_display_rect = pygame.Rect(aggro_display_x, aggro_display_y, aggro_surf.get_width() + 20,
                                                   aggro_surf.get_height() + 10)
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, self.aggro_mode_display_rect)
        border_color_aggro = UI_BORDER_COLOR_ACTIVE if enemy_aggression_enabled else UI_BORDER_COLOR
        pygame.draw.rect(self.display_surface, border_color_aggro, self.aggro_mode_display_rect, 3)
        self.display_surface.blit(aggro_surf, aggro_surf.get_rect(center=self.aggro_mode_display_rect.center))
        if pathfinding_alert_data:
            self.display_pathfinding_alert(  # Phương thức này bạn đã định nghĩa ở bước trước
                pathfinding_alert_data['npc_name'],
                pathfinding_alert_data['algo_name'],
                pathfinding_alert_data['time']
            )
            if self.show_algo_menu_due_to_error and not self.show_algo_menu:
                self.show_algo_menu = True
        if show_victory_message_flag:
            self.display_victory_notification()

    def handle_click(self, click_pos, level_instance_ref):
        if hasattr(self,
                   'po_toggle_button_rect') and self.po_toggle_button_rect and self.po_toggle_button_rect.collidepoint(
            click_pos):
            level_instance_ref.toggle_partial_observability()
            return True

        if self.algo_button_rect and self.algo_button_rect.collidepoint(click_pos):
            self.show_algo_menu = not self.show_algo_menu
            if self.show_algo_menu:
                self.algo_menu_scroll_offset = 0
            return True

        if self.show_algo_menu:
            clicked_on_menu_item = False
            for item_data in self.algo_menu_rects:
                item_rect = item_data['rect']
                if item_rect.collidepoint(click_pos):
                    selected_index = item_data['index']
                    if 0 <= selected_index < len(ALGORITHM_NAMES):
                        if selected_index != self.selected_algo_index:
                            level_instance_ref.selected_npc_algorithm_name = ALGORITHM_NAMES[selected_index]
                            level_instance_ref.selected_npc_algorithm_func = PATHFINDING_ALGORITHMS[
                                ALGORITHM_NAMES[selected_index]]
                            self.selected_algo_index = selected_index
                            for sprite in level_instance_ref.visible_sprites:
                                if isinstance(sprite, NPC):
                                    sprite.pathfinding_func = level_instance_ref.selected_npc_algorithm_func
                                    sprite.recalculation_needed = True
                                    sprite.path.clear()
                                    sprite.next_step = None
                        self.show_algo_menu = False  # Đóng menu sau khi chọn
                        self.show_algo_menu_due_to_error = False
                        if level_instance_ref.active_pathfinding_alert_npc_id is not None:
                            npc_id_had_alert = level_instance_ref.active_pathfinding_alert_npc_id
                            if npc_id_had_alert in level_instance_ref.pathfinding_issues:
                                del level_instance_ref.pathfinding_issues[npc_id_had_alert]
                            level_instance_ref.active_pathfinding_alert_npc_id = None
                        clicked_on_menu_item = True
                        return True

            if not clicked_on_menu_item and self.algo_button_rect and not self.algo_button_rect.collidepoint(click_pos):
                is_click_on_menu_area = False
                if self.algo_menu_rects and self.show_algo_menu:
                    if self.algo_button_rect:
                        menu_y_start = self.algo_button_rect.bottom + 5
                        menu_bg_height = (min(len(ALGORITHM_NAMES) - self.algo_menu_scroll_offset,
                                              self.algo_menu_visible_items) *
                                          (self.small_font.get_height() + 8)) + 10
                        if menu_bg_height > 0:
                            actual_menu_rect = pygame.Rect(self.algo_button_rect.left, menu_y_start,
                                                           self.algo_button_rect.width, menu_bg_height)
                            if actual_menu_rect.collidepoint(click_pos):
                                is_click_on_menu_area = True
                if not is_click_on_menu_area:
                    self.show_algo_menu = False
        return False

    def scroll_algo_menu(self, direction):
        if not self.show_algo_menu: return
        if direction > 0:
            if (self.algo_menu_scroll_offset + self.algo_menu_visible_items) < len(ALGORITHM_NAMES):
                self.algo_menu_scroll_offset += 1
        elif direction < 0:
            if self.algo_menu_scroll_offset > 0:
                self.algo_menu_scroll_offset -= 1