import pygame
from collections import deque
import heapq
from random import choice
from pygame.math import Vector2
from settings import *
from entity import Entity
from support import *

class Enemy(Entity):
    def __init__(self, monster_name, pos, groups, obstacle_sprites, damage_player, trigger_death_particles, add_exp):
        # General setup
        super().__init__(groups)
        self.sprite_type = 'enemy'
        self.monster_name = monster_name
        self.obstacle_sprites = obstacle_sprites
        self.damage_player = damage_player
        self.trigger_death_particles = trigger_death_particles
        self.add_exp = add_exp

        # Graphics setup
        self.animations = {}
        self.status = 'idle' if monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else 'idle_left'
        self.frame_index = 0
        self.animation_speed = 0.15
        if monster_name in ['bamboo', 'squid', 'raccoon', 'spirit']:
            self.import_graphics(monster_name)
        else:
            self.import_graphics_new(monster_name)
        self.image = self.animations[self.status][self.frame_index]

        # Movement
        self.rect = self.image.get_rect(topleft=pos)
        inflate_value = -8 if monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else -40
        self.hitbox = self.rect.inflate(inflate_value * 2, inflate_value * 2)
        self.hitbox_width = max(1, self.hitbox.width)
        self.hitbox_height = max(1, self.hitbox.height)
        self.direction = Vector2()

        # Stats
        monster_info = monster_data.get(monster_name, {})
        if not monster_info:
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
            attack_sound_path = monster_info.get('attack_sound')
            self.attack_sound = pygame.mixer.Sound(attack_sound_path) if attack_sound_path else None
            self.death_sound.set_volume(0.2)
            self.hit_sound.set_volume(0.2)
            if self.attack_sound:
                self.attack_sound.set_volume(0.3)
        except pygame.error:
            self.death_sound = self.hit_sound = self.attack_sound = None

        # Pathfinding setup
        self.pathfinding_algorithm = None
        self.learned_h_costs = {}
        self.max_rtaa_expansion = 100
        if self.monster_name in ['bamboo','squid','spirit']:
            self.pathfinding_algorithm = self.hill_climbing
        elif self.monster_name in ['Minotaur_1','Minotaur_2','Minotaur_3','raccoon']:
            self.pathfinding_algorithm = self.bfs_pathfinding
        else:
            self.pathfinding_algorithm = self.rtaa_star
        self.path = deque()
        self.next_step = None
        self.last_path_time = 0
        self.path_cooldown = 250
        self.path_cooldown_far = 750
        self.recalculation_needed = True
        self.is_stuck = False
        self.last_stuck_check_time = 0
        self.stuck_check_interval = 300
        self.last_pos_stuck_check = None
        self.stuck_move_threshold_sq = 2 * 2
        self.apply_separation = True
        self.separation_radius = TILESIZE * 1.5
        self.separation_radius_sq = self.separation_radius ** 2
        self.separation_strength = 0.8

    def import_graphics(self, name):
        self.animations = {'idle': [], 'move': [], 'attack': []}
        main_path = f'../graphics/monsters/{name}/'
        placeholder_created = False
        placeholder_surf = None
        for animation in self.animations.keys():
            full_path = main_path + animation
            try:
                self.animations[animation] = import_folder(full_path)
            except FileNotFoundError:
                if not placeholder_created:
                    placeholder_surf = pygame.Surface((TILESIZE, TILESIZE))
                    placeholder_surf.fill('purple')
                    placeholder_created = True
                self.animations[animation] = [placeholder_surf] * 3
            if not self.animations[animation]:
                print(f"Warning: No images found for animation '{animation}' at path '{full_path}'")

    def import_graphics_new(self, name):
        self.animations = {'left': [], 'right': [], 'idle_left': [], 'idle_right': [], 'attack_left': [], 'attack_right': []}
        main_path = f'../graphics/monsters/{name}/'
        placeholder_created = False
        placeholder_surf = None
        for animation in self.animations.keys():
            full_path = main_path + animation
            try:
                self.animations[animation] = import_folder(full_path)
            except FileNotFoundError:
                if not placeholder_created:
                    placeholder_surf = pygame.Surface((TILESIZE, TILESIZE))
                    placeholder_surf.fill('purple')
                    placeholder_created = True
                self.animations[animation] = [placeholder_surf] * 3
            if not self.animations[animation]:
                print(f"Warning: No images found for animation '{animation}' at path '{full_path}'")

    def get_tile_coords(self, pixel_coords=None):
        center = pixel_coords if pixel_coords else self.hitbox.center
        return (int(center[0] // TILESIZE), int(center[1] // TILESIZE)) if TILESIZE > 0 else (0, 0)

    def get_player_distance_direction(self, player):
        if not hasattr(player, 'hitbox') or not hasattr(self, 'hitbox'):
            return (float('inf'), Vector2(0, 0))
        try:
            enemy_vec = Vector2(self.hitbox.center)
            player_vec = Vector2(player.hitbox.center)
            distance = enemy_vec.distance_to(player_vec)
            direction = (player_vec - enemy_vec).normalize() if distance > 0 else Vector2(0, 0)
        except (AttributeError, TypeError):
            return (float('inf'), Vector2(0, 0))
        return (distance, direction)

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

    def rtaa_star(self, goal_tile, max_expansion):
        start_tile = self.get_tile_coords()
        if start_tile == goal_tile:
            return None
        open_list = []
        start_h = self.heuristic(start_tile, goal_tile)
        heapq.heappush(open_list, (start_h, start_h, 0, start_tile))
        came_from = {start_tile: None}
        g_cost_so_far = {start_tile: 0}
        iterations = 0
        best_leaf_node = start_tile
        min_f_cost_leaf = start_h
        processed_nodes = set()
        while open_list and iterations < max_expansion:
            current_f, current_h, current_g, current_node = heapq.heappop(open_list)
            if current_node in processed_nodes:
                continue
            processed_nodes.add(current_node)
            iterations += 1
            min_f_cost_leaf = current_f
            best_leaf_node = current_node
            if current_node == goal_tile:
                break
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                neighbor = (current_node[0] + dx, current_node[1] + dy)
                if neighbor in processed_nodes:
                    continue
                if self.is_walkable(neighbor):
                    move_cost = 1.414 if dx != 0 and dy != 0 else 1
                    new_g_cost = current_g + move_cost
                    if neighbor not in g_cost_so_far or new_g_cost < g_cost_so_far[neighbor]:
                        g_cost_so_far[neighbor] = new_g_cost
                        h = self.heuristic(neighbor, goal_tile)
                        priority = new_g_cost + h
                        heapq.heappush(open_list, (priority, h, new_g_cost, neighbor))
                        came_from[neighbor] = current_node
        path_to_best = []
        temp = best_leaf_node
        reconstruction_iterations = 0
        max_iterations_recon = iterations + 50
        while temp != start_tile and reconstruction_iterations < max_iterations_recon:
            reconstruction_iterations += 1
            parent = came_from.get(temp)
            if parent is None and temp != start_tile:
                best_first_step = None
                min_f = float('inf')
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    neighbor = (start_tile[0] + dx, start_tile[1] + dy)
                    if self.is_walkable(neighbor):
                        cost = 1.414 if dx != 0 and dy != 0 else 1
                        f = cost + self.heuristic(neighbor, goal_tile)
                        if f < min_f:
                            min_f = f
                            best_first_step = neighbor
                return best_first_step
            path_to_best.append(temp)
            temp = parent
        return path_to_best[-1] if path_to_best else None

    def bfs_pathfinding(self, goal_tile):
        start_tile = self.get_tile_coords()
        if start_tile == goal_tile:
            return None
        queue = deque([(start_tile, [start_tile])])
        visited = {start_tile}
        max_iterations = 500
        iterations = 0
        while queue and iterations < max_iterations:
            iterations += 1
            current_node, path = queue.popleft()
            if current_node == goal_tile:
                return path[1:]
            neighbors = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                neighbors.append((current_node[0] + dx, current_node[1] + dy))
            for neighbor in neighbors:
                if neighbor not in visited and self.is_walkable(neighbor):
                    visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append((neighbor, new_path))
        return None

    def hill_climbing(self, goal_tile):
        current_pos = self.get_tile_coords()
        if current_pos == goal_tile:
            return None
        h_cost_sq = lambda node: (node[0] - goal_tile[0]) ** 2 + (node[1] - goal_tile[1]) ** 2
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        best_step = None
        min_cost_sq = h_cost_sq(current_pos)
        valid_steps = []
        for dx, dy in directions:
            neighbor = (current_pos[0] + dx, current_pos[1] + dy)
            if self.is_walkable(neighbor):
                cost_sq = h_cost_sq(neighbor)
                if cost_sq <= min_cost_sq:
                    valid_steps.append({'pos': neighbor, 'cost': cost_sq})
        if not valid_steps:
            return None
        valid_steps.sort(key=lambda step: step['cost'])
        if valid_steps[0]['cost'] <= min_cost_sq:
            if valid_steps[0]['cost'] < min_cost_sq:
                best_step = valid_steps[0]['pos']
            else:
                equal_cost_steps = [step['pos'] for step in valid_steps if step['cost'] == min_cost_sq]
                if equal_cost_steps:
                    best_step = choice(equal_cost_steps)
        return best_step

    def check_player_on_obstacle(self, player):
        if not hasattr(player, 'hitbox'):
            return False
        player_hitbox = player.hitbox
        for sprite in self.obstacle_sprites:
            if hasattr(sprite, 'hitbox') and sprite.hitbox.colliderect(player_hitbox):
                return True
        return False

    def get_status(self, player):
        distance, direction = self.get_player_distance_direction(player)
        if self.status in ['attack', 'attack_left', 'attack_right'] and not self.can_attack:
            current_time = pygame.time.get_ticks()
            if self.attack_time is not None and current_time - self.attack_time < self.attack_cooldown:
                return
        new_status = 'idle' if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else 'idle_left'
        if distance <= self.attack_radius and self.can_attack:
            new_status = 'attack' if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else ('attack_right' if direction.x > 0 else 'attack_left')
        elif distance <= self.notice_radius:
            new_status = 'move' if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else ('right' if direction.x > 0 else 'left')
        if new_status != self.status:
            self.status = new_status
            self.frame_index = 0
            if new_status in ['move', 'right', 'left', 'attack', 'attack_left', 'attack_right']:
                self.recalculation_needed = True

    def actions(self, player, can_calculate_path_this_frame):
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
                self.path.clear()
                self.next_step = None
                return

        if self.status in ['attack', 'attack_left', 'attack_right']:
            _, direction_to_player = self.get_player_distance_direction(player)
            self.direction = direction_to_player if direction_to_player.magnitude() > 0 else Vector2()
            if self.can_attack:
                self.attack_time = pygame.time.get_ticks()
                self.damage_player(self.attack_damage, self.attack_type)
                if self.attack_sound:
                    self.attack_sound.play()
                self.can_attack = False
        elif self.status in ['move', 'right', 'left']:
            current_time = pygame.time.get_ticks()
            distance_to_player, _ = self.get_player_distance_direction(player)
            current_path_cooldown = self.path_cooldown_far if distance_to_player > self.notice_radius * 0.8 else self.path_cooldown
            needs_recalc_now = can_calculate_path_this_frame and (
                self.recalculation_needed or
                (current_time - self.last_path_time >= current_path_cooldown) or
                (self.pathfinding_algorithm in [self.rtaa_star, self.hill_climbing] and not self.next_step) or
                (self.pathfinding_algorithm == self.bfs_pathfinding and not self.path and not self.next_step)
            )
            if needs_recalc_now:
                player_on_obstacle = self.check_player_on_obstacle(player)
                if not player_on_obstacle:
                    self.recalculation_needed = False
                    self.last_path_time = current_time
                    goal_tile = self.get_tile_coords(player.hitbox.center)
                    self.path.clear()
                    self.next_step = None
                    calculated_result = None
                    if self.is_walkable(goal_tile):
                        if self.pathfinding_algorithm == self.rtaa_star:
                            calculated_result = self.rtaa_star(goal_tile, self.max_rtaa_expansion)
                        elif self.pathfinding_algorithm:
                            calculated_result = self.pathfinding_algorithm(goal_tile)
                    if calculated_result:
                        if isinstance(calculated_result, list):
                            self.path.extend(calculated_result)
                            self.next_step = self.path.popleft() if self.path else None
                        elif isinstance(calculated_result, tuple):
                            self.next_step = calculated_result
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
                close_enough = self.speed * 0.6
                if distance_to_step < close_enough:
                    self.hitbox.center = target_pos
                    self.rect.center = self.hitbox.center
                    if self.path and self.pathfinding_algorithm == self.bfs_pathfinding:
                        self.next_step = self.path.popleft() if self.path else None
                    else:
                        self.next_step = None
                        self.recalculation_needed = True
                    if not self.next_step:
                        self.direction = Vector2()
                elif distance_to_step > 0:
                    self.direction = direction_to_step.normalize()
                else:
                    self.direction = Vector2()
                    self.next_step = None
                    self.recalculation_needed = True
            else:
                self.direction = Vector2()
                if self.status in ['move', 'right', 'left'] and not self.recalculation_needed and current_time - self.last_path_time >= current_path_cooldown:
                    self.recalculation_needed = True
        else:
            self.direction = Vector2()
            if self.path or self.next_step:
                self.path.clear()
                self.next_step = None
                self.recalculation_needed = True

    def apply_steering(self, all_enemies):
        if not self.apply_separation or self.is_stuck or not self.vulnerable:
            return Vector2(0, 0)
        separation_vector = Vector2()
        neighbor_count = 0
        current_center = Vector2(self.hitbox.center)
        for other_enemy in all_enemies:
            if other_enemy is self or other_enemy.monster_name != self.monster_name or not hasattr(other_enemy, 'hitbox'):
                continue
            other_center = Vector2(other_enemy.hitbox.center)
            dist_sq = current_center.distance_squared_to(other_center)
            if 0 < dist_sq < self.separation_radius_sq:
                away_vec = current_center - other_center
                dist = dist_sq ** 0.5
                if dist > 0:
                    separation_vector += away_vec.normalize() / dist
                neighbor_count += 1
        final_steering = Vector2()
        if neighbor_count > 0:
            separation_vector /= neighbor_count
            if separation_vector.magnitude() > 0:
                separation_vector.normalize_ip()
                final_steering += separation_vector * self.separation_strength
        return final_steering

    def animate(self):
        animation = self.animations.get(self.status, self.animations.get('idle', self.animations.get('idle_left')))
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            if self.status in ['attack', 'attack_left', 'attack_right']:
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
            self.status = 'move' if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else ('right' if direction_from_player.x > 0 else 'left')
            self.frame_index = 0
            self.is_stuck = False
            self.last_pos_stuck_check = None

    def check_death(self):
        if self.health <= 0:
            self.kill()
            self.trigger_death_particles(self.rect.center, self.monster_name)
            self.add_exp(self.exp)
            if self.death_sound:
                self.death_sound.play()

    def hit_reaction(self):
        if not self.vulnerable:
            self.direction *= -self.resistance

    def update(self):
        current_time_update = pygame.time.get_ticks()
        if current_time_update - self.last_stuck_check_time > self.stuck_check_interval:
            self.last_stuck_check_time = current_time_update
            is_trying_to_move = (self.status in ['move', 'right', 'left'] and self.direction.magnitude() > 0.1)
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
        self.hit_reaction()
        self.move(current_speed)
        self.animate()
        self.cooldowns()
        self.check_death()

    def enemy_update(self, player, all_enemies, can_calculate_path_this_frame):
        base_direction = Vector2()
        if self.vulnerable and not self.is_stuck:
            self.get_status(player)
            self.actions(player, can_calculate_path_this_frame)
            base_direction = self.direction
        elif not self.vulnerable:
            base_direction = self.direction
        steering_force = self.apply_steering(all_enemies)
        if not self.is_stuck:
            self.direction = base_direction + steering_force
        else:
            self.direction = Vector2()