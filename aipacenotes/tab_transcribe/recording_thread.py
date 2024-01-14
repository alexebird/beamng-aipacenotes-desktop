import logging
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

    def __init__(self, settings_manager, device):
        super(RecordingThread, self).__init__()

        self.settings_manager = settings_manager
        self.device = device
        self.samplerate = 16000
        self.channels = 1
        self.f_out = None
        self.fname_out = None
        self.should_write_audio = False
        self.cut_triggered = False
        self.stop_triggered = False
        self.stop_create_entry = True
        self.last_vehicle_pos = None
        self.q = queue.Queue()
        self.recording_enabled = True
        self.t_monitor_update = time.time()

        # add little delay before ending a recording to make the UX of hitting
        # cut a little more robust.
        # Thanks to SH for this idea.
        self.stop_delay = self.settings_manager.get_recording_cut_delay()
        self.stop_delay_start_t = None

        self.log_debounce_delay = 10
        self.last_debounced_log_t = time.time()

        self.setup_tmp_dir()

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

    def log_with_debounce(self, msg):
        t_now = time.time()
        if t_now - self.last_debounced_log_t > self.log_debounce_delay:
            self.last_debounced_log_t = t_now
            logging.warn(msg)

    def analyze_frame_for_monitor(self, frame, threshold=0.001):
        # Assuming frame is a NumPy array
        rms = np.sqrt(np.mean(np.square(frame)))

        if rms > threshold:
            return True  # Activate the monitor dot
        else:
            return False  # Deactivate the monitor dot

    def handle_monitoring(self, audio_data):
        monitor_update_limit_seconds = 0.1 # debounce the monitor indicator a little.
        t_now = time.time()
        if t_now - self.t_monitor_update > monitor_update_limit_seconds:
            self.audio_signal_detected.emit(self.analyze_frame_for_monitor(audio_data))
            self.t_monitor_update = t_now

    def read_audio_data_from_buffer(self):
        audio_data = None
        while not self.q.empty():
            frame = self.q.get()
            if audio_data is None:
                audio_data = np.empty((0,frame.shape[1]), dtype=frame.dtype)
            audio_data = np.concatenate((audio_data, frame))

        return audio_data

    def write_audio_data(self, audio_data):
        try:
            if self.f_out:
                if self.f_out.closed:
                    logging.warn('want to write_audio_data, but f_out is closed.')
                else:
                    self.f_out.write(audio_data)
        except sf.SoundFileRuntimeError as e:
            logging.error(e)

    def buffer_audio_in(self):
        def callback(indata, _frames, _time, status):
            """This is called (from a separate thread) for each audio block."""
            if status:
                logging.debug(f"buffer_audio_in: {status}")
            if self.recording_enabled:
                self.q.put(indata.copy())

        self.t_monitor_update = time.time()

        with sd.InputStream(samplerate=self.samplerate,
                            device=int(self.device['index']), # type:ignore
                            channels=self.channels,
                            callback=callback):
            while self.recording_enabled and self.isInterruptionRequested() == False:
                # This sleep is to prevent the audio buffering loop from eating up a bunch of CPU.
                # Put it at the top of the loop so that it runs no matter what.
                QThread.msleep(10)

                audio_data = self.read_audio_data_from_buffer()

                # update the monitor with the latest batch of audio data.
                if audio_data is not None:
                    self.handle_monitoring(audio_data)

                if self.should_write_audio:
                    if audio_data is None:
                        # if there's no audio data, then we can't do anything anyway, so just continue.
                        self.log_with_debounce("no audio data. is your mic plugged in?")
                        continue

                    self.write_audio_data(audio_data)
                    t_now = time.time()

                    if self.cut_triggered:
                        if self.stop_delay_start_t:
                            if t_now - self.stop_delay_start_t > self.stop_delay:
                                self.cut_triggered = False
                                self.stop_delay_start_t = None
                                self.close_soundfile_and_emit_transcript('cut_recording')
                                self.fname_out, self.f_out = self.open_new_soundfile()
                        else:
                            self.stop_delay_start_t = time.time()

                    if self.stop_triggered:
                        if self.stop_delay_start_t:
                            if t_now - self.stop_delay_start_t > self.stop_delay:
                                self.stop_triggered = False
                                self.stop_delay_start_t = None
                                self.should_write_audio = False
                                self.close_soundfile_and_emit_transcript('stop_recording')
                                self.f_out = None
                                self.fname_out = None
                                self.update_recording_status.emit(False)
                        else:
                            self.stop_delay_start_t = time.time()

    def run(self):
        logging.info("starting RecordingThread")
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
        self.audio_signal_detected.emit(False)

    def open_new_soundfile(self):
        fname_out = tempfile.mktemp(prefix='out_', suffix='.wav', dir=self.tmpdir)
        fname_out = aipacenotes.util.normalize_path(fname_out)
        f_out = sf.SoundFile(fname_out, mode='x', samplerate=self.samplerate, channels=self.channels)
        return fname_out, f_out

    def close_soundfile_and_emit_transcript(self, src):
        if self.f_out:
            self.f_out.close()
            if self.stop_create_entry:
                transcript = Transcript(src, self.fname_out, self.last_vehicle_pos)
                self.transcript_created.emit(transcript)
            self.last_vehicle_pos = None
        else:
            logging.warn("close_soundfile_and_emit_transcript: f_out was unexpectedly None")

    def set_vehicle_pos(self, vehicle_pos):
        if vehicle_pos is False:
            vehicle_pos = None
        self.last_vehicle_pos = vehicle_pos

    def start_recording(self):
        logging.debug("start_recording")
        if not self.recording_enabled:
            return

        self.update_recording_status.emit(True)

        self.fname_out, self.f_out = self.open_new_soundfile()
        self.should_write_audio = True

    def stop_recording(self, create_entry=True, vehicle_pos=None):
        logging.debug("stop_recording")
        if not self.recording_enabled:
            return
        self.set_vehicle_pos(vehicle_pos)
        self.stop_create_entry = create_entry
        self.stop_triggered = True

    def cut_recording(self, vehicle_pos=None):
        logging.debug("cut_recording")
        if not self.recording_enabled:
            return

        self.set_vehicle_pos(vehicle_pos)

        # whenever you cut, recording starts.
        self.update_recording_status.emit(True)

        if self.should_write_audio: # ie, is already recording?
            self.cut_triggered = True
        else: # the same as start_recording.
            self.fname_out, self.f_out = self.open_new_soundfile()
            self.should_write_audio = True
            self.cut_triggered = False

    def stop(self):
        logging.debug("RecordingThread stopping")
        self.requestInterruption()
