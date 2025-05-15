import pygame
from collections import deque  # Sử dụng deque cho path_history
import os
import random
import math
from settings import *
from entity import Entity
from support import import_folder
from pygame.math import Vector2
from pathfinding_algorithms import a_star_pathfinding, heuristic_diagonal,PATHFINDING_ALGORITHMS
from enemy import Enemy


class NPC(Entity):
    def __init__(self, npc_name, pos, groups, obstacle_sprites, player, damage_enemy_callback,
                 pathfinding_func=a_star_pathfinding, level_instance_ref=None):
        super().__init__(groups)
        self.sprite_type = 'npc'
        self.npc_name = npc_name
        self.obstacle_sprites = obstacle_sprites
        self.player = player
        self.damage_enemy_callback = damage_enemy_callback
        self.level_ref = level_instance_ref

        self.ai_mode = 'omni_hunt'
        self.facing_direction = Vector2(0, 1)

        self.is_hunting_all_enemies = True
        self.is_invincible_override = True

        self.apply_separation = False
        self.separation_radius_sq = (TILESIZE * 1.5) ** 2
        self.separation_strength = 0.5

        self.pathfinding_func = pathfinding_func
        self.current_algorithm_name_str = "Unknown"  # Sẽ được đặt bởi Level/UI
        # Cố gắng xác định tên thuật toán ban đầu
        if level_instance_ref and hasattr(level_instance_ref, 'selected_npc_algorithm_name'):
            self.current_algorithm_name_str = level_instance_ref.selected_npc_algorithm_name
        else:  # Thử tìm từ dict nếu không được cung cấp qua level_ref
            for name, func_obj in PATHFINDING_ALGORITHMS.items():
                if func_obj == self.pathfinding_func:
                    self.current_algorithm_name_str = name
                    break

        self.has_performance_issue = False
        self.problematic_algo_name = None
        self.last_path_calc_duration_ms = 0
        npc_info = npc_data.get(self.npc_name)
        if not npc_info:
            print(f"Cảnh báo: Không tìm thấy dữ liệu cho NPC '{self.npc_name}' trong settings.npc_data")
            self.kill()
            return

        self.notice_radius = npc_info.get('notice_radius', TILESIZE * 7)
        self.sight_radius = npc_info.get('sight_radius', DEFAULT_SIGHT_RADIUS)
        self.lkp_max_age = npc_info.get('lkp_max_age', DEFAULT_LKP_MAX_AGE)
        self.last_known_positions = {}
        self.pursuing_lkp_info = None
        self.original_lkp_search_tile = None
        self.lkp_search_pattern_points = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
        self.current_lkp_search_index = 0
        self.next_lkp_search_sub_tile = None
        self.target_is_visible = False

        self.animations = {'idle': [], 'move': [], 'attack': [], 'searching_lkp': []}
        self.status = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.15
        self.import_graphics(self.npc_name)

        default_anim_key = 'idle'
        if not self.animations.get(default_anim_key) or not self.animations[default_anim_key]:
            for key in ['idle_down', 'idle_left', 'idle_right', 'idle_up', 'move_down', 'move_left', 'idle', 'move']:
                if self.animations.get(key) and self.animations[key]:
                    default_anim_key = key
                    break
            else:
                default_anim_key = 'idle'
                if 'idle' not in self.animations: self.animations['idle'] = []

        if not self.animations.get(default_anim_key) or not self.animations[default_anim_key]:
            self.animations[default_anim_key] = [pygame.Surface((TILESIZE, TILESIZE))]
            self.animations[default_anim_key][0].fill('purple')

        if 'searching_lkp' not in self.animations or not self.animations['searching_lkp']:
            if 'move' in self.animations and self.animations['move']:
                self.animations['searching_lkp'] = self.animations['move']
            elif default_anim_key in self.animations and self.animations[default_anim_key]:
                self.animations['searching_lkp'] = self.animations[default_anim_key]
            else:
                placeholder_surf = pygame.Surface((TILESIZE, TILESIZE))
                placeholder_surf.fill('orange')
                self.animations['searching_lkp'] = [placeholder_surf]

        self.image = self.animations[default_anim_key][0]
        self.rect = self.image.get_rect(topleft=pos)
        base_inflate_x = npc_info.get('hitbox_inflate_x', -140)
        base_inflate_y = npc_info.get('hitbox_inflate_y', -140)
        self.hitbox = self.rect.inflate(base_inflate_x, base_inflate_y)

        min_hitbox_size = 8
        if self.hitbox.width < min_hitbox_size: self.hitbox.width = min_hitbox_size
        if self.hitbox.height < min_hitbox_size: self.hitbox.height = min_hitbox_size

        self.direction = Vector2()

        self.health = npc_info.get('health', 70)
        self.exp = npc_info.get('exp', 120)
        self.speed = npc_info.get('speed', 2.5)
        self.attack_damage = npc_info.get('damage', 6)
        self.resistance = npc_info.get('resistance', 3)
        self.attack_radius = npc_info.get('attack_radius', TILESIZE * 1.5)
        self.follow_radius = npc_info.get('follow_radius', TILESIZE * 8)
        self.stop_radius = npc_info.get('stop_radius', TILESIZE * 0.8)
        self.aggro_radius = npc_info.get('aggro_radius', TILESIZE * 6)
        self.attack_type = npc_info.get('attack_type', 'nova')

        self.can_attack = True
        self.attack_time = None
        self.attack_cooldown = npc_info.get('attack_cooldown', 700)
        self.vulnerable = True
        self.hit_time = None
        self.invincibility_duration = 300

        try:
            self.death_sound = pygame.mixer.Sound('../audio/death.wav')
            self.hit_sound = pygame.mixer.Sound('../audio/hit.wav')
            attack_sound_path = npc_info.get('attack_sound')
            self.attack_sound = pygame.mixer.Sound(attack_sound_path) if attack_sound_path else None
            if self.death_sound: self.death_sound.set_volume(0.2)
            if self.hit_sound: self.hit_sound.set_volume(0.2)
            if self.attack_sound: self.attack_sound.set_volume(0.3)
        except pygame.error as e:
            print(f"Lỗi tải âm thanh NPC: {e}")
            self.death_sound = self.hit_sound = self.attack_sound = None

        self.pathfinding_func = pathfinding_func
        self.path = deque()
        self.next_step = None
        self.last_path_time = 0
        self.path_cooldown = npc_info.get('path_cooldown', 400)
        self.path_cooldown_far = npc_info.get('path_cooldown_far', 800)
        self.recalculation_needed = True
        self.is_stuck = False
        self.last_stuck_check_time = 0
        self.stuck_check_interval = 800
        self.last_pos_stuck_check = None
        self.stuck_move_threshold_sq = (self.speed * 0.3) ** 2

        self.last_status_time = 0
        self.status_cooldown = 150
        self.heuristic = heuristic_diagonal

        self.current_target_entity = None
        self.last_target_tile_for_path = None

        self.can_guard_player = npc_info.get('can_guard_player', False)
        self.guard_min_dist_to_player = npc_info.get('guard_min_dist_to_player', TILESIZE * 1.0)
        self.guard_max_dist_to_player = npc_info.get('guard_max_dist_to_player', TILESIZE * 3.5)
        self.guard_ideal_dist_to_player = npc_info.get('guard_ideal_dist_to_player', TILESIZE * 2.0)
        self.guard_reposition_cooldown = npc_info.get('guard_reposition_cooldown', 2000)
        self.guard_threat_scan_radius = npc_info.get('guard_threat_scan_radius', TILESIZE * 10)
        self.last_guard_reposition_time = 0
        self.current_guard_target_tile = None

        self.obstacle_tiles = set()
        if obstacle_sprites:
            for sprite in obstacle_sprites:
                if hasattr(sprite, 'rect') and hasattr(sprite, 'hitbox') and \
                        hasattr(sprite.hitbox, 'width') and hasattr(sprite.hitbox, 'height') and \
                        sprite.hitbox.width > 0 and sprite.hitbox.height > 0 and \
                        getattr(sprite, 'sprite_type', '') != 'grass':
                    start_col = sprite.hitbox.left // TILESIZE
                    end_col = (sprite.hitbox.right - 1) // TILESIZE
                    start_row = sprite.hitbox.top // TILESIZE
                    end_row = (sprite.hitbox.bottom - 1) // TILESIZE
                    for col in range(start_col, end_col + 1):
                        for row in range(start_row, end_row + 1):
                            self.obstacle_tiles.add((col, row))

        # --- THUỘC TÍNH CHO DẤU VẾT ĐƯỜNG ĐI ---
        self.path_history = deque(maxlen=1000)
        self.path_color = (50, 50, 255, 120)
        self.path_point_radius = 3
        self.path_record_interval = 150
        self.last_path_record_time = 0
        # --- KẾT THÚC THUỘC TÍNH DẤU VẾT ---

    def import_graphics(self, name):
        main_path = npc_data.get(name, {}).get('graphics', f'../graphics/npcs/{name}/')
        if not main_path.endswith('/'): main_path += '/'

        desired_animations = ['idle_down', 'idle_up', 'idle_left', 'idle_right',
                              'move_down', 'move_up', 'move_left', 'move_right',
                              'attack_down', 'attack_up', 'attack_left', 'attack_right',
                              'searching_lkp_down', 'searching_lkp_up', 'searching_lkp_left', 'searching_lkp_right',
                              'idle', 'move', 'attack', 'searching_lkp']

        available_folders = []
        try:
            if os.path.exists(main_path):
                available_folders = [f.name for f in os.scandir(main_path) if f.is_dir()]
        except FileNotFoundError:
            print(f"Lỗi: Không tìm thấy thư mục đồ họa cho NPC: {main_path}")
        except Exception as e:
            print(f"Lỗi khi quét thư mục đồ họa NPC: {e}")

        for anim_name in desired_animations:
            if anim_name in self.animations and self.animations.get(anim_name):
                continue

            if anim_name in available_folders:
                anim_path = os.path.join(main_path, anim_name)
                imported_frames = import_folder(anim_path)
                if imported_frames:
                    self.animations[anim_name] = imported_frames
            elif '_' in anim_name:
                base_anim_name = anim_name.split('_')[0]
                if base_anim_name in available_folders and base_anim_name not in self.animations:
                    if base_anim_name in self.animations and self.animations[base_anim_name]: continue
                    anim_path = os.path.join(main_path, base_anim_name)
                    imported_frames = import_folder(anim_path)
                    if imported_frames:
                        self.animations[base_anim_name] = imported_frames

        if not self.animations.get('searching_lkp'):
            if self.animations.get('move'):
                self.animations['searching_lkp'] = self.animations['move']
            elif self.animations.get('idle'):
                self.animations['searching_lkp'] = self.animations['idle']
            else:
                surf = pygame.Surface((TILESIZE, TILESIZE))
                surf.fill('orange')
                self.animations['searching_lkp'] = [surf]
                print(f"NPC {name}: Sử dụng placeholder cho animation 'searching_lkp'.")

        if self.status not in self.animations or not self.animations[self.status]:
            if '_' in self.status:
                base_status = self.status.split('_')[0]
                if base_status in self.animations and self.animations[base_status]:
                    self.status = base_status
                else:
                    self.status = 'idle'
            else:
                self.status = 'idle'

            if self.status not in self.animations or not self.animations[self.status]:
                if 'idle' not in self.animations or not self.animations['idle']:
                    surf = pygame.Surface((TILESIZE, TILESIZE))
                    surf.fill('cyan')
                    self.animations['idle'] = [surf]

    def get_tile_coords(self, pixel_coords=None):
        center = pixel_coords if pixel_coords else self.hitbox.center
        if TILESIZE > 0:
            if isinstance(center, (tuple, list, pygame.math.Vector2)) and len(center) == 2:
                return int(center[0] // TILESIZE), int(center[1] // TILESIZE)
            elif hasattr(self, 'rect'):
                return int(self.rect.centerx // TILESIZE), int(self.rect.centery // TILESIZE)
            else:
                return 0, 0
        return 0, 0

    def get_entity_distance_direction(self, target_entity):
        if not target_entity or not hasattr(target_entity, 'groups') or not target_entity.groups() or \
                not hasattr(target_entity, 'hitbox') or not hasattr(target_entity.hitbox, 'center'):
            return float('inf'), Vector2(0, 0)
        try:
            npc_vec = Vector2(self.hitbox.center)
            target_vec = Vector2(target_entity.hitbox.center)
            distance = npc_vec.distance_to(target_vec)
            if distance < 0.001:
                direction = Vector2(0, 0)
            else:
                direction = (target_vec - npc_vec).normalize()
            return distance, direction
        except Exception as e:
            return float('inf'), Vector2(0, 0)

    def get_target_id(self, target_entity):
        if target_entity == self.player: return 'player'
        if hasattr(target_entity, 'id') and target_entity.id is not None: return target_entity.id
        return id(target_entity)

    def is_walkable(self, tile_coords):
        if not isinstance(tile_coords, tuple) or len(tile_coords) != 2:
            return False
        if tile_coords in self.obstacle_tiles:
            return False
        return True

    def check_target_tile_on_obstacle(self, target_tile_coords):
        return target_tile_coords in self.obstacle_tiles

    def target_tile_moved_significantly(self, new_target_tile):
        if self.last_target_tile_for_path is None or new_target_tile != self.last_target_tile_for_path:
            return True
        return False

    def evaluate_guard_position(self, tile_coords, player_tile, nearby_enemies):
        score = 1000.0
        npc_pos_center = Vector2(tile_coords[0] * TILESIZE + TILESIZE // 2, tile_coords[1] * TILESIZE + TILESIZE // 2)
        player_pos_center = Vector2(player_tile[0] * TILESIZE + TILESIZE // 2,
                                    player_tile[1] * TILESIZE + TILESIZE // 2)
        dist_to_player = npc_pos_center.distance_to(player_pos_center)

        if not (self.guard_min_dist_to_player <= dist_to_player <= self.guard_max_dist_to_player):
            return -float('inf')
        score -= abs(dist_to_player - self.guard_ideal_dist_to_player) * 1.5

        if nearby_enemies:
            closest_enemy_to_player = None
            min_dist_sq_to_player = float('inf')
            for enemy in nearby_enemies:
                if enemy and enemy.groups() and hasattr(enemy, 'hitbox'):
                    dist_sq = player_pos_center.distance_squared_to(Vector2(enemy.hitbox.center))
                    if dist_sq < min_dist_sq_to_player:
                        min_dist_sq_to_player = dist_sq
                        closest_enemy_to_player = enemy
            if closest_enemy_to_player:
                enemy_pos_center = Vector2(closest_enemy_to_player.hitbox.center)
                vec_player_npc = npc_pos_center - player_pos_center
                vec_player_enemy = enemy_pos_center - player_pos_center
                if vec_player_npc.length_squared() > 0.1 and vec_player_enemy.length_squared() > 0.1:
                    angle = vec_player_npc.angle_to(vec_player_enemy)
                    if abs(angle) < 45:
                        score += 200
                    elif abs(angle) < 90:
                        score += 100
        open_neighbors = 0
        for dx_o in [-1, 0, 1]:
            for dy_o in [-1, 0, 1]:
                if dx_o == 0 and dy_o == 0: continue
                if self.is_walkable((tile_coords[0] + dx_o, tile_coords[1] + dy_o)):
                    open_neighbors += 1
        score += open_neighbors * 10
        return score

    def find_best_guard_spot(self, enemy_sprites_for_eval):
        if not self.player or not self.player.groups(): return None
        player_tile = self.get_tile_coords(self.player.hitbox.center)
        candidate_tiles = []
        search_radius_in_tiles = int(self.guard_max_dist_to_player // TILESIZE) + 2

        for r_tile in range(int(self.guard_min_dist_to_player // TILESIZE) - 1, search_radius_in_tiles + 1):
            if r_tile < 1: continue
            for dx_tile in range(-r_tile, r_tile + 1):
                dy_abs_options = []
                if abs(dx_tile) < r_tile:
                    dy_val = int(math.sqrt(max(0, r_tile ** 2 - dx_tile ** 2)))
                    dy_abs_options.extend([dy_val, -dy_val])
                elif abs(dx_tile) == r_tile:
                    dy_abs_options.append(0)

                if abs(dx_tile) == 0 and r_tile > 0:
                    if (player_tile[0], player_tile[1] + r_tile) not in [(player_tile[0] + dx, player_tile[1] + dy) for
                                                                         dx, dy in dy_abs_options if dx == 0]:
                        candidate_tiles.append((player_tile[0], player_tile[1] + r_tile))
                    if (player_tile[0], player_tile[1] - r_tile) not in [(player_tile[0] + dx, player_tile[1] + dy) for
                                                                         dx, dy in dy_abs_options if dx == 0]:
                        candidate_tiles.append((player_tile[0], player_tile[1] - r_tile))

                for dy_tile_val in dy_abs_options:
                    check_tile = (player_tile[0] + dx_tile, player_tile[1] + dy_tile_val)
                    npc_candidate_pos_center = Vector2(check_tile[0] * TILESIZE + TILESIZE // 2,
                                                       check_tile[1] * TILESIZE + TILESIZE // 2)
                    player_pos_center = Vector2(player_tile[0] * TILESIZE + TILESIZE // 2,
                                                player_tile[1] * TILESIZE + TILESIZE // 2)
                    dist_to_player = npc_candidate_pos_center.distance_to(player_pos_center)

                    if self.is_walkable(check_tile) and \
                            self.guard_min_dist_to_player <= dist_to_player <= self.guard_max_dist_to_player:
                        if check_tile not in candidate_tiles:
                            candidate_tiles.append(check_tile)
        if not candidate_tiles: return None
        best_spot = None
        highest_score = -float('inf')
        for tile_candidate in candidate_tiles:
            score = self.evaluate_guard_position(tile_candidate, player_tile, enemy_sprites_for_eval)
            if score > highest_score:
                highest_score = score
                best_spot = tile_candidate
        return best_spot

    def get_status(self, enemy_sprites):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_status_time < self.status_cooldown:
            return
        self.last_status_time = current_time

        self.clear_expired_lkps()
        self.target_is_visible = False
        current_base_status = self.status.split('_')[0]

        if self.level_ref and self.level_ref.partial_observability_enabled:
            visible_direct_targets = []
            for entity in enemy_sprites:
                if isinstance(entity, Enemy) and entity.groups() and self.can_see_target(entity):
                    visible_direct_targets.append(entity)
                    self.update_lkp(entity)
                    self.target_is_visible = True

            player_visible_this_frame = False
            if self.player and self.player.groups() and self.can_see_target(self.player):
                self.update_lkp(self.player)
                player_visible_this_frame = True
                if not self.is_hunting_all_enemies or not visible_direct_targets:
                    self.target_is_visible = True

            if visible_direct_targets:
                visible_direct_targets.sort(key=lambda e: self.get_entity_distance_direction(e)[0])
                self.current_target_entity = visible_direct_targets[0]
                self.pursuing_lkp_info = None
                current_base_status = 'move'
                dist_to_target, _ = self.get_entity_distance_direction(self.current_target_entity)
                if dist_to_target <= self.attack_radius and self.can_attack:
                    current_base_status = 'attack'
            elif player_visible_this_frame and (self.can_guard_player or not self.is_hunting_all_enemies):
                self.current_target_entity = self.player
                self.pursuing_lkp_info = None
                player_distance, _ = self.get_entity_distance_direction(self.player)
                if self.can_guard_player:
                    current_base_status = 'guarding_player'
                elif player_distance <= self.stop_radius:
                    current_base_status = 'idle'
                elif player_distance <= self.follow_radius:
                    current_base_status = 'move'
                else:
                    current_base_status = 'idle'
            elif self.pursuing_lkp_info and self.status == 'searching_lkp':
                current_base_status = 'searching_lkp'
            elif self.last_known_positions:
                best_lkp_target_id = None
                most_recent_lkp_time = 0
                for target_id, lkp_data in self.last_known_positions.items():
                    if lkp_data['timestamp'] > most_recent_lkp_time:
                        most_recent_lkp_time = lkp_data['timestamp']
                        best_lkp_target_id = target_id

                if best_lkp_target_id:
                    lkp_data = self.last_known_positions[best_lkp_target_id]
                    self.pursuing_lkp_info = {'tile': lkp_data['tile'], 'target_id': best_lkp_target_id}
                    self.current_target_entity = None
                    current_base_status = 'move'
                    if self.get_tile_coords() == self.pursuing_lkp_info['tile']:
                        lkp_target_instance = self.player if best_lkp_target_id == 'player' else \
                            next((s for s in (self.level_ref.attackable_sprites if self.level_ref else []) if
                                  self.get_target_id(s) == best_lkp_target_id), None)
                        if lkp_target_instance and self.can_see_target(lkp_target_instance):
                            self.current_target_entity = lkp_target_instance
                            self.target_is_visible = True
                            self.pursuing_lkp_info = None
                            dist_to_target, _ = self.get_entity_distance_direction(self.current_target_entity)
                            if dist_to_target <= self.attack_radius and self.can_attack:
                                current_base_status = 'attack'
                            else:
                                current_base_status = 'move'
                        else:
                            current_base_status = 'searching_lkp'
                            self.original_lkp_search_tile = self.pursuing_lkp_info['tile']
                            self.current_lkp_search_index = 0
                            self.next_lkp_search_sub_tile = None
                else:
                    current_base_status = 'idle'
                    self.current_target_entity = None
                    self.pursuing_lkp_info = None
            else:
                current_base_status = 'idle'
                self.current_target_entity = None
                self.pursuing_lkp_info = None
        else:
            target_selected_for_omni_mode = None
            min_dist_sq_omni = float('inf')
            my_pos = Vector2(self.hitbox.center)

            if self.is_hunting_all_enemies and enemy_sprites:
                for enemy in enemy_sprites:
                    if enemy and enemy.groups() and hasattr(enemy, 'hitbox') and enemy != self:
                        dist_sq = my_pos.distance_squared_to(Vector2(enemy.hitbox.center))
                        if dist_sq < min_dist_sq_omni:
                            min_dist_sq_omni = dist_sq
                            target_selected_for_omni_mode = enemy

            if not target_selected_for_omni_mode and self.player and self.player.groups():
                if not self.is_hunting_all_enemies or self.can_guard_player:
                    target_selected_for_omni_mode = self.player

            if target_selected_for_omni_mode:
                self.current_target_entity = target_selected_for_omni_mode
                distance_to_target, _ = self.get_entity_distance_direction(self.current_target_entity)
                can_and_should_attack = False
                if isinstance(self.current_target_entity, Enemy):
                    if distance_to_target <= self.attack_radius and self.can_attack:
                        can_and_should_attack = True

                if can_and_should_attack:
                    current_base_status = 'attack'
                elif self.can_guard_player and self.current_target_entity == self.player:
                    current_base_status = 'guarding_player'
                elif distance_to_target <= self.stop_radius:
                    current_base_status = 'idle'
                else:
                    current_base_status = 'move'
            else:
                self.current_target_entity = None
                current_base_status = 'idle'

        new_full_status = self.get_directional_status(current_base_status)
        if new_full_status != self.status:
            self.status = new_full_status
            self.frame_index = 0
            if current_base_status in ['move', 'guarding_player', 'searching_lkp'] and self.status != 'attack':
                self.recalculation_needed = True
                self.last_target_tile_for_path = None
            elif current_base_status == 'idle' or current_base_status == 'attack':
                self.path.clear()
                self.next_step = None

    def get_directional_status(self, base_status):
        current_focus_vector = self.direction if self.direction.length_squared() > 0.01 else self.facing_direction
        direction_suffix = ""
        if current_focus_vector.length_squared() > 0.01:
            if abs(current_focus_vector.x) > abs(current_focus_vector.y):
                direction_suffix = '_right' if current_focus_vector.x > 0 else '_left'
            else:
                direction_suffix = '_down' if current_focus_vector.y > 0 else '_up'
        elif '_' in self.status and base_status == self.status.split('_')[0]:
            direction_suffix = '_' + self.status.split('_')[-1]

        if f"{base_status}{direction_suffix}" in self.animations and self.animations[
            f"{base_status}{direction_suffix}"]:
            return f"{base_status}{direction_suffix}"
        elif base_status in self.animations and self.animations[base_status]:
            return base_status
        elif f"idle{direction_suffix}" in self.animations and self.animations[f"idle{direction_suffix}"]:
            return f"idle{direction_suffix}"
        return "idle"

    def animate(self):
        current_animation_frames = self.animations.get(self.status)
        if not current_animation_frames:
            base_status_name = self.status.split('_')[0]
            current_animation_frames = self.animations.get(base_status_name)
            if not current_animation_frames:
                idle_suffix = self.status.split('_')[-1] if '_' in self.status else 'down'
                current_animation_frames = self.animations.get(f'idle_{idle_suffix}', self.animations.get('idle'))

        if not current_animation_frames:
            if not hasattr(self, '_default_surface_npc_anim'):
                self._default_surface_npc_anim = pygame.Surface(
                    (max(1, self.rect.width if hasattr(self, 'rect') else TILESIZE),
                     max(1, self.rect.height if hasattr(self, 'rect') else TILESIZE)))
                self._default_surface_npc_anim.fill('deeppink')
            self.image = self._default_surface_npc_anim
            if hasattr(self, 'hitbox'): self.rect = self.image.get_rect(center=self.hitbox.center)
            return

        self.frame_index += self.animation_speed
        if self.frame_index >= len(current_animation_frames):
            self.frame_index = 0
            if self.status.startswith('attack'):
                self.can_attack = True
            elif self.status.startswith('searching_lkp'):
                pass

        if 0 <= int(self.frame_index) < len(current_animation_frames):
            self.image = current_animation_frames[int(self.frame_index)]
            if hasattr(self, 'hitbox'):
                self.rect = self.image.get_rect(center=self.hitbox.center)

        if not self.vulnerable:
            alpha = self.wave_value()
            self.image.set_alpha(alpha)
        else:
            self.image.set_alpha(255)

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if not self.can_attack and self.attack_time is not None:
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True
        if not self.vulnerable and self.hit_time is not None:
            if current_time - self.hit_time >= self.invincibility_duration:
                self.vulnerable = True

    def _handle_damage_effects(self, damage_amount, attacker_entity):
        if self.vulnerable:
            if hasattr(self, 'is_invincible_override') and self.is_invincible_override: return
            if self.hit_sound: self.hit_sound.play()
            self.health -= damage_amount
            self.hit_time = pygame.time.get_ticks()
            self.vulnerable = False
            if attacker_entity and hasattr(attacker_entity, 'hitbox'):
                direction_from_attacker = (Vector2(self.hitbox.center) - Vector2(attacker_entity.hitbox.center))
                if direction_from_attacker.length_squared() > 0.01:
                    self.direction = direction_from_attacker.normalize()
                else:
                    self.direction = Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
            else:
                self.direction = Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
            self.path.clear()
            self.next_step = None
            self.recalculation_needed = True
            self.frame_index = 0
            self.is_stuck = False
            self.last_pos_stuck_check = None
            self.status = self.get_directional_status('idle')

    def get_damage(self, player_attacker, attack_type_from_player):
        if self.vulnerable:
            if hasattr(self, 'is_invincible_override') and self.is_invincible_override: return
            damage_taken = 0
            if attack_type_from_player == 'weapon':
                damage_taken = player_attacker.get_full_weapon_damage()
            elif attack_type_from_player == 'magic':
                if hasattr(player_attacker, 'get_full_magic_damage'):
                    damage_taken = player_attacker.get_full_magic_damage()
                else:
                    damage_taken = player_attacker.stats.get('magic', 0) * 5
            self._handle_damage_effects(damage_taken, player_attacker)

    def receive_damage_from_enemy(self, damage_amount, attack_type_from_enemy, enemy_attacker):
        if hasattr(self, 'is_invincible_override') and self.is_invincible_override: return
        if self.vulnerable:
            self._handle_damage_effects(damage_amount, enemy_attacker)

    def check_death(self):
        if self.health <= 0:
            if hasattr(self, 'is_invincible_override') and self.is_invincible_override:
                self.health = 1
                return
            if self.death_sound: self.death_sound.play()
            if self.level_ref and hasattr(self.level_ref, 'animation_player'):
                death_particle_type = self.npc_name
                if death_particle_type not in self.level_ref.animation_player.frames:
                    death_particle_type = 'smoke'
                self.level_ref.animation_player.create_particles(death_particle_type, self.rect.center,
                                                                 [self.level_ref.visible_sprites])
            self.kill()

    def npc_update(self, player, enemy_sprites, can_calculate_path_this_frame):
        if not self.groups(): return

        current_time_update = pygame.time.get_ticks()
        if current_time_update - self.last_stuck_check_time > self.stuck_check_interval:
            self.last_stuck_check_time = current_time_update
            is_trying_to_move = (self.status.startswith('move') or self.status.startswith(
                'guarding') or self.status.startswith('searching_lkp')) and self.direction.length_squared() > 0.01
            if is_trying_to_move and self.vulnerable:
                current_pos_vec = Vector2(self.hitbox.center)
                if self.last_pos_stuck_check is not None:
                    if current_pos_vec.distance_squared_to(self.last_pos_stuck_check) < self.stuck_move_threshold_sq:
                        if not self.is_stuck:
                            self.is_stuck = True
                            self.direction = -self.facing_direction if self.facing_direction.length_squared() > 0 else Vector2(
                                random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
                            self.path.clear()
                            self.next_step = None
                            self.next_lkp_search_sub_tile = None
                            self.recalculation_needed = True
                            self.last_target_tile_for_path = None
                            self.current_guard_target_tile = None
                            self.last_path_time = 0
                    else:
                        if self.is_stuck: self.is_stuck = False
                    self.last_pos_stuck_check = current_pos_vec
                else:
                    self.last_pos_stuck_check = current_pos_vec;
                    self.is_stuck = False
            else:
                if self.is_stuck: self.is_stuck = False; self.last_pos_stuck_check = None

        if self.vulnerable and not self.is_stuck:
            self.get_status(enemy_sprites)
            self.actions(enemy_sprites, can_calculate_path_this_frame)

        final_move_direction = self.direction.copy()
        current_move_speed = 0

        if not self.vulnerable:
            current_move_speed = self.resistance
        elif self.is_stuck:
            current_move_speed = self.speed * 0.7
        elif self.status.startswith('move') or self.status.startswith('guarding') or self.status.startswith(
                'searching_lkp'):
            current_move_speed = self.speed

        if final_move_direction.length_squared() > 0.01 and current_move_speed > 0:
            self.move(current_move_speed, final_move_direction)
        elif not self.vulnerable and final_move_direction.length_squared() > 0.01:  # Knockback
            self.move(current_move_speed, final_move_direction)

        self.animate()
        self.cooldowns()
        self.check_death()

    def move(self, speed, direction_vector=None):
        move_dir_to_use = self.direction
        if direction_vector is not None and direction_vector.length_squared() > 0:
            move_dir_to_use = direction_vector.normalize()
        elif self.direction.length_squared() > 0:
            move_dir_to_use = self.direction.normalize()
        else:
            return

        original_entity_direction = self.direction
        self.direction = move_dir_to_use # Tạm thời đặt cho logic va chạm của Entity

        self.hitbox.x += self.direction.x * speed
        self.collision('horizontal')
        self.hitbox.y += self.direction.y * speed
        self.collision('vertical')
        self.rect.center = self.hitbox.center

        # --- GHI LẠI DẤU VẾT ĐƯỜNG ĐI ---
        current_time = pygame.time.get_ticks()
        if self.direction.length_squared() > 0 and \
           (current_time - self.last_path_record_time > self.path_record_interval):
            current_center_tuple = (int(self.hitbox.centerx), int(self.hitbox.centery))
            if not self.path_history or self.path_history[-1] != current_center_tuple:
                self.path_history.append(current_center_tuple)
                self.last_path_record_time = current_time
                # ----- THÊM DÒNG PRINT Ở ĐÂY -----
                print(f"NPC {self.npc_name} tại {self.rect.topleft}: path_history cập nhật, độ dài: {len(self.path_history)}, điểm cuối: {current_center_tuple if self.path_history else 'N/A'}")
                # ----- KẾT THÚC DÒNG PRINT -----
        # --- KẾT THÚC GHI DẤU VẾT ---

        self.direction = original_entity_direction

    def is_in_fov(self, target_entity):
        if not target_entity or not hasattr(target_entity, 'hitbox') or target_entity.hitbox is None: return False
        dist_vec = Vector2(target_entity.hitbox.center) - Vector2(self.hitbox.center)
        distance = dist_vec.length()
        return distance <= self.sight_radius

    def has_line_of_sight(self, target_entity):
        if not target_entity or not hasattr(target_entity, 'hitbox') or target_entity.hitbox is None: return False
        start_pos = Vector2(self.hitbox.center)
        end_pos = Vector2(target_entity.hitbox.center)
        direction_vector = end_pos - start_pos
        distance = direction_vector.length()
        if distance == 0: return True
        num_steps = int(distance / (TILESIZE / 4))
        if num_steps == 0: num_steps = 1
        for i in range(1, num_steps + 1):
            t = i / num_steps
            current_point_on_line = start_pos.lerp(end_pos, t)
            point_tile = self.get_tile_coords_from_pos(current_point_on_line)
            if point_tile in self.obstacle_tiles:
                target_tile = self.get_tile_coords_from_pos(end_pos)
                if point_tile == target_tile and i == num_steps: continue
                return False
        return True

    def can_see_target(self, target_entity):
        if not self.level_ref or not self.level_ref.partial_observability_enabled:
            if not target_entity or not hasattr(target_entity, 'hitbox'): return False
            dist_vec = Vector2(target_entity.hitbox.center) - Vector2(self.hitbox.center)
            return dist_vec.length() <= self.notice_radius

        if not self.is_in_fov(target_entity): return False
        if not self.has_line_of_sight(target_entity): return False
        return True

    def update_lkp(self, target_entity):
        if not target_entity or not hasattr(target_entity, 'hitbox'): return
        target_id = self.get_target_id(target_entity)
        current_tile = self.get_tile_coords(target_entity.hitbox.center)
        self.last_known_positions[target_id] = {
            'tile': current_tile,
            'timestamp': pygame.time.get_ticks(),
        }
        if self.pursuing_lkp_info and self.pursuing_lkp_info['target_id'] == target_id:
            if self.status == 'searching_lkp' and self.original_lkp_search_tile == self.pursuing_lkp_info['tile']:
                self.original_lkp_search_tile = None
                self.next_lkp_search_sub_tile = None
            self.pursuing_lkp_info = None

    def clear_expired_lkps(self):
        current_time = pygame.time.get_ticks()
        expired_ids = [
            target_id for target_id, lkp_data in self.last_known_positions.items()
            if current_time - lkp_data['timestamp'] > self.lkp_max_age
        ]
        for target_id in expired_ids:
            del self.last_known_positions[target_id]
            if self.pursuing_lkp_info and self.pursuing_lkp_info['target_id'] == target_id:
                self.pursuing_lkp_info = None
                if self.status == 'searching_lkp' or (
                        self.original_lkp_search_tile and self.pursuing_lkp_info and self.original_lkp_search_tile ==
                        self.pursuing_lkp_info['tile']):
                    self.original_lkp_search_tile = None
                    self.next_lkp_search_sub_tile = None
                    self.recalculation_needed = True

    def on_po_mode_changed(self, po_enabled):
        self.last_known_positions.clear()
        self.pursuing_lkp_info = None
        self.target_is_visible = False
        self.original_lkp_search_tile = None
        self.next_lkp_search_sub_tile = None
        self.recalculation_needed = True
        self.status = self.get_directional_status('idle')
        self.direction = Vector2()

    def actions(self, enemy_sprites_for_guard_eval, can_calculate_path_this_frame):
        current_time = pygame.time.get_ticks()

        if self.has_performance_issue and self.current_algorithm_name_str == self.problematic_algo_name:
            self.direction = Vector2()
            self.path.clear()
            self.next_step = None
            self.status = self.get_directional_status('idle')
            return

        if self.direction.length_squared() > 0.01:
            self.facing_direction = self.direction.normalize()

        if self.status.startswith('attack'):
            target_is_enemy = isinstance(self.current_target_entity, Enemy)
            target_is_valid_for_attack = (self.current_target_entity and
                                          self.current_target_entity.groups() and
                                          (target_is_enemy or
                                           (not self.is_hunting_all_enemies and
                                            self.current_target_entity == self.player and
                                            (not self.level_ref or not self.level_ref.partial_observability_enabled)
                                            )
                                           )
                                          )
            if target_is_valid_for_attack:
                distance_to_target, direction_to_target = self.get_entity_distance_direction(self.current_target_entity)
                if direction_to_target.length_squared() > 0.01:
                    self.facing_direction = direction_to_target
                if distance_to_target <= self.attack_radius and self.can_attack:
                    self.attack_time = current_time
                    if target_is_enemy:
                        self.damage_enemy_callback(self.attack_damage, self.attack_type, self.current_target_entity)
                    if self.attack_sound:
                        self.attack_sound.play()
                    self.can_attack = False
                    self.direction = Vector2()
                elif distance_to_target > self.attack_radius:
                    self.status = self.get_directional_status('move')
                    self.recalculation_needed = True
            else:
                self.status = self.get_directional_status('idle')
                self.recalculation_needed = True
                self.current_target_entity = None
            return

        elif self.status.startswith('guarding'):
            pathfinding_target_tile_for_guarding = None
            if self.can_guard_player and self.player and self.player.groups():
                player_tile_for_guard = self.get_tile_coords(self.player.hitbox.center)
                dist_to_player_guarding, _ = self.get_entity_distance_direction(self.player)

                needs_new_guard_spot_logic = False
                if (self.current_guard_target_tile is None or
                        current_time - self.last_guard_reposition_time > self.guard_reposition_cooldown or
                        not (
                                self.guard_min_dist_to_player * 0.8 < dist_to_player_guarding < self.guard_max_dist_to_player * 1.2)):
                    if (self.current_guard_target_tile and
                            self.get_tile_coords() == self.current_guard_target_tile and
                            Vector2(player_tile_for_guard).distance_to(Vector2(
                                self.current_guard_target_tile)) * TILESIZE > self.guard_ideal_dist_to_player * 1.5):
                        needs_new_guard_spot_logic = True
                    elif not self.current_guard_target_tile:
                        needs_new_guard_spot_logic = True

                if needs_new_guard_spot_logic and can_calculate_path_this_frame:
                    best_spot_found = self.find_best_guard_spot(enemy_sprites_for_guard_eval)
                    if best_spot_found and best_spot_found != self.get_tile_coords():
                        self.current_guard_target_tile = best_spot_found
                        self.recalculation_needed = True
                        self.last_guard_reposition_time = current_time
                    elif not best_spot_found:
                        self.current_guard_target_tile = player_tile_for_guard
                        self.recalculation_needed = True

                pathfinding_target_tile_for_guarding = self.current_guard_target_tile

                if not pathfinding_target_tile_for_guarding or self.get_tile_coords() == pathfinding_target_tile_for_guarding:
                    if dist_to_player_guarding > self.guard_ideal_dist_to_player * 1.1:
                        if player_tile_for_guard != self.get_tile_coords():
                            pathfinding_target_tile_for_guarding = player_tile_for_guard
                        else:
                            self.direction = Vector2()
                            self.path.clear()
                            self.next_step = None
                            return
                    else:
                        self.direction = Vector2()
                        self.path.clear()
                        self.next_step = None
                        return
            else:
                self.status = self.get_directional_status('idle')
                self.current_guard_target_tile = None
                self.direction = Vector2()
                return

            if pathfinding_target_tile_for_guarding is None or self.get_tile_coords() == pathfinding_target_tile_for_guarding:
                self.direction = Vector2()
                self.path.clear()
                self.next_step = None
            return

        elif self.status.startswith('searching_lkp'):
            if not self.original_lkp_search_tile or not self.pursuing_lkp_info:
                self.status = self.get_directional_status('idle')
                self.recalculation_needed = True
                return

            lkp_target_id = self.pursuing_lkp_info['target_id']
            lkp_target_instance = None
            if lkp_target_id == 'player':
                lkp_target_instance = self.player
            elif self.level_ref and hasattr(self.level_ref, 'attackable_sprites'):
                lkp_target_instance = next(
                    (s for s in self.level_ref.attackable_sprites if self.get_target_id(s) == lkp_target_id), None)

            if lkp_target_instance and self.can_see_target(lkp_target_instance):
                self.current_target_entity = lkp_target_instance
                self.target_is_visible = True
                self.pursuing_lkp_info = None
                self.original_lkp_search_tile = None
                self.next_lkp_search_sub_tile = None
                dist_to_target, _ = self.get_entity_distance_direction(self.current_target_entity)
                if dist_to_target <= self.attack_radius and self.can_attack:
                    self.status = self.get_directional_status('attack')
                else:
                    self.status = self.get_directional_status('move')
                self.recalculation_needed = True
                return

            if self.next_lkp_search_sub_tile is None:
                if self.current_lkp_search_index < len(self.lkp_search_pattern_points):
                    offset = self.lkp_search_pattern_points[self.current_lkp_search_index]
                    potential_sub_tile = (self.original_lkp_search_tile[0] + offset[0],
                                          self.original_lkp_search_tile[1] + offset[1])
                    if self.is_walkable(potential_sub_tile):
                        self.next_lkp_search_sub_tile = potential_sub_tile
                    self.current_lkp_search_index += 1
                    self.path.clear()
                    self.next_step = self.next_lkp_search_sub_tile
                    self.recalculation_needed = False
                else:
                    if self.pursuing_lkp_info and self.pursuing_lkp_info['target_id'] in self.last_known_positions:
                        del self.last_known_positions[self.pursuing_lkp_info['target_id']]
                    self.pursuing_lkp_info = None
                    self.original_lkp_search_tile = None
                    self.next_lkp_search_sub_tile = None
                    self.status = self.get_directional_status('idle')
                    self.recalculation_needed = True
                    return

            if self.next_step:
                target_px = self.next_step[0] * TILESIZE + TILESIZE // 2
                target_py = self.next_step[1] * TILESIZE + TILESIZE // 2
                direction_to_step = Vector2(target_px, target_py) - Vector2(self.hitbox.center)
                dist_sq_to_step = direction_to_step.length_squared()
                close_enough_sq = max((self.speed * 1.0) ** 2, (TILESIZE * 0.3) ** 2)
                if dist_sq_to_step < close_enough_sq:
                    self.next_lkp_search_sub_tile = None
                    self.next_step = None
                elif direction_to_step.length() > 0:
                    self.direction = direction_to_step.normalize()
                else:
                    self.direction = Vector2()
                    self.next_lkp_search_sub_tile = None
                    self.next_step = None
            else:
                self.next_lkp_search_sub_tile = None
            return

        elif self.status.startswith('move'):
            pathfinding_target_tile = None
            effective_stop_threshold = self.stop_radius

            if self.status.startswith('guarding_player_move_target'):
                pathfinding_target_tile = self.current_guard_target_tile
                effective_stop_threshold = TILESIZE * 0.4
            elif self.level_ref and self.level_ref.partial_observability_enabled:
                if self.target_is_visible and self.current_target_entity and self.current_target_entity.groups():
                    pathfinding_target_tile = self.get_tile_coords(self.current_target_entity.hitbox.center)
                    if (isinstance(self.current_target_entity, Enemy) or
                            (self.is_hunting_all_enemies and self.current_target_entity == self.player)):
                        effective_stop_threshold = self.attack_radius * 0.8
                elif self.pursuing_lkp_info:
                    pathfinding_target_tile = self.pursuing_lkp_info['tile']
                    effective_stop_threshold = TILESIZE * 0.3
                else:
                    self.status = self.get_directional_status('idle')
                    self.direction = Vector2()
                    self.path.clear()
                    self.next_step = None
                    return
            else:
                if self.current_target_entity and self.current_target_entity.groups():
                    pathfinding_target_tile = self.get_tile_coords(self.current_target_entity.hitbox.center)
                    if (isinstance(self.current_target_entity, Enemy) or
                            (self.is_hunting_all_enemies and self.current_target_entity == self.player)):
                        effective_stop_threshold = self.attack_radius * 0.8
                else:
                    self.status = self.get_directional_status('idle')
                    self.direction = Vector2()
                    self.path.clear()
                    self.next_step = None
                    return

            if not pathfinding_target_tile:
                self.status = self.get_directional_status('idle')
                self.direction = Vector2()
                self.path.clear()
                self.next_step = None
                return

            if (self.current_target_entity and
                    self.current_target_entity.groups() and
                    (self.target_is_visible or
                     not (self.level_ref and self.level_ref.partial_observability_enabled))):
                distance_to_live_target, _ = self.get_entity_distance_direction(self.current_target_entity)
                if distance_to_live_target <= effective_stop_threshold:
                    self.path.clear()
                    self.next_step = None
                    self.direction = Vector2()
                    if ((isinstance(self.current_target_entity, Enemy) or
                         (self.is_hunting_all_enemies and self.current_target_entity == self.player)) and
                            self.can_attack and distance_to_live_target <= self.attack_radius):
                        self.status = self.get_directional_status('attack')
                    else:
                        self.status = self.get_directional_status('idle')
                    self.last_target_tile_for_path = None
                    return

            dist_to_pf_target_approx = Vector2(self.hitbox.center).distance_to(
                Vector2(pathfinding_target_tile[0] * TILESIZE + TILESIZE // 2,
                        pathfinding_target_tile[1] * TILESIZE + TILESIZE // 2))
            current_path_cooldown_move = self.path_cooldown_far if dist_to_pf_target_approx > self.follow_radius * 0.7 else self.path_cooldown
            moved_significantly = self.target_tile_moved_significantly(pathfinding_target_tile)
            if self.pursuing_lkp_info:
                moved_significantly = True

            needs_recalc_now = (can_calculate_path_this_frame and
                                (self.recalculation_needed or
                                 (
                                             current_time - self.last_path_time >= current_path_cooldown_move and moved_significantly) or
                                 (not self.next_step and not self.path and self.pathfinding_func is not None)
                                 )
                                )

            if needs_recalc_now:
                self.last_target_tile_for_path = pathfinding_target_tile
                target_tile_on_obstacle = self.check_target_tile_on_obstacle(pathfinding_target_tile)
                if not target_tile_on_obstacle and self.pathfinding_func:
                    self.recalculation_needed = False
                    self.last_path_time = current_time
                    start_tile = self.get_tile_coords()
                    self.path.clear()
                    self.next_step = None

                    calculated_path = None
                    PERFORMANCE_LIMIT_MS = 250
                    algo_display_name = self.current_algorithm_name_str
                    is_complex_algo_for_timing = algo_display_name in ['Backtracking', 'Forward Checking BS']

                    time_before_pf_action = pygame.time.get_ticks()
                    try:
                        func_name_for_call = getattr(self.pathfinding_func, '__name__', 'unknown')
                        if func_name_for_call in ['bfs_pathfinding',
                                                  'dfs_pathfinding',
                                                  'ucs_pathfinding',
                                                  'backtracking_pathfinding',
                                                  'forward_checking_backtracking_pathfinding'
                                                  ]:
                            calculated_path = self.pathfinding_func(start_tile, pathfinding_target_tile,
                                                                    self.is_walkable)
                        else:
                            calculated_path = self.pathfinding_func(start_tile, pathfinding_target_tile,
                                                                    self.is_walkable, heuristic_func=self.heuristic)

                        if calculated_path and isinstance(calculated_path, deque):
                            self.path = calculated_path
                            if self.path:
                                self.next_step = self.path.popleft()

                    except Exception as e:
                        print(
                            f"Lỗi pathfinding (move) cho {self.npc_name} bằng {getattr(self.pathfinding_func, '__name__', '?')}: {e}")
                        self.direction = Vector2()
                        self.path.clear()
                        self.next_step = None
                        self.recalculation_needed = True
                        if self.pursuing_lkp_info:
                            self.pursuing_lkp_info = None

                    time_after_pf_action = pygame.time.get_ticks()
                    self.last_path_calc_duration_ms = time_after_pf_action - time_before_pf_action

                    if (is_complex_algo_for_timing and
                            (self.last_path_calc_duration_ms > PERFORMANCE_LIMIT_MS or
                             (calculated_path is None and self.last_path_calc_duration_ms > 20))):
                        if self.level_ref and hasattr(self.level_ref, 'report_npc_pathfinding_issue'):
                            pass
                        self.level_ref.report_npc_pathfinding_issue(self, algo_display_name,self.last_path_calc_duration_ms)
                        self.has_performance_issue = True
                        self.problematic_algo_name = algo_display_name
                        self.path.clear()
                        self.next_step = None
                        self.status = self.get_directional_status('idle')
                        self.direction = Vector2()
                        return

                    if not self.next_step and not self.path:
                        self.direction = Vector2()
                        self.recalculation_needed = True
                        if self.pursuing_lkp_info:
                            if self.pursuing_lkp_info['target_id'] in self.last_known_positions:
                                del self.last_known_positions[self.pursuing_lkp_info['target_id']]
                            self.pursuing_lkp_info = None
                elif target_tile_on_obstacle:
                    self.direction = Vector2()
                    self.path.clear()
                    self.next_step = None
                    self.recalculation_needed = True
                    if self.pursuing_lkp_info:
                        self.pursuing_lkp_info = None

            if self.next_step:
                target_px = self.next_step[0] * TILESIZE + TILESIZE // 2
                target_py = self.next_step[1] * TILESIZE + TILESIZE // 2
                direction_to_step = Vector2(target_px, target_py) - Vector2(self.hitbox.center)
                dist_sq_to_step = direction_to_step.length_squared()
                close_enough_sq = max((self.speed * 0.8) ** 2, (TILESIZE * 0.25) ** 2)
                if dist_sq_to_step < close_enough_sq:
                    if self.pursuing_lkp_info and self.next_step == self.pursuing_lkp_info['tile']:
                        self.recalculation_needed = True
                        self.direction = Vector2()
                        self.next_step = None
                        return
                    self.next_step = self.path.popleft() if self.path else None
                    if not self.next_step:
                        self.recalculation_needed = True
                        self.direction = Vector2()
                elif direction_to_step.length() > 0:
                    self.direction = direction_to_step.normalize()
                else:
                    self.direction = Vector2()
                    self.next_step = None
                    self.recalculation_needed = True
            return

        elif self.status.startswith('idle'):
            self.direction = Vector2()
            return

    def get_tile_coords_from_pos(self, pos_vector):
        if TILESIZE > 0:
            return (int(pos_vector.x // TILESIZE), int(pos_vector.y // TILESIZE))
        return (0, 0)