# enemy.py
from collections import deque
import heapq  # Vẫn cần thiết nếu các thuật toán được import từ pathfinding_algorithms.py sử dụng nó nội bộ
from random import choice, uniform
import math
from pygame.math import Vector2
from settings import *
from entity import Entity
from support import *
# --- THAY ĐỔI: Import các thuật toán từ pathfinding_algorithms.py ---
from pathfinding_algorithms import (
    a_star_pathfinding,
    bfs_pathfinding as bfs_pathfinding_external,  # Sử dụng alias để tránh nhầm lẫn
    ucs_pathfinding as ucs_pathfinding_external,  # Sử dụng alias
    heuristic_diagonal  # Import heuristic để dùng cho A*
)


class Enemy(Entity):
    def __init__(self, monster_name, pos, groups, obstacle_sprites, damage_player,
                 trigger_death_particles, add_exp, level_instance_ref=None):
        super().__init__(groups)
        self.sprite_type = 'enemy'
        self.monster_name = monster_name
        self.obstacle_sprites = obstacle_sprites
        self.damage_player = damage_player
        self.trigger_death_particles = trigger_death_particles
        self.add_exp = add_exp
        self.level_ref = level_instance_ref

        self.animations = {}
        self.status = 'idle' if monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else 'idle_left'
        self.frame_index = 0
        self.animation_speed = 0.15
        if monster_name in ['bamboo', 'squid', 'raccoon', 'spirit']:
            self.import_graphics(monster_name)
        else:
            self.import_graphics_new(monster_name)

        if not self.animations.get(self.status) or not self.animations[self.status]:
            if 'idle' in self.animations and self.animations['idle']:
                self.status = 'idle'
            elif 'idle_left' in self.animations and self.animations['idle_left']:
                self.status = 'idle_left'
            else:
                default_key = list(self.animations.keys())[0] if self.animations else None
                if default_key:
                    self.status = default_key
                else:
                    self.animations['idle'] = [pygame.Surface((TILESIZE, TILESIZE))]
                    self.status = 'idle'
        self.image = self.animations[self.status][self.frame_index]

        self.rect = self.image.get_rect(topleft=pos)

        if monster_name in ['bamboo', 'squid', 'raccoon', 'spirit']:
            inflate_value = -4
        else:
            inflate_value = -20

        self.hitbox = self.rect.inflate(inflate_value * 2, inflate_value * 2)
        # --- THAY ĐỔI: Đảm bảo hitbox luôn có chiều rộng/cao dương ---
        self.hitbox.width = max(1, self.hitbox.width)
        self.hitbox.height = max(1, self.hitbox.height)
        self.direction = Vector2()

        monster_info = monster_data.get(monster_name, {})
        if not monster_info:
            print(f"Cảnh báo: Không tìm thấy dữ liệu cho monster '{monster_name}'. Sẽ tự hủy.")
            self.kill()
            return
        self.health = monster_info.get('health', 50)
        self.exp = monster_info.get('exp', 50)
        self.speed = monster_info.get('speed', 3)
        self.attack_damage = monster_info.get('damage', 10)
        self.resistance = monster_info.get('resistance', 3)
        self.attack_radius = monster_info.get('attack_radius', 60)
        self.notice_radius = monster_info.get('notice_radius', 300)
        self.attack_type = monster_info.get('attack_type', 'slash')

        self.can_attack = True
        self.attack_time = None
        self.attack_cooldown = 400
        self.vulnerable = True
        self.hit_time = None
        self.invincibility_duration = 300

        try:
            self.death_sound = pygame.mixer.Sound('../audio/death.wav')
            self.hit_sound = pygame.mixer.Sound('../audio/hit.wav')
            attack_sound_path = monster_info.get('attack_sound')
            self.attack_sound = pygame.mixer.Sound(attack_sound_path) if attack_sound_path else None
            if self.death_sound: self.death_sound.set_volume(0.2)
            if self.hit_sound: self.hit_sound.set_volume(0.2)
            if self.attack_sound: self.attack_sound.set_volume(0.3)
        except pygame.error as e:
            print(f"Lỗi tải âm thanh cho Enemy {monster_name}: {e}")
            self.death_sound = self.hit_sound = self.attack_sound = None

        # --- THAY ĐỔI: Gán thuật toán tìm đường ---
        self.pathfinding_algorithm = None
        # Gán hàm heuristic cho A* (nếu dùng A*)
        self.heuristic_func_for_a_star = heuristic_diagonal  # Sử dụng heuristic đã import

        if self.monster_name in ['bamboo', 'squid', 'spirit']:
            self.pathfinding_algorithm = bfs_pathfinding_external
        elif self.monster_name in ['Minotaur_1', 'Minotaur_2', 'Minotaur_3', 'raccoon']:
            self.pathfinding_algorithm = ucs_pathfinding_external
        else:  # Các loại quái còn lại
            self.pathfinding_algorithm = a_star_pathfinding

        self.path = deque()
        self.next_step = None
        self.last_path_time = 0
        self.path_cooldown = 180  # Giảm cooldown một chút để phản ứng nhanh hơn
        self.path_cooldown_far = 500
        self.recalculation_needed = True
        self.is_stuck = False
        self.last_stuck_check_time = 0
        self.stuck_check_interval = 300
        self.last_pos_stuck_check = None
        self.stuck_move_threshold_sq = (self.speed * 0.2) ** 2
        self.apply_separation = True
        self.separation_radius = TILESIZE * 1.5
        self.separation_radius_sq = self.separation_radius ** 2
        self.separation_strength = 0.8

        self.obstacle_tiles_cache = set()
        if self.obstacle_sprites:
            for sprite in self.obstacle_sprites:
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
                            self.obstacle_tiles_cache.add((col, row))

    def import_graphics(self, name):
        self.animations = {'idle': [], 'move': [], 'attack': []}
        main_path = f'../graphics/monsters/{name}/'
        placeholder_created = False
        placeholder_surf = None
        for animation in self.animations.keys():
            full_path = main_path + animation
            try:
                imported_frames = import_folder(full_path)
                if not imported_frames:
                    raise FileNotFoundError
                self.animations[animation] = imported_frames
            except FileNotFoundError:
                if not placeholder_created:
                    placeholder_surf = pygame.Surface((TILESIZE, TILESIZE))
                    placeholder_surf.fill('purple')
                    placeholder_created = True
                self.animations[animation] = [placeholder_surf.copy() for _ in range(3)]
                print(
                    f"Cảnh báo: Không tìm thấy animation cho '{animation}' của '{name}' tại '{full_path}'. Đã tạo placeholder.")

    def import_graphics_new(self, name):
        self.animations = {'left': [], 'right': [], 'idle_left': [], 'idle_right': [], 'attack_left': [],
                           'attack_right': []}
        main_path = f'../graphics/monsters/{name}/'
        placeholder_created = False
        placeholder_surf = None
        for animation in self.animations.keys():
            full_path = main_path + animation
            try:
                imported_frames = import_folder(full_path)
                if not imported_frames:
                    raise FileNotFoundError
                self.animations[animation] = imported_frames
            except FileNotFoundError:
                if not placeholder_created:
                    placeholder_surf = pygame.Surface((TILESIZE, TILESIZE))
                    placeholder_surf.fill('magenta')
                    placeholder_created = True
                self.animations[animation] = [placeholder_surf.copy() for _ in range(3)]
                print(
                    f"Cảnh báo: Không tìm thấy animation cho '{animation}' của '{name}' tại '{full_path}'. Đã tạo placeholder.")

    def get_tile_coords(self, pixel_coords=None):
        center = pixel_coords if pixel_coords else self.hitbox.center
        return (int(center[0] // TILESIZE), int(center[1] // TILESIZE)) if TILESIZE > 0 else (0, 0)

    def get_player_distance_direction(self, player):
        if not player or not hasattr(player, 'hitbox') or not hasattr(self, 'hitbox'):
            return (float('inf'), Vector2(0, 0))
        try:
            enemy_vec = Vector2(self.hitbox.center)
            player_vec = Vector2(player.hitbox.center)
            distance = enemy_vec.distance_to(player_vec)
            direction = (player_vec - enemy_vec).normalize() if distance > 0 else Vector2(0, 0)
        except (AttributeError, TypeError) as e:
            return (float('inf'), Vector2(0, 0))
        return (distance, direction)

    # --- THAY ĐỔI: Hàm heuristic này có thể giữ lại hoặc bỏ nếu chỉ dùng heuristic_diagonal từ import ---
    # def heuristic(self, node, goal): # Có thể bỏ nếu dùng heuristic_diagonal trực tiếp
    #     try:
    #         return ((node[0] - goal[0]) ** 2 + (node[1] - goal[1]) ** 2) ** 0.5
    #     except TypeError:
    #         return float('inf')

    def is_walkable(self, tile_coords):
        if not isinstance(tile_coords, tuple) or len(tile_coords) != 2:
            return False
        if tile_coords in self.obstacle_tiles_cache:
            return False
        return True

    # --- THAY ĐỔI: Loại bỏ các hàm rtaa_star, bfs_pathfinding, hill_climbing định nghĩa trong lớp Enemy ---

    def check_player_on_obstacle(self, player):
        if not player or not hasattr(player, 'hitbox'):
            return True
        player_hitbox = player.hitbox
        player_tile = self.get_tile_coords(player_hitbox.center)
        if player_tile in self.obstacle_tiles_cache:
            return True
        return False

    def get_status(self, player):
        if not player:
            self.status = 'idle' if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else 'idle_left'
            self.direction = Vector2()
            self.recalculation_needed = False
            return

        distance, direction_to_player = self.get_player_distance_direction(player)
        is_aggressive_mode = self.level_ref and self.level_ref.enemy_aggression_mode_enabled
        current_base_status = self.status.split('_')[0]

        if current_base_status == 'attack' and not self.can_attack:
            current_time = pygame.time.get_ticks()
            if self.attack_time is not None and current_time - self.attack_time < self.attack_cooldown:
                return

        new_status_base = 'idle'
        if is_aggressive_mode:
            if distance <= self.attack_radius and self.can_attack:
                new_status_base = 'attack'
            elif player and player.health > 0:
                new_status_base = 'move'
            else:
                new_status_base = 'idle'
        else:
            if distance <= self.attack_radius and self.can_attack and player and player.health > 0:
                new_status_base = 'attack'
            elif distance <= self.notice_radius and player and player.health > 0:
                new_status_base = 'move'

        new_status_actual = ''
        if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit']:
            new_status_actual = new_status_base
        else:
            if new_status_base == 'idle':
                new_status_actual = 'idle_right' if direction_to_player.x >= 0 else 'idle_left'
            elif new_status_base == 'move':
                new_status_actual = 'right' if direction_to_player.x >= 0 else 'left'
            elif new_status_base == 'attack':
                new_status_actual = 'attack_right' if direction_to_player.x >= 0 else 'attack_left'
            else:
                new_status_actual = self.status

        if new_status_actual != self.status:
            self.status = new_status_actual
            self.frame_index = 0
            if new_status_base in ['move', 'attack']:
                self.recalculation_needed = True
            elif new_status_base == 'idle':
                self.direction = Vector2()
                self.path.clear()
                self.next_step = None
                self.recalculation_needed = False

    def actions(self, player, can_calculate_path_this_frame):
        if not player or player.health <= 0:
            self.status = 'idle' if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else 'idle_left'
            self.direction = Vector2()
            self.path.clear()
            self.next_step = None
            self.recalculation_needed = False
            return

        if self.is_stuck:
            distance_to_player, _ = self.get_player_distance_direction(player)
            unstick_radius = self.attack_radius * 1.5
            if distance_to_player < unstick_radius:
                self.is_stuck = False
                self.recalculation_needed = True
                self.last_pos_stuck_check = None
                self.last_stuck_check_time = pygame.time.get_ticks()
            else:
                self.direction = Vector2()
                return

        current_base_status = self.status.split('_')[0]
        if current_base_status == 'attack':
            _, direction_to_player = self.get_player_distance_direction(player)
            if direction_to_player.magnitude_squared() > 0:
                self.direction = direction_to_player.normalize()
            if self.can_attack:
                self.attack_time = pygame.time.get_ticks()
                self.damage_player(self.attack_damage, self.attack_type)
                if self.attack_sound:
                    self.attack_sound.play()
                self.can_attack = False
        elif current_base_status in ['move', 'right', 'left']:
            current_time = pygame.time.get_ticks()
            distance_to_player, _ = self.get_player_distance_direction(player)
            current_path_cooldown = self.path_cooldown_far if distance_to_player > self.notice_radius * 0.8 else self.path_cooldown

            needs_recalc_now = can_calculate_path_this_frame and (
                    self.recalculation_needed or
                    (current_time - self.last_path_time >= current_path_cooldown) or
                    (not self.next_step and not self.path and self.pathfinding_algorithm)
            )

            if needs_recalc_now:
                player_on_obstacle = self.check_player_on_obstacle(player)
                if not player_on_obstacle:
                    self.recalculation_needed = False
                    self.last_path_time = current_time
                    goal_tile = self.get_tile_coords(player.hitbox.center)
                    start_tile = self.get_tile_coords()  # --- THÊM: Lấy start_tile ---
                    self.path.clear()
                    self.next_step = None
                    calculated_path = None  # --- THAY ĐỔI: Tên biến ---

                    if self.is_walkable(goal_tile) and self.pathfinding_algorithm:
                        try:  # --- THÊM: Khối try-except để bắt lỗi tiềm ẩn ---
                            if self.pathfinding_algorithm == a_star_pathfinding:
                                calculated_path = self.pathfinding_algorithm(
                                    start_tile, goal_tile, self.is_walkable, self.heuristic_func_for_a_star
                                )
                            elif self.pathfinding_algorithm in [bfs_pathfinding_external, ucs_pathfinding_external]:
                                calculated_path = self.pathfinding_algorithm(
                                    start_tile, goal_tile, self.is_walkable
                                )
                        except Exception as e:
                            print(
                                f"Lỗi khi chạy thuật toán {self.pathfinding_algorithm.__name__} cho {self.monster_name}: {e}")
                            calculated_path = None

                    # --- THAY ĐỔI: Xử lý calculated_path ---
                    if calculated_path and isinstance(calculated_path, deque):
                        self.path = calculated_path
                        # Loại bỏ nút bắt đầu nếu nó có trong đường đi trả về
                        if self.path and len(self.path) > 0 and self.path[0] == start_tile:
                            self.path.popleft()
                        self.next_step = self.path.popleft() if self.path else None
                    # --- KẾT THÚC THAY ĐỔI XỬ LÝ ---

                    if not self.next_step:
                        self.direction = Vector2()
                else:
                    self.direction = Vector2()
                    self.path.clear()
                    self.next_step = None

            if self.next_step:
                target_px = self.next_step[0] * TILESIZE + TILESIZE // 2
                target_py = self.next_step[1] * TILESIZE + TILESIZE // 2
                target_pos = Vector2(target_px, target_py)
                direction_to_step = target_pos - Vector2(self.hitbox.center)
                distance_to_step_sq = direction_to_step.length_squared()
                close_enough_sq = (self.speed * 0.5) ** 2
                close_enough_sq = max(close_enough_sq, 4 * 4)

                if distance_to_step_sq < close_enough_sq:
                    self.hitbox.center = target_pos
                    self.rect.center = self.hitbox.center
                    if self.path:
                        self.next_step = self.path.popleft()
                    else:
                        self.next_step = None
                        self.recalculation_needed = True
                    if not self.next_step:
                        self.direction = Vector2()
                elif distance_to_step_sq > 0:
                    self.direction = direction_to_step.normalize()
                else:
                    self.direction = Vector2()
                    if self.path:
                        self.next_step = self.path.popleft()
                    else:
                        self.next_step = None;
                        self.recalculation_needed = True
            else:
                self.direction = Vector2()
                if current_base_status in ['move', 'right', 'left']:
                    self.recalculation_needed = True
        elif current_base_status == 'idle':
            self.direction = Vector2()
            if self.path or self.next_step:
                self.path.clear()
                self.next_step = None
        else:
            self.direction = Vector2()
            self.path.clear()
            self.next_step = None

    def apply_steering(self, all_enemies):
        if not self.apply_separation or self.is_stuck or not self.vulnerable:
            return Vector2(0, 0)
        separation_vector = Vector2()
        neighbor_count = 0
        current_center = Vector2(self.hitbox.center)
        for other_enemy in all_enemies:
            if other_enemy is self or not hasattr(other_enemy, 'hitbox') or \
                    (hasattr(other_enemy,
                             'monster_name') and other_enemy.monster_name != self.monster_name):
                continue

            other_center = Vector2(other_enemy.hitbox.center)
            dist_sq = current_center.distance_squared_to(other_center)
            effective_separation_radius_sq = (max(self.hitbox.width, self.hitbox.height) * 1.2) ** 2

            if 0 < dist_sq < effective_separation_radius_sq:
                away_vec = current_center - other_center
                strength = 1.0 / (dist_sq + 0.0001)
                separation_vector += away_vec.normalize() * strength
                neighbor_count += 1

        final_steering = Vector2()
        if neighbor_count > 0:
            separation_vector /= neighbor_count
            if separation_vector.length_squared() > 0:
                final_steering = separation_vector.normalize() * self.separation_strength
        return final_steering

    def animate(self):
        if self.status not in self.animations or not self.animations[self.status]:
            fallback_status = None
            if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit']:
                fallback_status = 'idle'
            else:
                if 'idle_left' in self.animations and self.animations['idle_left']:
                    fallback_status = 'idle_left'
                elif 'idle' in self.animations and self.animations[
                    'idle']:
                    fallback_status = 'idle'
            if fallback_status and fallback_status in self.animations and self.animations[fallback_status]:
                self.status = fallback_status
            else:
                if not hasattr(self, 'image') or self.image is None:
                    self.image = pygame.Surface((TILESIZE, TILESIZE));
                    self.image.fill((255, 0, 255))
                return

        animation = self.animations[self.status]
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            current_base_status = self.status.split('_')[0]
            if current_base_status == 'attack':
                self.can_attack = True
            self.frame_index = 0

        if int(self.frame_index) < len(animation):
            self.image = animation[int(self.frame_index)]
        else:
            self.image = animation[0]
            self.frame_index = 0

        self.rect = self.image.get_rect(center=self.hitbox.center)
        if not self.vulnerable:
            alpha = 0 if (pygame.time.get_ticks() // 100) % 2 == 0 else 255
            try:
                self.image.set_alpha(alpha)
            except pygame.error:
                pass
        else:
            try:
                self.image.set_alpha(255)
            except pygame.error:
                pass

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if not self.can_attack and self.attack_time is not None:
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True
        if not self.vulnerable and self.hit_time is not None:
            if current_time - self.hit_time >= self.invincibility_duration:
                self.vulnerable = True

    def get_damage(self, player, attack_type):
        if self.vulnerable:
            if self.hit_sound:
                self.hit_sound.play()
            if player and hasattr(player, 'hitbox'):
                direction_from_player = Vector2(self.hitbox.center) - Vector2(player.hitbox.center)
                if direction_from_player.length_squared() > 0:
                    self.direction = direction_from_player.normalize()
                else:
                    self.direction = Vector2(choice([-1, 1]), choice([-1, 1])).normalize() if Vector2(choice([-1, 1]),
                                                                                                      choice([-1,
                                                                                                              1])).length_squared() > 0 else Vector2(
                        1, 0)
            else:
                self.direction = Vector2(1, 0)

            damage_taken = 0
            if attack_type == 'weapon' and player and hasattr(player, 'get_full_weapon_damage'):
                damage_taken = player.get_full_weapon_damage()
            elif attack_type == 'magic' and player and hasattr(player, 'get_full_magic_damage'):
                damage_taken = player.get_full_magic_damage()
            elif player and hasattr(player, 'attack_damage'):
                damage_taken = player.attack_damage
            else:
                damage_taken = 10

            self.health -= damage_taken
            self.hit_time = pygame.time.get_ticks()
            self.vulnerable = False
            self.path.clear()
            self.next_step = None
            self.recalculation_needed = True
            self.frame_index = 0
            self.is_stuck = False
            self.last_pos_stuck_check = None

    def check_death(self):
        if self.health <= 0:
            if self.groups():
                self.kill()
                if self.level_ref and hasattr(self.level_ref, 'trigger_death_particles'):
                    self.trigger_death_particles(self.rect.center, self.monster_name)
                if self.level_ref and hasattr(self.level_ref, 'add_exp'):
                    self.add_exp(self.exp)
                if self.death_sound:
                    self.death_sound.play()
            return True
        return False

    def update(self):
        if self.check_death():
            return

        current_time_update = pygame.time.get_ticks()
        if current_time_update - self.last_stuck_check_time > self.stuck_check_interval:
            self.last_stuck_check_time = current_time_update
            is_trying_to_move = (self.status.startswith('move') or self.status.startswith(
                'right') or self.status.startswith('left')) \
                                and self.direction.length_squared() > 0.01

            if is_trying_to_move and self.vulnerable:
                current_pos = Vector2(self.hitbox.center)
                if self.last_pos_stuck_check is not None:
                    dist_sq_moved = current_pos.distance_squared_to(self.last_pos_stuck_check)
                    if dist_sq_moved < self.stuck_move_threshold_sq and (self.next_step or self.recalculation_needed):
                        if not self.is_stuck:
                            self.is_stuck = True
                            random_angle = uniform(0, 2 * math.pi)
                            self.direction = Vector2(math.cos(random_angle), math.sin(random_angle)).normalize()
                            self.next_step = None
                            self.path.clear()
                            self.recalculation_needed = True
                            self.last_path_time = 0
                    else:
                        if self.is_stuck: self.is_stuck = False;
                self.last_pos_stuck_check = current_pos
            elif not is_trying_to_move and self.is_stuck:
                self.is_stuck = False
                self.last_pos_stuck_check = None
            elif not self.vulnerable and self.is_stuck:
                self.is_stuck = False
                self.last_pos_stuck_check = None

        current_move_speed = 0
        effective_direction = self.direction.copy()

        if not self.vulnerable:
            current_move_speed = self.resistance
            effective_direction = self.direction
        elif self.is_stuck:
            current_move_speed = self.speed * 0.6
            effective_direction = self.direction
        elif self.status.startswith('attack'):
            current_move_speed = 0
        elif self.status.startswith('idle'):
            current_move_speed = 0
        else:
            current_move_speed = self.speed
            effective_direction = self.direction

        if effective_direction.length_squared() > 0.01 and current_move_speed > 0:
            self.move(current_move_speed)  # Entity.move sẽ dùng self.direction đã được cập nhật

        self.animate()
        self.cooldowns()

    def enemy_update(self, player, all_npcs, all_enemies_for_separation, can_calculate_path_this_frame):
        if self.vulnerable and not self.is_stuck:
            self.get_status(player)
            self.actions(player, can_calculate_path_this_frame)

        final_move_direction = self.direction.copy()
        if self.vulnerable and not self.is_stuck and \
                not (self.status.startswith('attack') or self.status.startswith('idle')):
            steering_force = self.apply_steering(all_enemies_for_separation)
            if self.direction.length_squared() > 0:
                combined_direction = self.direction.normalize() * 0.7 + steering_force * 0.3
                if combined_direction.length_squared() > 0:
                    final_move_direction = combined_direction.normalize()
            elif steering_force.length_squared() > 0:
                final_move_direction = steering_force.normalize()
        self.direction = final_move_direction