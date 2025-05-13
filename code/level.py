import pygame
from settings import *
from tile import Tile
from player import Player
# from debug import debug
from support import import_csv_layout, import_folder
from random import choice, randint
from weapon import Weapon
from ui import UI
from enemy import Enemy
from npc import NPC
from particles import AnimationPlayer
from magic import MagicPlayer
from upgrade import Upgrade
from pathfinding_algorithms import PATHFINDING_ALGORITHMS, ALGORITHM_NAMES


class Level:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.game_paused = False

        self.visible_sprites = YSortCameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()

        self.current_attack = None
        self.attack_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()  # Enemies and NPCs that can be attacked

        self.player = None
        self.camera_target_npc = None

        self.selected_npc_algorithm_name = 'Forward Checking BS'
        self.selected_npc_algorithm_func = PATHFINDING_ALGORITHMS[self.selected_npc_algorithm_name]

        self.partial_observability_enabled = DEFAULT_PARTIAL_OBSERVABILITY_ENABLED
        self.enemy_aggression_mode_enabled = ENEMY_AGGRESSION_MODE_ENABLED

        self.ui = None
        self.upgrade = None

        # --- THÊM CHO THÔNG BÁO DIỆT QUÁI ---
        self.initial_enemy_count = 0
        self.all_enemies_defeated_this_level = False
        self.victory_message_shown_this_level = False  # Để đảm bảo chỉ hiển thị một lần mỗi khi đạt được
        # --- KẾT THÚC THÊM ---

        self.create_map()

        if self.player is None:
            raise ValueError("Lỗi nghiêm trọng: Player không được tạo từ map_Entities.csv!")

        self.ui = UI()
        self.upgrade = Upgrade(self.player)

        self.animation_player = AnimationPlayer()
        self.magic_player = MagicPlayer(self.animation_player)

        self.enemy_pathfinding_counter = 0
        self.max_enemies_per_frame = 5
        self.npc_pathfinding_counter = 0
        self.max_npcs_per_frame = 2

    def create_map(self):
        layouts = {
            'boundary': import_csv_layout('../map/map_FloorBlocks.csv'),
            'grass': import_csv_layout('../map/map_Grass.csv'),
            'object': import_csv_layout('../map/map_Objects.csv'),
            'entities': import_csv_layout('../map/map_Entities.csv')
        }
        graphics = {
            'grass': import_folder('../graphics/Grass'),
            'objects': import_folder('../graphics/objects')
        }

        npc_creation_data = []
        self.initial_enemy_count = 0  # Reset khi tạo map mới (nếu có thể load nhiều map)

        for style, layout in layouts.items():
            for row_index, row in enumerate(layout):
                for col_index, col in enumerate(row):
                    if col != '-1':
                        x = col_index * TILESIZE
                        y = row_index * TILESIZE
                        if style == 'boundary':
                            Tile((x, y), [self.obstacle_sprites], 'invisible', hitbox_inflation=(-10, None))
                        elif style == 'grass':
                            random_grass_image = choice(graphics['grass'])
                            Tile(
                                (x, y),
                                [self.visible_sprites, self.obstacle_sprites, self.attackable_sprites],
                                'grass',
                                random_grass_image)
                        elif style == 'object':
                            surf = graphics['objects'][int(col)]
                            Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'object',
                                 surf)
                        elif style == 'entities':
                            if col == '394':
                                if self.player is None:
                                    self.player = Player(
                                        (x, y),
                                        [self.visible_sprites],
                                        self.obstacle_sprites,
                                        self.create_attack,
                                        self.destroy_attack,
                                        self.create_magic)
                            elif col == '395':
                                npc_creation_data.append({'name': '2BlueWizard', 'pos': (x, y)})
                            else:
                                monster_name_map = {
                                    '390': 'bamboo', '391': 'spirit', '0': 'Fire vizard',
                                    '392': 'raccoon', '1': 'Lightning Mage', '2': 'Minotaur_1',
                                    '3': 'Minotaur_2', '4': 'Minotaur_3', '5': 'Samurai',
                                    '6': 'Samurai_Archer', '7': 'Samurai_Commander', '8': 'Wanderer Magican'
                                }
                                monster_name = monster_name_map.get(col, 'squid')
                                Enemy(
                                    monster_name, (x, y),
                                    [self.visible_sprites, self.attackable_sprites],
                                    # Enemy cũng thuộc attackable_sprites
                                    self.obstacle_sprites,
                                    self.damage_player,
                                    self.trigger_death_particles,
                                    self.add_exp,
                                    level_instance_ref=self)
                                self.initial_enemy_count += 1  # Đếm số lượng quái ban đầu

        if self.player:
            for npc_data_item in npc_creation_data:
                npc = NPC(
                    npc_data_item['name'],
                    npc_data_item['pos'],
                    [self.visible_sprites, self.attackable_sprites],  # NPC cũng thuộc attackable_sprites
                    self.obstacle_sprites,
                    self.player,
                    self.damage_enemy_by_npc,
                    self.selected_npc_algorithm_func,
                    level_instance_ref=self
                )
                if self.camera_target_npc is None:
                    self.camera_target_npc = npc

    # ... (create_attack, create_magic, destroy_attack giữ nguyên) ...
    def create_attack(self):
        if self.player:
            self.current_attack = Weapon(self.player, [self.visible_sprites, self.attack_sprites])

    def create_magic(self, style, strength, cost):
        if self.player:
            if style == 'heal':
                self.magic_player.heal(self.player, strength, cost, [self.visible_sprites])
            if style == 'flame':
                self.magic_player.flame(self.player, cost, [self.visible_sprites, self.attack_sprites])

    def destroy_attack(self):
        if self.current_attack:
            self.current_attack.kill()
        self.current_attack = None

    def player_attack_logic(self):
        if self.attack_sprites:
            for attack_sprite in self.attack_sprites:
                # Chỉ va chạm với attackable_sprites (bao gồm Enemy và NPC)
                collision_sprites = pygame.sprite.spritecollide(attack_sprite, self.attackable_sprites, False)
                if collision_sprites:
                    for target_sprite in collision_sprites:
                        if target_sprite.sprite_type == 'grass':  # Cỏ vẫn có thể bị phá hủy
                            pos = target_sprite.rect.center
                            offset = pygame.math.Vector2(0, 75)
                            for _ in range(randint(3, 6)):
                                self.animation_player.create_grass_particles(pos - offset, [self.visible_sprites])
                            target_sprite.kill()
                        elif target_sprite.sprite_type == 'enemy':
                            if self.player and hasattr(target_sprite, 'get_damage'):
                                target_sprite.get_damage(self.player, attack_sprite.sprite_type)
                        elif target_sprite.sprite_type == 'npc':  # Player có thể tấn công NPC
                            if self.player and hasattr(target_sprite, 'get_damage'):
                                target_sprite.get_damage(self.player, attack_sprite.sprite_type)

    # ... (damage_player, damage_enemy_by_npc, trigger_death_particles, add_exp, game_menu_toggle, toggle_partial_observability, toggle_enemy_aggression_mode, handle_input giữ nguyên) ...

    def damage_player(self, amount, attack_type):
        if self.player and self.player.vulnerable:
            self.player.health -= amount
            self.player.vulnerable = False
            self.player.hurt_time = pygame.time.get_ticks()
            self.animation_player.create_particles(attack_type, self.player.rect.center, [self.visible_sprites])

    def damage_enemy_by_npc(self, amount, attack_type, enemy_sprite):
        if enemy_sprite and enemy_sprite.groups() and hasattr(enemy_sprite, 'vulnerable') and hasattr(enemy_sprite,
                                                                                                      'health'):
            if enemy_sprite.vulnerable and enemy_sprite.sprite_type == 'enemy':  # Đảm bảo chỉ tấn công enemy
                enemy_sprite.health -= amount
                enemy_sprite.vulnerable = False
                enemy_sprite.hit_time = pygame.time.get_ticks()
                self.animation_player.create_particles(attack_type, enemy_sprite.rect.center, [self.visible_sprites])

    def trigger_death_particles(self, pos, particle_type):
        self.animation_player.create_particles(particle_type, pos, self.visible_sprites)

    def add_exp(self, amount):
        if self.player:
            self.player.exp += amount

    def game_menu_toggle(self):
        if self.ui and self.ui.show_algo_menu:
            self.ui.show_algo_menu = False
        else:
            self.game_paused = not self.game_paused

    def toggle_partial_observability(self):
        self.partial_observability_enabled = not self.partial_observability_enabled
        mode = "Enabled" if self.partial_observability_enabled else "Disabled"
        print(f"Partial Observability mode: {mode}")

        for sprite in self.visible_sprites:
            if isinstance(sprite, NPC):
                if hasattr(sprite, 'on_po_mode_changed'):
                    sprite.on_po_mode_changed(self.partial_observability_enabled)

    def toggle_enemy_aggression_mode(self):
        self.enemy_aggression_mode_enabled = not self.enemy_aggression_mode_enabled
        mode_text = "Aggressive" if self.enemy_aggression_mode_enabled else "Normal"
        print(f"Enemy Aggression Mode: {mode_text}")

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                self.game_menu_toggle()
            elif event.key == pygame.K_p:
                self.toggle_partial_observability()
            elif event.key == pygame.K_g:
                self.toggle_enemy_aggression_mode()
            elif event.key == pygame.K_c:
                if self.camera_target_npc and hasattr(self,
                                                      '_original_camera_target') and self._original_camera_target == self.camera_target_npc:
                    self.camera_target_npc = self.player
                    print("Camera theo dõi Player")
                elif self.player:
                    first_npc = None
                    for sprite in self.visible_sprites:
                        if isinstance(sprite, NPC):
                            first_npc = sprite
                            break
                    if first_npc:
                        self.camera_target_npc = first_npc
                        self._original_camera_target = first_npc
                        print(f"Camera theo dõi NPC: {getattr(first_npc, 'npc_name', 'NPC')}")
                    else:
                        self.camera_target_npc = self.player
                        print("Không tìm thấy NPC, camera theo dõi Player")

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.ui and self.ui.handle_click(event.pos, self):
                    pass
            elif event.button == 4:
                if self.ui and self.ui.show_algo_menu:
                    self.ui.scroll_algo_menu(-1)
            elif event.button == 5:
                if self.ui and self.ui.show_algo_menu:
                    self.ui.scroll_algo_menu(1)

    # --- THÊM PHƯƠNG THỨC KIỂM TRA DIỆT QUÁI ---
    def check_all_enemies_defeated(self):
        if self.initial_enemy_count > 0 and not self.all_enemies_defeated_this_level:
            # Đếm số enemy còn sống trong attackable_sprites
            # Quan trọng: Đảm bảo rằng khi enemy chết, chúng được remove khỏi group này
            # hoặc ít nhất là không còn được coi là "còn sống" (ví dụ, health <= 0)
            current_living_enemies = [sprite for sprite in self.attackable_sprites
                                      if isinstance(sprite, Enemy) and sprite.health > 0]
            if not current_living_enemies:
                self.all_enemies_defeated_this_level = True
                self.victory_message_shown_this_level = False  # Reset để thông báo có thể hiển thị
                print("Thông báo: Tất cả quái đã bị tiêu diệt!")  # Dùng để debug

    # --- KẾT THÚC PHƯƠNG THỨC KIỂM TRA ---

    def run(self):
        if not self.player or not self.ui:
            pygame.quit()
            import sys
            sys.exit()

        entity_to_draw_around = self.player
        if self.camera_target_npc and self.camera_target_npc.groups():
            entity_to_draw_around = self.camera_target_npc
        elif self.camera_target_npc and not self.camera_target_npc.groups():
            self.camera_target_npc = self.player
            entity_to_draw_around = self.player
            if hasattr(self, '_original_camera_target'): delattr(self, '_original_camera_target')

        self.visible_sprites.custom_draw(entity_to_draw_around)

        # --- CẬP NHẬT CHO THÔNG BÁO DIỆT QUÁI ---
        # Truyền cờ all_enemies_defeated_this_level và victory_message_shown_this_level cho UI
        # UI sẽ quyết định có hiển thị thông báo không
        should_show_victory = self.all_enemies_defeated_this_level and not self.victory_message_shown_this_level
        self.ui.display(self.player, self.selected_npc_algorithm_name, self.partial_observability_enabled,
                        self.enemy_aggression_mode_enabled,
                        show_victory_message_flag=should_show_victory)  # Truyền cờ mới

        if should_show_victory:
            # Sau khi UI đã có cơ hội hiển thị nó dựa trên cờ,
            # chúng ta có thể đánh dấu là đã hiển thị (nếu UI không tự quản lý việc này)
            # Hoặc, nếu UI tự quản lý (ví dụ: hiển thị trong X giây rồi tự ẩn),
            # thì Level không cần làm gì thêm ở đây.
            # Để đơn giản, giả sử UI sẽ hiển thị nó một lần khi cờ là True.
            # Nếu muốn thông báo biến mất, logic đó nên ở trong UI.
            # Nếu muốn nó chỉ hiển thị MỘT LẦN cho đến khi level reset, cờ victory_message_shown_this_level là cần thiết.
            # self.victory_message_shown_this_level = True # Cờ này sẽ được UI quản lý hoặc set sau khi hiển thị
            pass
        # --- KẾT THÚC CẬP NHẬT ---

        if self.game_paused:
            if self.upgrade:
                self.upgrade.display()
        else:
            if not self.ui.show_algo_menu:
                self.visible_sprites.update()

                all_sprites_list = self.visible_sprites.sprites()
                enemy_sprites_list = [sprite for sprite in all_sprites_list if isinstance(sprite, Enemy)]
                npc_sprites_list = [sprite for sprite in all_sprites_list if isinstance(sprite, NPC)]

                self.visible_sprites.enemy_update(
                    self.player,
                    npc_sprites_list,
                    enemy_sprites_list,
                    self.enemy_pathfinding_counter,
                    self.max_enemies_per_frame
                )

                self.visible_sprites.npc_update(
                    self.player,
                    enemy_sprites_list,  # Truyền danh sách enemy cho NPC update
                    npc_sprites_list,  # Truyền danh sách NPC cho NPC update (để tách bầy)
                    self.npc_pathfinding_counter,
                    self.max_npcs_per_frame
                )

                self.player_attack_logic()
                self.check_all_enemies_defeated()  # Gọi kiểm tra sau khi các hành động có thể tiêu diệt quái

                self.enemy_pathfinding_counter = (self.enemy_pathfinding_counter + 1) % max(1,
                                                                                            self.max_enemies_per_frame)
                self.npc_pathfinding_counter = (self.npc_pathfinding_counter + 1) % max(1, self.max_npcs_per_frame)


class YSortCameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2
        self.offset = pygame.math.Vector2()

        try:
            self.floor_surf = pygame.image.load('../graphics/tilemap/ground.png').convert()
        except pygame.error:
            self.floor_surf = pygame.Surface((WIDTH * 2, HEIGTH * 2))  # HEIGTH -> HEIGHT
            self.floor_surf.fill(WATER_COLOR)
        self.floor_rect = self.floor_surf.get_rect(topleft=(0, 0))

    def custom_draw(self, target_entity):
        if target_entity and hasattr(target_entity, 'rect'):
            self.offset.x = target_entity.rect.centerx - self.half_width
            self.offset.y = target_entity.rect.centery - self.half_height
        else:
            pass

        floor_offset_pos = self.floor_rect.topleft - self.offset
        self.display_surface.blit(self.floor_surf, floor_offset_pos)

        try:
            sorted_sprites = sorted(self.sprites(), key=lambda sprite: sprite.hitbox.centery if hasattr(sprite,
                                                                                                        'hitbox') else sprite.rect.centery)
        except AttributeError:
            sorted_sprites = sorted(self.sprites(),
                                    key=lambda sprite: sprite.rect.centery if hasattr(sprite, 'rect') else 0)

        for sprite in sorted_sprites:
            if hasattr(sprite, 'rect') and hasattr(sprite, 'image'):
                offset_pos = sprite.rect.topleft - self.offset
                self.display_surface.blit(sprite.image, offset_pos)

            if hasattr(sprite, 'path_history') and sprite.path_history:
                # ----- THÊM DÒNG PRINT Ở ĐÂY -----
                # if isinstance(sprite, NPC): # Kiểm tra thêm nếu cần, nhưng hasattr là đủ nếu chỉ NPC có path_history
                #    print(f"Đang vẽ đường đi cho {getattr(sprite, 'npc_name', 'NPC không tên')}, số điểm: {len(sprite.path_history)}, điểm đầu: {sprite.path_history[0]}, offset camera: {self.offset}")
                # ----- KẾT THÚC DÒNG PRINT -----

                path_color_from_npc = sprite.path_color if hasattr(sprite, 'path_color') else (0, 0, 255, 100)
                path_radius_from_npc = sprite.path_point_radius if hasattr(sprite, 'path_point_radius') else 3

                num_points = len(sprite.path_history)
                for i, point_world_coords in enumerate(sprite.path_history):
                    point_screen_coords = (point_world_coords[0] - self.offset.x,
                                           point_world_coords[1] - self.offset.y)

                    alpha = path_color_from_npc[3] * ((i + 1) / num_points)
                    dynamic_color = (path_color_from_npc[0], path_color_from_npc[1], path_color_from_npc[2], int(alpha))

                    # ----- CÓ THỂ THÊM PRINT Ở ĐÂY ĐỂ DEBUG TỪNG ĐIỂM -----
                    # print(f"  Vẽ điểm {i}: World={point_world_coords}, Screen={point_screen_coords}, Màu={dynamic_color}, Bán kính={path_radius_from_npc}")
                    # ----- KẾT THÚC PRINT ĐIỂM -----

                    point_draw_surface = pygame.Surface((path_radius_from_npc * 2, path_radius_from_npc * 2),
                                                        pygame.SRCALPHA)
                    pygame.draw.circle(point_draw_surface, dynamic_color,
                                       (path_radius_from_npc, path_radius_from_npc),
                                       path_radius_from_npc)
                    self.display_surface.blit(point_draw_surface,
                                              (point_screen_coords[0] - path_radius_from_npc,
                                               point_screen_coords[1] - path_radius_from_npc))

    def enemy_update(self, player_watcher, npc_list, all_enemies_for_separation, pathfinding_counter,
                     max_enemies_per_frame):
        current_enemy_sprites = [sprite for sprite in self.sprites() if
                                 hasattr(sprite, 'sprite_type') and sprite.sprite_type == 'enemy' and hasattr(sprite,
                                                                                                              'enemy_update')]
        effective_max = max(1, max_enemies_per_frame)
        for index, enemy in enumerate(current_enemy_sprites):
            try:
                can_calculate_path = (index % effective_max) == (pathfinding_counter % effective_max)
                enemy.enemy_update(player_watcher, npc_list, all_enemies_for_separation, can_calculate_path)
            except Exception as e:
                pass

    def npc_update(self, player, enemy_sprites, npc_sprites_list_for_separation, pathfinding_counter,
                   max_npcs_per_frame):
        current_npc_sprites = [sprite for sprite in self.sprites() if isinstance(sprite, NPC)]
        effective_max = max(1, max_npcs_per_frame)
        for index, npc in enumerate(current_npc_sprites):
            try:
                can_calculate_path = (index % effective_max) == (pathfinding_counter % effective_max)
                # Truyền enemy_sprites cho npc_update để NPC có thể nhận biết và tương tác (nếu cần)
                npc.npc_update(player, enemy_sprites, can_calculate_path)
            except Exception as e:
                pass