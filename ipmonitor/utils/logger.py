\
import logging
import os
import time

from ipmonitor import app_globals as G

logger = logging.getLogger("ipmon")
logger.setLevel(logging.INFO)
logger.propagate = False

def ensure_parent_dir(path: str):
    try:
        parent = os.path.dirname(os.path.abspath(path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
    except Exception:
        pass

def configure_logger():
    """Reconfigure file handler when LOG_FILE changes."""
    global logger
    try:
        for h in list(logger.handlers):
            try:
                h.flush()
                h.close()
            except Exception:
                pass
            logger.removeHandler(h)
    except Exception:
        pass

    ensure_parent_dir(G.LOG_FILE)
    fh = logging.FileHandler(G.LOG_FILE, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s - %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

def _parse_log_line_ts(line: str):
    try:
        base = line[:19]
        return time.mktime(time.strptime(base, "%Y-%m-%d %H:%M:%S"))
    except Exception:
        try:
            base = line[:23]
            base2 = base.split(",")[0]
            return time.mktime(time.strptime(base2, "%Y-%m-%d %H:%M:%S"))
        except Exception:
            return None

def prune_log_file():
    if not os.path.exists(G.LOG_FILE):
        return

    if G.LOG_RETENTION_DAYS > 0:
        cutoff = time.time() - (G.LOG_RETENTION_DAYS * 86400)
        tmp_path = G.LOG_FILE + ".tmp"
        try:
            with open(G.LOG_FILE, "r", encoding="utf-8", errors="ignore") as fin, \
                 open(tmp_path, "w", encoding="utf-8") as fout:
                for line in fin:
                    ts = _parse_log_line_ts(line)
                    if ts is None or ts >= cutoff:
                        fout.write(line)
            os.replace(tmp_path, G.LOG_FILE)
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    if G.LOG_MAX_SIZE_MB > 0:
        try:
            max_bytes = G.LOG_MAX_SIZE_MB * 1024 * 1024
            size = os.path.getsize(G.LOG_FILE)
            if size > max_bytes:
                with open(G.LOG_FILE, "rb") as f:
                    f.seek(-max_bytes, os.SEEK_END)
                    data = f.read()
                idx = data.find(b"\n")
                if idx != -1:
                    data = data[idx+1:]
                tmp_path = G.LOG_FILE + ".tmp"
                with open(tmp_path, "wb") as out:
                    out.write(data)
                os.replace(tmp_path, G.LOG_FILE)
        except Exception:
            pass
