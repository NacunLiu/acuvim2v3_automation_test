# Description: This script is primarily designed to automate the BACnet connection tests, for Acuvim II v3.
# last updated by Nacun Liu 2024-05-02

import subprocess
from time import sleep
import os
import shutil
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(BASE_DIR, 'data', 'screenshots')
IS_WINDOWS = sys.platform.startswith("win")
HAS_DISPLAY = IS_WINDOWS or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
cv2 = None
ssim = None
pyautogui = None
ImageGrab = None
screeninfo = None

if IS_WINDOWS:
    try:
        import cv2
    except Exception:
        cv2 = None

    try:
        from skimage.metrics import structural_similarity as ssim
    except Exception:
        ssim = None

    try:
        import pyautogui
    except Exception:
        pyautogui = None

    try:
        from PIL import ImageGrab
    except Exception:
        ImageGrab = None

    try:
        import screeninfo
    except Exception:
        screeninfo = None


def _env_flag(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

class Client():
    def __init__(self,Serial,id):
        self.start_scan_button_location = None
        self.port_location = None
        self.firstMeter = None
        self.secMeter = None
        self.test_start = None
        self.first_slave = None
        self.close_Yabe = None
        self.whichScreen = None
        self.yabe_executable_path = os.environ.get(
            "ACU_YABE_PATH",
            'C:\\Program Files\\Yabe\\Yabe.exe',
        )
        self.reference_path = os.path.join(BASE_DIR, "Reference.png")
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        if(not Serial):
            Serial = 'Test'
        self.test_path = os.path.join(SCREENSHOT_DIR, Serial + ".png")
        self.ssim_value = None
        self.id = id
        self.ui_enabled = self.is_supported_environment()
        if self.ui_enabled:
            self.whichScreen = self.findScreen()

    @classmethod
    def is_supported_environment(cls):
        return _env_flag(
            "ACU_ENABLE_UI_AUTOMATION",
            IS_WINDOWS and HAS_DISPLAY and pyautogui is not None and ImageGrab is not None
            and screeninfo is not None and cv2 is not None and ssim is not None,
        )

    def findScreen(self):
        if screeninfo is None:
            raise RuntimeError("screeninfo is unavailable in this environment")
        screen_list = screeninfo.get_monitors()
        # print(screen_list)
        if(len(screen_list)>1):
            #two monitor config
            self.start_scan_button_location = (28, 65)
            self.port_location = (517, 144)
            self.firstMeter = (483,168)
            self.secMeter = (466,183)
            self.test_start = (891,142)
            self.first_slave = (92,135)
            self.close_Yabe = (1899,0)
            self.screen_type = 1
        elif(screen_list[-1].height_mm<200):
            #laptop screen config
            self.start_scan_button_location = (17, 59)
            self.port_location = (202, 255)
            self.firstMeter = (148,296)
            self.secMeter = (148,308)
            self.test_start = (910,358)
            self.first_slave = (80,127)
            self.close_Yabe = (1888,0)
            self.screen_type = 1
        else:
            #depends on screen setups
            self.start_scan_button_location = (28, 65)
            self.port_location = (517, 144)
            self.firstMeter = (483,168)
            self.secMeter = (466,183)
            self.test_start = (891,142)
            self.first_slave = (92,135)
            self.close_Yabe = (1899,0)
            self.screen_type = 0

    def compare_Port(self, curPath, refPath):
        if cv2 is None or ssim is None:
            raise RuntimeError("OpenCV or scikit-image is unavailable in this environment")
        image1 = cv2.imread(curPath)
        image2 = cv2.imread(refPath)
        # Convert images to grayscale
        gray_image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        gray_image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
        # Compute Similarity Index SSIM
        ssim_value, _ = ssim(gray_image1, gray_image2, full=True)
        if(ssim_value>0.9):
            return True
        else:
            return False
        
    def take_screenshot(self, option = None):
        if ImageGrab is None:
            raise RuntimeError("ImageGrab is unavailable in this environment")
        # Take a screenshot of the box
        if(option):
            screenshot = ImageGrab.grab(bbox=option)
        else:
            screenshot = ImageGrab.grab(bbox=(0,95,184,440))
        # Save the screenshot to the target location, subject to change
        screenshot.save(self.test_path)
        pyautogui.click(self.close_Yabe)
        
    def compare_images(self):
        if cv2 is None or ssim is None:
            raise RuntimeError("OpenCV or scikit-image is unavailable in this environment")
        image1 = cv2.imread(self.reference_path)
        image2 = cv2.imread(self.test_path)
        # Convert images to grayscale
        gray_image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        gray_image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
        # Compute Similarity Index SSIM
        self.ssim_value, _ = ssim(gray_image1, gray_image2, full=True)
        os.remove(self.test_path)

    # Purpose: 
    # Compare the test screenshot with the reference, if smilarity index is greater than 0.9, connection succeed
    def checkSSIM(self):
        if(self.ssim_value>0.9):
            return True
        else:
            return False
        
    # Purpose: execute sequential commands to perform bacnect connection test
    def run(self):
        if not self.ui_enabled:
            raise RuntimeError(
                "BACnet UI automation is disabled in this environment. "
                "Set ACU_ENABLE_UI_AUTOMATION=true on a Windows desktop host to enable it."
            )
        if not IS_WINDOWS:
            raise RuntimeError("BACnet UI automation currently supports Windows only")
        if not os.path.exists(self.yabe_executable_path):
            raise FileNotFoundError(f"YABE executable not found: {self.yabe_executable_path}")

        if shutil.which("taskkill"):
            subprocess.run(
                ["taskkill", "/f", "/im", "msedge.exe"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        subprocess.Popen([self.yabe_executable_path])
        sleep(2)
        if(self.screen_type ==1):
            pass
        else:
            pyautogui.hotkey('winleft', 'up')
        sleep(2)
        pyautogui.click(self.start_scan_button_location)
        sleep(2)
        pyautogui.hotkey('winleft', 'left')
        sleep(2)
        pyautogui.click(self.port_location)
        if(self.id==1):
            pyautogui.click(self.firstMeter)
        else:
            pyautogui.click(self.secMeter)
        sleep(1)
        pyautogui.click(self.test_start)
        sleep(50)
        pyautogui.click(self.first_slave)
        sleep(5)
        self.take_screenshot()
        self.compare_images()
        return self.checkSSIM()
    
    # Purpose: print cursor location
    def debug(self):
        if pyautogui is None:
            raise RuntimeError("pyautogui is unavailable in this environment")
        print(pyautogui.displayMousePosition())

if __name__ == '__main__':
    client = Client('Debug',1)
    Connection = client.run()
    print(client.ssim_value)
    # client.debug()
