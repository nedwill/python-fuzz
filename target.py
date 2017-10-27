from html.parser import HTMLParser

def json_target(data):
    try:
        data = data.decode()
    except:
        return
    try:
        parser = HTMLParser()
        parser.feed(data)
        parser.close()
        # plistlib.readPlistFromString(data)
        # obj1 = json.loads(data)
        # data1 = json.dumps(obj1)
        # obj2 = json.loads(data1)
        # assert obj1 == obj2
    except ValueError:
        pass
