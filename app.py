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
    <h2>Upload Excel File (Client VAST Tag Sheet)</h2>
    <form method="POST" action="/process" enctype="multipart/form-data">
        Upload Excel file: <input type="file" name="file"><br><br>
        <input type="submit" value="Upload and Process">
    </form>
    '''

@app.route('/process', methods=['POST'])
def process_file():
    uploaded_file = request.files.get('file')

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

        df.insert(len(df.columns), 'CACHEBUSTED Tag', df['tag'].apply(
            lambda x: re.sub(r'\[timestamp\]', '%%CACHEBUSTER%%', str(x), flags=re.IGNORECASE)
        ))

        output_path = os.path.join(PROCESSED_FOLDER, "processed_" + uploaded_file.filename)
        df.to_excel(output_path, index=False)

        return send_file(output_path, as_attachment=True)

    return "❌ Invalid file. Please upload a .xlsx file."

if __name__ == '__main__':
    app.run(debug=True)
