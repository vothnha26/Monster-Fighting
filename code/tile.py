import pygame
from settings import *

class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, groups, sprite_type, surface=pygame.Surface((TILESIZE,TILESIZE)), hitbox_inflation=(0, None)):
        super().__init__(groups)
        self.sprite_type = sprite_type
        self.image = surface

        if sprite_type == 'object':
            self.rect = self.image.get_rect(topleft=(pos[0], pos[1] - (self.image.get_height() - TILESIZE)))
        else:
            self.rect = self.image.get_rect(topleft=pos)

        default_y_offset = HITBOX_OFFSET.get(sprite_type, 0)
        inflate_x = hitbox_inflation[0]
        inflate_y = hitbox_inflation[1] if hitbox_inflation[1] is not None else default_y_offset

        self.hitbox = self.rect.inflate(inflate_x, inflate_y)

        if self.hitbox.width < 1: self.hitbox.width = 1
        if self.hitbox.height < 1: self.hitbox.height = 1