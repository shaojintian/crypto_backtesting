import sys

def is_gil_enabled():
    try:
        gil_status = sys._is_gil_enabled()
        return gil_status
    except AttributeError:
        return "Cannot determine GIL status. This function is not available in your Python version."

print("GIL is enabled" if is_gil_enabled() else "GIL is not enabled")