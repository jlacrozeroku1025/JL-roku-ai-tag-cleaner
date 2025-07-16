from flask import Flask, request, send_file
import os
import pandas as pd
import re
import urllib.parse

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
    <title>Roku Tag Cleaner</title>
    <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .container { background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; width: 420px; }
    h2 { margin-top: 0; }
    input[type='file'] { margin: 20px 0; }
    input[type='submit'] { background-color: #0055ff; color: white; padding: 10px 20px; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; }
    input[type='submit']:hover { background-color: #0041c4; }
    label { font-size: 14px; }
    </style>
    </head>
    <body>
    <div class="container">
        <h2>👻 Roku Tag Cleaner</h2>
        <form method='POST' action='/process' enctype='multipart/form-data'>
            <input type='file' name='file' required><br>
            <label>
                <input type='checkbox' name='apply_kids_fix'> Apply Kids Compliance (DCM only)
            </label><br><br>
            <input type='submit' value='Upload & Clean Tags'>
        </form>
    </div>
    </body>
    </html>
    """

@app.route('/process', methods=['POST'])
def process_file():
    try:
        uploaded_file = request.files.get('file')
        apply_kids_fix = request.form.get('apply_kids_fix') == 'on'

        if not uploaded_file or uploaded_file.filename == '':
            return "❌ No file uploaded.", 400

        if not allowed_file(uploaded_file.filename):
            return "❌ Invalid file format. Only .xlsx, .xls, .csv allowed.", 400

        filepath = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        uploaded_file.save(filepath)

        ext = uploaded_file.filename.rsplit('.', 1)[1].lower()

        if ext == 'csv':
            df = pd.read_csv(filepath, header=0)
        else:
            df = pd.read_excel(filepath, header=0)

        # Flexible column matching
        col_map = {col.lower().strip(): col for col in df.columns}
        placement_col = next((col_map[c] for c in col_map if 'placement' in c and 'id' in c), None)
        tag_col = next((col_map[c] for c in col_map if 'tag' in c), None)

        if not placement_col or not tag_col:
            return "❌ Could not find 'Placement ID' or 'TAG' column.", 400

        df = df.rename(columns={placement_col: 'PLACEMENT ID', tag_col: 'TAG'})
        df['PLACEMENT ID MAPPING'] = df['PLACEMENT ID']
        df['TAG (👻 BUSTED)'] = df['TAG'].apply(lambda x: clean_tag(str(x), apply_kids_fix)[0])
        df['Tag Notes'] = df['TAG'].apply(lambda x: clean_tag(str(x), apply_kids_fix)[1])

        output_path = os.path.join(PROCESSED_FOLDER, "processed_" + uploaded_file.filename)
        df.to_excel(output_path, index=False)

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return f"❌ Internal Server Error: {str(e)}", 500

def clean_tag(tag, apply_kids_fix):
    notes = []

    # Remove <img src="...">
    if '<img' in tag.lower():
        match = re.search(r'src\s*=\s*"(.*?)"', tag, re.IGNORECASE)
        if match:
            tag = match.group(1)
            notes.append("HTML img wrapper removed")

    # Unquote VAST param
    if '_vast=' in tag:
        tag = urllib.parse.unquote(tag)

    # Replace macros (including variations)
    tag = re.sub(r'\[timestamp\]|\[ord\]|\[correlator\]|\[cachebuster\]', '%%CACHEBUSTER%%', tag, flags=re.IGNORECASE)
    tag = re.sub(r'\[random\]', '%%RANDOM%%', tag, flags=re.IGNORECASE)
    tag = re.sub(r'\[campaignid\]', '%%CAMPAIGN_ID%%', tag, flags=re.IGNORECASE)
    tag = re.sub(r'\[device\]', '%%DEVICE%%', tag, flags=re.IGNORECASE)
    tag = re.sub(r'\[placement\]', '%%PLACEMENT%%', tag, flags=re.IGNORECASE)
    tag = re.sub(r'\[user_id\]', '%%USER_ID%%', tag, flags=re.IGNORECASE)
    tag = re.sub(r'\[gdid\]', '%%GDID%%', tag, flags=re.IGNORECASE)
    tag = re.sub(r'\[adid\]', '%%AD_ID%%', tag, flags=re.IGNORECASE)

    # Fix various broken cachebuster macros (buster/breaker)
    tag = re.sub(
        r'(\[|\{)INSERT_CACHEB(USTER|REAKER)_HERE(\]|\})|INSERT CACHEB(USTER|REAKER)|%REPLACE-TIMESTAMP-MACRO%',
        '%%CACHEBUSTER%%',
        tag,
        flags=re.IGNORECASE
    )

    # Nielsen
    if 'imrworldwide.com' in tag:
        tag = tag.strip('"')
        notes.append("Nielsen tag cleaned")

    # Flashtalking
    if 'servedby.flashtalking.com' in tag:
        tag = re.sub(r'\[CACHEBUSTER\]', '%%CACHEBUSTER%%', tag, flags=re.IGNORECASE)
        notes.append("Flashtalking macros updated")

    # DCM kids fix
    if apply_kids_fix and ('doubleclick.net' in tag.lower() or 'dcm.net' in tag.lower()):
        tag = re.sub(r'tag_for_child_directed_treatment=[^;&?]*', 'tag_for_child_directed_treatment=1', tag, flags=re.IGNORECASE)
        tag = re.sub(r'tfua=[^;&?]*', 'tfua=1', tag, flags=re.IGNORECASE)
        notes.append("Kids compliance applied")

    # Extreme Reach
    if 'extremereach.io' in tag:
        notes.append("Extreme Reach macros updated")

    # Sizmek / MediaMind
    if 'serving-sys.com' in tag or 'mediamind.com' in tag or 'sizmek.com' in tag:
        tag = re.sub(r'\[timestamp\]', '%%CACHEBUSTER%%', tag, flags=re.IGNORECASE)
        if '^' in tag:
            tag = tag.replace('^', '%5E')
            notes.append("Replaced ^ with %5E for Sizmek compliance")
        notes.append("Sizmek tag cleaned")

    return tag, "; ".join(set(notes)) or "Macros updated"

if __name__ == '__main__':
    app.run(debug=True)
