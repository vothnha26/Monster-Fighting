import pygame
import heapq
from collections import deque
from settings import *
from entity import Entity
from support import *
from pygame.math import Vector2

class NPC(Entity):
    def __init__(self, npc_name, pos, groups, obstacle_sprites, player, damage_enemy):
        super().__init__(groups)
        self.sprite_type = 'npc'
        self.npc_name = npc_name
        self.obstacle_sprites = obstacle_sprites
        self.player = player
        self.damage_enemy = damage_enemy

        # Tải thông tin cấu hình NPC
        npc_info = npc_data.get(self.npc_name, {})
        if not npc_info:
            print(f"Lỗi: Không tìm thấy dữ liệu NPC cho '{self.npc_name}' trong settings.py")
            self.kill()
            return

        # Graphics setup
        self.animations = {'idle': [], 'move': [], 'attack': []}
        self.status = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.15
        self.import_graphics(self.npc_name)
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=pos)
        inflate_value = -8
        self.hitbox = self.rect.inflate(inflate_value * 2, inflate_value * 2)
        self.hitbox_width = max(1, self.hitbox.width)
        self.hitbox_height = max(1, self.hitbox.height)
        self.direction = Vector2()

        # Stats
        self.health = npc_info.get('health', 70)
        self.exp = npc_info.get('exp', 120)
        self.speed = npc_info.get('speed', 2.5)
        self.attack_damage = npc_info.get('damage', 6)
        self.resistance = npc_info.get('resistance', 3)
        self.attack_radius = npc_info.get('attack_radius', 130)
        self.follow_radius = npc_info.get('follow_radius', TILESIZE * 8)
        self.stop_radius = npc_info.get('stop_radius', TILESIZE * 2)
        self.aggro_radius = npc_info.get('aggro_radius', TILESIZE * 5)
        self.attack_type = npc_info.get('attack_type', 'nova')

        # Player interaction
        self.can_attack = True
        self.attack_time = None
        self.attack_cooldown = 400
        self.vulnerable = True
        self.hit_time = None
        self.invincibility_duration = 300

        # Sounds
        try:
            self.death_sound = pygame.mixer.Sound('../audio/death.wav')
            self.hit_sound = pygame.mixer.Sound('../audio/hit.wav')
            attack_sound_path = npc_info.get('attack_sound')
            self.attack_sound = pygame.mixer.Sound(attack_sound_path) if attack_sound_path else None
            self.death_sound.set_volume(0.2)
            self.hit_sound.set_volume(0.2)
            if self.attack_sound:
                self.attack_sound.set_volume(0.3)
        except pygame.error:
            self.death_sound = self.hit_sound = self.attack_sound = None

        # Pathfinding setup
        self.pathfinding_algorithm = self.astar_pathfinding
        self.path = deque()
        self.next_step = None
        self.last_path_time = 0
        self.path_cooldown = npc_info.get('path_cooldown', 750)  # Tăng từ 500ms
        self.path_cooldown_far = npc_info.get('path_cooldown', 1500) * 2  # Tăng từ 1000ms
        self.recalculation_needed = True
        self.is_stuck = False
        self.last_stuck_check_time = 0
        self.stuck_check_interval = 500  # Tăng từ 300ms
        self.last_pos_stuck_check = None
        self.stuck_move_threshold_sq = 2 * 2
        self.max_distance_tiles = 10
        self.is_following = False
        self.last_status_time = 0
        self.status_cooldown = 100  # Kiểm tra trạng thái mỗi 100ms
        self.last_target_pos = None  # Lưu vị trí mục tiêu để kiểm tra thay đổi

    def import_graphics(self, name):
        main_path = npc_data.get(name, {}).get('graphics', f'../graphics/npcs/{name}/')
        self.animations = {'idle': [], 'move': [], 'attack': []}
        placeholder_created = False
        placeholder_surf = None
        for animation in self.animations.keys():
            full_path = main_path + animation
            try:
                self.animations[animation] = import_folder(full_path)
            except FileNotFoundError:
                if not placeholder_created:
                    placeholder_surf = pygame.Surface((TILESIZE, TILESIZE))
                    placeholder_surf.fill('cyan')
                    placeholder_created = True
                self.animations[animation] = [placeholder_surf] * 3
            if not self.animations[animation]:
                print(f"Warning: No images found for animation '{animation}' at path '{full_path}'")

    def get_tile_coords(self, pixel_coords=None):
        center = pixel_coords if pixel_coords else self.hitbox.center
        return (int(center[0] // TILESIZE), int(center[1] // TILESIZE)) if TILESIZE > 0 else (0, 0)

    def get_entity_distance_direction(self, target_entity):
        if not target_entity or not hasattr(target_entity, 'hitbox') or not hasattr(self, 'hitbox'):
            return (float('inf'), Vector2(0, 0))
        try:
            npc_vec = Vector2(self.hitbox.center)
            target_vec = Vector2(target_entity.hitbox.center)
            distance_sq = npc_vec.distance_squared_to(target_vec)
            distance = distance_sq ** 0.5
            direction = (target_vec - npc_vec).normalize() if distance > 0 else Vector2(0, 0)
            return (distance, direction)
        except (AttributeError, TypeError):
            return (float('inf'), Vector2(0, 0))

    def heuristic(self, node, goal):
        try:
            return ((node[0] - goal[0]) ** 2 + (node[1] - goal[1]) ** 2) ** 0.5
        except TypeError:
            return float('inf')

    def is_walkable(self, tile_coords):
        try:
            center_x = tile_coords[0] * TILESIZE + TILESIZE // 2
            center_y = tile_coords[1] * TILESIZE + TILESIZE // 2
        except IndexError:
            return False
        temp_hitbox = pygame.Rect(0, 0, self.hitbox_width, self.hitbox_height)
        temp_hitbox.center = (center_x, center_y)
        for sprite in self.obstacle_sprites:
            if hasattr(sprite, 'hitbox') and isinstance(sprite.hitbox, pygame.Rect) and temp_hitbox.colliderect(sprite.hitbox):
                return False
        return True

    def astar_pathfinding(self, goal_tile):
        start_tile = self.get_tile_coords()
        if start_tile == goal_tile or not self.is_walkable(goal_tile):
            return None
        open_list = []
        start_h = self.heuristic(start_tile, goal_tile)
        heapq.heappush(open_list, (start_h, 0, start_tile))
        came_from = {start_tile: None}
        g_cost_so_far = {start_tile: 0}
        max_iterations = 300  # Giảm từ 500
        iterations = 0
        while open_list and iterations < max_iterations:
            iterations += 1
            _, current_g, current_node = heapq.heappop(open_list)
            if current_node == goal_tile:
                path = deque()
                temp = current_node
                while temp != start_tile:
                    path.appendleft(temp)
                    parent = came_from.get(temp)
                    if parent is None:
                        break
                    temp = parent
                return path
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                neighbor = (current_node[0] + dx, current_node[1] + dy)
                if self.is_walkable(neighbor):
                    move_cost = 1.414 if dx != 0 and dy != 0 else 1
                    new_g_cost = current_g + move_cost
                    if neighbor not in g_cost_so_far or new_g_cost < g_cost_so_far[neighbor]:
                        g_cost_so_far[neighbor] = new_g_cost
                        h_cost = self.heuristic(neighbor, goal_tile)
                        f_cost = new_g_cost + h_cost
                        heapq.heappush(open_list, (f_cost, new_g_cost, neighbor))
                        came_from[neighbor] = current_node
        return None

    def check_player_on_obstacle(self, player):
        if not hasattr(player, 'hitbox'):
            return False
        player_hitbox = player.hitbox
        for sprite in self.obstacle_sprites:
            if hasattr(sprite, 'hitbox') and sprite.hitbox.colliderect(player_hitbox):
                return True
        return False

    def target_moved_significantly(self, target_entity):
        if not target_entity or not hasattr(target_entity, 'hitbox'):
            return True
        current_target_pos = Vector2(target_entity.hitbox.center)
        if self.last_target_pos is None:
            self.last_target_pos = current_target_pos
            return True
        distance_sq = current_target_pos.distance_squared_to(self.last_target_pos)
        threshold_sq = (TILESIZE * 0.5) ** 2  # Chỉ tính lại nếu mục tiêu di chuyển > 0.5 ô
        if distance_sq > threshold_sq:
            self.last_target_pos = current_target_pos
            return True
        return False

    def get_status(self, enemy_sprites):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_status_time < self.status_cooldown:
            return  # Bỏ qua nếu chưa đến lúc cập nhật trạng thái

        self.last_status_time = current_time
        player_distance, _ = self.get_entity_distance_direction(self.player)
        player_tile = self.player.get_tile_coords() if hasattr(self.player, 'get_tile_coords') else self.get_tile_coords(self.player.hitbox.center)
        npc_tile = self.get_tile_coords()
        tile_distance = abs(player_tile[0] - npc_tile[0]) + abs(player_tile[1] - npc_tile[1])

        # Kiểm tra xem NPC có bắt đầu theo người chơi chưa
        if not self.is_following and player_distance <= self.follow_radius:
            self.is_following = True

        new_status = 'idle'
        self.target_enemy = None

        if player_distance > self.follow_radius * 1.5:  # Nếu quá xa người chơi
            self.is_following = False
            self.path.clear()
            self.next_step = None
            self.direction = Vector2()
        elif self.is_following:
            if tile_distance > self.max_distance_tiles:
                new_status = 'move'
            else:
                # Tìm kiếm tối đa 5 kẻ địch gần nhất
                enemy_distances = []
                for enemy in enemy_sprites:
                    if enemy.groups() and hasattr(enemy, 'hitbox'):
                        dist, _ = self.get_entity_distance_direction(enemy)
                        if dist <= self.aggro_radius:
                            enemy_distances.append((dist, enemy))
                enemy_distances.sort()  # Sắp xếp theo khoảng cách
                closest_enemy = None
                if enemy_distances:
                    closest_enemy = enemy_distances[0][1]  # Lấy kẻ địch gần nhất

                if closest_enemy:
                    dist_to_enemy, _ = self.get_entity_distance_direction(closest_enemy)
                    if dist_to_enemy <= self.attack_radius and self.can_attack:
                        new_status = 'attack'
                        self.target_enemy = closest_enemy
                    else:
                        new_status = 'move'
                        self.target_enemy = closest_enemy
                else:
                    if player_distance <= self.stop_radius:
                        new_status = 'idle'
                    else:
                        new_status = 'move'

        if new_status != self.status:
            self.status = new_status
            self.frame_index = 0
            self.recalculation_needed = True
            if new_status == 'idle':
                self.direction = Vector2()
                self.path.clear()
                self.next_step = None

    def actions(self, can_calculate_path_this_frame):
        if self.is_stuck:
            distance_to_player, _ = self.get_entity_distance_direction(self.player)
            unstick_radius = self.follow_radius * 0.5
            if distance_to_player < unstick_radius:
                self.is_stuck = False
                self.recalculation_needed = True
                self.last_pos_stuck_check = None
                self.last_stuck_check_time = pygame.time.get_ticks()
            else:
                self.direction = Vector2()
                self.path.clear()
                self.next_step = None
                return

        current_time = pygame.time.get_ticks()
        target_entity = self.player if self.status == 'move' and not self.target_enemy else self.target_enemy

        if self.status == 'attack':
            if self.target_enemy and self.target_enemy.groups():
                _, direction_to_enemy = self.get_entity_distance_direction(self.target_enemy)
                self.direction = direction_to_enemy if direction_to_enemy.magnitude() > 0 else Vector2()
                if self.can_attack:
                    self.attack_time = pygame.time.get_ticks()
                    self.damage_enemy(self.attack_damage, self.attack_type, self.target_enemy)
                    if self.attack_sound:
                        self.attack_sound.play()
                    self.can_attack = False
            else:
                self.status = 'idle'
                self.target_enemy = None
                self.recalculation_needed = True
                self.path.clear()
                self.next_step = None
                self.direction = Vector2()
        elif self.status == 'move':
            if target_entity and target_entity.groups():
                distance_to_target, _ = self.get_entity_distance_direction(target_entity)
                stop_threshold = self.stop_radius if target_entity == self.player else self.attack_radius
                current_path_cooldown = self.path_cooldown_far if distance_to_target > self.follow_radius * 0.8 else self.path_cooldown

                if distance_to_target <= stop_threshold and target_entity == self.player:
                    self.status = 'idle'
                    self.path.clear()
                    self.next_step = None
                    self.direction = Vector2()
                    return

                needs_recalc_now = can_calculate_path_this_frame and (
                    self.recalculation_needed or
                    (current_time - self.last_path_time >= current_path_cooldown and self.target_moved_significantly(target_entity)) or
                    (not self.next_step and not self.path)
                )

                if needs_recalc_now:
                    player_on_obstacle = self.check_player_on_obstacle(self.player) if target_entity == self.player else False
                    if not player_on_obstacle:
                        self.recalculation_needed = False
                        self.last_path_time = current_time
                        goal_tile = self.get_tile_coords(target_entity.hitbox.center)
                        self.path.clear()
                        self.next_step = None
                        if self.is_walkable(goal_tile):
                            calculated_path = self.pathfinding_algorithm(goal_tile)
                            if calculated_path:
                                self.path = calculated_path
                                self.next_step = self.path.popleft() if self.path else None
                        if not self.next_step and not self.path:
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
                    distance_to_step = direction_to_step.length()
                    close_enough = self.speed * 0.8
                    if distance_to_step < close_enough:
                        self.hitbox.center = target_pos
                        self.rect.center = self.hitbox.center
                        self.next_step = self.path.popleft() if self.path else None
                        if not self.next_step:
                            self.direction = Vector2()
                            self.recalculation_needed = True
                    elif distance_to_step > 0:
                        self.direction = direction_to_step.normalize()
                    else:
                        self.direction = Vector2()
                        self.next_step = None
                        self.recalculation_needed = True
                else:
                    self.direction = Vector2()
                    if current_time - self.last_path_time >= current_path_cooldown:
                        self.recalculation_needed = True
        elif self.status == 'idle':
            self.direction = Vector2()
            self.path.clear()
            self.next_step = None

    def animate(self):
        animation = self.animations.get(self.status, self.animations.get('idle'))
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            if self.status == 'attack':
                self.can_attack = False
            self.frame_index = 0
        self.image = animation[int(self.frame_index)]
        self.rect = self.image.get_rect(center=self.hitbox.center)
        if not self.vulnerable:
            alpha = 0 if (pygame.time.get_ticks() - self.hit_time) % (self.invincibility_duration // 5) < (self.invincibility_duration // 10) else 255
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

    def get_damage(self, player, attack_type):
        if self.vulnerable:
            if self.hit_sound:
                self.hit_sound.play()
            direction_from_player = Vector2(self.hitbox.center) - Vector2(player.hitbox.center)
            self.direction = direction_from_player.normalize() if direction_from_player.magnitude() > 0 else Vector2(1, 0)
            damage_taken = player.get_full_weapon_damage() if attack_type == 'weapon' else player.get_full_magic_damage()
            self.health -= damage_taken
            self.hit_time = pygame.time.get_ticks()
            self.vulnerable = False
            self.path.clear()
            self.next_step = None
            self.recalculation_needed = True
            self.status = 'move'
            self.frame_index = 0
            self.is_stuck = False
            self.last_pos_stuck_check = None

    def check_death(self):
        if self.health <= 0:
            self.kill()

    def update(self):
        current_time_update = pygame.time.get_ticks()
        if current_time_update - self.last_stuck_check_time > self.stuck_check_interval:
            self.last_stuck_check_time = current_time_update
            is_trying_to_move = (self.status == 'move' and self.direction.magnitude() > 0.1)
            if is_trying_to_move and self.vulnerable:
                current_pos = Vector2(self.hitbox.center)
                if self.last_pos_stuck_check is not None:
                    dist_sq = current_pos.distance_squared_to(self.last_pos_stuck_check)
                    if dist_sq < self.stuck_move_threshold_sq and (self.next_step or self.recalculation_needed):
                        self.is_stuck = True
                        self.direction = Vector2()
                        self.next_step = None
                        self.path.clear()
                    else:
                        if self.is_stuck:
                            self.is_stuck = False
                        self.last_pos_stuck_check = current_pos
                else:
                    self.last_pos_stuck_check = current_pos
                    self.is_stuck = False
            else:
                if self.is_stuck:
                    self.is_stuck = False
                self.last_pos_stuck_check = None
        current_speed = 0 if self.is_stuck else (self.speed if self.vulnerable else self.resistance * 1.5)
        self.move(current_speed)
        self.animate()
        self.cooldowns()
        self.check_death()

    def npc_update(self, player, enemy_sprites, can_calculate_path_this_frame):
        self.get_status(enemy_sprites)
        self.actions(can_calculate_path_this_frame)