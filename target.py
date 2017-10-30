import plistlib
import io
import struct

def plist_target(data):
    if len(data) < 32:
        return

    (offset_size, ref_size, num_objects, top_object,
    offset_table_offset) = struct.unpack('>6xBBQQQ', data[-32:])
    if num_objects > 16 or offset_size == 0 or ref_size == 0:
        return

    try:
        plistlib.loads(data, fmt=plistlib.FMT_BINARY)
    except OverflowError:
        pass
    except plistlib.InvalidFileException:
        pass
    except MemoryError:
        pass
