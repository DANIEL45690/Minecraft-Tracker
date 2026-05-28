import os
import sys
import time
import threading
import psutil
import pystray
from PIL import Image, ImageDraw
from plyer import notification
from datetime import datetime
import json
from pathlib import Path

class MinecraftTracker:
    def __init__(self):
        self.minecraft_running = False
        self.stop_event = threading.Event()
        self.config_file = Path.home() / ".minecraft_tracker_config.json"
        self.load_config()

    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {"notifications_enabled": True, "check_interval": 2}
            self.save_config()

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    def is_minecraft_running(self):
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower()
                if any(name in proc_name for name in ['minecraft', 'javaw', 'java']):
                    if 'minecraft' in proc_name or proc_name == 'javaw.exe' or proc_name == 'java.exe':
                        try:
                            if proc.parent() and 'minecraft' in proc.parent().name().lower():
                                return True
                        except:
                            pass
                        cmdline = ' '.join(proc.cmdline()).lower()
                        if 'minecraft' in cmdline or 'mojang' in cmdline:
                            return True
                        if len(proc.cmdline()) > 1 and 'minecraft' in proc.cmdline()[1].lower():
                            return True
                        if proc_name == 'javaw.exe' and len(proc.cmdline()) > 1:
                            for arg in proc.cmdline():
                                if 'minecraft' in arg.lower() or '.jar' in arg.lower():
                                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def send_notification(self, title, message):
        if self.config["notifications_enabled"]:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    timeout=5,
                    app_name="Minecraft Tracker"
                )
            except:
                pass

    def check_minecraft(self):
        current_state = self.is_minecraft_running()

        if current_state and not self.minecraft_running:
            self.minecraft_running = True
            self.send_notification("Minecraft запущен", "Игра Minecraft была открыта")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Minecraft запущен")

        elif not current_state and self.minecraft_running:
            self.minecraft_running = False
            self.send_notification("Minecraft закрыт", "Игра Minecraft была закрыта")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Minecraft закрыт")

    def monitoring_loop(self):
        while not self.stop_event.is_set():
            self.check_minecraft()
            time.sleep(self.config["check_interval"])

    def start_monitoring(self):
        self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.stop_event.set()
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=3)

class SystemTrayIcon:
    def __init__(self, tracker):
        self.tracker = tracker
        self.setup_tray()

    def create_image(self):
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)

        draw.ellipse([(8, 8), (56, 56)], fill=(0, 150, 0), outline=(0, 0, 0), width=2)
        draw.rectangle([(25, 25), (39, 39)], fill=(255, 255, 255))

        return image

    def on_quit(self, icon, item):
        self.tracker.stop_monitoring()
        icon.stop()
        sys.exit(0)

    def on_toggle_notifications(self, icon, item):
        self.tracker.config["notifications_enabled"] = not self.tracker.config["notifications_enabled"]
        self.tracker.save_config()
        item.checked = self.tracker.config["notifications_enabled"]
        icon.update_menu()

    def on_check_status(self, icon, item):
        status = "запущен" if self.tracker.minecraft_running else "не запущен"
        notification.notify(
            title="Статус Minecraft",
            message=f"Minecraft в данный момент {status}",
            timeout=3,
            app_name="Minecraft Tracker"
        )

    def on_open_logs(self, icon, item):
        log_file = Path.home() / "minecraft_tracker.log"
        try:
            if not log_file.exists():
                with open(log_file, "w") as f:
                    f.write(f"Лог запущен: {datetime.now()}\n")
            os.startfile(str(log_file))
        except:
            pass

    def setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Статус Minecraft", self.on_check_status),
            pystray.MenuItem("Уведомления", self.on_toggle_notifications, checked=lambda item: self.tracker.config["notifications_enabled"]),
            pystray.MenuItem("Открыть лог", self.on_open_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self.on_quit)
        )

        self.icon = pystray.Icon("minecraft_tracker", self.create_image(), "Minecraft Tracker", menu)

    def run(self):
        self.icon.run()

def main():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    os.chdir(base_path)

    tracker = MinecraftTracker()
    tracker.start_monitoring()

    tray_icon = SystemTrayIcon(tracker)
    tray_icon.run()

if __name__ == "__main__":
    main()
