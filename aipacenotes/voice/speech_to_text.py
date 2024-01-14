import logging
from aipacenotes import client as aip_client

class SpeechToText:
    def __init__(self, fname):
        self.fname = fname

    def transcribe(self):
        response = aip_client.post_transcribe(self.fname)
        logging.info(response)
        if response:
            if response['error'] == True:
                return None
            else:
                return response['text']
        else:
            return None
