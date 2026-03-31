import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app) 

UPLOAD_FOLDER = 'temp_audio'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---> PASTE YOUR API KEYS HERE <---
DEEPGRAM_API_KEY = 'd38d50c2a0d4ad4e00a84712655f70e2d7fdaeec'
SUPABASE_URL = 'https://qovvautzbdxiwojeriew.supabase.co '
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFvdnZhdXR6YmR4aXdvamVyaWV3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyMTE4ODYsImV4cCI6MjA4ODc4Nzg4Nn0.-wUSAHVQoCW5kw-3nguM1AqlriGLMv38WRKImNkHC-0'

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
        
    file = request.files['file']
    # NEW: Grab the user_id if the frontend sent one
    user_id = request.form.get('user_id') 
    
    if file.filename == '':
        return jsonify({'error': 'Empty file name'}), 400
        
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    
    try:
        with open(path, 'rb') as audio_file:
            url = 'https://api.deepgram.com/v1/listen?model=nova-2'
            headers = {
                'Authorization': f'Token {DEEPGRAM_API_KEY}',
                'Content-Type': 'audio/webm'
            }
            response = requests.post(url, headers=headers, data=audio_file)
            response.raise_for_status()
            data = response.json()
            transcript = data['results']['channels'][0]['alternatives'][0]['transcript']
            
            if transcript.strip(): 
                # NEW: Prepare the data to save
                data_to_insert = {"text": transcript}
                if user_id:
                    data_to_insert["user_id"] = user_id # Attach the user ID!
                    
                supabase.table("transcripts").insert(data_to_insert).execute()
            
            return jsonify({
                'status': 'success', 
                'message': transcript, 
            })
            
    except Exception as e:
        print("Error during transcription:", e)
        return jsonify({'error': 'Failed to transcribe audio.'}), 500

@app.route('/transcripts', methods=['GET'])
def get_transcripts():
    try:
        # NEW: Check if a specific user is requesting their history
        user_id = request.args.get('user_id')
        
        query = supabase.table("transcripts").select("*")
        
        # If we have a user_id, filter the database to ONLY show their transcripts
        if user_id:
            query = query.eq("user_id", user_id)
            
        response = query.order("created_at", desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        print("Error fetching transcripts:", e)
        return jsonify({'error': 'Failed to fetch history.'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)