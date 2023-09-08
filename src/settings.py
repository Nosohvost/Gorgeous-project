import json
import threading

# A class for saving and loading settings from settings.json
# Do not confuse with SettingsMenu in main.py, which is a part of GUI, unlike this class
class Settings():
    def __init__(self, path='settings.json'):
        self.settings_path = path
        self.lock = threading.Lock() # A mutex lock used to prevent race condition
        self.settings = {} # Settings dictionary
        self.load()

    # Reload settings from settings.json
    def load(self):
        with self.lock and open(self.settings_path, 'r') as file:
            self.settings = json.load(file)

    # Save settings from self.settings to settings.json
    def apply(self):
        with self.lock and open(self.settings_path, 'w') as file:
            json.dump(self.settings, file, indent=4)


if __name__ == "__main__":
    settings = Settings('../settings.json')