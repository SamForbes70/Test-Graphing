# Quantum Stock Dashboard

This is a small web dashboard that runs on your own computer.

It opens in your browser, but it is not a normal website. You start it from your computer first, then open `http://localhost:8501`.

## Very Easy Windows Instructions

### Step 1: Install Python

Only do this once.

1. Go to https://www.python.org/downloads/
2. Download Python 3.11 or newer.
3. Open the installer.
4. Tick the box that says **Add python.exe to PATH**.
5. Click install.

### Step 2: Download This Dashboard

1. Click the green **Code** button on this GitHub page.
2. Click **Download ZIP**.
3. Unzip the downloaded file.
4. Open the unzipped folder.

### Step 3: Open Command Prompt

1. Click in the folder address bar at the top.
2. Type `cmd`.
3. Press Enter.

A black Command Prompt window should open in the right folder.

### Step 4: Copy And Paste These Commands

Paste these one at a time into Command Prompt.

```bat
py -3.11 -m venv .venv
```

```bat
.venv\Scripts\python.exe -m pip install --upgrade pip
```

```bat
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

```bat
.venv\Scripts\python.exe -m streamlit run dashboard.py --server.port=8501
```

### Step 5: Open The Dashboard

Open this in your browser:

```text
http://localhost:8501
```

## How To Stop It

Go back to the black Command Prompt window and press:

```text
Ctrl+C
```

## If Something Goes Wrong

If `py -3.11` does not work, try this instead:

```bat
python -m venv .venv
```

If port `8501` is busy, start it on port `8502` instead:

```bat
.venv\Scripts\python.exe -m streamlit run dashboard.py --server.port=8502
```

Then open:

```text
http://localhost:8502
```

## Important Note

This dashboard is for learning and research. It is not financial advice.
