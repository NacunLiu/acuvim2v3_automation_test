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


def wait_for_window(app, title_re=None, title=None, timeout=30):
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

    # Detect COM port and baud rate combos in a single pass (no slow polling)
    com_port_combo = baud_rate_combo = port_to_use = None
    deadline = time.time() + 15
    while time.time() < deadline and (com_port_combo is None or baud_rate_combo is None):
        for combo in dialog.children(class_name="TComboBox"):
            try:
                items = combo.item_texts()
                if COM_PORT_VALUE in items and com_port_combo is None:
                    com_port_combo = combo
                    port_to_use = COM_PORT_VALUE
                elif com_ports := [i for i in items if i.startswith("COM")]:
                    if com_port_combo is None:
                        com_port_combo = combo
                        port_to_use = com_ports[0]
                        print(f"Warning: {COM_PORT_VALUE} not found, using {port_to_use}")
                if BAUD_RATE_VALUE in items and baud_rate_combo is None:
                    baud_rate_combo = combo
            except Exception:
                continue
        if com_port_combo is None or baud_rate_combo is None:
            time.sleep(0.5)

    if com_port_combo is None:
        raise RuntimeError(f"Could not find COM port combo in Communications dialog")
    if baud_rate_combo is None:
        raise RuntimeError(f"Could not find baud rate combo in Communications dialog")

    com_port_combo.select(port_to_use)
    pause()
    baud_rate_combo.select(BAUD_RATE_VALUE)
    pause()

    ok_button = dialog.child_window(title="OK", class_name="TButton")
    ok_button.click()
    pause()
    print(f"Configured communications: {port_to_use}, {BAUD_RATE_VALUE}")


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
    open_button.invoke()
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

    download_button = main_window.child_window(title="Downlo&ad", class_name="TButton")
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if download_button.is_enabled():
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        print("Download button never became enabled — firmware may already be up to date. Skipping flash.")
        return

    download_button.click()
    pause()

    confirm_dialog = wait_for_desktop_window(
        backend="win32",
        process_id=process_id,
        title="Warning",
        timeout=30,
    )
    yes_button = confirm_dialog.child_window(title="&Yes", class_name="Button")
    yes_button.click()
    pause()
    print("Confirmed programming start. Firmware download in progress...")


PROGRAMMING_INITIAL_WAIT = 300  # 5 minutes for firmware flash
PROGRAMMING_RETRY_WAIT   = 30
PROGRAMMING_MAX_RETRIES  = 5


def wait_for_programming_complete(process_id):
    print(f"Waiting {PROGRAMMING_INITIAL_WAIT}s for firmware programming to complete...")
    time.sleep(PROGRAMMING_INITIAL_WAIT)

    for attempt in range(1, PROGRAMMING_MAX_RETRIES + 1):
        try:
            desktop = Desktop(backend="win32")
            for title in ["Programming finished", "Information", "Message"]:
                try:
                    dialog = desktop.window(title=title, process=process_id)
                    if dialog.exists():
                        dialog.wait("visible ready", timeout=3)
                        for btn_class in ["Button", "TButton"]:
                            try:
                                ok_button = dialog.child_window(title="OK", class_name=btn_class)
                                if ok_button.exists():
                                    ok_button.click()
                                    print("Firmware programming completed. Clicked OK.")
                                    return
                            except Exception:
                                continue
                except Exception:
                    continue
        except Exception:
            pass

        if attempt < PROGRAMMING_MAX_RETRIES:
            print(
                f"'Programming finished' dialog not found "
                f"(attempt {attempt}/{PROGRAMMING_MAX_RETRIES}). "
                f"Waiting {PROGRAMMING_RETRY_WAIT}s before retry..."
            )
            time.sleep(PROGRAMMING_RETRY_WAIT)

    # Log all visible windows on the process to find the actual dialog title
    print("DEBUG: Programming finished dialog not found. Visible windows:")
    try:
        desktop = Desktop(backend="win32")
        for win in desktop.windows():
            try:
                if win.process_id() == process_id:
                    print(f"  Window: title={repr(win.window_text())} class={win.class_name()}")
                    for child in win.children():
                        try:
                            print(f"    Child: title={repr(child.window_text())} class={child.class_name()}")
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception as e:
        print(f"  (could not enumerate: {e})")

    total_wait = PROGRAMMING_INITIAL_WAIT + PROGRAMMING_MAX_RETRIES * PROGRAMMING_RETRY_WAIT
    raise RuntimeError(
        f"Firmware programming did not complete after {total_wait}s total. "
        "Update failed — check meter connection and USProgram."
    )


def main():
    process = launch_app()
    time.sleep(2)
    configure_communications(process.pid)
    time.sleep(6)  # Wait for USProgram to connect to meter after communications configured
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
