import os
import random
import pandas as pd
import calendar
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory
import webview
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = 'vocabulary_master_secret_key'

# --- DICTIONARY API CONFIG ---
MW_COLLEGIATE_KEY = os.getenv('MW_COLLEGIATE_KEY')
MW_THESAURUS_KEY = os.getenv('MW_THESAURUS_KEY')

# --- CONFIGURATION ---
DATA_DIR = 'data'
VOCAB_FILE = os.path.join(DATA_DIR, 'vocab.csv')
STATS_FILE = os.path.join(DATA_DIR, 'word_stats.csv')
HISTORY_FILE = os.path.join(DATA_DIR, 'quiz_history.csv')
GOALS_FILE = os.path.join(DATA_DIR, 'monthly_goals.csv')

VOCAB_COLS = ['word', 'meaning_en', 'meaning_gr', 'synonyms', 'antonyms', 'example', 'hw', 'prs', 'audio_src']
STATS_COLS = ['word', 'appearances', 'correct', 'wrong', 'skipped']
HISTORY_COLS = ['date', 'quiz_type', 'num_questions', 'words_asked', 'points_list', 'final_score', 'quiz_points']
GOALS_COLS = ['month_key', 'days_in_month', 'target_points', 'current_points', 's1_limit', 's2_limit', 's3_limit']

HELP_COSTS = {'synonyms': 0.5, 'antonyms': 0.5, 'meaning_gr': 1.0, 'meaning_en': 1.0, 'example': 1.0}

# --- HELPERS ---
def get_app_time():
    return datetime.now()

def init_db():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    if not os.path.exists(VOCAB_FILE): pd.DataFrame(columns=VOCAB_COLS).to_csv(VOCAB_FILE, index=False)
    if not os.path.exists(STATS_FILE): pd.DataFrame(columns=STATS_COLS).to_csv(STATS_FILE, index=False)
    if not os.path.exists(HISTORY_FILE): pd.DataFrame(columns=HISTORY_COLS).to_csv(HISTORY_FILE, index=False)
    if not os.path.exists(GOALS_FILE): pd.DataFrame(columns=GOALS_COLS).to_csv(GOALS_FILE, index=False)

def get_df(file_path, columns):
    init_db()
    try:
        df = pd.read_csv(file_path).fillna('')
        if file_path == VOCAB_FILE:
            for col in VOCAB_COLS:
                if col not in df.columns: df[col] = ""
        if file_path == STATS_FILE:
            if 'skipped' not in df.columns: df['skipped'] = 0
            for col in ['appearances', 'correct', 'wrong', 'skipped']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        if file_path == GOALS_FILE:
            if 's1_limit' not in df.columns: return pd.DataFrame(columns=columns)
            for col in ['target_points', 'current_points', 's1_limit', 's2_limit', 's3_limit']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)
    except Exception:
        return pd.DataFrame(columns=columns)
    return df

def update_word_stat(word, result):
    df = get_df(STATS_FILE, STATS_COLS)
    word = str(word).strip().lower() # Force format
    
    # Check if word exists
    if word not in df['word'].astype(str).values:
        new_row = pd.DataFrame([{'word': word, 'appearances': 0, 'correct': 0, 'wrong': 0, 'skipped': 0}])
        df = pd.concat([df, new_row], ignore_index=True)
    
    # Find index
    idx = df.index[df['word'] == word].tolist()[0]
    
    # Update Stats
    df.at[idx, 'appearances'] = int(df.at[idx, 'appearances']) + 1
    if result == 'correct': df.at[idx, 'correct'] = int(df.at[idx, 'correct']) + 1
    elif result == 'wrong': df.at[idx, 'wrong'] = int(df.at[idx, 'wrong']) + 1
    elif result == 'skip': df.at[idx, 'skipped'] = int(df.at[idx, 'skipped']) + 1
    
    df.to_csv(STATS_FILE, index=False)

def process_list_input(field_name):
    raw_list = request.form.getlist(field_name)
    return "|".join([x.strip().lower() for x in raw_list if x.strip()])

def pick_random_item(pipe_string):
    if not isinstance(pipe_string, str) or not pipe_string: return "N/A"
    items = [x.strip() for x in pipe_string.split('|') if x.strip()]
    return random.choice(items) if items else "N/A"

# --- GOAL LOGIC ---
def get_or_create_monthly_goal():
    df = get_df(GOALS_FILE, GOALS_COLS)
    now = get_app_time()
    month_key = now.strftime('%Y-%m')
    
    if month_key not in df['month_key'].values:
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        target_points = int((4 * 30 * 4) + (8 * 15 * 4) + (max(0, days_in_month - 12) * 10 * 4) )
        s1, s2, s3 = int(target_points * 0.39), int(target_points * 0.69), int(target_points * 0.89)
        new_row = {'month_key': month_key, 'days_in_month': days_in_month, 'target_points': target_points, 'current_points': 0, 's1_limit': s1, 's2_limit': s2, 's3_limit': s3}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(GOALS_FILE, index=False)
        return new_row
    return df[df['month_key'] == month_key].iloc[0].to_dict()

def add_points_to_month(points):
    get_or_create_monthly_goal() 
    df = get_df(GOALS_FILE, GOALS_COLS)
    month_key = get_app_time().strftime('%Y-%m')
    if month_key in df['month_key'].values:
        idx = df.index[df['month_key'] == month_key].tolist()[0]
        df.at[idx, 'current_points'] = float(df.at[idx, 'current_points']) + points
        df.to_csv(GOALS_FILE, index=False)

# --- ROUTES ---
@app.route('/')
def index():
    vocab_df = get_df(VOCAB_FILE, VOCAB_COLS)
    month_stats = get_or_create_monthly_goal()
    current, target = int(month_stats['current_points']), int(month_stats['target_points'])
    s1, s2, s3 = int(month_stats['s1_limit']), int(month_stats['s2_limit']), int(month_stats['s3_limit'])
    
    if current >= target: stage_text, stage_color = "Goal Reached!", "success"
    elif current >= s3: stage_text, stage_color = "Stage 4 (Master)", "success"
    elif current >= s2: stage_text, stage_color = "Stage 3 (Advanced)", "warning"
    elif current >= s1: stage_text, stage_color = "Stage 2 (Intermediate)", "orange"
    else: stage_text, stage_color = "Stage 1 (Beginner)", "danger"
        
    return render_template('index.html', count=len(vocab_df), month_name=get_app_time().strftime('%B'), stats=month_stats, stage_text=stage_text, stage_color=stage_color, current_points=current, target_points=target)

@app.route('/app_icon')
def get_app_icon(): return send_from_directory('.', 'app.ico')

@app.route('/exit')
def exit_app(): os._exit(0)

@app.route('/add', methods=['GET', 'POST'])
def add_word():
    if request.method == 'POST':
        word = request.form.get('word', '').strip().lower()
        df = get_df(VOCAB_FILE, VOCAB_COLS)
        if not df.empty and word in df['word'].astype(str).values:
            return render_template('add.html', error=f"The word '{word}' already exists!")

        new_row = {
            'word': word,
            'meaning_en': process_list_input('meaning_en[]'),
            'meaning_gr': request.form.get('meaning_gr', '').strip().lower(),
            'synonyms': process_list_input('synonyms[]'),
            'antonyms': process_list_input('antonyms[]'),
            'example': process_list_input('example[]'),
            'hw': request.form.get('hw', '').strip(),
            'prs': request.form.get('prs', '').strip(),
            'audio_src': request.form.get('audio_src', '').strip()
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(VOCAB_FILE, index=False)
        update_word_stat(word, 'new') # Init stats
        return render_template('add.html', success=f"Added '{word}'!", last_word=new_row)
    return render_template('add.html')

@app.route('/lookup_word', methods=['POST'])
def lookup_word():
    word = request.json.get('word', '').strip()
    if not word: return jsonify({'error': 'No word provided'})
    data = {'definitions': [], 'examples': [], 'synonyms': [], 'antonyms': [], 'audio_src': None, 'hw': '', 'prs': ''}

    if MW_COLLEGIATE_KEY:
        try:
            url = f"https://dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={MW_COLLEGIATE_KEY}"
            resp = requests.get(url).json()
            if resp and isinstance(resp, list) and len(resp) > 0 and isinstance(resp[0], dict):
                first = resp[0]
                if 'hwi' in first:
                    data['hw'] = first['hwi'].get('hw', '')
                    if 'prs' in first['hwi'] and len(first['hwi']['prs']) > 0:
                        data['prs'] = first['hwi']['prs'][0].get('mw', '')
                        if 'sound' in first['hwi']['prs'][0]:
                            audio = first['hwi']['prs'][0]['sound']['audio']
                            subdir = 'number' if audio[0].isdigit() or audio[0] == '_' else audio[0]
                            if audio.startswith('bix'): subdir = 'bix'
                            elif audio.startswith('gg'): subdir = 'gg'
                            
                            try:
                                r = requests.get(f"https://media.merriam-webster.com/audio/prons/en/us/mp3/{subdir}/{audio}.mp3")
                                if r.status_code == 200:
                                    audio_dir = os.path.join('static', 'audio')
                                    if not os.path.exists(audio_dir): os.makedirs(audio_dir)
                                    with open(os.path.join(audio_dir, f"{audio}.mp3"), 'wb') as f: f.write(r.content)
                                    data['audio_src'] = f"/static/audio/{audio}.mp3"
                            except: pass

                all_examples = []
                def find_examples(obj):
                    if isinstance(obj, dict):
                        if 't' in obj:
                            clean = obj['t']
                            for tag in ['{wi}', '{/wi}', '{it}', '{/it}', '{qword}', '{/qword}', '{bc}', '{sc}', '{/sc}']:
                                clean = clean.replace(tag, '')
                            if ' ' in clean: all_examples.append(clean.strip())
                        for k, v in obj.items(): find_examples(v)
                    elif isinstance(obj, list):
                        for item in obj: find_examples(item)

                for entry in resp:
                    if 'shortdef' in entry:
                        for d in entry['shortdef']:
                            for p in d.split('; also :'): 
                                if p.strip() not in data['definitions']: data['definitions'].append(p.strip())
                    find_examples(entry)
                data['examples'] = list(dict.fromkeys(all_examples))[:15]
        except Exception as e: print(f"Collegiate Error: {e}")

    if MW_THESAURUS_KEY:
        try:
            url = f"https://dictionaryapi.com/api/v3/references/thesaurus/json/{word}?key={MW_THESAURUS_KEY}"
            resp = requests.get(url).json()
            if resp and isinstance(resp, list) and len(resp) > 0 and isinstance(resp[0], dict):
                syns, ants = set(), set()
                for entry in resp:
                    if 'meta' in entry:
                        if 'syns' in entry['meta']: 
                            for g in entry['meta']['syns']: syns.update(g)
                        if 'ants' in entry['meta']: 
                            for g in entry['meta']['ants']: ants.update(g)
                if syns: data['synonyms'] = random.sample(list(syns), min(len(syns), 10))
                if ants: data['antonyms'] = random.sample(list(ants), min(len(ants), 10))
        except Exception as e: print(f"Thesaurus Error: {e}")

    return jsonify(data)

@app.route('/quiz_setup/<mode>')
def quiz_setup(mode):
    df = get_df(VOCAB_FILE, VOCAB_COLS)
    stats_df = get_df(STATS_FILE, STATS_COLS)
    if len(df) < 1: return render_template('index.html', error="Add words first!")
    merged = pd.merge(df, stats_df[['word', 'appearances']], on='word', how='left').fillna(0)
    merged['weight'] = 1 / (merged['appearances'] + 1)

    quiz_data = []
    if mode == 'daily':
        quiz_data = merged.sample(n=min(10, len(df)), weights='weight').to_dict('records')
    elif mode == 'weekly':
        quiz_data = merged.sample(n=min(30, len(df)), weights='weight').to_dict('records')
    elif mode == 'hard':
        if stats_df.empty:
            quiz_data = df.sample(n=min(15, len(df))).to_dict('records')
        else:
            # IMPROVED HARD MODE LOGIC
            stats_df['total'] = stats_df['correct'] + stats_df['wrong'] + stats_df['skipped']
            # Sort by Wrong Ratio DESC, then by Total Appearances DESC
            stats_df['ratio'] = stats_df.apply(lambda x: (x['wrong'] + x['skipped']) / x['total'] if x['total'] > 0 else 0, axis=1)
            sorted_stats = stats_df.sort_values(by=['ratio', 'appearances'], ascending=[False, False])
            
            top_words = sorted_stats.head(15)['word'].tolist()
            quiz_data = df[df['word'].isin(top_words)].to_dict('records')
            
            # Fill remaining spots if needed
            if len(quiz_data) < 15 and len(df) > len(quiz_data):
                remaining_df = df[~df['word'].isin(top_words)]
                quiz_data.extend(remaining_df.sample(n=min(15 - len(quiz_data), len(remaining_df))).to_dict('records'))

    # SESSION FIX: Store minimal data + Set Total Steps
    session['quiz_data'] = [item['word'] for item in quiz_data]
    session['total_steps'] = len(quiz_data) # <--- THIS WAS MISSING
    
    session['quiz_type'] = mode.capitalize()
    session['current_step'] = 0
    session['total_score_points'] = 0
    session['history_words'] = []
    session['history_points'] = []
    session['helps_used'] = [] 
    session['current_hints'] = {} 
    
    return redirect(url_for('quiz_step'))

@app.route('/quiz_step', methods=['GET', 'POST'])
def quiz_step():
    step = session.get('current_step')
    data = session.get('quiz_data')
    
    # SAFETY CHECK: Ensure data and total_steps exist
    if data is None or step is None or session.get('total_steps') is None:
        return redirect(url_for('index'))
    
    if step >= len(data):
        # Quiz Finish Logic
        max_pts = session['total_steps'] * 4
        actual_pts = session['total_score_points']
        pct = int((actual_pts / max_pts) * 100) if max_pts > 0 else 0
        pct = max(0, pct)
        
        hist_df = get_df(HISTORY_FILE, HISTORY_COLS)
        new_hist = {
            'date': get_app_time().strftime('%Y-%m-%d'),
            'quiz_type': session.get('quiz_type', 'Normal'),
            'num_questions': session['total_steps'],
            'words_asked': "|".join(session['history_words']),
            'points_list': "|".join(map(str, session['history_points'])),
            'final_score': f"{pct}%",
            'quiz_points': actual_pts
        }
        hist_df = pd.concat([hist_df, pd.DataFrame([new_hist])], ignore_index=True)
        hist_df.to_csv(HISTORY_FILE, index=False)
        add_points_to_month(actual_pts)
        return render_template('quiz.html', finished=True, score=pct, points=actual_pts)

    # Rehydrate Word
    target_word = data[step]
    vocab_df = get_df(VOCAB_FILE, VOCAB_COLS)
    row = vocab_df[vocab_df['word'] == target_word]
    
    if not row.empty:
        current_word = row.iloc[0].to_dict()
    else:
        current_word = {col: "" for col in VOCAB_COLS}
        current_word['word'] = target_word
    
    # Determine Hints
    if 'current_hints' not in session or session.get('last_step_index') != step:
        session['last_step_index'] = step
        session['helps_used'] = []
        session['current_hints'] = {
            'synonym': pick_random_item(current_word['synonyms']),
            'antonym': pick_random_item(current_word['antonyms']),
            'example': pick_random_item(current_word['example'])
        }

    active_hints = session.get('current_hints')
    helps_used = session.get('helps_used', [])

    if request.method == 'POST':
        if 'help_action' in request.form:
            help_type = request.form.get('help_action')
            if help_type not in helps_used:
                helps_used.append(help_type)
                session['helps_used'] = helps_used
            return redirect(url_for('quiz_step'))
            
        action = request.form.get('action') 
        points_earned = 0
        is_correct, is_skipped, is_partial = False, False, False
        correct_answer_data = {} 
        penalty = sum([HELP_COSTS[h] for h in helps_used])

        if action == 'skip':
            update_word_stat(current_word['word'], 'skip')
            is_skipped = True
            correct_answer_data = {'type': 1, 'text': current_word['word']}
        else:
            ans = request.form.get('answer', '').strip().lower()
            if ans == "": 
                update_word_stat(current_word['word'], 'skip')
                is_skipped = True
            elif ans == current_word['word'].lower(): 
                is_correct = True
                points_earned = 4 - penalty
            else: 
                points_earned = -1
            
            correct_answer_data = {'type': 1, 'text': current_word['word']}
            
            if is_correct: update_word_stat(current_word['word'], 'correct')
            elif not is_skipped: update_word_stat(current_word['word'], 'wrong')

        session['history_words'].append(current_word['word'])
        session['history_points'].append(points_earned)
        session['total_score_points'] += points_earned
        session['current_step'] += 1
        return render_template('quiz.html', 
                               result=True, 
                               is_correct=is_correct, 
                               is_partial=is_partial, 
                               skipped=is_skipped, 
                               correct_answer=correct_answer_data, 
                               points_earned=points_earned, 
                               next_url=url_for('quiz_step'),
                               word_data=current_word,
                               user_answer=ans if action != 'skip' else None)
                               
    return render_template('quiz.html', finished=False, step=step+1, total=session['total_steps'], word_data=current_word, step_type=1, hints=active_hints, helps_used=helps_used)

@app.route('/data_menu')
def data_menu(): return render_template('data_menu.html')

@app.route('/data/words')
def data_words():
    vocab_df = get_df(VOCAB_FILE, VOCAB_COLS)
    stats_df = get_df(STATS_FILE, STATS_COLS)
    combined_data = []
    vocab_df = vocab_df.sort_values('word')
    for _, row in vocab_df.iterrows():
        w = row['word']
        stat_row = stats_df[stats_df['word'] == w]
        if not stat_row.empty:
            apps, corr, wrong, skipped = int(stat_row.iloc[0]['appearances']), int(stat_row.iloc[0]['correct']), int(stat_row.iloc[0]['wrong']), int(stat_row.iloc[0]['skipped'])
        else: apps, corr, wrong, skipped = 0, 0, 0, 0
        combined_data.append({'word': w, 'details': row.to_dict(), 'stats': {'appearances': apps, 'correct': corr, 'wrong': wrong, 'skipped': skipped}})
    return render_template('words_list.html', words=combined_data)

@app.route('/data/reports')
def data_reports():
    hist_df = get_df(HISTORY_FILE, HISTORY_COLS)
    goals_df = get_df(GOALS_FILE, GOALS_COLS)
    year, month = request.args.get('year', type=int), request.args.get('month', type=int)
    
    if not hist_df.empty:
        hist_df['dt_obj'] = pd.to_datetime(hist_df['date'])
        years = sorted(hist_df['dt_obj'].dt.year.unique(), reverse=True)
    else: years = []
        
    months, history, summary = [], [], None
    if year:
        mask = hist_df['dt_obj'].dt.year == year
        months = [(m, calendar.month_name[m]) for m in sorted(hist_df.loc[mask, 'dt_obj'].dt.month.unique())]
        if month:
            mask = mask & (hist_df['dt_obj'].dt.month == month)
            for r in hist_df[mask].iloc[::-1].to_dict('records'):
                details = []
                for w, p in zip(str(r['words_asked']).split('|'), str(r['points_list']).split('|')):
                    if not w: continue
                    try: p = float(p)
                    except: p = 0
                    if p >= 2: s = 'correct'
                    elif p <= -1: s = 'wrong'
                    else: s = 'skipped'
                    details.append({'text': w, 'status': s, 'points': p})
                r['detailed_results'] = details
                history.append(r)
            
            g_row = goals_df[goals_df['month_key'] == f"{year}-{month:02d}"]
            summary = g_row.iloc[0].to_dict() if not g_row.empty else {'current_points': 0, 'target_points': 0}

    return render_template('reports.html', years=years, months=months, selected_year=year, selected_month=month, history=history, summary=summary)

@app.errorhandler(500)
def internal_error(error): return render_template('500.html'), 500

if __name__ == '__main__':
    window = webview.create_window("Vocap", app, fullscreen=True)
    webview.start()