import plistlib
import io
import struct


def plist_target(data):
    if len(data) < 32:
        return

    (offset_size, ref_size, num_objects, top_object,
     offset_table_offset) = struct.unpack('>6xBBQQQ', data[-32:])
    if num_objects > 64:
        return

    try:
        plistlib.loads(data, fmt=plistlib.FMT_BINARY)
    except plistlib.InvalidFileException:
        pass
    except RecursionError:
        pass
    except UnicodeDecodeError:
        pass
    except OverflowError:
        pass
    except ValueError:
        pass
