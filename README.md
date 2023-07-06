call C:\Users\bird\.virtualenvs\aipacenotes\Scripts\activate.bat
pyinstaller "AI Pacenotes.spec"
python app.py
curl -H'Content-type: application/json' https://pacenotes-concurrent-mo5q6vt2ea-uw.a.run.app/pacenotes/audio/create -d'{"note_text":"hello there little nuggest","voice_name":"en-GB-Neural2-D","language_code":"en-GB"}' -otmp/out.ogg