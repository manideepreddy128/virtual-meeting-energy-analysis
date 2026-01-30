STUDENT MONITORING CLIENT - INSTALLATION INSTRUCTIONS
=====================================================

FILES INCLUDED:
1. student_server.py  (The main program)
2. requirements.txt   (List of required libraries)

-----------------------------------------------------
STEP 1: INSTALL PYTHON
-----------------------------------------------------
Ensure you have Python installed on your laptop.
- Windows: Download from https://www.python.org/downloads/
  (IMPORTANT: Check the box "Add Python to PATH" during installation)
- Mac: You likely already have python3.

-----------------------------------------------------
STEP 2: INSTALL DEPENDENCIES (Download All)
-----------------------------------------------------
1. Open your Terminal (Mac/Linux) or Command Prompt (Windows).
2. Type the following command and press ENTER:

   pip install -r requirements.txt

   (Note: If that fails on Mac, try: pip3 install -r requirements.txt)

   This will automatically download all the required tools.

-----------------------------------------------------
STEP 3: RUN THE CLIENT
-----------------------------------------------------
Run the following command:

   python student_server.py

(Or on Mac/Linux: python3 student_server.py)

-----------------------------------------------------
STEP 4: CONNECT
-----------------------------------------------------
1. The program will ask for the "Host IP".
   Ask your teacher for this IP address (it is displayed on their server).
2. Enter your Name.
3. The camera window will open. Leave it open to be monitored.

TROUBLESHOOTING:
- If you get "ModuleNotFoundError", run Step 2 again.
- If the Audio Alert trigger loop error occurs, ensure you are using the latest version of the file.
