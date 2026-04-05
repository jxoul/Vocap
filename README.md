# Vocap - Vocabulary Master

**Vocap** is a modern desktop application built with Python (Flask & pywebview), designed for efficient English vocabulary learning and practice (with Greek translations). It offers a complete word management system, gamification with dynamic monthly goals, and detailed progress statistics.

---

## Key Features

### 1. Vocabulary Management (Mode 1)
* **Add Words:** Easily insert an English word, its English definition, Greek translation, synonyms, antonyms, and example sentences.
* **Auto-Save:** All data is stored locally in `.csv` files for easy management, portability, and backup.

### 2. Smart Tests (Mode 2)
* **Three Quiz Modes:**
  * **Daily:** A random selection of 10 words.
  * **Weekly:** A random selection of 30 words.
  * **Hard:** A targeted 15-word quiz focusing on the words you struggle with the most (based on historical error ratios).
* **Three Question Types:**
  * **Type 1:** Guess the English word based on its English definition.
  * **Type 2:** Translate the English word into Greek.
  * **Type 3:** Provide ONE synonym and ONE antonym for the given word.
* **Help & Hints System:** Access examples, definitions, or translations during a quiz. Using hints applies a specific point penalty to your final score.

### 3. Gamification & Goals
* **Dynamic Monthly Goals:** The app automatically calculates a custom monthly point target based on the total number of days in the current month.
* **Progress Stages:** Your monthly progress is divided into 4 stages (Beginner, Intermediate, Advanced, Master) and visualized through a custom, smooth-animated progress bar on the main dashboard.

### 4. Data Center
* **Words Library:** A comprehensive list of your entire vocabulary. Features a custom SVG pie chart for each word, visualizing your success, skip, and fail rates.
* **Quiz History Archive:** A complete log of past quizzes, neatly organized by Year and Month. Includes a summary card comparing actual points vs. the monthly goal, and clickable rows that reveal detailed performance for every single word tested.


---

## Tech Stack

* **Backend:** Python 3, Flask, Pandas (for robust CSV data handling).
* **Frontend:** HTML5, CSS3, Bootstrap 5 (for responsive styling), Jinja2 (for templating).
* **Desktop Wrapper:** `pywebview` (renders the web application inside a native, standalone desktop window).

---

## Project Structure

```text
Vocap/
│
├── app.py                 # Main application file (Backend logic & Routes)
├── app.ico                # Application icon
├── data/                  # Local database folder (Auto-generated)
│   ├── vocab.csv          # Vocabulary storage
│   ├── word_stats.csv     # Success/fail statistics per word
│   ├── quiz_history.csv   # Complete log of all taken quizzes
│   └── monthly_goals.csv  # Monthly point targets and current scores
│
└── templates/             # HTML Pages (Jinja2 Templates)
    ├── base.html          # Global layout, CSS variables, and navigation
    ├── index.html         # Main Dashboard & Progress Bar
    ├── add.html           # Word insertion form
    ├── quiz_menu.html     # Quiz mode selection
    ├── quiz.html          # The testing interface (Questions, Hints, Results)
    ├── data_menu.html     # Data Center navigation
    ├── words_list.html    # Vocabulary library and visual stats
    ├── reports.html       # Time-based quiz history archive
    └── 500.html           # Custom Internal Server Error page
