import time
import json
from datetime import datetime

from aipacenotes.voice import SpeechToText

class Transcript:
    col_count = 5
    table_headers = ["Transcript", "File", "Timestamp", "Source", "Vehicle Position"]

    def __init__(self, src, fname, vehicle_pos, ts=time.time(), txt=None, success=False):
        self.src = src
        self.fname = fname
        self.vehicle_pos = vehicle_pos
        self.ts = ts
        self.txt = txt
        self.success = success

    def as_json(self):
        return  {
            'transcript': self.txt,
            'success': self.success,
            'src': self.src,
            'file': self.fname,
            'timestamp': self.ts,
            'vehicle_pos': self.vehicle_pos,
        }

    def __str__(self):
        return f"{self.txt}, {self.ts}, {self.fname}"

    def fieldAt(self, col):
        if col == 0:
            if self.txt:
                return self.txt
            else:
                return '[processing...]'
        elif col == 1:
            return self.fname
        elif col == 2:
            return datetime.fromtimestamp(self.ts).strftime('%Y-%m-%d %H:%M:%S')
        elif col == 3:
            return self.src
        elif col == 4:
            vp = ""
            if self.vehicle_pos and "pos" in self.vehicle_pos:
                vp = '[' + ', '.join(["{:.1f}".format(v) for v in self.vehicle_pos['pos'].values()]) + ']'

            return vp
        else:
            return None

    def transcribe(self):
        speech = SpeechToText(self.fname)
        # speech.trim_silence()
        txt = speech.transcribe()
        if txt is None:
            txt = "[unknown]"
            self.success = False
        else:
            txt = txt.lower()
            self.success = True
        self.txt = txt

class TranscriptStore:
    transcripts_key = 'transcripts'

    def __init__(self, fname):
        self.fname = fname
        self.load()

    def load(self):
        try:
            with open(self.fname, 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            # If the file doesn't exist, initialize data with default content
            data = {'transcripts': []}

        self.clear()
        for item in data["transcripts"]:
            transcript = Transcript(
                src=item.get("src"),
                fname=item.get("file"),
                vehicle_pos=item.get("vehicle_pos"),
                ts=item.get("timestamp"),
                txt=item.get("transcript"),
                success=item.get("success")
            )
            self.transcripts.append(transcript)

    def __getitem__(self, i):
        return self.transcripts[i]

    def write_to_file(self):
        with open(self.fname, 'w') as f:
            f.write(json.dumps(
                {self.transcripts_key: [tt.as_json() for tt in self.transcripts]},
                indent=4,
            ))

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
