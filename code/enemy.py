# enemy.py
from collections import deque
import heapq
from random import choice, uniform
import math
from pygame.math import Vector2
from settings import *
from entity import Entity
from support import *


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
            # Fallback nếu animation cho status ban đầu không tồn tại
            if 'idle' in self.animations and self.animations['idle']:
                self.status = 'idle'
            elif 'idle_left' in self.animations and self.animations['idle_left']:
                self.status = 'idle_left'
            else:  # Fallback cuối cùng nếu không có animation idle nào
                default_key = list(self.animations.keys())[0] if self.animations else None
                if default_key:
                    self.status = default_key
                else:  # Trường hợp không có animation nào được load
                    self.animations['idle'] = [pygame.Surface((TILESIZE, TILESIZE))]  # Tạo placeholder
                    self.status = 'idle'
        self.image = self.animations[self.status][self.frame_index]

        self.rect = self.image.get_rect(topleft=pos)

        if monster_name in ['bamboo', 'squid', 'raccoon', 'spirit']:
            inflate_value = -4
        else:
            inflate_value = -20

        self.hitbox = self.rect.inflate(inflate_value * 2, inflate_value * 2)
        self.hitbox_width = max(1, self.hitbox.width)
        self.hitbox_height = max(1, self.hitbox.height)
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

        self.pathfinding_algorithm = None
        self.learned_h_costs = {}
        self.max_rtaa_expansion = 100
        if self.monster_name in ['bamboo', 'squid', 'spirit']:
            self.pathfinding_algorithm = self.hill_climbing
        elif self.monster_name in ['Minotaur_1', 'Minotaur_2', 'Minotaur_3', 'raccoon']:
            self.pathfinding_algorithm = self.bfs_pathfinding
        else:
            self.pathfinding_algorithm = self.rtaa_star

        self.path = deque()
        self.next_step = None
        self.last_path_time = 0
        self.path_cooldown = 180
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

        # Cache các ô bị chặn để tăng tốc is_walkable
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
                if not imported_frames:  # Nếu import_folder trả về list rỗng
                    raise FileNotFoundError  # Coi như không tìm thấy file để dùng placeholder
                self.animations[animation] = imported_frames
            except FileNotFoundError:
                if not placeholder_created:
                    placeholder_surf = pygame.Surface((TILESIZE, TILESIZE))
                    placeholder_surf.fill('purple')  # Màu placeholder dễ nhận biết
                    placeholder_created = True
                self.animations[animation] = [placeholder_surf.copy() for _ in range(3)]  # Tạo vài frame placeholder
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
                    placeholder_surf.fill('magenta')  # Màu placeholder khác
                    placeholder_created = True
                self.animations[animation] = [placeholder_surf.copy() for _ in range(3)]
                print(
                    f"Cảnh báo: Không tìm thấy animation cho '{animation}' của '{name}' tại '{full_path}'. Đã tạo placeholder.")

    def get_tile_coords(self, pixel_coords=None):
        center = pixel_coords if pixel_coords else self.hitbox.center
        return (int(center[0] // TILESIZE), int(center[1] // TILESIZE)) if TILESIZE > 0 else (0, 0)

    def get_player_distance_direction(self, player):
        if not player or not hasattr(player, 'hitbox') or not hasattr(self, 'hitbox'):  # Thêm kiểm tra player is None
            return (float('inf'), Vector2(0, 0))
        try:
            enemy_vec = Vector2(self.hitbox.center)
            player_vec = Vector2(player.hitbox.center)
            distance = enemy_vec.distance_to(player_vec)
            direction = (player_vec - enemy_vec).normalize() if distance > 0 else Vector2(0, 0)
        except (AttributeError, TypeError) as e:
            # print(f"Lỗi trong get_player_distance_direction: {e}")
            return (float('inf'), Vector2(0, 0))
        return (distance, direction)

    def heuristic(self, node, goal):
        try:
            return ((node[0] - goal[0]) ** 2 + (node[1] - goal[1]) ** 2) ** 0.5
        except TypeError:
            return float('inf')

    def is_walkable(self, tile_coords):
        if not isinstance(tile_coords, tuple) or len(tile_coords) != 2:
            return False
        # Sử dụng cache đã tạo trong __init__
        if tile_coords in self.obstacle_tiles_cache:
            return False

        # (Tùy chọn) Kiểm tra biên bản đồ nếu có thông tin về kích thước map
        # if self.level_ref and hasattr(self.level_ref, 'map_width_tiles') and hasattr(self.level_ref, 'map_height_tiles'):
        #     if not (0 <= tile_coords[0] < self.level_ref.map_width_tiles and \
        #             0 <= tile_coords[1] < self.level_ref.map_height_tiles):
        #         return False # Ngoài biên map
        return True

    def rtaa_star(self, goal_tile, max_expansion):
        start_tile = self.get_tile_coords()
        if start_tile == goal_tile:
            return None  # Hoặc deque([start_tile]) nếu muốn trả về đường đi một bước
        open_list = []
        start_h = self.heuristic(start_tile, goal_tile)
        heapq.heappush(open_list,
                       (start_h, start_h, 0, start_tile, [start_tile]))  # (f_cost, h_cost, g_cost, node, path)

        # came_from không còn cần thiết nếu lưu path trực tiếp
        g_cost_so_far = {start_tile: 0}
        iterations = 0

        # Theo dõi nút lá tốt nhất dựa trên f_cost (hoặc h_cost nếu g_cost không quan trọng cho "lá")
        best_leaf_node_info = (start_h, start_tile, [start_tile])  # (f_cost, node, path_to_node)

        processed_nodes_in_iteration = set()  # Tránh xử lý lại nút trong cùng một lần mở rộng RTAA*

        while open_list and iterations < max_expansion:
            current_f, current_h, current_g, current_node, current_path = heapq.heappop(open_list)

            if current_node in processed_nodes_in_iteration:
                continue
            processed_nodes_in_iteration.add(current_node)

            iterations += 1

            # Cập nhật nút lá tốt nhất
            # Ưu tiên f_cost thấp hơn. Nếu bằng nhau, ưu tiên nút gần đích hơn (h_cost thấp hơn).
            if current_f < best_leaf_node_info[0] or \
                    (current_f == best_leaf_node_info[0] and current_h < self.heuristic(best_leaf_node_info[1],
                                                                                        goal_tile)):
                best_leaf_node_info = (current_f, current_node, current_path)

            if current_node == goal_tile:
                # Mục tiêu đạt được trong phạm vi mở rộng
                return current_path[1] if len(current_path) > 1 else None  # Trả về bước tiếp theo

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                neighbor = (current_node[0] + dx, current_node[1] + dy)

                if self.is_walkable(neighbor):
                    move_cost = 1.414 if dx != 0 and dy != 0 else 1
                    new_g_cost = current_g + move_cost

                    if new_g_cost < g_cost_so_far.get(neighbor, float('inf')):  # Kiểm tra g_cost tốt hơn
                        g_cost_so_far[neighbor] = new_g_cost
                        h_neighbor = self.heuristic(neighbor, goal_tile)
                        priority = new_g_cost + h_neighbor  # f_cost

                        new_path = list(current_path)  # Sao chép đường đi hiện tại
                        new_path.append(neighbor)  # Thêm nút hàng xóm

                        heapq.heappush(open_list, (priority, h_neighbor, new_g_cost, neighbor, new_path))
                        # came_from[neighbor] = current_node # Không cần nữa

        # Nếu không đạt mục tiêu, trả về bước đầu tiên trên đường tới nút lá tốt nhất
        final_path_to_best_leaf = best_leaf_node_info[2]
        return final_path_to_best_leaf[1] if len(final_path_to_best_leaf) > 1 else None

    def bfs_pathfinding(self, goal_tile):
        start_tile = self.get_tile_coords()
        if start_tile == goal_tile:
            return None
        queue = deque([(start_tile, deque())])  # (node, path_from_start_exclusive_of_node)
        visited = {start_tile}

        # Giới hạn số lần lặp để tránh treo game nếu map quá lớn hoặc không có đường
        max_iterations_bfs = 750  # Tăng nhẹ giới hạn nếu cần
        iterations = 0

        while queue and iterations < max_iterations_bfs:
            iterations += 1
            current_node, path_to_current = queue.popleft()

            # Xây dựng lại đường đi hoàn chỉnh chỉ khi tìm thấy mục tiêu
            # hoặc để trả về bước đầu tiên của đường đi ngắn nhất tìm thấy.

            # Ưu tiên các hướng chính, sau đó đến đường chéo
            # Điều này có thể giúp đường đi trông "tự nhiên" hơn một chút trong một số trường hợp
            primary_moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            diagonal_moves = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

            for dx, dy in primary_moves + diagonal_moves:
                neighbor = (current_node[0] + dx, current_node[1] + dy)

                if neighbor == goal_tile:  # Tìm thấy mục tiêu
                    if not path_to_current:  # Mục tiêu là hàng xóm trực tiếp của điểm bắt đầu
                        return neighbor
                    else:  # Trả về bước đầu tiên của đường đi đã tìm thấy
                        return path_to_current[0]

                if neighbor not in visited and self.is_walkable(neighbor):
                    visited.add(neighbor)
                    new_path_to_neighbor = path_to_current.copy()
                    if not new_path_to_neighbor:  # Nếu đây là bước đầu tiên từ start_node
                        new_path_to_neighbor.append(neighbor)  # Thì neighbor là bước đầu tiên
                    # else: không thêm neighbor vào new_path_to_neighbor vội, vì ta chỉ cần bước đầu
                    queue.append((neighbor, new_path_to_neighbor))
        return None  # Không tìm thấy đường

    def hill_climbing(self, goal_tile):
        current_pos = self.get_tile_coords()
        if current_pos == goal_tile:
            return None

        h_cost_sq = lambda node, g: (node[0] - g[0]) ** 2 + (node[1] - g[1]) ** 2  # Sửa để nhận goal_tile

        # Giữ nguyên thứ tự ưu tiên: dọc/ngang trước, chéo sau
        # Thêm một chút ngẫu nhiên vào việc chọn hướng để tránh bị kẹt lặp đi lặp lại
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        choice(directions)  # Xáo trộn nhẹ thứ tự để tránh thiên vị cố định

        best_step = None
        # Đặt min_cost_sq ban đầu là chi phí của vị trí hiện tại để đảm bảo chỉ di chuyển nếu tốt hơn hoặc bằng
        min_h_val = h_cost_sq(current_pos, goal_tile)

        equally_good_steps = []

        for dx, dy in directions:
            neighbor = (current_pos[0] + dx, current_pos[1] + dy)
            if self.is_walkable(neighbor):
                cost = h_cost_sq(neighbor, goal_tile)  # Truyền goal_tile
                if cost < min_h_val:
                    min_h_val = cost
                    best_step = neighbor
                    equally_good_steps = [neighbor]  # Reset danh sách các bước tốt bằng nhau
                elif cost == min_h_val:
                    if best_step is None:  # Nếu chưa có best_step nào (ví dụ, tất cả các bước đều bằng chi phí hiện tại)
                        best_step = neighbor  # Lấy bước đầu tiên tìm thấy
                    equally_good_steps.append(neighbor)

        # Nếu có nhiều bước "tốt nhất" (cùng chi phí min_h_val), chọn một cách ngẫu nhiên
        if equally_good_steps:
            best_step = choice(equally_good_steps)

        # Chỉ trả về best_step nếu nó thực sự là một bước di chuyển (khác vị trí hiện tại)
        # và chi phí của nó không tệ hơn chi phí ban đầu của vị trí hiện tại (đã được xử lý bởi min_h_val khởi tạo)
        if best_step and best_step != current_pos:
            return best_step
        return None  # Không tìm thấy bước nào tốt hơn hoặc bằng để di chuyển

    def check_player_on_obstacle(self, player):
        if not player or not hasattr(player, 'hitbox'):  # Thêm kiểm tra player
            return True  # Coi như player ở trên vật cản nếu không hợp lệ
        player_hitbox = player.hitbox
        # Sử dụng cache thay vì lặp qua obstacle_sprites
        player_tile = self.get_tile_coords(player_hitbox.center)
        if player_tile in self.obstacle_tiles_cache:
            return True

        # Kiểm tra chi tiết hơn với hitbox nếu cần thiết (có thể bỏ qua nếu cache đủ tốt)
        # for sprite in self.obstacle_sprites:
        #     if hasattr(sprite, 'hitbox') and sprite.hitbox.colliderect(player_hitbox):
        #         return True
        return False

    def get_status(self, player):
        if not player:  # Nếu không có player, enemy sẽ đứng yên
            self.status = 'idle' if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else 'idle_left'
            self.direction = Vector2()
            self.recalculation_needed = False  # Không cần tính đường nếu không có player
            return

        distance, direction_to_player = self.get_player_distance_direction(player)
        is_aggressive_mode = self.level_ref and self.level_ref.enemy_aggression_mode_enabled

        current_base_status = self.status.split('_')[0]  # vd: 'move' từ 'move_left'

        # Giữ nguyên trạng thái tấn công nếu đang trong animation và cooldown
        if current_base_status == 'attack' and not self.can_attack:
            current_time = pygame.time.get_ticks()
            if self.attack_time is not None and current_time - self.attack_time < self.attack_cooldown:
                return  # Vẫn đang trong cooldown/animation tấn công

        new_status_base = 'idle'

        if is_aggressive_mode:
            if distance <= self.attack_radius and self.can_attack:
                new_status_base = 'attack'
            elif player and player.health > 0:  # Chỉ di chuyển nếu player còn sống
                new_status_base = 'move'
            else:  # Player đã chết hoặc không tồn tại, enemy đứng yên
                new_status_base = 'idle'
        else:  # Chế độ hung hãn TẮT
            if distance <= self.attack_radius and self.can_attack and player and player.health > 0:
                new_status_base = 'attack'
            elif distance <= self.notice_radius and player and player.health > 0:
                new_status_base = 'move'
            # else: new_status_base vẫn là 'idle'

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
                new_status_actual = self.status  # Giữ trạng thái cũ nếu base không hợp lệ

        if new_status_actual != self.status:
            self.status = new_status_actual
            self.frame_index = 0
            if new_status_base in ['move', 'attack']:
                self.recalculation_needed = True
            elif new_status_base == 'idle':  # Khi chuyển sang idle, dừng di chuyển và xóa path
                self.direction = Vector2()
                self.path.clear()
                self.next_step = None
                self.recalculation_needed = False  # Không cần tính lại path khi đang idle

    def actions(self, player, can_calculate_path_this_frame):
        # Trường hợp không có player hoặc player đã chết
        if not player or player.health <= 0:
            self.status = 'idle' if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit'] else 'idle_left'
            self.direction = Vector2()
            self.path.clear()
            self.next_step = None
            self.recalculation_needed = False
            return

        # Logic xử lý kẹt
        if self.is_stuck:
            distance_to_player, _ = self.get_player_distance_direction(player)
            unstick_radius = self.attack_radius * 1.5
            if distance_to_player < unstick_radius:
                self.is_stuck = False
                self.recalculation_needed = True
                self.last_pos_stuck_check = None
                self.last_stuck_check_time = pygame.time.get_ticks()
            else:
                self.direction = Vector2()  # Tiếp tục đứng yên nếu vẫn kẹt và player ở xa
                # self.path.clear() # Không cần xóa path nếu đang cố thoát kẹt bằng hướng ngẫu nhiên
                # self.next_step = None
                return

                # Logic tấn công
        current_base_status = self.status.split('_')[0]
        if current_base_status == 'attack':
            _, direction_to_player = self.get_player_distance_direction(player)
            if direction_to_player.magnitude_squared() > 0:  # Cập nhật hướng nhìn ngay cả khi tấn công
                self.direction = direction_to_player.normalize()

            if self.can_attack:
                self.attack_time = pygame.time.get_ticks()
                self.damage_player(self.attack_damage, self.attack_type)
                if self.attack_sound:
                    self.attack_sound.play()
                self.can_attack = False
                # Không di chuyển vật lý khi đang trong animation tấn công
                # self.direction sẽ được dùng cho animation, nhưng không cho self.move()
        # Logic di chuyển
        elif current_base_status in ['move', 'right', 'left']:
            current_time = pygame.time.get_ticks()
            distance_to_player, _ = self.get_player_distance_direction(player)
            current_path_cooldown = self.path_cooldown_far if distance_to_player > self.notice_radius * 0.8 else self.path_cooldown

            needs_recalc_now = can_calculate_path_this_frame and (
                    self.recalculation_needed or
                    (current_time - self.last_path_time >= current_path_cooldown) or
                    (not self.next_step and not self.path and self.pathfinding_algorithm)
            # Thêm điều kiện có thuật toán
            )

            if needs_recalc_now:
                player_on_obstacle = self.check_player_on_obstacle(player)
                if not player_on_obstacle:
                    self.recalculation_needed = False  # Đặt lại trước khi tính toán
                    self.last_path_time = current_time
                    goal_tile = self.get_tile_coords(player.hitbox.center)
                    self.path.clear()
                    self.next_step = None
                    calculated_result = None
                    if self.is_walkable(
                            goal_tile) and self.pathfinding_algorithm:  # Thêm kiểm tra self.pathfinding_algorithm
                        if self.pathfinding_algorithm == self.rtaa_star:
                            calculated_result = self.rtaa_star(goal_tile, self.max_rtaa_expansion)
                        else:  # bfs_pathfinding hoặc hill_climbing
                            calculated_result = self.pathfinding_algorithm(goal_tile)

                    if calculated_result:
                        if isinstance(calculated_result, deque) or isinstance(calculated_result, list):
                            # BFS có thể trả về list, RTAA* có thể trả về path trong list (nếu sửa)
                            self.path.extend(list(calculated_result))  # Chuyển sang list nếu là deque để extend
                            self.next_step = self.path.popleft() if self.path else None
                        elif isinstance(calculated_result, tuple):  # Hill-climbing, RTAA* (bước tiếp theo)
                            self.next_step = calculated_result

                    if not self.next_step:  # Nếu không tìm thấy đường hoặc không có bước tiếp theo
                        self.direction = Vector2()  # Đứng yên
                        # Không đặt recalculation_needed = True ở đây nữa,
                        # để tránh yêu cầu tính lại ngay lập tức nếu không có đường.
                        # get_status sẽ xử lý việc này nếu cần.
                else:  # Player đang ở trên vật cản
                    self.direction = Vector2()
                    self.path.clear()
                    self.next_step = None
                    # Không đặt recalculation_needed = True, chờ player di chuyển

            # Di chuyển theo next_step nếu có
            if self.next_step:
                target_px = self.next_step[0] * TILESIZE + TILESIZE // 2
                target_py = self.next_step[1] * TILESIZE + TILESIZE // 2
                target_pos = Vector2(target_px, target_py)
                direction_to_step = target_pos - Vector2(self.hitbox.center)
                distance_to_step_sq = direction_to_step.length_squared()

                # Ngưỡng để coi như đã đến nơi, nên nhỏ hơn TILESIZE một chút
                close_enough_sq = (self.speed * 0.5) ** 2  # Ví dụ: nửa tốc độ trong 1 frame, hoặc TILESIZE*0.2
                close_enough_sq = max(close_enough_sq, 4 * 4)  # Tối thiểu 4 pixel

                if distance_to_step_sq < close_enough_sq:
                    self.hitbox.center = target_pos  # Di chuyển chính xác đến điểm
                    self.rect.center = self.hitbox.center
                    if self.path:
                        self.next_step = self.path.popleft()
                    else:
                        self.next_step = None
                        self.recalculation_needed = True  # Hết đường, cần tính lại cho mục tiêu mới (player)

                    if not self.next_step:
                        self.direction = Vector2()  # Dừng nếu hết đường
                elif distance_to_step_sq > 0:  # length_squared > 0 để tránh normalize vector 0
                    self.direction = direction_to_step.normalize()
                else:  # Đã ở ngay trên next_step (rất hiếm)
                    self.direction = Vector2()
                    if self.path:
                        self.next_step = self.path.popleft()
                    else:
                        self.next_step = None; self.recalculation_needed = True
            else:  # Không có next_step (có thể do không tìm thấy đường hoặc đã đến cuối path cũ)
                self.direction = Vector2()
                # Nếu đang trong trạng thái di chuyển mà không có next_step, yêu cầu tính lại
                if current_base_status in ['move', 'right', 'left']:
                    self.recalculation_needed = True

        # Logic cho trạng thái idle
        elif current_base_status == 'idle':
            self.direction = Vector2()
            if self.path or self.next_step:  # Dọn dẹp path nếu đang idle
                self.path.clear()
                self.next_step = None
            # Không đặt self.recalculation_needed = True ở đây.
            # get_status sẽ xử lý việc này khi enemy chuyển từ idle sang move/attack.
        else:  # Trạng thái không xác định
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
                             'monster_name') and other_enemy.monster_name != self.monster_name):  # Chỉ tách khỏi cùng loại (tùy chọn)
                continue

            other_center = Vector2(other_enemy.hitbox.center)
            dist_sq = current_center.distance_squared_to(other_center)

            # Ngưỡng tách xa hơn một chút để tránh chồng chéo hitbox
            # Nên lớn hơn kích thước hitbox một chút
            effective_separation_radius_sq = (max(self.hitbox.width, self.hitbox.height) * 1.2) ** 2
            # Hoặc giữ nguyên self.separation_radius_sq nếu đã hoạt động tốt

            if 0 < dist_sq < effective_separation_radius_sq:  # Sửa self.separation_radius_sq
                away_vec = current_center - other_center
                # Lực đẩy mạnh hơn khi ở gần hơn
                # Tránh chia cho 0 nếu dist_sq rất nhỏ (mặc dù kiểm tra 0 < dist_sq đã có)
                strength = 1.0 / (dist_sq + 0.0001)  # Thêm một epsilon nhỏ
                separation_vector += away_vec.normalize() * strength
                neighbor_count += 1

        final_steering = Vector2()
        if neighbor_count > 0:
            separation_vector /= neighbor_count
            if separation_vector.length_squared() > 0:  # Sửa magnitude() thành length_squared()
                # Giới hạn lực steering để không quá mạnh so với tốc độ di chuyển
                # final_steering = separation_vector.normalize() * self.speed * self.separation_strength # Giới hạn bởi tốc độ * hệ số
                # Hoặc đơn giản là normalize và nhân với hệ số
                final_steering = separation_vector.normalize() * self.separation_strength
        return final_steering

    def animate(self):
        # Đảm bảo self.status luôn có trong self.animations
        if self.status not in self.animations or not self.animations[self.status]:
            # Tìm một trạng thái fallback hợp lệ
            fallback_status = None
            if self.monster_name in ['bamboo', 'squid', 'raccoon', 'spirit']:
                fallback_status = 'idle'
            else:  # Quái vật có hướng
                if 'idle_left' in self.animations and self.animations['idle_left']:
                    fallback_status = 'idle_left'
                elif 'idle' in self.animations and self.animations[
                    'idle']:  # Fallback cho quái có hướng nếu không có idle_left
                    fallback_status = 'idle'

            if fallback_status and fallback_status in self.animations and self.animations[fallback_status]:
                self.status = fallback_status
            else:  # Fallback cuối cùng nếu không có animation nào
                # print(f"Cảnh báo: Enemy {self.monster_name} không có animation cho status {self.status} và không có fallback.")
                # Tạo một surface placeholder nếu self.image chưa tồn tại
                if not hasattr(self, 'image') or self.image is None:
                    self.image = pygame.Surface((TILESIZE, TILESIZE));
                    self.image.fill((255, 0, 255))
                return  # Không làm gì nếu không có animation

        animation = self.animations[self.status]
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            current_base_status = self.status.split('_')[0]
            if current_base_status == 'attack':
                self.can_attack = True  # Cho phép cooldown bắt đầu
                # Sau khi tấn công xong, nên chuyển về trạng thái idle hoặc move thay vì giữ attack
                # Quyết định này sẽ được đưa ra ở get_status() trong lần gọi tiếp theo
            self.frame_index = 0

        if int(self.frame_index) < len(animation):
            self.image = animation[int(self.frame_index)]
        else:  # Should not happen if frame_index is reset properly
            self.image = animation[0]
            self.frame_index = 0

        self.rect = self.image.get_rect(center=self.hitbox.center)
        if not self.vulnerable:
            alpha = 0 if (pygame.time.get_ticks() // 100) % 2 == 0 else 255  # Nhấp nháy nhanh hơn
            try:
                self.image.set_alpha(alpha)
            except pygame.error:  # Một số surface (ví dụ placeholder) có thể không hỗ trợ set_alpha nếu không convert_alpha()
                pass
        else:
            try:
                self.image.set_alpha(255)
            except pygame.error:
                pass

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        # Cooldown cho phép tấn công lại
        if not self.can_attack and self.attack_time is not None:  # Nếu self.can_attack là False nghĩa là vừa tấn công
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True  # Sẵn sàng tấn công lại
                # Không tự động đặt lại attack_time ở đây, nó sẽ được đặt khi tấn công thực sự xảy ra

        # Cooldown cho trạng thái bất tử (vulnerable)
        if not self.vulnerable and self.hit_time is not None:
            if current_time - self.hit_time >= self.invincibility_duration:
                self.vulnerable = True

    def get_damage(self, player, attack_type):
        if self.vulnerable:
            if self.hit_sound:
                self.hit_sound.play()

            # Tính hướng bị đẩy lùi
            if player and hasattr(player, 'hitbox'):  # Đảm bảo player hợp lệ
                direction_from_player = Vector2(self.hitbox.center) - Vector2(player.hitbox.center)
                if direction_from_player.length_squared() > 0:
                    self.direction = direction_from_player.normalize()
                else:  # Nếu ở quá gần, đẩy lùi theo hướng ngẫu nhiên nhẹ
                    self.direction = Vector2(choice([-1, 1]), choice([-1, 1])).normalize() if Vector2(choice([-1, 1]),
                                                                                                      choice([-1,
                                                                                                              1])).length_squared() > 0 else Vector2(
                        1, 0)
            else:  # Không có player hoặc player không có hitbox, không bị đẩy lùi hoặc đẩy theo hướng mặc định
                self.direction = Vector2(1, 0)

            damage_taken = 0
            if attack_type == 'weapon' and player and hasattr(player, 'get_full_weapon_damage'):
                damage_taken = player.get_full_weapon_damage()
            elif attack_type == 'magic' and player and hasattr(player, 'get_full_magic_damage'):
                damage_taken = player.get_full_magic_damage()
            elif player and hasattr(player, 'attack_damage'):  # Trường hợp khác, ví dụ NPC tấn công enemy
                damage_taken = player.attack_damage
            else:
                damage_taken = 10  # Sát thương mặc định nếu không xác định được

            self.health -= damage_taken
            self.hit_time = pygame.time.get_ticks()
            self.vulnerable = False  # Trở nên bất tử tạm thời

            # Dừng các hành động hiện tại và chuẩn bị cho phản ứng bị đánh
            self.path.clear()
            self.next_step = None
            self.recalculation_needed = True

            # Không chuyển trạng thái ở đây, self.update sẽ xử lý việc này dựa trên self.vulnerable
            # self.status sẽ tự động được cập nhật trong get_status sau khi hết vulnerable hoặc
            # self.direction sẽ được dùng để di chuyển lùi trong khi vulnerable.
            self.frame_index = 0
            self.is_stuck = False  # Reset trạng thái kẹt nếu đang kẹt
            self.last_pos_stuck_check = None

    def check_death(self):
        if self.health <= 0:
            if self.groups():  # Kiểm tra xem sprite còn trong group nào không trước khi kill
                self.kill()
                if self.level_ref and hasattr(self.level_ref, 'trigger_death_particles'):  # Đảm bảo level_ref tồn tại
                    self.trigger_death_particles(self.rect.center, self.monster_name)
                if self.level_ref and hasattr(self.level_ref, 'add_exp'):  # Đảm bảo level_ref tồn tại
                    self.add_exp(self.exp)
                if self.death_sound:
                    self.death_sound.play()
            return True  # Báo hiệu đã chết
        return False  # Chưa chết

    def update(self):
        if self.check_death():  # Nếu chết thì không làm gì nữa
            return

        current_time_update = pygame.time.get_ticks()

        # Logic kiểm tra kẹt
        if current_time_update - self.last_stuck_check_time > self.stuck_check_interval:
            self.last_stuck_check_time = current_time_update
            # Chỉ kiểm tra kẹt nếu đang cố di chuyển (status là move/right/left) và không bị đẩy lùi (vulnerable)
            is_trying_to_move = (self.status.startswith('move') or self.status.startswith(
                'right') or self.status.startswith('left')) \
                                and self.direction.length_squared() > 0.01

            if is_trying_to_move and self.vulnerable:
                current_pos = Vector2(self.hitbox.center)
                if self.last_pos_stuck_check is not None:
                    dist_sq_moved = current_pos.distance_squared_to(self.last_pos_stuck_check)

                    # Điều kiện kẹt: di chuyển quá ít VÀ (đang có next_step HOẶC đang cần tính lại đường)
                    # Điều này ngụ ý rằng enemy đang có ý định di chuyển đến một mục tiêu cụ thể nhưng không thành công.
                    if dist_sq_moved < self.stuck_move_threshold_sq and (self.next_step or self.recalculation_needed):
                        if not self.is_stuck:
                            # print(f"Enemy {self.monster_name} is stuck at {self.get_tile_coords()}!")
                            self.is_stuck = True
                            # Logic thoát kẹt: thử di chuyển theo hướng ngẫu nhiên hoặc lùi lại
                            random_angle = uniform(0, 2 * math.pi)
                            self.direction = Vector2(math.cos(random_angle), math.sin(random_angle)).normalize()
                            # Hoặc: self.direction = -self.direction.normalize() if self.direction.length_squared() > 0 else Vector2(choice([-1,1]),0)

                            self.next_step = None  # Xóa bước hiện tại để không cố đi vào đó nữa
                            self.path.clear()
                            self.recalculation_needed = True  # Yêu cầu tính lại đường sau khi thử thoát kẹt
                            self.last_path_time = 0  # Cho phép tính toán lại đường ngay
                    else:  # Nếu di chuyển đủ xa, không còn kẹt
                        if self.is_stuck: self.is_stuck = False;  # print(f"Enemy {self.monster_name} unstuck.")
                self.last_pos_stuck_check = current_pos
            elif not is_trying_to_move and self.is_stuck:  # Nếu không cố di chuyển nữa mà vẫn đang flag is_stuck
                self.is_stuck = False  # Reset
                self.last_pos_stuck_check = None
            elif not self.vulnerable and self.is_stuck:  # Nếu bị đẩy lùi thì không thể coi là kẹt
                self.is_stuck = False
                self.last_pos_stuck_check = None

        # Xác định tốc độ di chuyển dựa trên trạng thái
        current_move_speed = 0
        effective_direction = self.direction.copy()  # Hướng sẽ được sử dụng để di chuyển

        if not self.vulnerable:  # Đang trong trạng thái không thể tổn thương (bị đẩy lùi)
            current_move_speed = self.resistance
            # self.direction đã được set trong get_damage (hướng bị đẩy lùi)
            effective_direction = self.direction  # Di chuyển theo hướng bị đẩy lùi
        elif self.is_stuck:  # Nếu đang bị kẹt và đã thử logic thoát kẹt
            current_move_speed = self.speed * 0.6  # Di chuyển chậm hơn khi cố thoát kẹt
            effective_direction = self.direction  # Di chuyển theo hướng thoát kẹt đã tính
        elif self.status.startswith('attack'):  # Nếu đang tấn công
            current_move_speed = 0  # Không di chuyển khi tấn công
            # Hướng nhìn (self.direction) vẫn có thể được cập nhật trong actions() để xoay animation
        elif self.status.startswith('idle'):
            current_move_speed = 0  # Không di chuyển khi idle
        else:  # Trạng thái di chuyển bình thường
            current_move_speed = self.speed
            effective_direction = self.direction  # Di chuyển theo hướng đã tính trong actions()

        # Thực hiện di chuyển
        if effective_direction.length_squared() > 0.01 and current_move_speed > 0:
            # Tạo một bản sao của direction để truyền vào move, tránh self.direction bị thay đổi bên trong move nếu có logic phức tạp
            move_vector = effective_direction.normalize()
            self.move(current_move_speed)  # Entity.move sẽ sử dụng self.direction nội bộ của nó, đã được cập nhật.
            # Hoặc, nếu Entity.move chấp nhận vector: self.move(current_move_speed, move_vector)

        self.animate()
        self.cooldowns()
        # check_death đã được gọi ở đầu update

    def enemy_update(self, player, all_npcs, all_enemies_for_separation, can_calculate_path_this_frame):
        # Hàm này được gọi từ YSortCameraGroup.all_npcs không thực sự được enemy sử dụng trực tiếp ở đây.

        # 1. Cập nhật trạng thái và hành động dựa trên player (nếu không bị đẩy lùi hoặc kẹt)
        if self.vulnerable and not self.is_stuck:
            self.get_status(player)
            self.actions(player, can_calculate_path_this_frame)

            # 2. Xử lý steering (tách khỏi các enemy khác)
        # Chỉ áp dụng steering nếu enemy đang chủ động di chuyển (không bị đẩy lùi, không kẹt, không tấn công/idle)
        final_move_direction = self.direction.copy()  # Lấy hướng từ get_status/actions hoặc từ knockback/unstuck

        if self.vulnerable and not self.is_stuck and \
                not (self.status.startswith('attack') or self.status.startswith('idle')):

            steering_force = self.apply_steering(all_enemies_for_separation)

            # Kết hợp hướng cơ bản và steering force
            # Nếu enemy đang có ý định di chuyển (base_direction có độ lớn)
            if self.direction.length_squared() > 0:
                # Trọng số cho hướng gốc và hướng tách, ví dụ 70% hướng gốc, 30% hướng tách
                # Điều này giúp enemy vẫn hướng về mục tiêu trong khi tránh va chạm
                combined_direction = self.direction.normalize() * 0.7 + steering_force * 0.3  # Điều chỉnh trọng số nếu cần
                if combined_direction.length_squared() > 0:
                    final_move_direction = combined_direction.normalize()
                # else: giữ nguyên final_move_direction nếu combined_direction là zero (rất hiếm)
            elif steering_force.length_squared() > 0:  # Nếu không có hướng gốc, chỉ dùng steering
                final_move_direction = steering_force.normalize()
            # else: nếu cả hai đều là zero, final_move_direction vẫn là zero

        # Cập nhật hướng cuối cùng cho Enemy để Entity.move() sử dụng
        self.direction = final_move_direction