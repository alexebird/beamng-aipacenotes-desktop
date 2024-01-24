import queue

from .proxy_request import ProxyRequest

class ProxyRequestManager:
    def __init__(self, signal_added, signal_done):
        self.signal_added = signal_added
        self.signal_done = signal_done
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
        self.signal_added.emit()
        return proxy_req

    def run(self):
        proxy_req = self.request_q.get()
        print('pre execute')
        proxy_req.execute()
        print('post execute')
        self.signal_done.emit()
