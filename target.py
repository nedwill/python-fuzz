import plistlib
import io

def json_target(data):
    try:
        plistlib.loads(data, fmt=plistlib.FMT_BINARY)
    except OverflowError:
        pass
    except plistlib.InvalidFileException:
        pass
    except MemoryError:
        pass
