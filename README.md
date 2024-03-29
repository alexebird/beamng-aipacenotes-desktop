AI Pacenotes Desktop App
===

USAGE
---

1. open a windows command prompt terminal
2. cd to the repo, activate virtualenv, run.
```
cd C:\Users\bird\Desktop\beam-bird\gh_repos\beamng-aipacenotes-desktop
.\aip\Scripts\activate
set AIP_DEV=t
python app.py
python app.py --local-vocalizer
```

PACKAGING
---

### Non-exe-style distribution:
```
cd C:\Users\bird\Documents\GitHub\beamng-aipacenotes-desktop
.\aip\Scripts\activate
python app.py
```

### exe-style distribution

This windows GUI app watches your BeamNG.drive user folder for pacenotes.json files, and creates audio files from pacenote text.

Used by the [AI Pacenotes](https://www.beamng.com/resources/a-i-rally-pacenotes.27352/) mod.

```
# in Windows Command Prompt shell
call C:\Users\bird\.virtualenvs\aipacenotes\Scripts\activate.bat
pyinstaller "AI-Pacenotes.spec"

# after pyinstaller is done, in ubuntu shell
mv dist/AI-Pacenotes-Desktop.exe "dist/AI-Pacenotes-Desktop-$(git describe --tags --exact-match HEAD).exe"
```

```
python app.py
curl -H'Content-type: application/json' https://pacenotes-concurrent-mo5q6vt2ea-uw.a.run.app/pacenotes/audio/create -d'{"note_text":"hello there little nuggest","voice_name":"en-GB-Neural2-D","language_code":"en-GB"}' -otmp/out.ogg
```

virtualenvs
---

Creation (windows):

```
cd C:\Users\bird\Desktop\beam-bird\gh_repos\beamng-aipacenotes-desktop
python -m venv aip
.\aip\Scripts\activate
pip install -r requirements.txt
```

Mac
```
pip install virtualenv
virtualenv aip
source aip/bin/activate
pip install -r requirements.txt
```
