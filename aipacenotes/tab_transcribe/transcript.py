import time
import json
from datetime import datetime

from aipacenotes.voice import SpeechToText

class Transcript:
    col_count = 3
    table_headers = ["Transcript", "Timestamp", "File"]

    def __init__(self, src, fname, vehicle_pos):
        self.ts = time.time()
        self.src = src
        self.fname = fname
        self.vehicle_pos = vehicle_pos
        self.txt = None

    def as_json(self):
        return  {
            '_transcript': self.txt,
            '_src': self.src,
            '_file': self.fname,
        }
    
    def __str__(self):
        return f"{self.txt}, {self.ts}, {self.fname}"
    
    def fieldAt(self, col):
        if col == 0:
            return self.txt
        elif col == 1:
            return datetime.fromtimestamp(self.ts).strftime('%Y-%m-%d %H:%M:%S')
        elif col == 2:
            return self.fname
        else:
            return None

    def transcribe(self, done_signal=None):
        speech = SpeechToText(self.fname)
        speech.trim_silence()
        txt = speech.transcribe() or "[unknown]"
        txt = txt.lower()
        self.txt = txt

        # if self.vehicle_pos:
            # self.vehicle_pos['_src'] = self.src
            # self.vehicle_pos['_file'] = self.fname
            # self.vehicle_pos['_transcript'] = txt
            # self.append_vehicle_pos(self.vehicle_pos, txt + " || ")
        # else:
            # self.append_transcript(txt)
        
        # self.update_transcription_txt.emit()
        # if done_signal:
        #     done_signal.emit()

class TranscriptStore:
    def __init__(self):
        self.clear()
    
    def __getitem__(self, i):
        return self.transcripts[i]

    def write_to_file(self, fname):
        with open(fname, 'w') as f:
            for tt in self.transcripts:
                f.write(json.dumps(tt.as_json()) + '\n')
    
    def size(self):
        return len(self.transcripts)
    
    def clear(self):
        self.transcripts = []

    def print(self):
        print(f"--------------------")
        print(f"TranscriptStore")
        print(f"  len={self.size()}")
        for t in self.transcripts:
            print(f"  - {t}")
    
    def add(self, transcript):
        self.transcripts.append(transcript)
        self.sort()
    
    def sort(self):
        self.transcripts.sort(key=lambda x: x.ts, reverse=False)