AI Pacenotes Desktop App
===

USAGE
---

1. open a windows command prompt terminal
2. cd to the repo
3. activate virtualenv. run:

    ```
    call C:\Users\bird\.virtualenvs\aipacenotes\Scripts\activate.bat
    ```
4. run app:

    ```
    python app.py
    ```

PACKAGING
---

This windows GUI app watches your BeamNG.drive user folder for pacenotes.json files, and creates audio files from pacenote text.

Used by the [AI Pacenotes](https://www.beamng.com/resources/a-i-rally-pacenotes.27352/) mod.

```
call C:\Users\bird\.virtualenvs\aipacenotes\Scripts\activate.bat
pyinstaller "AI Pacenotes.spec"
python app.py
curl -H'Content-type: application/json' https://pacenotes-concurrent-mo5q6vt2ea-uw.a.run.app/pacenotes/audio/create -d'{"note_text":"hello there little nuggest","voice_name":"en-GB-Neural2-D","language_code":"en-GB"}' -otmp/out.ogg
```
