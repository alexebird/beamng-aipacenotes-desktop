import logging
import os
import queue
import tempfile
import time

from PyQt6.QtCore import QThread, pyqtSignal
import sounddevice as sd
import soundfile as sf
import numpy as np

import aipacenotes
import aipacenotes.util
from . import Transcript

class RecordingThread(QThread):
    update_recording_status = pyqtSignal(bool)
    # update_transcription = pyqtSignal(str)
    # source, fname, vehicle_pos dict
    recording_file_created = pyqtSignal(str, str, float, object)
    transcript_created = pyqtSignal(Transcript)
    audio_signal_detected = pyqtSignal(bool)

    def __init__(self, settings_manager):
        super(RecordingThread, self).__init__()

        self.settings_manager = settings_manager
        self.device = None
        self.samplerate = 16000
        self.channels = 1
        self.f_out = None
        self.should_record = False
        self.q = queue.Queue()
        self.recording_enabled = False

        self.setup_tmp_dir()

    def set_recording_enabled(self, enabled):
        if not enabled:
            self.stop_recording('recording_thread_internal')
        self.recording_enabled = enabled

    def setup_tmp_dir(self):
        if aipacenotes.util.is_dev():
            self.tmpdir = 'tmp\\audio'
        else:
            self.tmpdir = self.settings_manager.get_tempdir()

        # for filename in os.listdir(self.tmpdir):
        #     file_path = os.path.join(self.tmpdir, filename)
        #     try:
        #         if os.path.isfile(file_path):
        #             os.unlink(file_path)
        #     except Exception as e:
        #         print(f"Failed to delete {file_path}. Reason: {e}")

    def set_device(self, device):
        self.device = device

    def analyze_frame_for_monitor(self, frame, threshold=0.001):
        # Assuming frame is a NumPy array
        rms = np.sqrt(np.mean(np.square(frame)))

        if rms > threshold:
            return True  # Activate the monitor dot
        else:
            return False  # Deactivate the monitor dot

    def buffer_audio_in(self):
        def callback(indata, _frames, _time, status):
            """This is called (from a separate thread) for each audio block."""
            if status:
                print(f"buffer_audio_in: {status}")
            if self.recording_enabled:
                self.q.put(indata.copy())

        t_monitor_update = time.time()
        monitor_update_limit_seconds = 0.1 # debounce the monitor indicator a little.

        with sd.InputStream(samplerate=self.samplerate,
                            device=int(self.device['index']), # type:ignore
                            channels=self.channels,
                            callback=callback):
            while self.recording_enabled and self.isInterruptionRequested() == False:
                QThread.msleep(10) # put this at the top of the loop so that it runs no matter what.

                audio_data = None
                while not self.q.empty():
                    frame = self.q.get()
                    if audio_data is None:
                        audio_data = np.empty((0,frame.shape[1]), dtype=frame.dtype)
                    audio_data = np.concatenate((audio_data, frame))

                if audio_data is None:
                    continue

                t_now = time.time()
                if t_now - t_monitor_update > monitor_update_limit_seconds:
                    self.audio_signal_detected.emit(self.analyze_frame_for_monitor(audio_data))
                    t_monitor_update = t_now

                if self.should_record:
                    try:
                        if self.f_out:
                            if self.f_out.closed:
                                logging.warn('f_out is closed')
                            self.f_out.write(audio_data)
                    except sf.SoundFileRuntimeError as e:
                        logging.error(e)

    def run(self):
        logging.info("starting RecordingThread (but recording is not enabled)")
        while self.isInterruptionRequested() == False:
            try:
                if self.recording_enabled and self.device:
                    # blip the monitor to ack that it's turning on.
                    self.audio_signal_detected.emit(True)
                    QThread.msleep(100)
                    self.audio_signal_detected.emit(False)

                    self.buffer_audio_in()
            except Exception as e:
                logging.exception("RecordingThread error")
                # self.update_status.emit(f"Error: {str(e)}")
            QThread.msleep(10)

    def start_recording(self):
        logging.debug("start_recording")
        self.fname_out = tempfile.mktemp(prefix='out_', suffix='.wav', dir=self.tmpdir)
        self.fname_out = aipacenotes.util.normalize_path(self.fname_out)
        self.f_out = sf.SoundFile(self.fname_out, mode='x', samplerate=self.samplerate, channels=self.channels)
        self.should_record = True
        self.update_recording_status.emit(True)
        return self.fname_out

    def stop_recording(self, src, vehicle_pos=None):
        logging.debug("stop_recording")
        if vehicle_pos is False:
            vehicle_pos = None

        self.should_record = False
        if self.f_out:
            self.f_out.close()
            transcript = Transcript(src, self.fname_out, vehicle_pos)
            self.transcript_created.emit(transcript)
        self.f_out = None
        self.update_recording_status.emit(False)

    def stop(self):
        print("RecordingThread stopping")
        self.requestInterruption()
