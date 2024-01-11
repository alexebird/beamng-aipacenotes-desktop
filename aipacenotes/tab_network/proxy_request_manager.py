import queue

from .proxy_request import ProxyRequest

class ProxyRequestManager:
    def __init__(self, signal):
        self.signal = signal
        self.request_q = queue.Queue()
        self.request_l = []

    def __getitem__(self, i):
        return self.request_l[i]

    def __len__(self):
        return len(self.request_l)

    # its a flask request.
    def add_request(self, request):
        proxy_req = ProxyRequest(request)
        self.request_l.append(proxy_req)
        self.request_q.put(proxy_req)
        self.signal.emit()
        return proxy_req

    def run(self):
        proxy_req = self.request_q.get()
        proxy_req.execute()
        self.signal.emit()
