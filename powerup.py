# powerup.py

import pygame

class PowerItem:

    def __init__(

        self,

        x,
        y,

        item_type,

        image

    ):

        self.type = item_type

        self.image = image

        self.rect = self.image.get_rect(
            center=(x,y)
        )

        self.speed = 4

    # ==================================
    # UPDATE
    # ==================================

    def update(self):

        self.rect.x -= self.speed

    # ==================================
    # DRAW
    # ==================================

    def draw(self,screen):

        screen.blit(

            self.image,

            self.rect

        )