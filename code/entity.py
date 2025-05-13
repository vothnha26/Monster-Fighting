# 
import pygame
from math import sin

class Entity(pygame.sprite.Sprite):
	def __init__(self,groups):
		super().__init__(groups)
		self.frame_index = 0
		self.animation_speed = 0.15
		self.direction = pygame.math.Vector2()
		# ## ADDED FOR NPC/ENEMY - make sure obstacle_sprites is set in subclasses
		if not hasattr(self, 'obstacle_sprites'):
			self.obstacle_sprites = pygame.sprite.Group()


	def move(self,speed):
		if self.direction.magnitude() != 0:
			self.direction = self.direction.normalize()

		self.hitbox.x += self.direction.x * speed
		self.collision('horizontal')
		self.hitbox.y += self.direction.y * speed
		self.collision('vertical')
		self.rect.center = self.hitbox.center

	def collision(self,direction_axis):
		# ## MODIFIED for better sliding ##
		if direction_axis == 'horizontal':
			for sprite in self.obstacle_sprites:
				if hasattr(sprite, 'hitbox') and sprite.hitbox.colliderect(self.hitbox):
					if self.direction.x > 0: # moving right
						self.hitbox.right = sprite.hitbox.left
					if self.direction.x < 0: # moving left
						self.hitbox.left = sprite.hitbox.right

		if direction_axis == 'vertical':
			for sprite in self.obstacle_sprites:
				if hasattr(sprite, 'hitbox') and sprite.hitbox.colliderect(self.hitbox):
					if self.direction.y > 0: # moving down
						self.hitbox.bottom = sprite.hitbox.top
					if self.direction.y < 0: # moving up
						self.hitbox.top = sprite.hitbox.bottom

	def wave_value(self):
		value = sin(pygame.time.get_ticks()) # Original was sin(pygame.time.get_ticks())
		# A slightly different wave for invincibility flicker
		# value = sin(pygame.time.get_ticks() / 200.0) # Using this from NPC
		if value >= 0:
			return 255
		else:
			# Return a lower alpha value for flicker to be more visible than 0
			return 64 # Or 0 if you prefer complete disappearance