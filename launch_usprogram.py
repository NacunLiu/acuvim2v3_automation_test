import os
import subprocess
import time
from pathlib import Path

from pywinauto import Application, Desktop
from pywinauto.findwindows import ElementNotFoundError


EXE_PATH = os.environ.get(
    "USPROGRAM_EXE_PATH",
    r"C:\Users\NacunLiu\Nacun_Work\test apps install package"
    r"\Acuvim-II v3 USProgram English\Acuvim-II v3 USProgram English\USProgram.exe",
)
FIRMWARE_DIR = os.environ.get("FIRMWARE_DIR", str(Path.home() / "Downloads"))
MAIN_WINDOW_TITLE_RE = r".*S-Programmer.*"
COMMUNICATIONS_TITLE = "Communications"
COM_PORT_VALUE = os.environ.get("ACU_WIN_COM_PORT", "COM6")
BAUD_RATE_VALUE = "115200"
OPEN_DIALOG_TITLE = "Open"
REQUEST_DIALOG_TITLE_RE = r".*Request.*"
ACTION_DELAY_SECONDS = 1


def launch_app():
    if not os.path.isfile(EXE_PATH):
        raise FileNotFoundError(f"Could not find executable: {EXE_PATH}")

    process = subprocess.Popen([EXE_PATH])
    print(f"Launched: {EXE_PATH}")
    return process


def pause():
    time.sleep(ACTION_DELAY_SECONDS)


def wait_for_window(app, title_re=None, title=None, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if title is not None:
                window = app.window(title=title)
            else:
                window = app.window(title_re=title_re)
            window.wait("visible ready", timeout=1)
            return window
        except Exception:
            time.sleep(0.5)
    target = title if title is not None else title_re
    raise TimeoutError(f"Could not find ready window matching: {target}")


def wait_for_desktop_window(backend, process_id, title=None, title_re=None, timeout=15):
    desktop = Desktop(backend=backend)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if title is not None:
                window = desktop.window(title=title, process=process_id)
            else:
                window = desktop.window(title_re=title_re, process=process_id)
            if window.exists():
                window.wait("visible ready", timeout=1)
                return window
        except Exception:
            pass
        time.sleep(0.5)
    target = title if title is not None else title_re
    raise TimeoutError(f"Could not find desktop window matching: {target}")


def find_combo_by_item(dialog, expected_item):
    seen_items = []
    deadline = time.time() + 15
    while time.time() < deadline:
        for combo in dialog.children(class_name="TComboBox"):
            try:
                items = combo.item_texts()
                if items:
                    seen_items.append(items)
                if expected_item in items:
                    return combo
            except Exception:
                continue
        time.sleep(0.5)
    if seen_items:
        raise RuntimeError(
            f"Could not find combo box containing item: {expected_item}. "
            f"Available combo items: {seen_items}"
        )
    raise RuntimeError(
        f"Could not find combo box containing item: {expected_item}. "
        "The combo box items never populated, which usually means the serial port "
        "is not currently available to the application."
    )


def get_latest_firmware_file():
    firmware_dir = Path(FIRMWARE_DIR)
    candidates = [p for p in firmware_dir.iterdir()
                  if p.is_file() and p.name.upper().startswith("AHB")]
    if not candidates:
        candidates = [p for p in firmware_dir.iterdir()
                      if p.is_file() and p.suffix.lower() == ".abin"]
    if not candidates:
        raise FileNotFoundError(
            f"Could not find any AHB* firmware files in {firmware_dir}"
        )
    return max(candidates, key=lambda p: p.stat().st_mtime)


def configure_communications(process_id):
    app = Application(backend="win32").connect(process=process_id, timeout=15)
    dialog = wait_for_window(app, title=COMMUNICATIONS_TITLE)

    com_port_combo = find_combo_by_item(dialog, COM_PORT_VALUE)
    com_port_combo.select(COM_PORT_VALUE)
    pause()

    baud_rate_combo = find_combo_by_item(dialog, BAUD_RATE_VALUE)
    baud_rate_combo.select(BAUD_RATE_VALUE)
    pause()

    ok_button = dialog.child_window(title="OK", class_name="TButton")
    ok_button.click_input()
    pause()
    print(f"Configured communications: {COM_PORT_VALUE}, {BAUD_RATE_VALUE}")


def import_latest_firmware(process_id):
    app = Application(backend="win32").connect(process=process_id, timeout=15)
    main_window = wait_for_window(app, title_re=MAIN_WINDOW_TITLE_RE)
    firmware_path = get_latest_firmware_file()

    browse_button = main_window.child_window(title="&Browse", class_name="TButton")
    open_dialog = None
    for _ in range(3):
        browse_button.click()
        pause()
        try:
            open_dialog = wait_for_desktop_window(
                backend="uia",
                process_id=process_id,
                title=OPEN_DIALOG_TITLE,
                timeout=5,
            )
            break
        except TimeoutError:
            continue
    if open_dialog is None:
        raise TimeoutError("Could not open the firmware file picker dialog")

    file_name_edit = open_dialog.child_window(auto_id="1148", control_type="Edit")
    file_name_edit.set_edit_text(str(firmware_path))
    pause()

    open_button = open_dialog.child_window(title="Open", auto_id="1", control_type="Button")
    open_button.click_input()
    pause()
    print(f"Imported firmware: {firmware_path}")


def request_meter(process_id):
    app = Application(backend="win32").connect(process=process_id, timeout=15)
    main_window = wait_for_window(app, title_re=MAIN_WINDOW_TITLE_RE)

    request_button = main_window.child_window(title="Reques&t", class_name="TButton")
    request_button.click()
    pause()

    request_dialog = wait_for_desktop_window(
        backend="win32",
        process_id=process_id,
        title_re=REQUEST_DIALOG_TITLE_RE,
        timeout=15,
    )
    ok_button = request_dialog.child_window(title="OK", class_name="TButton")
    ok_button.click()
    pause()
    print("Requested meter and confirmed dialog")


def start_download(process_id):
    app = Application(backend="win32").connect(process=process_id, timeout=15)
    main_window = wait_for_window(app, title_re=MAIN_WINDOW_TITLE_RE)

    time.sleep(4)
    download_button = main_window.child_window(title="Downlo&ad", class_name="TButton")
    if not download_button.is_enabled():
        raise RuntimeError("Download button is not enabled")

    download_button.click()
    pause()
    print("Started firmware download")


def main():
    process = launch_app()
    time.sleep(2)
    configure_communications(process.pid)
    import_latest_firmware(process.pid)
    request_meter(process.pid)
    start_download(process.pid)


if __name__ == "__main__":
    try:
        main()
    except ElementNotFoundError as exc:
        raise RuntimeError(
            "Could not find one of the expected UI controls. "
            "Please confirm the window labels still match the screenshot."
        ) from exc
