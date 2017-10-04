def get_open_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("",0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port

def bytes2human(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n

def toLocalTime(hhmm):
    import time, datetime
    diff = time.timezone
    diff = -diff
    now = datetime.datetime.strptime(hhmm, "%H:%M")
    delta = datetime.timedelta(seconds=diff)
    newtime = now + delta
    h = str(newtime.hour)
    m = str(newtime.minute)
    if len(h) == 1:
        h = '0' + h
    if len(m) == 1:
        m = '0' + m
    return h + ':' + m