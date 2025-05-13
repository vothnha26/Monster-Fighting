# game setup
WIDTH    = 1280
HEIGTH   = 720
FPS      = 60
TILESIZE = 64
HITBOX_OFFSET = {
	'player': -13,
	'object': -20,
	'grass': -5,
	'invisible': 0}

# --- LOẠI BỎ CÀI ĐẶT MẶC ĐỊNH CHO PARTIAL OBSERVABILITY ---
# DEFAULT_PARTIAL_OBSERVABILITY = True # Không còn cần thiết

# ui
BAR_HEIGHT = 20
HEALTH_BAR_WIDTH = 200
ENERGY_BAR_WIDTH = 140
ITEM_BOX_SIZE = 80
UI_FONT = '../graphics/font/joystix.ttf'
UI_FONT_SIZE = 18

# general colors
WATER_COLOR = '#71ddee'
UI_BG_COLOR = '#222222'
UI_BORDER_COLOR = '#111111'
TEXT_COLOR = '#EEEEEE'

# ui colors
HEALTH_COLOR = 'red'
ENERGY_COLOR = 'blue'
UI_BORDER_COLOR_ACTIVE = 'gold'

# upgrade menu
TEXT_COLOR_SELECTED = '#111111'
BAR_COLOR = '#EEEEEE'
BAR_COLOR_SELECTED = '#111111'
UPGRADE_BG_COLOR_SELECTED = '#EEEEEE'

# --- PARTIAL OBSERVABILITY SETTINGS ---
DEFAULT_PARTIAL_OBSERVABILITY_ENABLED = True # Trạng thái bật/tắt PO mặc định
# (Các giá trị này sẽ được dùng trong npc_data nếu NPC cụ thể không có override)
DEFAULT_SIGHT_RADIUS = TILESIZE * 8
DEFAULT_SIGHT_ANGLE = 120  # Góc nhìn (độ), ví dụ 120 độ. Dùng None nếu chỉ muốn hình tròn.
DEFAULT_LKP_MAX_AGE = 10000  # Thời gian LKP còn hợp lệ (milliseconds)
VERY_LARGE_RADIUS = TILESIZE * 100

# --- ENEMY AGGRESSION MODE SETTING --- # MỚI
ENEMY_AGGRESSION_MODE_ENABLED = False # Mặc định là tắt

# weapons
weapon_data = {
	'sword': {'cooldown': 100, 'damage': 15,'graphic':'../graphics/weapons/sword/full.png'},
	'lance': {'cooldown': 400, 'damage': 30,'graphic':'../graphics/weapons/lance/full.png'},
	'axe': {'cooldown': 300, 'damage': 20, 'graphic':'../graphics/weapons/axe/full.png'},
	'rapier':{'cooldown': 50, 'damage': 8, 'graphic':'../graphics/weapons/rapier/full.png'},
	'sai':{'cooldown': 80, 'damage': 10, 'graphic':'../graphics/weapons/sai/full.png'}}

# magic
magic_data = {
	'flame': {'strength': 5,'cost': 20,'graphic':'../graphics/particles/flame/fire.png'},
	'heal' : {'strength': 20,'cost': 10,'graphic':'../graphics/particles/heal/heal.png'}}

# enemy
monster_data = {
	'squid': {'health': 100,'exp':100,'damage':20,'attack_type': 'slash', 'attack_sound':'../audio/attack/slash.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 80, 'notice_radius': 360},
	'raccoon': {'health': 300,'exp':250,'damage':40,'attack_type': 'claw',  'attack_sound':'../audio/attack/claw.wav','speed': 2, 'resistance': 3, 'attack_radius': 120, 'notice_radius': 400},
	'spirit': {'health': 100,'exp':110,'damage':8,'attack_type': 'thunder', 'attack_sound':'../audio/attack/fireball.wav', 'speed': 4, 'resistance': 3, 'attack_radius': 60, 'notice_radius': 350},
	'bamboo': {'health': 70,'exp':120,'damage':6,'attack_type': 'leaf_attack', 'attack_sound':'../audio/attack/slash.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 50, 'notice_radius': 300},
    'Fire vizard': {'health': 70,'exp':120,'damage':6,'attack_type': 'leaf_attack', 'attack_sound':'../audio/attack/slash.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 130, 'notice_radius': 300},
    'Lightning Mage': {'health': 70,'exp':120,'damage':6,'attack_type': 'nova', 'attack_sound':'../audio/attack/fireball.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 130, 'notice_radius': 300},
    'Minotaur_1': {'health': 70,'exp':120,'damage':6,'attack_type': 'leaf_attack', 'attack_sound':'../audio/attack/slash.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 130, 'notice_radius': 300},
    'Minotaur_2': {'health': 70,'exp':120,'damage':6,'attack_type': 'leaf_attack', 'attack_sound':'../audio/attack/slash.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 130, 'notice_radius': 300},
    'Minotaur_3': {'health': 70,'exp':120,'damage':6,'attack_type': 'leaf_attack', 'attack_sound':'../audio/attack/slash.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 130, 'notice_radius': 300},
    'Samurai': {'health': 70,'exp':120,'damage':6,'attack_type': 'leaf_attack', 'attack_sound':'../audio/attack/slash.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 130, 'notice_radius': 300},
    'Samurai_Archer': {'health': 70,'exp':120,'damage':6,'attack_type': 'leaf_attack', 'attack_sound':'../audio/attack/slash.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 130, 'notice_radius': 300},
    'Samurai_Commander': {'health': 70,'exp':120,'damage':6,'attack_type': 'leaf_attack', 'attack_sound':'../audio/attack/slash.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 130, 'notice_radius': 300},
    'Wanderer Magican': {'health': 70,'exp':120,'damage':6,'attack_type': 'thunder', 'attack_sound':'../audio/attack/fireball.wav', 'speed': 3, 'resistance': 3, 'attack_radius': 130, 'notice_radius': 300}
}

npc_data = {
    '2BlueWizard': {
        'sight_angle': 120,
        'lkp_max_age': 12000,
        'speed': 4,
        'follow_radius': VERY_LARGE_RADIUS,
        'stop_radius': TILESIZE * 1,
        'path_cooldown': 500,
        'path_cooldown_far': 1000,
        'graphics': '../graphics/npcs/2BlueWizard/',
        'aggro_radius': TILESIZE * 6,
        'health': 99999,
        'exp':120,
		'damage': 150,
        'attack_radius': TILESIZE * 2,
        'attack_cooldown': 600,
        'attack_type': 'nova',
        'attack_sound':'../audio/attack/fireball.wav',
		'resistance': 3,
        'notice_radius': VERY_LARGE_RADIUS,
        'can_guard_player': True,
        'guard_min_dist_to_player': TILESIZE * 1.0,
        'guard_max_dist_to_player': TILESIZE * 3.5,
        'guard_ideal_dist_to_player': TILESIZE * 2.0,
        'guard_reposition_cooldown': 2500,
        'guard_threat_scan_radius': TILESIZE * 10,
    },
	'Demon': {
        'sight_radius': DEFAULT_SIGHT_RADIUS, # Sử dụng giá trị mặc định
        'sight_angle': None, # Chỉ dùng bán kính, không dùng góc
        'lkp_max_age': DEFAULT_LKP_MAX_AGE,
        'speed': 3.0,
        'follow_radius': TILESIZE * 2.5,
        'stop_radius': TILESIZE * 2,
        'path_cooldown': 450,
        'path_cooldown_far': 900,
        'graphics': '../graphics/npcs/Demon/',
        'aggro_radius': TILESIZE * 5,
        'health': 100,
        'exp':150,
		'damage':45,
        'attack_radius': TILESIZE * 1.8,
        'attack_cooldown': 800,
        'attack_type': 'thunder',
        'attack_sound':'../audio/attack/fireball.wav',
		'resistance': 4,
        'notice_radius': 300,
        'can_guard_player': False
    }
}