import logging
from aipacenotes import client as aip_client
import wave
import struct

import numpy as np
from numpy import array, int16
# from scipy.io.wavfile import read,write
# from scipy.signal import lfilter, butter
# import librosa

from audiomentations import (
    Compose,
#     AddGaussianNoise,
#     Normalize,
#     BandPassFilter,
#     ClippingDistortion,
#     TanhDistortion,
#     LoudnessNormalization,
    Trim,
)

class SpeechToText:
    def __init__(self, fname):
        self.fname = fname
        self.fname2 = "out2.wav"

    def transcribe(self):
        response = aip_client.post_transcribe(self.fname)
        logging.info(response)
        if response:
            if response['error'] == True:
                return None
            else:
                return response['transcript']
        else:
            return None

    def trim_silence(self):
        # sample_rate, audio_data = read(audio_io)
        # sample_rate=24000 data-type=int16
        # print(f"sample_rate={sample_rate} data-type={audio_data.dtype}")
        # pdb.set_trace()

        # with open(fname, "rb") as f:
            # audio_content = f.read()

        # audio_bytes = io.BytesIO(audio_content)

        # Open the WAV file
        with wave.open(self.fname, 'r') as wav_file:
            # Get basic properties
            num_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            num_frames = wav_file.getnframes()
            sample_rate = framerate

            # print(f"Number of Channels: {num_channels}")
            # print(f"Sample Width: {sample_width}")
            # print(f"Number of Frames: {num_frames}")
            logging.debug(f"Sample Rate: {sample_rate}")

            # Read audio data
            audio_data = wav_file.readframes(num_frames)
            audio_data = np.frombuffer(audio_data, dtype=np.int16)
            # Now, audio_data is a NumPy array containing the audio samples.


        augment = Compose([
            Trim(top_db=30.0, p=1.0),
        ])

        augmented_samples = augment(samples=audio_data, sample_rate=sample_rate)

        with wave.open(self.fname2, 'w') as f:
            # 1: Number of channels (mono)
            # 2: Sample width in bytes (2 bytes or 16 bits)
            # 16000: Sample rate (16,000 samples per second)
            # 512: Number of frames (not strictly necessary for writing, often set to nframes which is the total number of frames)
            # "NONE": Compression type (no compression)
            # "NONE": Compression name (no compression)
            f.setparams((num_channels, sample_width, sample_rate, num_frames, "NONE", "NONE"))
            f.writeframes(struct.pack("h" * len(augmented_samples), *augmented_samples))
