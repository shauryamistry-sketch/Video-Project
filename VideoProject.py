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
    min_detection_confidence = 0.6,
    min_tracking_confidence = 0.6,
)

pygame.init()
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("green lantern sim")
clock = pygame.time.Clock()

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    cap.release()
    cap = cv2.VideoCapture(1)

if not cap.isOpened():
    raise RuntimeError("Could not open webcam.")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

RING_GLOW = (0, 255, 128)
RING_BRIGHT = (180, 255, 200)

PINCH_THRESHOLD_PX = 30
GESTURE_HOLD_FRAMES = 15

class Construct:
    def __init__(self, shape_type, x, y):
        self.shape_type = shape_type  
        self.x = x
        self.y = y
        self.size = 70.0
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.points = []
        self.bbox = pygame.Rect(int(x), int(y), 1, 1) 

    def add_point(self, x, y):
        
        self.points.append((x, y))
        if len(self.points) == 1:
            self.bbox = pygame.Rect(int(x), int(y), 1, 1)
        else:
            xs = [p[0] for p in self.points]
            ys = [p[1] for p in self.points]
            left, top = int(min(xs)), int(min(ys))
            right, bottom = int(max(xs)), int(max(ys))
            self.bbox = pygame.Rect(left, top, right - left+1, bottom-top+1)

    def set_position(self, x, y):
        
        if self.shape_type == "freedraw" and self.points:
            
            avg_x = sum(p[0] for p in self.points) / len(self.points)
            avg_y = sum(p[1] for p in self.points) / len(self.points)
            
            
            dx, dy = x - avg_x, y - avg_y
            
            
            self.points = [(p[0] + dx, p[1] + dy) for p in self.points]

            xs = [p[0] for p in self.points]
            ys = [p[1] for p in self.points]

            self.bbox = pygame.Rect(
                int(min(xs)),
                int(min(ys)),
                int(max(xs) - min(xs) + 1),
                int(max(ys) - min(ys) + 1)
            )

            self.x, self.y = x, y
        else:
            self.x, self.y = x, y

    def duplicate(self):
        new_construct = Construct(
            self.shape_type,
            self.x + 40,
            self.y + 40
        )
        new_construct.size = self.size
        new_construct.angle = self.angle
        new_construct.vx = 0.0
        new_construct.vy = 0.0

        if self.shape_type == "freedraw":
            new_construct.points = [
                (x + 40, y + 40)
                for x, y in self.points
            ]

            xs = [p[0] for p in new_construct.points]
            ys = [p[1] for p in new_construct.points]

            new_construct.bbox = pygame.Rect(
                int(min(xs)),
                int(min(ys)),
                int(max(xs) - min(xs) + 1),
                int(max(ys) - min(ys) + 1)
                )
            
        return new_construct

    def scale_from(self, anchor, factor):
        if self.shape_type == "freedraw" and self.points:
            cx, cy = anchor
            self.points = [((p[0] - cx) * factor + cx,
                            (p[1]-cy) * factor + cy) for p in self.points]
            xs = [p[0] for p in self.points]
            ys = [p[1] for p in self.points]
            left, top = int(min(xs)), int(min(ys))
            right, bottom = int(max(xs)), int(max(ys))
            self.bbox = pygame.Rect(left, top, right-left+1, bottom-top+1)

            self.x = sum(xs)/len(xs)
            self.y = sum(ys)/len(ys)
        else:
            self.size = max(20.0, min(400.0, self.size*factor))

    def draw(self, surface, glow_surf):
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
            pts = [(self.x + math.cos(self.angle+ i*2*math.pi / 3) * self.size, self.y + math.sin(self.angle + i * 2 * math.pi / 3) * self.size)
                   for i in range(3)]
            pygame.draw.polygon(glow_surf, (0, 255, 120, 50), pts, width=10)
            pygame.draw.polygon(surface, RING_GLOW, pts, width=3)
            for p in pts:
                pygame.draw.circle(surface, RING_BRIGHT, (int(p[0]), int(p[1])), 4)

        elif self.shape_type == "rectangle":
            w, h = self.size * 1.3, self.size * 0.8
            pts = []
            corners = [(-w, -h), (w, -h), (w, h), (-w, h)]
            for cx, cy in corners:
                rx = cx * math.cos(self.angle) - cy * math.sin(self.angle)
                ry = cx * math.sin(self.angle) + cy * math.cos(self.angle)
                pts.append((self.x + rx, self.y + ry))
            pygame.draw.polygon(glow_surf, (0, 255, 120, 50), pts, width=10)
            pygame.draw.polygon(surface, RING_GLOW, pts, width=3)
            for p in pts:
                pygame.draw.circle(surface, RING_BRIGHT, (int(p[0]), int(p[1])), 4)

        elif self.shape_type == "pentagon":
            pts = [(self.x + math.cos(self.angle + i * 2 * math.pi / 5 - math.pi/2) * self.size, self.y + math.sin(self.angle + i * 2 * math.pi / 5 - math.pi/2) * self.size) for i in range(5)]
            pygame.draw.polygon(glow_surf, (0, 255 , 120, 50), pts, width=10)
            pygame.draw.polygon(surface, RING_GLOW, pts, width=3)
            for p in pts:
                pygame.draw.circle(surface, RING_BRIGHT, (int(p[0]), int(p[1])), 4)

_TIPS = [
    mp_hands.HandLandmark.INDEX_FINGER_TIP,
    mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
    mp_hands.HandLandmark.RING_FINGER_TIP,
    mp_hands.HandLandmark.PINKY_TIP,
]
_PIPS = [
    mp_hands.HandLandmark.INDEX_FINGER_PIP,
    mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
    mp_hands.HandLandmark.RING_FINGER_PIP,
    mp_hands.HandLandmark.PINKY_PIP,
]

def thumb_is_extended(landmarks):
    thumb_tip = landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    thumb_mcp = landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]
    index_mcp = landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
    pinky_mcp = landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]

    vx = index_mcp.x - pinky_mcp.x
    vy = index_mcp.y - pinky_mcp.y
    mag = math.hypot(vx, vy)
    if mag < 1e-6:
        return False
    vx /= mag
    vy /= mag
    return(thumb_tip.x * vx + thumb_tip.y*vy) > (thumb_mcp.x * vx + thumb_mcp.y * vy)

def count_extended_fingers(landmarks):
    count = sum(1 for tip, pip in zip(_TIPS, _PIPS)
                if landmarks.landmark[tip].y < landmarks.landmark[pip].y)
    if count == 4 and thumb_is_extended(landmarks):
        return 5
    return count

def all_non_thumb_fingers_curled(landmarks):
    return all(landmarks.landmark[tip].y > landmarks.landmark[pip].y
               for tip, pip in zip(_TIPS, _PIPS))

constructs = []
gesture_timers = {}
last_gestures = {}
was_pinching = {}

scaling_construct = None
initial_pinch_dist = None
initial_pinch_midpoint = None
initial_construct_size = None
initial_construct_points = None
selected_construct = None
dragged_by_hand = {}
active_freedraw_by_hand = {}
last_hand_positions = {}

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            constructs.clear()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_d:
            if selected_construct is not None:
                selected_construct = selected_construct.duplicate()
                constructs.append(selected_construct)

    ret, frame = cap.read()
    if not ret:
        print("Could not read frame from webcam.")
        running = False
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

    glow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    hands_data = []

    if results.multi_hand_landmarks:
        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

            tx, ty = int(thumb.x * WIDTH), int(thumb.y * HEIGHT)
            ix, iy = int(index.x * WIDTH), int(index.y * HEIGHT)
            pos = ((tx + ix) // 2, (ty + iy) // 2)

            pinch_dist = math.hypot(tx - ix, ty - iy)
            all_curled = all_non_thumb_fingers_curled(hand_landmarks)
            thumb_out = thumb_is_extended(hand_landmarks)
            is_fist = all_curled and not thumb_out
            is_pinching = pinch_dist < PINCH_THRESHOLD_PX and not is_fist
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

    
    for hand_id in list(dragged_by_hand.keys()):
        if not any(h["id"] == hand_id for h in pinching_hands):
            del dragged_by_hand[hand_id]

   
    if len(pinching_hands) == 2:
            p1 = pinching_hands[0]["pos"]
            p2 = pinching_hands[1]["pos"]
            current_hands_dist = math.hypot(p1[0] - p2[0], p1[1]-p2[1])
            midpoint = ((p1[0] + p2[0])//2, (p1[1] + p2[1])//2)

            pygame.draw.line(screen, (150, 255, 200), p1, p2, 2)

            if scaling_construct is None:
                for c in reversed(constructs):
                    grabbed_stretch = False
                    if c.shape_type == "freedraw":
                        grabbed_stretch = c.bbox.inflate(80, 80).collidepoint(midpoint)
                    else:
                        if math.hypot(c.x - midpoint[0], c.y - midpoint[1]) < c.size + 80:
                            grabbed_stretch = True
                    if grabbed_stretch :
                        scaling_construct = c
                        selected_construct = c
                        initial_pinch_dist = max(current_hands_dist, 10.0)
                        initial_construct_points = list(c.points) if c.shape_type == "freedraw" else None
                        initial_construct_size = c.size
                        break
            if scaling_construct is not None:
                ratio = current_hands_dist / initial_pinch_dist
                if scaling_construct.shape_type == "freedraw" and initial_construct_points:
                    cx = sum(p[0] for p in initial_construct_points) / len(initial_construct_points)
                    cy = sum(p[1] for p in initial_construct_points) / len(initial_construct_points)
                    scaling_construct.points = [((p[0] - cx) * ratio + midpoint[0], (p[1] - cy) * ratio + midpoint[1]) for p in initial_construct_points]
                    xs = [p[0] for p in scaling_construct.points]
                    ys = [p[1] for p in scaling_construct.points]
                    scaling_construct.bbox = pygame.Rect(int(min(xs)), int(min(ys)), int(max(xs) - min(xs) + 1), int(max(ys) - min(ys) + 1))
                    scaling_construct.x = midpoint[0]
                    scaling_construct.y = midpoint[1]
                else: 
                    scaling_construct.size = max(20.0, min(400.0, initial_construct_size * ratio))
                    scaling_construct.set_position(midpoint[0], midpoint[1])
                    scaling_construct.angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])

            dragged_by_hand.clear()


    else:
        scaling_construct = None
        initial_pinch_dist = None
        initial_construct_points = None

        
        for hand in pinching_hands:
            hid = hand["id"]
            hx, hy = hand["pos"]
            fingers = hand["fingers"]

            if fingers == 1:
                
                if hid in dragged_by_hand:
                    del dragged_by_hand[hid]

                if hid not in active_freedraw_by_hand:
                    new_draw = Construct("freedraw", hx, hy)
                    constructs.append(new_draw)
                    active_freedraw_by_hand[hid] = new_draw
                    new_draw.add_point(hx, hy)
                active_freedraw_by_hand[hid].add_point(hx, hy)

            else:
                
                if hid in active_freedraw_by_hand:
                    del active_freedraw_by_hand[hid]

                if hid not in dragged_by_hand:
                    candidates = []

                    for c in constructs:
                        if c in dragged_by_hand.values():
                            continue
                        if c.shape_type == "freedraw":
                            if c.bbox.inflate(20,20).collidepoint(hx, hy):
                                dist = math.hypot(c.x - hx, c.y - hy)
                            else:
                                continue

                        else:
                            dist = math.hypot(c.x - hx, c.y - hy)
                            if dist > c.size+15:
                                continue

                        candidates.append((dist, c))

                    
                    if candidates:
                        c = min(candidates, key=lambda item: item[0])[1]
                        dragged_by_hand[hid] = c
                        selected_construct = c
                        c.vx = c.vy = 0
                        last_hand_positions[hid] = (hx, hy)
                        break

                if hid in dragged_by_hand:
                    dragged = dragged_by_hand[hid]

                    if hid in last_hand_positions:
                        old_x, old_y = last_hand_positions[hid]

                        dragged.vx = hx - old_x
                        dragged.vy = hy - old_y

                        dragged.vx = max(-30, min(30, dragged.vx))
                        dragged.vy = max(-30, min(30, dragged.vy))

                    dragged.set_position(hx, hy)
                    dragged.angle += 0.05
                last_hand_positions[hid] = (hx, hy)

        
        non_pinching_hands = [h for h in hands_data if not h["pinching"]]
        for hand in non_pinching_hands:
            hid = hand["id"]
            hx, hy = hand["pos"]
            fingers = hand["fingers"]

            if hid in active_freedraw_by_hand:
                del active_freedraw_by_hand[hid]
            if hid in dragged_by_hand:
                del dragged_by_hand[hid]
                last_hand_positions.pop(hid, None)

            if was_pinching.get(hid, False):
                gesture_timers[hid] = 0
                last_gestures[hid] = fingers
            
            if hid not in gesture_timers:
                gesture_timers[hid] = 0
                last_gestures[hid] = fingers

            if last_gestures[hid] == fingers:
                gesture_timers[hid] += 1
            else:
                last_gestures[hid] = fingers
                gesture_timers[hid] = 0

            
            if gesture_timers[hid] == GESTURE_HOLD_FRAMES:
                if fingers == 0:
                    if selected_construct is not None:
                        if selected_construct in constructs:
                            constructs.remove(selected_construct)
                        selected_construct = None
                    else:
                        constructs.clear()
                elif fingers == 2:
                    constructs.append(Construct("rectangle", hx, hy))
                elif fingers == 3:
                    constructs.append(Construct("circle", hx, hy))
                elif fingers == 4:
                    constructs.append(Construct("triangle", hx, hy))
                elif fingers == 5:
                    constructs.append(Construct("pentagon", hx, hy))
    detected_ids = {h["id"] for h in hands_data}
    for hid in list(gesture_timers.keys()):
        if hid not in detected_ids:
            del gesture_timers[hid]
    for hid in list(last_gestures.keys()):
        if hid not in detected_ids:
            del last_gestures[hid]
    for hid in list(active_freedraw_by_hand.keys()):
        if hid not in detected_ids:
            del active_freedraw_by_hand[hid]
    for hid in list(was_pinching.keys()):
        if hid not in detected_ids:
            del was_pinching[hid]

    was_pinching = {h["id"]: h["pinching"] for h in hands_data}

    active_manipulations = list(dragged_by_hand.values())
    active_manipulations.extend(list(active_freedraw_by_hand.values()))
    if scaling_construct is not None:
        active_manipulations.append(scaling_construct)

    for c in constructs:
        if c not in active_manipulations:
            c.set_position(c.x + c.vx, c.y + c.vy)
            c.vx *= 0.96
            c.vy *= 0.96
            c.angle += 0.005
        c.draw(screen, glow_surf)
        if c is selected_construct:
            pygame.draw.rect(
                screen,
                RING_BRIGHT,
                c.bbox.inflate(20, 20),
                4,
                border_radius = 8
            )
    screen.blit(glow_surf, (0,0))
    font = pygame.font.SysFont("consolas", 16)
    hud = [
        "Open Hand (5)      : Spawn Pentagon",
        "4 Fingers          : Spawn Triangle",
        "3 Fingers          : Spawn Circle",
        "2 Fingers          : Spawn Rectangle",
        "Fist (hold)        : Clear All",
        "Pinch + 1 finger   : Free Draw",
        "Pinch (closed)     : Move Shape",
        "Both Hands Pinch   : Stretch / Rotate",
        "[D] duplicate [C]  Clear   [ESC] Quit",
    ]
    for idx, text in enumerate(hud):
        screen.blit(font.render(text, True, (150, 255, 180)), (20, 20 + idx * 22))

    pygame.display.flip()
    clock.tick(60)

cap.release()
pygame.quit()
sys.exit()
