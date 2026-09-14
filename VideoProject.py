import math
import random
import sys
import cv2
import mediapipe as mp
import pygame

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands = 2,
    min_detection_confidence = 0.5,
    min_tracking_confidence = 0.5
)

pygame.init()
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("green lantern sim")
clock = pygame.time.Clock()

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

RING_GLOW = (0, 255, 128)
RING_BRIGHT = (180, 255, 200)

RING_GLOW = (0, 255, 128)
RING_BRIGHT = (180, 255, 200)

class Construct:
    def __init__(self, shape_type, x, y):
        self.shape_type = shape_type  
        self.x = x
        self.y = y
        self.size = 70.0
        self.angle = 0.0
        
        
        self.points = []
        self.bbox = pygame.Rect(x, y, 1, 1) 

    def add_point(self, x, y):
        """Adds a point to the free-draw path and expands the bounding box."""
        if not self.points:
            self.bbox = pygame.Rect(x, y, 1, 1)
        self.points.append((x, y))
       
        self.bbox.left = min(self.bbox.left, x)
        self.bbox.top = min(self.bbox.top, y)
        self.bbox.right = max(self.bbox.right, x)
        self.bbox.bottom = max(self.bbox.bottom, y)

    def set_position(self, x, y):
        """Moves the entire freedraw construct by moving the points relative to the new center."""
        if self.shape_type == "freedraw" and self.points:
            
            avg_x = sum(p[0] for p in self.points) / len(self.points)
            avg_y = sum(p[1] for p in self.points) / len(self.points)
            
            
            dx, dy = x - avg_x, y - avg_y
            
            
            self.points = [(p[0] + dx, p[1] + dy) for p in self.points]
            self.bbox.move_ip(dx, dy)
            self.x, self.y = x, y # Update stored center
        else:
            self.x, self.y = x, y

    def draw(self, surface):
        glow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        if self.shape_type == "freedraw":
            if len(self.points) > 1:
                
                pygame.draw.lines(glow_surf, (0, 255, 120, 60), False, self.points, width=12)
                pygame.draw.lines(surface, RING_GLOW, False, self.points, width=4)
                pygame.draw.lines(surface, RING_BRIGHT, False, self.points, width=2)
                
                
                pygame.draw.circle(surface, RING_BRIGHT, (int(self.x), int(self.y)), 6)

        elif self.shape_type == "circle":
            r = int(self.size)
            pygame.draw.circle(glow_surf, (0, 255, 120, 50), (int(self.x), int(self.y)), r + 12, width=8)
            pygame.draw.circle(surface, RING_GLOW, (int(self.x), int(self.y)), r, width=3)
            pygame.draw.circle(surface, RING_BRIGHT, (int(self.x), int(self.y)), max(4, int(r * 0.35)), width=2)

        elif self.shape_type == "triangle":
            pts = []
            for i in range(3):
                theta = self.angle + (i * 2 * math.pi / 3)
                pts.append((self.x + math.cos(theta) * self.size, self.y + math.sin(theta) * self.size))
            pygame.draw.polygon(glow_surf, (0, 255, 120, 50), pts, width=10)
            pygame.draw.polygon(surface, RING_GLOW, pts, width=3)
            for p in pts:
                pygame.draw.circle(surface, RING_BRIGHT, (int(p[0]), int(p[1])), 4)

        elif self.shape_type == "rectangle":
            pts = []
            w, h = self.size * 1.3, self.size * 0.8
            corners = [(-w, -h), (w, -h), (w, h), (-w, h)]
            for cx, cy in corners:
                rx = cx * math.cos(self.angle) - cy * math.sin(self.angle)
                ry = cx * math.sin(self.angle) + cy * math.cos(self.angle)
                pts.append((self.x + rx, self.y + ry))
            pygame.draw.polygon(glow_surf, (0, 255, 120, 50), pts, width=10)
            pygame.draw.polygon(surface, RING_GLOW, pts, width=3)
            for p in pts:
                pygame.draw.circle(surface, RING_BRIGHT, (int(p[0]), int(p[1])), 4)

        surface.blit(glow_surf, (0, 0))

def count_extended_fingers(landmarks):
    tips = [
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP,
    ]
    pips = [
        mp_hands.HandLandmark.INDEX_FINGER_PIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
        mp_hands.HandLandmark.RING_FINGER_PIP,
        mp_hands.HandLandmark.PINKY_PIP,
    ]
    return sum(1 for tip, pip in zip(tips, pips) if landmarks.landmark[tip].y < landmarks.landmark[pip].y)

constructs = []
gesture_timers = {}
last_gestures = {}

scaling_construct = None
initial_pinch_dist = None
initial_construct_size = None
dragged_by_hand = {}

active_freedraw_by_hand = {}

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            constructs.clear()

    ret, frame = cap.read()
    if not ret:
        continue

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    frame_surface = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
    screen.blit(frame_surface, (0, 0))

    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(100)
    overlay.fill((0, 20, 10))
    screen.blit(overlay, (0, 0))

    hands_data = []

    if results.multi_hand_landmarks:
        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

            tx, ty = int(thumb.x * WIDTH), int(thumb.y * HEIGHT)
            ix, iy = int(index.x * WIDTH), int(index.y * HEIGHT)
            pos = ((tx + ix) // 2, (ty + iy) // 2)

            pinch_dist = math.hypot(tx - ix, ty - iy)
            is_pinching = pinch_dist < 42
            fingers = count_extended_fingers(hand_landmarks)

            pygame.draw.line(screen, RING_GLOW, (tx, ty), (ix, iy), 2)
            pygame.draw.circle(screen, RING_BRIGHT, pos, 7)

            hands_data.append({
                "id": idx,
                "pos": pos,
                "pinching": is_pinching,
                "fingers": fingers
            })

   
    pinching_hands = [h for h in hands_data if h["pinching"]]

    # 2. Release constructs if a hand stops pinching
    for hand_id in list(dragged_by_hand.keys()):
        if not any(h["id"] == hand_id for h in pinching_hands):
            del dragged_by_hand[hand_id]

    # 3. Two-handed stretch / resize logic
    two_hand_pinch = len(pinching_hands) == 2

    if two_hand_pinch:
        p1 = pinching_hands[0]["pos"]
        p2 = pinching_hands[1]["pos"]
        current_hands_dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
        midpoint = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)

        pygame.draw.line(screen, (150, 255, 200), p1, p2, 2)

        if scaling_construct is None:
            for c in reversed(constructs):
                d_mid = math.hypot(c.x - midpoint[0], c.y - midpoint[1])
                grabbed_stretch = False
                if c.shape_type == "freedraw":
                    if c.bbox.collidepoint(midpoint):
                        grabbed_stretch = True
                else:
                    if d_mid < c.size + 80:
                        grabbed_stretch = True

                if grabbed_stretch:
                    scaling_construct = c
                    initial_pinch_dist = max(current_hands_dist, 10.0)
                    initial_construct_size = c.size
                    break

        if scaling_construct:
            ratio = current_hands_dist / initial_pinch_dist
            scaling_construct.size = max(20.0, min(400.0, initial_construct_size * ratio))
            scaling_construct.set_position(midpoint[0], midpoint[1])
            scaling_construct.angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])

        dragged_by_hand.clear()

    else:
        scaling_construct = None
        initial_pinch_dist = None

        # 4. Process pinching hands (Dragging or Free Draw)
        for hand in pinching_hands:
            hid = hand["id"]
            hx, hy = hand["pos"]
            fingers = hand["fingers"]

            if fingers == 1:
                # 1 Finger pinch = Free Draw
                if hid in dragged_by_hand:
                    del dragged_by_hand[hid]

                if hid not in active_freedraw_by_hand:
                    new_draw = Construct("freedraw", hx, hy)
                    constructs.append(new_draw)
                    active_freedraw_by_hand[hid] = new_draw
                    new_draw.add_point(hx, hy)
                else:
                    active_freedraw_by_hand[hid].add_point(hx, hy)

            else:
                # Other finger pinch = Grab & Move
                if hid in active_freedraw_by_hand:
                    del active_freedraw_by_hand[hid]

                if hid not in dragged_by_hand:
                    for c in reversed(constructs):
                        if c not in dragged_by_hand.values():
                            grabbed = False
                            if c.shape_type == "freedraw":
                                if c.bbox.inflate(30, 30).collidepoint(hx, hy):
                                    grabbed = True
                            else:
                                if math.hypot(c.x - hx, c.y - hy) < c.size + 25:
                                    grabbed = True

                            if grabbed:
                                dragged_by_hand[hid] = c
                                break

                if hid in dragged_by_hand:
                    dragged_by_hand[hid].set_position(hx, hy)
                    dragged_by_hand[hid].angle += 0.05

        # 5. Process non-pinching hands (Shape Spawning Gestures)
        non_pinching_hands = [h for h in hands_data if not h["pinching"]]
        for hand in non_pinching_hands:
            hid = hand["id"]
            hx, hy = hand["pos"]
            fingers = hand["fingers"]

            if hid in active_freedraw_by_hand:
                del active_freedraw_by_hand[hid]
            if hid in dragged_by_hand:
                del dragged_by_hand[hid]

            if hid not in gesture_timers:
                gesture_timers[hid] = 0
                last_gestures[hid] = fingers

            if last_gestures[hid] == fingers:
                gesture_timers[hid] += 1
            else:
                last_gestures[hid] = fingers
                gesture_timers[hid] = 0

            # Hold pose for ~0.25s (15 frames) to trigger action
            if gesture_timers[hid] == 15:
                if fingers == 0:
                    constructs.clear()
                elif fingers == 2:
                    constructs.append(Construct("rectangle", hx, hy))
                elif fingers == 3:
                    constructs.append(Construct("circle", hx, hy))
                elif fingers == 4:
                    constructs.append(Construct("triangle", hx, hy))

    active_manipulations = list(dragged_by_hand.values())
    active_manipulations.extend(list(active_freedraw_by_hand.values()))
    if scaling_construct:
        active_manipulations.append(scaling_construct)

    for c in constructs:
        if c not in active_manipulations:
            c.angle += 0.005
        c.draw(screen)

    pygame.display.flip()
    clock.tick(60)

cap.release()
pygame.quit()
sys.exit()