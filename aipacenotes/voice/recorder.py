# import re
# import struct
# import sys
# import wave
# from pvrecorder import PvRecorder

# class Recorder():
#     def __init__(self):
#         pass

#     def record():
#         print('Recorder.record')
#         device_idx = -1

#         for index, device in enumerate(PvRecorder.get_available_devices()):
#             print(f"[{index}] {device}")
#             match = re.search(r"USB Audio Device", str(device))
#             if match:
#                 device_idx = index
#                 print(f"using device: {device}")
#                 break

#         if device_idx == -1:
#             print("cloudnt find device")
#             return False

#         recorder = PvRecorder(device_index=0, frame_length=512)
#         audio = []

#         path = 'out.wav'

#         try:
#             recorder.start()

#             while True:
#                 frame = recorder.read()
#                 audio.extend(frame)
#         except KeyboardInterrupt:
#             recorder.stop()
#             with wave.open(path, 'w') as f:
#                 f.setparams((1, 2, 16000, 512, "NONE", "NONE"))
#                 f.writeframes(struct.pack("h" * len(audio), *audio))
#             print(f'Recorder stopped and wrote file {path}')
#         finally:
#             recorder.delete()