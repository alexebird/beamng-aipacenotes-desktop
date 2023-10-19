import wave
import time
import struct
import logging
import sys
import os
import tempfile
import queue

from PyQt6.QtCore import QThread, pyqtSignal

import sounddevice as sd
import soundfile as sf
import numpy as np

from . import Transcript, TranscriptStore

class RecordingThread(QThread):
    update_status = pyqtSignal(str)
    # update_transcription = pyqtSignal(str)
    # source, fname, vehicle_pos dict
    recording_file_created = pyqtSignal(str, str, float, object)
    transcript_created = pyqtSignal(Transcript)
    audio_signal_detected = pyqtSignal(bool)

    def __init__(self, settings_manager):
        super(RecordingThread, self).__init__()

        self.settings_manager = settings_manager
        self.startup_error = False

        try:
            self.device = self.get_default_audio_device()
        except sd.PortAudioError as e:
            print("startup error in RecordingThread")
            self.startup_error = True

        self.samplerate = 16000
        self.channels = 1

        self.f_out = None
        
        self.should_record = False
        self.should_monitor = True
        self.q = queue.Queue()

        self.setup_tmp_dir()
    
    def shouldMonitor(self, on):
        self.should_monitor = on

    def setup_tmp_dir(self):
        if os.environ.get('AIP_DEV', 'f') == 't':
            self.tmpdir = 'tmp\\audio'
        else:
            self.tmpdir = self.settings_manager.get_tmpdir()

        for filename in os.listdir(self.tmpdir):
            file_path = os.path.join(self.tmpdir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    
    def get_default_audio_device(self):
        self.device = sd.query_devices(None, 'input')
        return [self.device]
    
    def analyze_frame_for_monitor(self, frame, threshold=0.001):
        # Assuming frame is a NumPy array
        rms = np.sqrt(np.mean(np.square(frame)))

        if rms > threshold:
            return True  # Activate the monitor dot
        else:
            return False  # Deactivate the monitor dot
    
    def buffer_audio_in(self):
        def callback(indata, frames, time, status):
            """This is called (from a separate thread) for each audio block."""
            if status:
                print(f"buffer_audio_in: {status}")
            if self.should_monitor or self.should_record:
                self.q.put(indata.copy())
        
        t_monitor_update = time.time()
        monitor_update_limit_seconds = 0.1

        # print(self.device)
        with sd.InputStream(samplerate=self.samplerate, device=int(self.device['index']), channels=self.channels, callback=callback):
            while self.isInterruptionRequested() == False:
                audio_data = None
                while not self.q.empty():
                    frame = self.q.get()
                    if audio_data is None:
                        audio_data = np.empty((0,frame.shape[1]), dtype=frame.dtype)
                    audio_data = np.concatenate((audio_data, frame))

                if audio_data is None:
                    continue

                t_now = time.time()
                if self.should_monitor and t_now - t_monitor_update > monitor_update_limit_seconds:
                    self.audio_signal_detected.emit(self.analyze_frame_for_monitor(audio_data))
                    t_monitor_update = t_now

                if self.should_record:
                    try:
                        if self.f_out.closed:
                            logging.warn('f_out is closed')
                        self.f_out.write(audio_data)
                    except sf.SoundFileRuntimeError as e:
                        logging.error(e)

                    # i dont really understand why this is needed, but without it, the UI gets blocked.
                    QThread.msleep(10)
                else:
                    # dont let the thread eat up cpu
                    QThread.msleep(100)
    
    def run(self):
        if self.startup_error:
            logging.error("startup_error is true, so not starting main loop")
            return

        try:
            self.buffer_audio_in()
        except Exception as e:
            logging.exception("RecordingThread error")
            self.update_status.emit(f"Error: {str(e)}")
    
    def start_recording(self):
        logging.debug("start_recording")
        self.fname_out = tempfile.mktemp(prefix='out_', suffix='.wav', dir=self.tmpdir)
        self.f_out = sf.SoundFile(self.fname_out, mode='x', samplerate=self.samplerate, channels=self.channels)
        self.should_record = True
        self.update_status.emit("recording...")
        return self.fname_out
        
    def stop_recording(self, src, vehicle_pos=None):
        logging.debug("stop_recording")
        self.should_record = False
        if self.f_out:
            self.f_out.close()
            # print(src)
            # print(self.fname_out)
            # print(vehicle_pos)
            transcript = Transcript(src, self.fname_out, vehicle_pos)
            self.transcript_created.emit(transcript)
            # self.recording_file_created.emit(src, self.fname_out, t_now, vehicle_pos)
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