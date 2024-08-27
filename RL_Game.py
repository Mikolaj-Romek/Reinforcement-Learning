import pygame
import random
import os
import time
import math
import json
import glob
import sys

# Initialize Pygame
pygame.init()

# Screen setup
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 400
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("RL Game")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Game variables
FPS = 60
GRAVITY = 0.8
JUMP_STRENGTH = -15

class Character(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 30, 50)
        self.vel_y = 0
        self.jumping = False
        self.falling = False

    def move(self, dx):
        self.rect.x += dx

    def jump(self):
        if not self.jumping and not self.falling:
            self.vel_y = JUMP_STRENGTH
            self.jumping = True
            return True
        return False

    def update(self):
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y

        if self.rect.bottom > SCREEN_HEIGHT - 50:  # Floor collision
            self.rect.bottom = SCREEN_HEIGHT - 50
            self.jumping = False
            self.falling = False
            self.vel_y = 0

class Player(Character):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.health = 100
        self.max_health = self.health
        self.speed = 5
        self.animation_list = []
        self.action = 0  # 0: Idle, 1: Run, 2: Jump, 3: Death, 4: Attack, 5: Fall, 6: Hurt
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        self.attacking = False
        self.attack_cooldown = 0
        self.facing_right = True
        self.alive = True
        self.hit_timer = 0
        self.knockback_speed = 0
        animation_types = ["Idle", "Run", "Jump", "Death", "Attack", "Fall", "Hurt"]
        for animation in animation_types:
            temp_list = []
            num_of_frames = len(os.listdir(f"img/player/{animation}"))
            for i in range(num_of_frames):
                img = pygame.image.load(f"img/player/{animation}/{i}.png").convert_alpha()
                img = pygame.transform.scale(img, (int(img.get_width() * 2), int(img.get_height() * 2)))
                temp_list.append(img)
            self.animation_list.append(temp_list)
        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)

    def update(self):
        if self.alive:
            super().update()
            self.update_animation()
            if self.attack_cooldown > 0:
                self.attack_cooldown -= 1
            
            if self.hit_timer > 0:
                self.hit_timer -= 1
                self.rect.x += self.knockback_speed
                self.knockback_speed *= 0.9  # Decelerate the knockback
            
            if not self.jumping and not self.falling and self.hit_timer == 0:
                if self.action in [2, 5, 6]:  # If was jumping, falling, or hurt
                    self.update_action(0)  # Set to Idle when landing or recovering
            elif self.vel_y > 0 and not self.falling:
                self.falling = True
                self.update_action(5)  # Set to Fall animation
        else:
            # If not alive, only update the death animation
            self.update_death_animation()

    def update_animation(self):
        ANIMATION_COOLDOWN = 100
        self.image = self.animation_list[self.action][self.frame_index]
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        
        if pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
        if self.frame_index >= len(self.animation_list[self.action]):
            if self.action == 4:  # Attack animation finished
                self.attacking = False
                self.update_action(0)  # Set to Idle after attack
            elif self.action in [2, 5]:  # For jump and fall animations, stay on last frame
                self.frame_index = len(self.animation_list[self.action]) - 1
            elif self.action == 6:  # Hurt animation finished
                self.update_action(0)  # Set to Idle after hurt
            else:
                self.frame_index = 0

    def update_death_animation(self):
        ANIMATION_COOLDOWN = 150  # Slower animation for death
        self.image = self.animation_list[3][self.frame_index]  # 3 is the index for Death animation
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        
        if pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            if self.frame_index < len(self.animation_list[3]) - 1:
                self.frame_index += 1

    def move(self, dx):
        if self.alive and not self.attacking and self.hit_timer == 0:  # Only move if alive and not attacking or hurt
            super().move(dx)
            if dx != 0:
                self.facing_right = dx > 0
                if not self.jumping and not self.falling:
                    self.update_action(1)  # Set to Run animation only if on the ground
            elif not self.jumping and not self.falling:
                self.update_action(0)  # Set to Idle animation if on the ground and not moving

    def jump(self):
        if self.alive and super().jump():
            self.update_action(2)  # Set to Jump animation
            return True
        return False

    def attack(self):
        if self.alive and self.attack_cooldown == 0 and not self.attacking and not self.jumping and not self.falling and self.hit_timer == 0:
            self.attacking = True
            self.attack_cooldown = 20
            self.update_action(4)  # Set to Attack animation
            return True
        return False

    def update_action(self, new_action):
        if self.alive and new_action != self.action:
            self.action = new_action
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def take_damage(self, amount, knockback_direction):
        if self.alive:
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.alive = False
                self.update_action(3)  # Set to Death animation
                self.frame_index = 0  # Start death animation from the beginning
            else:
                self.hit_timer = 30  # 0.5 seconds at 60 FPS
                self.knockback_speed = knockback_direction * 5  # Adjust for desired knockback strength
                self.update_action(6)  # Set to Hurt animation
                self.attacking = False  # Reset attacking state when hit
                self.attack_cooldown = 0  # Reset attack cooldown when hit

class Arrow(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        self.image = pygame.image.load("img/archer/arrow/0.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (int(self.image.get_width() * 1.5), int(self.image.get_height() * 1.5)))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 6
        self.direction = direction
        self.vel_y = 0
        self.angle = 0
        self.stopped = False

    def update(self):
        if not self.stopped:
            self.vel_y += GRAVITY * 0.05
            self.rect.x += self.speed * self.direction
            self.rect.y += self.vel_y
            
            # Rotate arrow based on trajectory
            self.angle = -math.atan2(self.vel_y, self.speed * self.direction)
            rotated_image = pygame.transform.rotate(pygame.image.load("img/archer/arrow/0.png").convert_alpha(), math.degrees(self.angle))
            self.image = pygame.transform.scale(rotated_image, (int(rotated_image.get_width() * 1.5), int(rotated_image.get_height() * 1.5)))

            # Check if arrow hits the ground
            if self.rect.bottom >= SCREEN_HEIGHT - 60:
                self.rect.bottom = SCREEN_HEIGHT - 60
                self.stopped = True

        # Remove arrow if it goes off-screen horizontally
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()

class Enemy(Character):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.health = 50
        self.max_health = self.health
        self.previous_health = self.health
        self.speed = 5
        self.direction = 1
        self.animation_list = []
        self.action = 0  # 0: Idle, 1: Run, 2: Death, 3: Attack
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        self.alive = True
        self.death_timer = time.time()
        self.vertical_offset = 24
        self.flash_timer = 0
        self.attack_cooldown = 0
        self.arrow_group = pygame.sprite.Group()
        self.attacking = False
        self.attack_frame = 0
        self.invulnerable_timer = 0
        self.invulnerable_duration = 60  # 1 second at 60 FPS
        self.just_attacked = False
        self.death_penalty_applied = False
        
        animation_types = ["Idle", "Run", "Death", "Attack"]
        for animation in animation_types:
            temp_list = []
            num_of_frames = len(os.listdir(f"img/archer/{animation}"))
            for i in range(num_of_frames):
                img = pygame.image.load(f"img/archer/{animation}/{i}.png").convert_alpha()
                img = pygame.transform.scale(img, (int(img.get_width() * 1.5), int(img.get_height() * 1.5)))
                temp_list.append(img)
            self.animation_list.append(temp_list)
        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.x = max(0, min(x, SCREEN_WIDTH - self.rect.width))
        self.rect.bottom = y + self.vertical_offset
        
        self.sarsa = SARSA()
        self.previous_state = None
        self.previous_action = None
        self.episode_steps = 0
        self.total_reward = 0

    def get_state(self, player):
        dx = player.rect.x - self.rect.x
        dy = player.rect.y - self.rect.y
        
        if abs(dx) <= 40:
            x_state = "melee_range"
        elif abs(dx) <= 80:
            x_state = "close"
        elif abs(dx) <= 120:
            x_state = "medium_close"
        elif abs(dx) <= 160:
            x_state = "medium"
        elif abs(dx) <= 200:
            x_state = "medium_far"
        elif abs(dx) <= 250:
            x_state = "far"
        elif abs(dx) <= 300:
            x_state = "very_far"
        else:
            x_state = "extreme_range"
        
        x_direction = "right" if dx > 0 else "left"
        
        if abs(dy) <= 20:
            y_state = "same_level"
        elif -60 < dy <= -20:
            y_state = "slightly_above"
        elif dy <= -60:
            y_state = "far_above"
        elif 20 < dy <= 60:
            y_state = "slightly_below"
        else:
            y_state = "far_below"
        
        enemy_health = "high" if self.health > 35 else ("medium" if self.health > 15 else "low")
        player_health = "high" if player.health > 66 else ("medium" if player.health > 33 else "low")
        
        current_action = ["idle", "run", "death", "attack"][self.action]
        
        facing_player = "facing_player" if (self.direction == 1 and dx > 0) or (self.direction == -1 and dx < 0) else "not_facing_player"
        
        attack_ready = "attack_ready" if self.attack_cooldown == 0 else "attack_cooldown"

        return f"{x_state}_{x_direction}_{y_state}_{enemy_health}_{player_health}_{current_action}_{facing_player}_{attack_ready}"

    def update_animation(self):
        ANIMATION_COOLDOWN = 100
        max_frames = len(self.animation_list[self.action])
        self.frame_index = min(self.frame_index, max_frames - 1)
        
        self.image = self.animation_list[self.action][self.frame_index]
        if self.direction == -1:
            self.image = pygame.transform.flip(self.image, True, False)
        
        if self.flash_timer > 0 and self.flash_timer % 4 < 2:
            self.image = self.image.copy()
            self.image.fill((255, 255, 255, 128), special_flags=pygame.BLEND_RGBA_MULT)
        elif self.invulnerable_timer > 0 and self.invulnerable_timer % 4 < 2:
            self.image = self.image.copy()
            self.image.fill((200, 200, 255, 128), special_flags=pygame.BLEND_RGBA_MULT)
        
        if self.attacking:
            self.frame_index = self.attack_frame
        elif pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
            if self.frame_index >= max_frames:
                if self.action == 2:
                    self.frame_index = max_frames - 1
                elif self.action == 3:
                    self.frame_index = 0
                    self.update_action(0)
                else:
                    self.frame_index = 0

    def update_action(self, new_action):
        if new_action != self.action:
            self.action = new_action
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def update(self, player):
        self.update_animation()
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        
        if self.alive:
            current_state = self.get_state(player)
            action = self.sarsa.get_action(current_state)
            self.act(action)

            hit_player, killed_player = self.check_arrow_hit(player)
            reward = self.get_reward(player, hit_player, killed_player)
            self.total_reward += reward

            next_state = self.get_state(player)
            next_action = self.sarsa.get_action(next_state)

            if self.previous_state is not None and self.previous_action is not None:
                self.sarsa.update_q_table(self.previous_state, self.previous_action, reward, current_state, action)

            self.previous_state = current_state
            self.previous_action = action

            self.episode_steps += 1

        if self.flash_timer > 0:
            self.flash_timer -= 1

        if self.attacking:
            self.attack_frame += 1
            if self.attack_frame >= len(self.animation_list[3]):
                self.attacking = False
                self.attack_frame = 0
                self.shoot_arrow()

        self.arrow_group.update()

    def move_ai(self):
        if self.alive and not self.attacking:
            new_x = self.rect.x + self.direction * self.speed
            
            if 0 < new_x < SCREEN_WIDTH - self.rect.width:
                self.rect.x = new_x
            else:
                self.direction *= -1
            
            self.update_action(1)

    def attack(self):
        if self.attack_cooldown == 0 and self.alive and not self.attacking:
            self.attacking = True
            self.attack_frame = 0
            self.attack_cooldown = 180
            self.update_action(3)
            self.just_attacked = True
            return True
        return False

    def shoot_arrow(self):
        arrow_x = self.rect.centerx + (50 * self.direction)
        arrow_y = self.rect.centery - 10
        new_arrow = Arrow(arrow_x, arrow_y, self.direction)
        self.arrow_group.add(new_arrow)

    def take_damage(self, amount, knockback_direction):
        if self.alive and self.invulnerable_timer == 0:
            self.health -= amount
            self.flash_timer = 30
            self.update_action(0)
            self.invulnerable_timer = self.invulnerable_duration
            if self.health <= 0:
                self.health = 0
                self.alive = False
                self.update_action(2)

    def draw_arrows(self, surface):
        self.arrow_group.draw(surface)

    def act(self, action):
        if action == 'move_left':
            self.direction = -1
            self.move_ai()
        elif action == 'move_right':
            self.direction = 1
            self.move_ai()
        elif action == 'shoot':
            self.attack()

    def get_reward(self, player, hit_player, killed_player):
        reward = 0
        if self.health < self.previous_health:
            reward -= 20
        if hit_player:
            reward += 30
        if killed_player:
            reward += 100
        if self.just_attacked:
            reward += 2
            self.just_attacked = False
        
        # Apply death penalty only once
        if self.health <= 0 and not self.death_penalty_applied:
            reward -= 50
            self.death_penalty_applied = True

        

        self.previous_health = self.health
        return reward

    def check_arrow_hit(self, player):
        hit_player = False
        killed_player = False
        for arrow in self.arrow_group:
            if player.alive and not arrow.stopped and arrow.rect.colliderect(player.rect):
                knockback_direction = 1 if arrow.direction > 0 else -1
                player.take_damage(5, knockback_direction)
                arrow.kill()
                hit_player = True
                if not player.alive:
                    killed_player = True
                break
        return hit_player, killed_player

    def reset(self):
        self.health = self.max_health
        self.previous_health = self.health
        self.rect.x = 500
        self.rect.bottom = SCREEN_HEIGHT - 50 + self.vertical_offset
        self.alive = True
        self.action = 0
        self.frame_index = 0
        self.arrow_group.empty()
        self.attacking = False
        self.attack_frame = 0
        self.flash_timer = 0
        self.attack_cooldown = 0
        self.episode_steps = 0
        self.total_reward = 0
        self.previous_state = None
        self.previous_action = None
        self.invulnerable_timer = 0
        self.just_attacked = False
        self.death_penalty_applied = False 
        
        
    def end_episode(self):
        self.sarsa.end_episode()
        print(f"Episode {self.sarsa.episode_count} ended. Steps: {self.episode_steps}, Total Reward: {self.total_reward}")
        print(f"Epsilon: {self.sarsa.epsilon:.4f}, Alpha: {self.sarsa.alpha:.4f}")
        self.episode_steps = 0
        self.total_reward = 0
        
        
class AIPlayer(Player):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.decision_cooldown = 0
        self.attack_idle_time = 0
        self.has_hit_enemy = False  # New attribute to track if the current attack has hit the enemy

    def make_decision(self, enemy):
        if self.attack_idle_time > 0:
            self.attack_idle_time -= 1
            return

        if self.decision_cooldown > 0:
            self.decision_cooldown -= 1
            return

        dx = enemy.rect.centerx - self.rect.centerx

        # Move towards the enemy
        if abs(dx) > 50:  # Approach until we're in attack range
            if dx > 0:
                self.move(self.speed)
            else:
                self.move(-self.speed)
        else:
            # If in range, attack
            if random.random() < 0.8:  # 80% chance to attack when in range
                if self.attack():  # Only set idle time if attack was successful
                    self.attack_idle_time = 30  # 0.5 seconds at 60 FPS
            else:
                # Sometimes move slightly away to avoid getting hit
                self.move(-self.speed if dx > 0 else self.speed)

        self.decision_cooldown = 3  # Wait 3 frames before next decision

    def update(self, enemy):
        super().update()
        self.make_decision(enemy)

        # Check for attack hitting enemy
        if self.attacking and not self.has_hit_enemy:
            if (abs(self.rect.centerx - enemy.rect.centerx) < 50 and
                abs(self.rect.centery - enemy.rect.centery) < 50):
                knockback_direction = 1 if self.facing_right else -1
                enemy.take_damage(5, knockback_direction)
                self.has_hit_enemy = True

        # Reset has_hit_enemy when attack animation ends
        if not self.attacking:
            self.has_hit_enemy = False

    def move(self, dx):
        # Override the move method to use the full player speed
        if self.alive and not self.attacking and self.hit_timer == 0:
            self.rect.x += dx
            self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))  # Keep player within screen bounds
            if dx != 0:
                self.facing_right = dx > 0
                if not self.jumping and not self.falling:
                    self.update_action(1)  # Set to Run animation
            elif not self.jumping and not self.falling:
                self.update_action(0)  # Set to Idle animation

    def attack(self):
        if super().attack():  
            self.attack_idle_time = 30  # Set idle time after successful attack
            self.has_hit_enemy = False  # Reset has_hit_enemy at the start of a new attack
            return True
        return False



        
        
        
class SARSA:
    def __init__(self, is_bird=False):
        self.epsilon = 0.90  # Start with 90% exploration
        self.epsilon_decay = 0.99999995  # Slower decay
        self.epsilon_min = 0.01
        self.alpha = 0.1
        self.alpha_decay = 0.99999999  # Learning rate decay
        self.alpha_min = 0.01
        self.gamma = 0.9
        if is_bird:
            self.actions = ['move_up', 'move_down', 'move_left', 'move_right', 
                            'move_up_left', 'move_up_right', 'move_down_left', 'move_down_right', 'stay']
        else:
            self.actions = ['move_left', 'move_right', 'shoot', 'idle']        
        self.q_table = self.load_q_table(is_bird)
        self.episode_count = self.get_latest_episode_count(is_bird)
        self.is_bird = is_bird

    def get_latest_episode_count(self, is_bird):
        folder = 'bird_q_tables' if is_bird else 'q_tables'
        q_table_files = glob.glob(f'{folder}/*.json')
        if not q_table_files:
            return 0
        latest_file = max(q_table_files, key=os.path.getctime)
        return int(latest_file.split('_')[-1].split('.')[0]) + 1

    def load_q_table(self, is_bird):
        folder = 'bird_q_tables' if is_bird else 'q_tables'
        q_table_files = glob.glob(f'{folder}/*.json')
        if not q_table_files:
            return {}
        latest_file = max(q_table_files, key=os.path.getctime)
        with open(latest_file, 'r') as f:
            return json.load(f)

    def save_q_table(self):
        folder = 'bird_q_tables' if self.is_bird else 'q_tables'
        if not os.path.exists(folder):
            os.makedirs(folder)
        filename = f'{folder}/q_table_episode_{self.episode_count}.json'
        with open(filename, 'w') as f:
            json.dump(self.q_table, f, indent=2)
        print(f"Q-table saved as {filename}")
        
        
    def get_action(self, state):
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        
        if random.random() < self.epsilon:
            return random.choice(self.actions)
        else:
            return max(self.q_table[state], key=self.q_table[state].get)

    def update_q_table(self, state, action, reward, next_state, next_action):
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        if next_state not in self.q_table:
            self.q_table[next_state] = {a: 0 for a in self.actions}

        current_q = self.q_table[state][action]
        next_q = self.q_table[next_state][next_action]
        new_q = current_q + self.alpha * (reward + self.gamma * next_q - current_q)
        self.q_table[state][action] = new_q

        # Decay epsilon and alpha
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.epsilon_min)
        #self.alpha = max(self.alpha * self.alpha_decay, self.alpha_min)

    def end_episode(self):
        self.episode_count += 1
        
class SimplePlayer(Player):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.direction = 1
        self.speed = 3

    def update(self):
        super().update()
        self.move(self.direction * self.speed)
        
        # Change direction when reaching screen borders
        if self.rect.left <= 0:
            self.direction = 1
        elif self.rect.right >= SCREEN_WIDTH:
            self.direction = -1

class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.load_animations()
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 2
        self.heal_cooldown = 0
        self.heal_cooldown_max = 300
        self.state = "idle"
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        self.facing_right = True
        
        self.sarsa = SARSA(is_bird=True)
        self.previous_state = None
        self.previous_action = None
        self.total_reward = 0
        
    def load_animations(self):
        self.animations = {
            "idle": self.load_animation("bird"),
            "heal": self.load_animation("heal")
        }
        self.image = self.animations["idle"][0]
        
    def load_animation(self, folder):
        animation = []
        for i in range(len(os.listdir(f"img/{folder}"))):
            img = pygame.image.load(f"img/{folder}/{i}.png").convert_alpha()
            img = pygame.transform.scale(img, (int(img.get_width() * 0.05), int(img.get_height() * 0.05)))
            animation.append(img)
        return animation
        
    def update(self, player):
        self.heal_cooldown = max(0, self.heal_cooldown - 1)
        
        current_state = self.get_state(player)
        action = self.sarsa.get_action(current_state)
        self.perform_action(action)
        
        reward = self.get_reward(player)
        self.total_reward += reward
        next_state = self.get_state(player)
        next_action = self.sarsa.get_action(next_state)

        if self.previous_state is not None and self.previous_action is not None:
            self.sarsa.update_q_table(self.previous_state, self.previous_action, reward, current_state, action)

        self.previous_state = current_state
        self.previous_action = action
        
        self.update_animation()
        
    def get_state(self, player):
        dx = abs(self.rect.centerx - player.rect.centerx)
        dy = abs(self.rect.centery - player.rect.centery)
        
        if dx <= 50 and dy <= 50:
            proximity = "close"
        elif dx <= 150 and dy <= 150:
            proximity = "far"
        else:
            proximity = "very_far"
        
        x_direction = "right" if player.rect.centerx > self.rect.centerx else "left"
        y_direction = "above" if player.rect.centery < self.rect.centery else "below"
        
        return f"{proximity}_{x_direction}_{y_direction}"
        
    def perform_action(self, action):
        dx, dy = 0, 0
        if action == 'move_up': dy = -self.speed
        elif action == 'move_down': dy = self.speed
        elif action == 'move_left': 
            dx = -self.speed
            self.facing_right = False
        elif action == 'move_right': 
            dx = self.speed
            self.facing_right = True
        elif action == 'move_up_left': 
            dx, dy = -self.speed, -self.speed
            self.facing_right = False
        elif action == 'move_up_right': 
            dx, dy = self.speed, -self.speed
            self.facing_right = True
        elif action == 'move_down_left': 
            dx, dy = -self.speed, self.speed
            self.facing_right = False
        elif action == 'move_down_right': 
            dx, dy = self.speed, self.speed
            self.facing_right = True
        
        self.rect.x += dx
        self.rect.y += dy
        
        # Keep bird within screen bounds
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        
    def get_reward(self, player):
        dx = abs(self.rect.centerx - player.rect.centerx)
        dy = abs(self.rect.centery - player.rect.centery)
        if dx <= 50 and dy <= 50:
            return 1
        return 0

    def update_animation(self):
        ANIMATION_COOLDOWN = 100
        self.image = self.animations[self.state][self.frame_index]
        
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        
        if pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
        if self.frame_index >= len(self.animations[self.state]):
            self.frame_index = 0

    def reset(self):
        self.rect.center = (400, SCREEN_HEIGHT - 100)
        self.heal_cooldown = 0
        self.state = "idle"
        self.frame_index = 0
        self.previous_state = None
        self.previous_action = None
        self.total_reward = 0
        self.facing_right = True


def reset_game():
    global player, bird, all_sprites
    player = SimplePlayer(250, SCREEN_HEIGHT - 50)
    bird.reset()
    all_sprites = pygame.sprite.Group(player, bird)

# Create initial bird outside the episode loop
bird = Bird(400, SCREEN_HEIGHT - 100)

# Main training loop
num_episodes = 200000
episode_rewards = []
frames_per_episode = 30 * 60  # 30 seconds at 60 FPS

start_time = time.time()

for episode in range(num_episodes):
    reset_game()
    frame_count = 0
    
    while frame_count < frames_per_episode:
        player.update()
        bird.update(player)

        frame_count += 1

        # Check if episode should end early
        if not player.alive:
            break

    episode_rewards.append(bird.total_reward)
    bird.sarsa.end_episode()
    
    # Print reward and epsilon for every episode
    print(f"Episode {episode + 1}: Reward: {bird.total_reward:.2f}, Epsilon: {bird.sarsa.epsilon:.4f}", flush=True)
    
    # Print more detailed statistics every 100 episodes
    if (episode + 1) % 100 == 0:
        avg_reward = sum(episode_rewards[-100:]) / 100
        print(f"Last 100 Episodes - Average Reward: {avg_reward:.2f}", flush=True)
        print(f"Alpha: {bird.sarsa.alpha:.4f}", flush=True)
        print(f"Time elapsed: {(time.time() - start_time) / 60:.2f} minutes", flush=True)
        print("-" * 50)  # Separator for readability

    # Save Q-table every 1000 episodes
    if (episode + 1) % 1000 == 0:
        bird.sarsa.save_q_table()

print("Training complete")

# Print final statistics
print("\nFinal Statistics:")
avg_reward = sum(episode_rewards[-1000:]) / 1000
print(f"Final 1000 Episodes: Average Reward: {avg_reward:.2f}")
print(f"Final Epsilon: {bird.sarsa.epsilon:.4f}")

# Save the final Q-table
bird.sarsa.save_q_table()

total_time = (time.time() - start_time) / 60
print(f"\nTotal training time: {total_time:.2f} minutes")