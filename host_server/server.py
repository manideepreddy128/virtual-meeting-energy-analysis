from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import time

from threading import Lock

app = FastAPI()

# =========================
# IN-MEMORY STORAGE
# =========================
students = {}   # student_id -> metrics
students_lock = Lock() # Locks access to students dict
SESSION_START = time.time()

# =========================
# DATA MODEL
# =========================
class StudentMetrics(BaseModel):
    student_id: str
    student_name: str
    ear: float # Keep raw EAR for debug
    eye_status: str     # "OPEN" / "CLOSED"
    fatigue: int        # PERCLOS %
    yawning_status: str # "YES" / "NO"
    head_status: str    # "NORMAL" / "ROTATED"
    status: str         # Final Status
    timestamp: float

# =========================
# DASHBOARD PAGE
# =========================
@app.get("/", response_class=HTMLResponse)
def dashboard():
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "dashboard/index.html")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# =========================
# RECEIVE STUDENT DATA
# =========================
@app.post("/update")
def update_student(data: StudentMetrics):
    with students_lock:
        students[data.student_id] = {
            "name": data.student_name,

            "ear": data.ear,
            "eye_status": data.eye_status,
            "fatigue": data.fatigue,
            "yawning_status": data.yawning_status,
            "head_status": data.head_status,
            "status": data.status,
            "status": data.status,
            "timestamp": time.time() # Use SERVER TIME to avoid clock drift issues
        }
    return {"message": "updated"}

# =========================
# SEND DATA TO DASHBOARD
# =========================
@app.get("/students")
def get_students():
    now = time.time()
    inactive = []

    with students_lock:
        # AUTO REMOVE DISCONNECTED STUDENTS
        for sid, s in list(students.items()): # Create copy for safe iteration
            if now - s["timestamp"] > 10:
                inactive.append(sid)

        for sid in inactive:
            del students[sid]
            
        return JSONResponse(content=students)

# =========================
# HISTORY STORAGE
# =========================
history = {} # Store data of disconnected students

@app.get("/students")
def get_students():
    now = time.time()
    inactive = []

    with students_lock:
        # AUTO REMOVE DISCONNECTED STUDENTS
        for sid, s in list(students.items()): # Create copy for safe iteration
            if now - s["timestamp"] > 15: # Increased timeout slightly to 15s to match 10s intervals
                inactive.append(sid)

        for sid in inactive:
            # Move to history before deleting
            history[sid] = students[sid]
            del students[sid]
            
        # Return currently active students
        return JSONResponse(content=students)

@app.post("/end_class")
def end_class():
    with students_lock:
        # Return EVERYTHING: Active + History
        all_participants = {**history, **students}
        
        final_report = {}
        total_session_fatigue = 0
        student_count = 0
        
        for sid, data in all_participants.items():
            # Calculate Session Average
            avg_fatigue = 0
            if data.get("count_samples", 0) > 0:
                avg_fatigue = int(data["sum_fatigue"] / data["count_samples"])
            elif "fatigue" in data: # Fallback to last known fatigue if no samples accumulated
                 avg_fatigue = data["fatigue"]

            
            total_session_fatigue += avg_fatigue
            student_count += 1
            
            # Determine Final State based on AVERAGE
            final_status = "ACTIVE"
            if avg_fatigue > 70: final_status = "DROWSY"
            elif avg_fatigue > 40: final_status = "PASSIVE"
            
            final_report[sid] = {
                "name": data["name"],
                "status": final_status, # This is the "Session State"
                "fatigue": avg_fatigue  # This is the "Average Fatigue"
            }
            
        # CALC CLASS METRICS
        class_avg = 0
        if student_count > 0:
            class_avg = round(total_session_fatigue / student_count, 1)
            
        summary = {
            "class_average_fatigue": class_avg,
            "engagement_score": 100 - class_avg,
            "total_students": student_count
        }

        # Clear everything for next session
        students.clear()
        history.clear()
        
        return JSONResponse(content={"students": final_report, "summary": summary})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
