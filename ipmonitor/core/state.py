\
import threading

devices = {}
results = {}
last_state = {}
monitoring_active = False

groups = set(["Default"])
selected_group_filter = "Tutti"

state_lock = threading.Lock()

current_sort_col = None
current_sort_reverse = False

critical_win = None
critical_after_id = None

report_state = {
    "last_report_ts": 0,
    "critical_enter_counts": {},
    "last_critical_status": {},
    "last_report_live_status": {},
    "last_report_critical_set": []
}

auto_report_after_id = None
log_prune_after_id = None
