import json

def json_target(data):
    try:
        data = data.decode()
    except:
        return
    try:
        json.loads(data)
    except ValueError:
        pass
