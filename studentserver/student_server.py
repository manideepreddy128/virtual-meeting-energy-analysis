import cv2
import mediapipe as mp
import numpy as np
import time
import requests
import uuid

from collections import deque

# ==========================
# CONFIG
# ==========================
HOST_IP = input("Enter Host IP (e.g., 10.84.87.149): ").strip()
SERVER_URL = f"http://{HOST_IP}:8000/update"

STUDENT_NAME = input("Enter Your Name: ").strip()
STUDENT_ID = str(uuid.uuid4())[:8]

# RESEARCH BACKED THRESHOLDS
# 1. EAR (Eyes): 0.22 
# Paper: Soukupova & Cech (2016) "Real-Time Eye Blink Detection"
# Link: https://vision.fe.uni-lj.si/cvww2016/proceedings/papers/05.pdf
ear_threshold = 0.22 

# 2. MAR (Yawning): 0.75
# Based on establishing a clear distinction from talking (typically < 0.5)
mar_threshold = 0.75

# 3. YAW (Distraction): 25 Degrees
# Standard driver distraction limit is often ~20-30 degrees off-center.
yaw_threshold = 25   
pitch_threshold = 20

blink_consec_frames = 3
send_interval = 10  # FIXED 10 SECOND WINDOW

# PERCLOS CONFIG
# We no longer use a sliding window deque. We use batch counters.
batch_closed_frames = 0
batch_total_frames = 0
display_perclos = 0 # Holds the value of the LAST completed batch for display

# ==========================
# MEDIAPIPE SETUP
# ==========================
mp_face = mp.solutions.face_mesh
# refine_landmarks=True gives us iris landmarks, but we just need standard 468 for basic pose + ear
face_mesh = mp_face.FaceMesh(max_num_faces=1, refine_landmarks=True)

# Indices for eyes (standard 468 landmarks)
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# Indices for mouth
MOUTH = [13, 14, 78, 308] # Using inner mouth points 

# Landmarks for Head Pose Estimation (Nose tip, Chin, Left Eye Left Corner, Right Eye Right Corner, Left Mouth Corner, Right Mouth Corner)
# 1: Nose Tip, 199: Chin, 33: Left Eye Left Corner, 263: Right Eye Right Corner, 61: Left Mouth Corner, 291: Right Mouth Corner
FACE_3D_LANDMARKS = [1, 199, 33, 263, 61, 291] 

# ==========================
# FUNCTIONS
# ==========================
def euclidean(p1, p2):
    return np.linalg.norm(p1 - p2)

def eye_aspect_ratio(landmarks, eye):
    p = [landmarks[i] for i in eye]
    A = euclidean(p[1], p[5])
    B = euclidean(p[2], p[4])
    C = euclidean(p[0], p[3])
    return (A + B) / (2.0 * C)

def mouth_aspect_ratio(landmarks, mouth):
    # points: 0=top, 1=bottom, 2=left, 3=right
    p = [landmarks[i] for i in mouth]
    
    # Vertical distance
    A = euclidean(p[0], p[1]) 
    
    # Horizontal distance
    B = euclidean(p[2], p[3])
    
    if B == 0: return 0
    return A / B

def get_head_pose(landmarks, shape):
    h, w, _ = shape
    
    # 2D Image Points
    image_points = np.array([
        (landmarks[1].x * w, landmarks[1].y * h),     # Nose Tip
        (landmarks[199].x * w, landmarks[199].y * h), # Chin
        (landmarks[33].x * w, landmarks[33].y * h),   # Left Eye Left Corner
        (landmarks[263].x * w, landmarks[263].y * h), # Right Eye Right Corner
        (landmarks[61].x * w, landmarks[61].y * h),   # Left Mouth Corner
        (landmarks[291].x * w, landmarks[291].y * h)  # Right Mouth Corner
    ], dtype="double")

    # 3D Model Points (Generic Human Face)
    model_points = np.array([
        (0.0, 0.0, 0.0),             # Nose Tip
        (0.0, -330.0, -65.0),        # Chin
        (-225.0, 170.0, -135.0),     # Left Eye Left Corner
        (225.0, 170.0, -135.0),      # Right Eye Right Corner
        (-150.0, -150.0, -125.0),    # Left Mouth Corner
        (150.0, -150.0, -125.0)      # Right Mouth Corner
    ])

    # Camera Internals
    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype="double")

    dist_coeffs = np.zeros((4, 1)) # Assuming no lens distortion
    
    success, rotation_vector, translation_vector = cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs)
    
    # Get Rotation Matrix
    rmat, jac = cv2.Rodrigues(rotation_vector)
    
    # Get Angles
    angles, mtxR, mtxQ, Q, Qx, Qy = cv2.RQDecomp3x3(rmat)

    # angles[0] = Pitch (Up/Down)
    # angles[1] = Yaw (Left/Right)
    # angles[2] = Roll (Tilt)
    
    pitch = angles[0]
    yaw = angles[1]
    roll = angles[2]
    
    return pitch, yaw, roll

def classify_status(perclos, is_yawning, yaw, pitch):
    if is_yawning:
        return "YAWNING"
    if abs(yaw) > yaw_threshold:
        return "DISTRACTED"
    
    if perclos < 40:
        return "ACTIVE"
    elif perclos < 70:
        return "PASSIVE"
    return "DROWSY"

def trigger_alert():
    global last_speech_time
    # 5 Second Cooldown
    if time.time() - last_speech_time < 5:
        return

    import sys
    try:
        if sys.platform == "darwin": # Mac
            os.system('say "Alert, please focus" &') # & to run in background
        elif sys.platform == "win32": # Windows
            import winsound
            # High pitch beep (Frequency=1000Hz, Duration=500ms)
            winsound.Beep(1000, 500)
            # Try Speech as well (optional, might fail on some configs)
            os.system('powershell -Command "(New-Object Media.SoundPlayer \'C:\Windows\Media\notify.wav\').PlaySync();"') 
        else: # Linux
             os.system('espeak "Alert, please focus" &')
    except Exception as e:
        print(f"Audio Error: {e}")
    
    last_speech_time = time.time()

# ==========================
# CAMERA
# ==========================
cap = cv2.VideoCapture(0)

blink_count = 0
frame_counter = 0
last_sent = time.time()
yawn_counter = 0
last_speech_time = 0

print(f"[INFO] Student: {STUDENT_NAME} (ID: {STUDENT_ID})")
print(f"[INFO] Connecting to: {SERVER_URL}")

# ==========================
# MAIN LOOP
# ==========================
live_perclos_buffer = deque(maxlen=300) # Approx 10 seconds of smoothing (30fps)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb)

    ear = 0.0
    mar = 0.0
    pitch, yaw, roll = 0, 0, 0
    is_yawning = False

    if result.multi_face_landmarks:
        lm = result.multi_face_landmarks[0].landmark
        img_h, img_w, _ = frame.shape
        
        # Convert landmarks to numpy array for EAR/MAR
        pts = np.array([(p.x * img_w, p.y * img_h, p.z) for p in lm]) # Use 3D if needed, but 2D is enough for aspect ratio logic on x,y
        
        # EAR
        left_ear = eye_aspect_ratio(pts, LEFT_EYE)
        right_ear = eye_aspect_ratio(pts, RIGHT_EYE)
        ear = (left_ear + right_ear) / 2

        # MAR (Yawning)
        mar = mouth_aspect_ratio(pts, MOUTH)
        if mar > mar_threshold:
             is_yawning = True

        # Head Pose
        pitch, yaw, roll = get_head_pose(lm, frame.shape)

        # Blink Counter & PERCLOS (BATCH LOGIC)
        is_closed = ear < ear_threshold
        
        # Update Batch Counters (Server)
        batch_total_frames += 1
        if is_closed:
            batch_closed_frames += 1
        
        # Update Live Buffer (Local Alert)
        live_perclos_buffer.append(1 if is_closed else 0)

        if is_closed:
            frame_counter += 1
        else:
            if frame_counter >= blink_consec_frames:
                blink_count += 1
            frame_counter = 0

        # Determine Head Direction
        direction = "Center"
        if yaw < -yaw_threshold: direction = "Left"
        elif yaw > yaw_threshold: direction = "Right"

        # Visualization
        # 1. EAR
        cv2.putText(frame, f"EAR: {ear:.2f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # 2. Eyes Status
        color = (0, 0, 255) if is_closed else (0, 255, 0)
        cv2.putText(frame, f"Eyes: {'CLOSED' if is_closed else 'OPEN'}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # 3. Yawning
        if is_yawning:
             cv2.putText(frame, "YAWNING: YES", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
             cv2.putText(frame, "Yawning: NO", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 4. Rotation
        dir_color = (0, 0, 255) if direction != "Center" else (0, 255, 0)
        cv2.putText(frame, f"Head: {direction}", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, dir_color, 2)

        # 5. PERCLOS (SHOW LAST COMPLETED BATCH)
        cv2.putText(frame, f"PERCLOS: {display_perclos}%", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    # ==========================
    # REAL-TIME ALERT LOGIC (INSTANT)
    # ==========================
    # We calculate a "Live Status" just for the alert, based on current instant + current perclos estimate
    # ==========================
    # REAL-TIME ALERT LOGIC (INSTANT & SMOOTHED)
    # ==========================
    # We calculate a "Live Status" using the sliding window buffer for stability
    live_perclos = 0
    if len(live_perclos_buffer) > 0:
         live_perclos = int((sum(live_perclos_buffer) / len(live_perclos_buffer)) * 100)
    
    live_status = classify_status(live_perclos, is_yawning, yaw, pitch)

    if live_status in ["DISTRACTED", "DROWSY", "YAWNING"]:
         # Visual Alert
         cv2.rectangle(frame, (0,0), (frame.shape[1], frame.shape[0]), (0,0,255), 10)
         cv2.putText(frame, "ALERT: PLEASE FOCUS!", (50, frame.shape[0]//2), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,255), 4)
         
         # Sound Alert
         trigger_alert()

    cv2.imshow("Student Camera (Press Q to exit)", frame)

    # ==========================
    # SEND DATA (EVERY 10 SECONDS)
    # ==========================
    if time.time() - last_sent > send_interval:
        # Calculate for THIS completed batch
        if batch_total_frames > 0:
            perclos_score = int((batch_closed_frames / batch_total_frames) * 100)
        else:
            perclos_score = 0

        # Update Display Value
        display_perclos = perclos_score

        # Categorical Statues
        eye_status = "CLOSED" if (ear < ear_threshold) else "OPEN" # Current instant state
        yawn_status = "YES" if is_yawning else "NO"
        head_status = "ROTATED" if (abs(yaw) > yaw_threshold) else "NORMAL"
        
        # Final Status for Server
        status = classify_status(perclos_score, is_yawning, yaw, pitch)

        payload = {
            "student_id": STUDENT_ID,
            "student_name": STUDENT_NAME,
            "ear": float(ear),
            "eye_status": eye_status,
            "fatigue": perclos_score,
            "yawning_status": yawn_status,
            "head_status": head_status,
            "status": status,
            "timestamp": time.time()
        }

        try:
            requests.post(SERVER_URL, json=payload, timeout=1)
            print(f"Sent: {status} | Yaw: {int(yaw)} | Fatigue: {perclos_score}%")
        except Exception as e:
            pass # print("Server not reachable")

        blink_count = 0
        
        # RESET BATCH COUNTERS
        batch_total_frames = 0
        batch_closed_frames = 0
        last_sent = time.time()

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()