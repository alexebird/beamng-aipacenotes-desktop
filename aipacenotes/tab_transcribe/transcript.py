import time
import logging
import json
from datetime import datetime
import aipacenotes

from aipacenotes.voice import SpeechToText
import aipacenotes.util

class Transcript:
    col_count = 5
    table_headers = ["Text", "File", "Timestamp", "Source", "Vehicle Data"]

    def __init__(self, src, fname, vehicle_data, ts=None, text=None, success=False):
        self.oldId = 0 # needed for loading into beamng
        self.src = src
        self.fname = fname
        self.beam_fname = None
        self.vehicle_data = vehicle_data
        self.ts = ts or time.time()
        self.text = text
        self.success = success

    def as_json(self):
        return  {
            'text': self.text,
            'success': self.success,
            'src': self.src,
            'file': self.fname,
            'beamng_file': self.beam_fname,
            'timestamp': self.ts,
            'vehicle_data': self.vehicle_data,
            'oldId': self.oldId,
        }

    def as_json_for_recce_app(self):
        return  {
            'text': self.text,
            'success': self.success,
        }

    def set_oldId(self, oldId):
        self.oldId = oldId

    def set_beam_fname(self, beam_user_home):
        self.beam_fname = self.fname.replace(beam_user_home, '')

    def __str__(self):
        return f"{self.text}, {self.ts}, {self.fname}"

    def fieldAt(self, col):
        if col == 0:
            if self.text:
                return self.text
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

            # "vehicle_data": {
            #     "capture_data": {
            #         "captures": {},
            #         "cornerAnglesStyle": "1(hard) to 6(easy)"
            #     },
            #     "vehicle_data": {
            #         "quat": {
            #             "y": -0.0064838185654324,
            #             "z": -0.26087964948587,
            #             "x": -0.029585562473837,
            #             "w": 0.96489608926249
            #         },
            #         "pos": {
            #             "x": 491.815979,
            #             "y": -417.3897095,
            #             "z": 129.1630402
            #         }
            #     }
            # },

            if self.vehicle_data:
                # vp = '[' + ', '.join(["{:.1f}".format(v) for v in self.vehicle_data['pos'].values()]) + ']'
                veh_data = self.vehicle_data.get('vehicle_data', {})
                vals = []

                pos = veh_data.get('pos', None)
                if pos:
                    val = ','.join([f"{k}={v:.1f}" for k,v in pos.items()])
                    vals.append(f"pos=[{val}]")

                quat = veh_data.get('quat', None)
                if quat:
                    val = ','.join([f"{k}={v:.1f}" for k,v in quat.items()])
                    vals.append(f"rot=[{val}]")

                capture_data = self.vehicle_data.get('capture_data', {})

                style = capture_data.get('cornerAnglesStyle', None)
                if style:
                    vals.append(f"corners='{style}'")

                captures = capture_data.get('captures', None)
                if captures is not None:
                    vals.append(f"#captures={len(captures)}")

                vp = ' | '.join(vals)

            return vp
        else:
            return None

    def transcribe(self):
        speech = SpeechToText(self.fname)
        text = speech.transcribe()
        if text is None:
            text = aipacenotes.util.UNKNOWN_PLACEHOLDER
            self.success = False
        else:
            text = text.lower()
            self.success = True
        self.text = text

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
            data = {self.transcripts_key: []}

        self.clear()
        for item in data[self.transcripts_key]:
            transcript = Transcript(
                src=item.get("src"),
                fname=item.get("file"),
                vehicle_data=item.get("vehicle_data"),
                ts=item.get("timestamp"),
                text=item.get("text"),
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
        logging.debug(f"--------------------")
        logging.debug(f"TranscriptStore")
        logging.debug(f"  len={self.size()}")
        for t in self.transcripts:
            logging.debug(f"  - {t}")

    def add(self, transcript):
        transcript.set_oldId(len(self.transcripts))
        self.transcripts.append(transcript)
        self.sort()

    def sort(self):
        self.transcripts.sort(key=lambda x: x.ts, reverse=False)

    def get_latest(self, count):
        transcripts = [t for t in self.transcripts if t.text is not None]
        rv = transcripts[-count:]
        rv.reverse()
        return rv
