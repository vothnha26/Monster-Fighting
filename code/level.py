import pygame
from settings import *
from tile import Tile
from player import Player
from debug import debug
from support import *
from random import choice, randint
from weapon import Weapon
from ui import UI
from enemy import Enemy
from npc import NPC
from particles import AnimationPlayer
from magic import MagicPlayer
from upgrade import Upgrade

class Level:
    def __init__(self):
        # Get the display surface
        self.display_surface = pygame.display.get_surface()
        self.game_paused = False

        # Sprite group setup
        self.visible_sprites = YSortCameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()

        # Attack sprites
        self.current_attack = None
        self.attack_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()

        # Sprite setup
        self.player = None  # Khởi tạo self.player là None
        self.create_map()

        # User interface
        if self.player is None:
            raise ValueError("Lỗi: Không tìm thấy Player trong map_Entities.csv (mã 394)")
        self.ui = UI()
        self.upgrade = Upgrade(self.player)

        # Particles
        self.animation_player = AnimationPlayer()
        self.magic_player = MagicPlayer(self.animation_player)

        # Pathfinding optimization
        self.enemy_pathfinding_counter = 0
        self.max_enemies_per_frame = 5  # Số lượng kẻ thù được phép tính toán đường đi mỗi khung hình
        self.npc_pathfinding_counter = 0
        self.max_npcs_per_frame = 2    # Số lượng NPC được phép tính toán đường đi mỗi khung hình

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

        # Lưu trữ các NPC để khởi tạo sau khi Player được tạo
        npc_positions = []

        for style, layout in layouts.items():
            for row_index, row in enumerate(layout):
                for col_index, col in enumerate(row):
                    if col != '-1':
                        x = col_index * TILESIZE
                        y = row_index * TILESIZE
                        if style == 'boundary':
                            Tile((x, y), [self.obstacle_sprites], 'invisible')
                        if style == 'grass':
                            random_grass_image = choice(graphics['grass'])
                            Tile(
                                (x, y),
                                [self.visible_sprites, self.obstacle_sprites, self.attackable_sprites],
                                'grass',
                                random_grass_image)
                        if style == 'object':
                            surf = graphics['objects'][int(col)]
                            Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'object', surf)
                        if style == 'entities':
                            if col == '394':
                                self.player = Player(
                                    (x, y),
                                    [self.visible_sprites],
                                    self.obstacle_sprites,
                                    self.create_attack,
                                    self.destroy_attack,
                                    self.create_magic)
                            elif col == '395':  # Mã cho NPC '2BlueWizard'
                                npc_positions.append((x, y))
                            else:
                                monster_name = {
                                    '390': 'bamboo',
                                    '391': 'spirit',
                                    '0': 'Fire vizard',
                                    '392': 'raccoon',
                                    '1': 'Lightning Mage',
                                    '2': 'Minotaur_1',
                                    '3': 'Minotaur_2',
                                    '4': 'Minotaur_3',
                                    '5': 'Samurai',
                                    '6': 'Samurai_Archer',
                                    '7': 'Samurai_Commander',
                                    '8': 'Wanderer Magican'
                                }.get(col, 'squid')
                                Enemy(
                                    monster_name,
                                    (x, y),
                                    [self.visible_sprites, self.attackable_sprites],
                                    self.obstacle_sprites,
                                    self.damage_player,
                                    self.trigger_death_particles,
                                    self.add_exp)

        # Khởi tạo các NPC sau khi Player đã được tạo
        for x, y in npc_positions:
            if self.player is not None:
                NPC(
                    '2BlueWizard',
                    (x, y),
                    [self.visible_sprites],  # Chỉ thêm vào visible_sprites
                    self.obstacle_sprites,
                    self.player,
                    self.damage_enemy)
            else:
                print(f"Cảnh báo: Không thể khởi tạo NPC tại ({x}, {y}) vì Player chưa được tạo.")

    def create_attack(self):
        self.current_attack = Weapon(self.player, [self.visible_sprites, self.attack_sprites])

    def create_magic(self, style, strength, cost):
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
                collision_sprites = pygame.sprite.spritecollide(attack_sprite, self.attackable_sprites, False)
                if collision_sprites:
                    for target_sprite in collision_sprites:
                        if target_sprite.sprite_type == 'grass':
                            pos = target_sprite.rect.center
                            offset = pygame.math.Vector2(0, 75)
                            for leaf in range(randint(3, 6)):
                                self.animation_player.create_grass_particles(pos - offset, [self.visible_sprites])
                            target_sprite.kill()
                        else:
                            target_sprite.get_damage(self.player, attack_sprite.sprite_type)

    def damage_player(self, amount, attack_type):
        if self.player.vulnerable:
            self.player.health -= amount
            self.player.vulnerable = False
            self.player.hurt_time = pygame.time.get_ticks()
            self.animation_player.create_particles(attack_type, self.player.rect.center, [self.visible_sprites])

    def damage_enemy(self, amount, attack_type, enemy):
        if enemy.vulnerable:
            enemy.health -= amount
            enemy.vulnerable = False
            enemy.hit_time = pygame.time.get_ticks()
            self.animation_player.create_particles(attack_type, enemy.rect.center, [self.visible_sprites])

    def trigger_death_particles(self, pos, particle_type):
        self.animation_player.create_particles(particle_type, pos, self.visible_sprites)

    def add_exp(self, amount):
        self.player.exp += amount

    def toggle_menu(self):
        self.game_paused = not self.game_paused

    def run(self):
        self.visible_sprites.custom_draw(self.player)
        self.ui.display(self.player)
        if self.game_paused:
            self.upgrade.display()
        else:
            self.visible_sprites.update()
            self.visible_sprites.enemy_update(self.player, self.enemy_pathfinding_counter, self.max_enemies_per_frame)
            self.visible_sprites.npc_update(self.player, self.npc_pathfinding_counter, self.max_npcs_per_frame)
            self.player_attack_logic()
            self.enemy_pathfinding_counter = (self.enemy_pathfinding_counter + 1) % self.max_enemies_per_frame
            self.npc_pathfinding_counter = (self.npc_pathfinding_counter + 1) % self.max_npcs_per_frame

class YSortCameraGroup(pygame.sprite.Group):
    def __init__(self):
        # General setup
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2
        self.offset = pygame.math.Vector2()

        # Creating the floor
        self.floor_surf = pygame.image.load('../graphics/tilemap/ground.png').convert()
        self.floor_rect = self.floor_surf.get_rect(topleft=(0, 0))

    def custom_draw(self, player):
        # Getting the offset
        self.offset.x = player.rect.centerx - self.half_width
        self.offset.y = player.rect.centery - self.half_height

        # Drawing the floor
        floor_offset_pos = self.floor_rect.topleft - self.offset
        self.display_surface.blit(self.floor_surf, floor_offset_pos)

        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)

    def enemy_update(self, player, pathfinding_counter, max_enemies_per_frame):
        enemy_sprites = [sprite for sprite in self.sprites() if hasattr(sprite, 'sprite_type') and sprite.sprite_type == 'enemy']
        for index, enemy in enumerate(enemy_sprites):
            can_calculate_path = (index % max_enemies_per_frame) == (pathfinding_counter % max_enemies_per_frame)
            enemy.enemy_update(player, enemy_sprites, can_calculate_path)

    def npc_update(self, player, pathfinding_counter, max_npcs_per_frame):
        npc_sprites = [sprite for sprite in self.sprites() if hasattr(sprite, 'sprite_type') and sprite.sprite_type == 'npc']
        enemy_sprites = [sprite for sprite in self.sprites() if hasattr(sprite, 'sprite_type') and sprite.sprite_type == 'enemy']
        for index, npc in enumerate(npc_sprites):
            can_calculate_path = (index % max_npcs_per_frame) == (pathfinding_counter % max_npcs_per_frame)
            npc.npc_update(player, enemy_sprites, can_calculate_path)