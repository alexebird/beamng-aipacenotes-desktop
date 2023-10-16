import wave
import struct
import re
import sys
import time
from pvrecorder import PvRecorder
from PyQt6.QtCore import QThread, pyqtSignal

from aipacenotes.voice import SpeechToText

class RecordingThread(QThread):
    update_status = pyqtSignal(str)
    update_transcription = pyqtSignal(str)

    def __init__(self, fname_transcription):
        super(RecordingThread, self).__init__()
        self.fname_transcription = fname_transcription

    def run(self):
        print("RecordingThread starting")
        device_idx = -1
        audio = []
        path = 'out.wav'

        for index, device in enumerate(PvRecorder.get_available_devices()):
            match = re.search(r"USB Audio Device", str(device))
            if match:
                print(f"using device [{index}]{device}")
                device_idx = index
                break

        if device_idx == -1:
            self.update_status.emit("Couldn't find device")
            return

        recorder = PvRecorder(device_index=device_idx, frame_length=512)

        try:
            recorder.start()
            start_ts = time.time()
            # reset_timeout_sec = 30
            self.update_status.emit("recording...")

            while self.isInterruptionRequested() == False:
                # now_ts = time.time()
                # if now_ts - start_ts > reset_timeout_sec:
                    # dont let audio recordings go on too long. if it has been too long, its probably idle so just throw away the data.
                    # audio = []

                frame = recorder.read()
                audio.extend(frame)
            self.update_status.emit("transcribing...")
        except Exception as e:
            print(e)
            self.update_status.emit(f"Error: {str(e)}")

        finally:
            # self.update_status.emit("recording...done")
            self.update_status.emit("transcribing...")
            recorder.stop()
            with wave.open(path, 'w') as f:
                f.setparams((1, 2, 16000, 512, "NONE", "NONE"))
                f.writeframes(struct.pack("h" * len(audio), *audio))
            recorder.delete()
            self.transcribe(path)
            self.update_status.emit("idle")

    def stop(self):
        print("RecordingThread stopping")
        self.requestInterruption()

    def transcribe(self, fname):
        speech = SpeechToText(fname)
        # self.update_status.emit("trimming silence...")
        speech.trim_silence()
        # self.update_status.emit("transcribing...")
        txt = speech.transcribe()
        # self.update_status.emit("transcribing...done")
        self.append_transcript(txt)
        self.update_transcription.emit(txt)
        # return txt
    
    def append_transcript(self, text):
        if isinstance(text, str):
            with open(self.fname_transcription, 'a') as f:
                f.write(text + '\n')