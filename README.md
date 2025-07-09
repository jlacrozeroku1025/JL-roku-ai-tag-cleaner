from flask import Flask, request, send_file
import os
import pandas as pd
import re

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
ALLOWED_EXTENSIONS = {'xlsx'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Roku Tag Cleaner</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f4f4;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                background: #fff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                text-align: center;
                width: 420px;
            }
            h2 {
                margin-top: 0;
            }
            input[type="file"] {
                margin: 20px 0;
            }
            input[type="submit"] {
                background-color: #0055ff;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                cursor: pointer;
            }
            input[type="submit"]:hover {
                background-color: #0041c4;
            }
            label {
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>👻 Roku Tag Cleaner</h2>
            <form method="POST" action="/process" enctype="multipart/form-data">
                <input type="file" name="file" required><br>
                <label>
                    <input type="checkbox" name="apply_kids_fix" checked>
                    Apply Kids Content Compliance
                </label><br><br>
                <input type="submit" value="Upload & Clean Tags">
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/process', methods=['POST'])
def process_file():
    uploaded_file = request.files.get('file')
    apply_kids_fix = request.form.get('apply_kids_fix') == 'on'

    if uploaded_file and allowed_file(uploaded_file.filename):
        filepath = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        uploaded_file.save(filepath)

        df = pd.read_excel(filepath, header=None)

        placement_id_col = None
        tag_col = None

        for col in df.columns:
            sample_values = df[col].astype(str).head(20).str.lower()

            if placement_id_col is None and sample_values.str.match(r'^\d{5,}$').any():
                placement_id_col = col

            if tag_col is None and sample_values.str.contains('timestamp').any():
                tag_col = col

        if placement_id_col is None or tag_col is None:
            return "❌ Could not find 'Placement ID' or 'Tag' column. Please check the file layout."

        df = df.rename(columns={
            placement_id_col: 'placement_id',
            tag_col: 'tag'
        })

        df.insert(len(df.columns), 'Placement ID Mapping', df['placement_id'])

        df['tag_replaced'] = df['tag'].apply(replace_tags)

        df[['TAG (👻 CACHEBUSTED)', 'Tag Notes']] = df['tag_replaced'].apply(
            lambda x: pd.Series(fix_child_directed_tag(x, apply_kids_fix))
        )

        df.drop(columns=['tag_replaced'], inplace=True)

        output_path = os.path.join(PROCESSED_FOLDER, "processed_" + uploaded_file.filename)
        df.to_excel(output_path, index=False)

        return send_file(output_path, as_attachment=True)

    return "❌ Invalid file. Please upload a .xlsx file."


def replace_tags(text):
    text = str(text)
    # BrightLine, DCM, and DoubleVerify macro replacements
    text = re.sub(r'\[timestamp\]', '%%CACHEBUSTER%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[correlator\]', '%%CACHEBUSTER%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[ord\]', '%%CACHEBUSTER%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[random\]', '%%RANDOM%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[campaignid\]', '%%CAMPAIGN_ID%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[device\]', '%%DEVICE%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[placement\]', '%%PLACEMENT%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[user_id\]', '%%USER_ID%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[gdid\]', '%%GDID%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[adid\]', '%%AD_ID%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[dv_tagid\]', '%%DV_TAGID%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[dv_userid\]', '%%DV_USERID%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[dv_campaign\]', '%%DV_CAMPAIGN%%', text, flags=re.IGNORECASE)
    text = re.sub(r'\[dv_random\]', '%%RANDOM%%', text, flags=re.IGNORECASE)
    return text

def fix_child_directed_tag(tag, apply_fix):
    tag = str(tag)
    notes = []

    if 'doubleclick.net' in tag.lower() or 'dcm.net' in tag.lower():
        if apply_fix:
            if 'tag_for_child_directed_treatment=' in tag.lower():
                tag = re.sub(r'tag_for_child_directed_treatment=[^;?&]*', 'tag_for_child_directed_treatment=1', tag, flags=re.IGNORECASE)
                notes.append("✔️ Set tag_for_child_directed_treatment=1")
            if 'tfua=' in tag.lower():
                tag = re.sub(r'tfua=[^;?&]*', 'tfua=1', tag, flags=re.IGNORECASE)
                notes.append("✔️ Set tfua=1")
            if notes:
                return tag, 'DCM tag auto-updated for Kids Content: ' + ' & '.join(notes)
        else:
            return tag, '⚠️ DCM tag detected (no kids fix applied)'
    return tag, ''

if __name__ == '__main__':
    app.run(debug=True)
