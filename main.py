import tkinter as tk
from tkVideoPlayer import TkinterVideo

class MainApp(tk.Tk):
    def __init__(self, title='Fox spy', *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Minimum width & height for the window
        self.MIN_WIDTH = 450
        self.MIN_HEIGHT = 450
        self.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)

        self.resizable(width=False, height=False)
        self.title(title)

        # Create main menu
        self.mainMenu = MainMenu(self)
        self.mainMenu.grid(row=0, column=0)

        # Current tab opened. By default is statistics tab
        self.currentTab = Placeholder(self, bg='red')
        self.currentTab.grid(row=0, column=1)

    def open_statistics_menu(self):
        self.currentTab.destroy()
        self.currentTab = Placeholder(self, bg='red')
        self.currentTab.grid(row=0, column=1)

    def open_video_player(self):
        self.currentTab.destroy()
        self.currentTab = VideoPlayer(self)
        self.currentTab.grid(row=0, column=1)

    def open_settings(self):
        self.currentTab.destroy()
        self.currentTab = Placeholder(self, bg='green')
        self.currentTab.grid(row=0, column=1)

# Main menu in top left corner
class MainMenu(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        # Creating buttons
        self.plotButton = tk.Button(self, text='Show plot', command=master.open_statistics_menu)
        self.videosButton = tk.Button(self, text='Saved videos', command=master.open_video_player) 
        self.settingsButton = tk.Button(self, text='Settings', command=master.open_settings)

        self.buttons_pady = 4
        self.buttons_ipady = 2

        self.plotButton.grid(row=0, column=0, ipady=self.buttons_ipady, pady=self.buttons_pady)
        self.videosButton.grid(row=1, column=0, ipady=self.buttons_ipady, pady=self.buttons_pady)
        self.settingsButton.grid(row=2, column=0, ipady=self.buttons_ipady, pady=self.buttons_pady)

class PlotCreator(tk.Frame):
    pass

class SettingsMenu(tk.Frame):
    pass

class VideoPlayer(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        video = TkinterVideo(self, height=1, width=1, scaled=True)
        video.load(r"videos\cool_cat.mp4")
        video.grid(row=0, column=0)
        video.play()

        
        
# Basic placeholder for features that aren't implemented yet
class Placeholder(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, height=300, width=300, *args, **kwargs)

def main():
    window = MainApp()
    window.mainloop()

if __name__ == '__main__':
    main()