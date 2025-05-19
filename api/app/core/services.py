import subprocess


def run_dashboard(trial_dir: str):
    process = subprocess.Popen(
        ["autorag", "dashboard", "--trial_dir", trial_dir], start_new_session=True
    )
    return process.pid


def run_chat(trial_dir: str):
    process = subprocess.Popen(
        ["autorag", "run_web", "--trial_path", trial_dir], start_new_session=True
    )
    return process.pid


def run_api_server(trial_dir: str):
    process = subprocess.Popen(
        ["autorag", "run_api", "--port", "8100", "--trial_dir", trial_dir],
        start_new_session=True,
    )
    return process.pid 