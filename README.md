# 🎓 Student Engagement & Fatigue Monitoring System

A real-time fatigue and engagement monitoring system for virtual classrooms using computer vision and machine learning. This system helps educators track student attention levels during online classes.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Face%20Mesh-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Overview

This project implements a **client-server architecture** where:
- **Student Client**: Runs on each student's computer, uses webcam to detect fatigue indicators
- **Host Server**: Aggregates data from all students and displays a real-time dashboard

## ✨ Features

### Fatigue Detection Metrics
| Metric | Description | Threshold |
|--------|-------------|-----------|
| **PERCLOS** | Percentage of Eye Closure | >40% Passive, >70% Drowsy |
| **EAR** | Eye Aspect Ratio | <0.22 = Eyes Closed |
| **MAR** | Mouth Aspect Ratio (Yawning) | >0.75 = Yawning |
| **Head Pose** | Yaw/Pitch Detection | >25° = Distracted |

### Dashboard Features
- 📊 Real-time class engagement graphs
- 👥 Individual student fatigue tracking
- ⚠️ High fatigue alerts (>50% class affected)
- 📈 Session summary reports
- 🔒 Privacy-focused (no video stored)

## 🏗️ Architecture

```
┌─────────────────┐     HTTP POST      ┌─────────────────┐
│  Student Client │ ─────────────────► │   Host Server   │
│   (Webcam +     │    /update         │   (FastAPI +    │
│   MediaPipe)    │                    │   Dashboard)    │
└─────────────────┘                    └─────────────────┘
        ▲                                      │
        │                                      ▼
   Face Detection                        Real-time
   EAR, MAR, Pose                       Dashboard
   Calculation                          Visualization
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Webcam (for student client)
- Network connectivity between host and students

### Host Server Setup

```bash
# Navigate to host server directory
cd host_server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py
```

The dashboard will be available at: `http://<HOST_IP>:8000`

### Student Client Setup

```bash
# Navigate to student server directory
cd studentserver

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the client
python student_server.py
```

You will be prompted to enter:
1. Host IP address (e.g., `192.168.1.100`)
2. Your name

## 📁 Project Structure

```
virtual-meeting-energy-analysis/
├── host_server/
│   ├── server.py           # FastAPI server
│   ├── requirements.txt    # Server dependencies
│   └── dashboard/
│       ├── index.html      # Dashboard UI
│       ├── styles.css      # Styling
│       └── app.js          # Frontend logic
│
├── studentserver/
│   ├── student_server.py   # Client with face detection
│   ├── requirements.txt    # Client dependencies
│   └── README.txt          # Setup instructions
│
├── .gitignore
├── LICENSE
└── README.md
```

## 🔬 Technical Details

### Research-Backed Thresholds
- **EAR Threshold (0.22)**: Based on Soukupova & Cech (2016) - "Real-Time Eye Blink Detection"
- **MAR Threshold (0.75)**: Distinguishes yawning from normal talking
- **Yaw Threshold (25°)**: Standard driver distraction limit

### Status Classification
```python
if PERCLOS < 40%:  status = "ACTIVE"
elif PERCLOS < 70%: status = "PASSIVE"
else:               status = "DROWSY"
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/update` | POST | Receive student metrics |
| `/students` | GET | Get all active students |
| `/end_class` | POST | End session & get report |

## 🛡️ Privacy

- ❌ No video/images are stored or transmitted
- ✅ Only numerical metrics (EAR, PERCLOS, etc.) are sent
- ✅ Student data is cleared after each session

## 👨‍💻 Author

**Manideep Reddy Bekkem**

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [MediaPipe](https://mediapipe.dev/) - Face mesh detection
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Chart.js](https://www.chartjs.org/) - Dashboard visualizations
