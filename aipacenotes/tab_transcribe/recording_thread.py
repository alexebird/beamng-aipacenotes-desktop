import wave
import struct
import logging
import re
import sys
import time
import os
import shutil
from pvrecorder import PvRecorder
from PyQt6.QtCore import QThread, pyqtSignal

from aipacenotes.settings import (
    replace_vars, 
    expand_windows_symlinks,
)

import argparse
import tempfile
import queue
import sys

import sounddevice as sd
import soundfile as sf
import numpy  # Make sure NumPy is loaded before it is used in the callback
assert numpy  # avoid "imported but unused" message (W0611)


class RecordingThread(QThread):
    update_status = pyqtSignal(str)
    # update_transcription = pyqtSignal(str)
    # source, fname, vehicle_pos dict
    recording_file_created = pyqtSignal(str, str, object)

    def __init__(self, device_name_substring):
        super(RecordingThread, self).__init__()
        # self.fname_transcription = fname_transcription
        # self.audio_out_fname = 'out.wav'
        # self.device_idx = None
        # self.device_name = None
        # self.device_name_substring = device_name_substring
        # self._detect_device()

        self.device = self.get_default_audio_device()
        self.samplerate = 16000
        self.channels = 1

        self.f_out = None
        
        # self.recorder = None
        self.should_record = False
        # self.reset_audio_buffer()
        self.q = queue.Queue()

        self.setup_tmp_dir()

    def setup_tmp_dir(self):
        if os.environ.get('AIP_DEV', 'f') == 't':
            self.tmpdir = 'tmp/audio'
        else:
            tmpdir = '$HOME/AppData/Local/BeamNG.drive/latest/temp/aipacenotes'
            tmpdir = replace_vars(tmpdir)
            tmpdir = expand_windows_symlinks(tmpdir)
            self.tmpdir = tmpdir

        print(f'tempdir={self.tmpdir}')
        os.makedirs(self.tmpdir, exist_ok=True)

        for filename in os.listdir(self.tmpdir):
            file_path = os.path.join(self.tmpdir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    
    def reset_audio_buffer(self):
        # self.audio_buffer = []
        self.q = queue.Queue()

    def query_devices(self):
        device_info = sd.query_devices(None, 'input')
        print(sd.default.device)
        device_info = sd.query_devices()
        # devices = []
        # for
        return device_info

    def get_default_audio_device(self):
        self.device = sd.query_devices(None, 'input')
        # print(self.device)
        # print(sd.default.device)
        # device_info = sd.query_devices()
        # devices = []
        # for
        return [self.device]
    
    # def _detect_device(self):
    #     for index, device in enumerate(PvRecorder.get_available_devices()):
    #         # match = re.search(r"USB Audio Device", str(device))
    #         # if match:
    #         if self.device_name_substring in str(device):
    #             print(f"using device [{index}]{device}")
    #             self.device_idx = index
    #             break

    #     if self.device_idx == -1:
    #         self.update_status.emit(f"Couldn't find device matching '{self.device_name_substring}'")
    
    # def read_frame(self):
    #     frame = self.recorder.read()
    #     self.audio_buffer.extend(frame)

    # def run(self):
    #     print("RecordingThread starting")
    #     try:
    #         while self.isInterruptionRequested() == False:
    #             if self.should_record:
    #                 self.read_frame()
    #             else:
    #                 # dont let the thread eat up cpu
    #                 QThread.msleep(100)
    #     except Exception as e:
    #         print("RecordingThread error")
    #         print(e)
    #         self.update_status.emit(f"Error: {str(e)}")
    #     # finally:
    #         # self.update_status.emit("recording...done")
    #         # self.update_status.emit("transcribing...")
    #         # recorder.stop()
    #         # with wave.open(self.audio_out_fname, 'w') as f:
    #         #     f.setparams((1, 2, 16000, 512, "NONE", "NONE"))
    #         #     f.writeframes(struct.pack("h" * len(audio), *audio))
    #         # recorder.delete()
    #         # self.transcribe(self.audio_out_fname)
    #         # self.update_status.emit("idle")

    # def _getq(self):
        # return self.q

    def run(self):
        try:
            # print(self.device)
            def callback(indata, frames, time, status):
                """This is called (from a separate thread) for each audio block."""
                if status:
                    print(status, file=sys.stderr)
                self.q.put(indata.copy())

            with sd.InputStream(samplerate=self.samplerate, device=int(self.device['index']), channels=self.channels, callback=callback):
                    while self.isInterruptionRequested() == False:
                        frame = self.q.get()
                        # print(frame)
                        if self.should_record:
                            # print(self.q.qsize())
                            try:
                                if self.f_out.closed:
                                    print('closed')
                                self.f_out.write(frame)
                            except sf.SoundFileRuntimeError as e:
                                print(e)
                                pass
                        else:
                            # dont let the thread eat up cpu
                            QThread.msleep(100)
        # except KeyboardInterrupt:
            # print('\nRecording finished: ' + repr(args.filename))
            # parser.exit(0)
        # except Exception as e:
            # parser.exit(type(e).__name__ + ': ' + str(e))
        except Exception as e:
            print("RecordingThread error")
            logging.exception("RecordingThread error")
            self.update_status.emit(f"Error: {str(e)}")
    
    def start_recording(self):
        self.fname_out = tempfile.mktemp(prefix='out_', suffix='.wav', dir=self.tmpdir)
        self.f_out = sf.SoundFile(self.fname_out, mode='x', samplerate=self.samplerate, channels=self.channels)
        self.should_record = True
        self.update_status.emit("recording...")
        return self.fname_out
        
    def stop_recording(self, src, vehicle_pos=None):
        self.should_record = False
        if self.f_out:
            self.f_out.close()
            # print(src)
            # print(self.fname_out)
            # print(vehicle_pos)
            self.recording_file_created.emit(src, self.fname_out, vehicle_pos)
        else:
            self.f_out = None
        self.update_status.emit("ready")

    def stop(self):
        print("RecordingThread stopping")
        self.requestInterruption()

    def write_audio_buffer(self, out_fname):
        with wave.open(out_fname, 'w') as f:
            # f.setparams(args) explained:
            # 1. Number of Channels: 1 indicates that this is a mono audio file. For stereo, you would use 2.
            # 2. Sample Width: 2 means that each sample is 2 bytes. This is often called 16-bit audio because 2 bytes * 8 bits/byte = 16 bits.
            # 3. Frame Rate: 16000 specifies that the sample rate is 16,000 samples per second. This is a common sample rate for speech audio.
            # 4. Number of Frames: 512 is the number of frames in the output. Note that in a real-world application, this would typically be set to the actual number of frames in the audio data you're writing.
            # 5. Compression Type: "NONE" means that the audio is not compressed.
            # 6. Compression Name: "NONE" is the human-readable name for the compression type, which is also none in this case.
            f.setparams((1, 2, 16000, 512, "NONE", "NONE"))
            f.writeframes(struct.pack("h" * len(self.audio_buffer), *self.audio_buffer))
        return out_fname

    # def run_old(self):
    #     # print("RecordingThread starting")
    #     # device_idx = -1
    #     audio = []
    #     frame_length = 512
    #     recorder = PvRecorder(device_index=self.device_idx, frame_length=frame_length)

    #     try:
    #         recorder.start()
    #         # start_ts = time.time()
    #         # reset_timeout_sec = 30
    #         self.update_status.emit("recording...")

    #         while self.isInterruptionRequested() == False:
    #             # now_ts = time.time()
    #             # if now_ts - start_ts > reset_timeout_sec:
    #                 # dont let audio recordings go on too long. if it has been too long, its probably idle so just throw away the data.
    #                 # audio = []

    #             frame = recorder.read()
    #             audio.extend(frame)
    #         self.update_status.emit("transcribing...")
    #     except Exception as e:
    #         print(e)
    #         self.update_status.emit(f"Error: {str(e)}")

    #     finally:
    #         # self.update_status.emit("recording...done")
    #         self.update_status.emit("transcribing...")
    #         recorder.stop()
    #         with wave.open(self.audio_out_fname, 'w') as f:
    #             f.setparams((1, 2, 16000, 512, "NONE", "NONE"))
    #             f.writeframes(struct.pack("h" * len(audio), *audio))
    #         recorder.delete()
    #         self.transcribe(self.audio_out_fname)
    #         self.update_status.emit("idle")