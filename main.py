import tkinter as tk
from tkVideoPlayer import TkinterVideo
import os
import threading

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
        self.mainMenu.grid(row=0, column=0, sticky='NE')

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

# Toolbar and video itself
class VideoPlayer(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.video_index = 0
        self.videos_list = ["videos\\" + file for file in os.listdir(r'.\videos')]

        self.video = TkinterVideo(self, height=1, width=1, scaled=True)
        # Fix for a bug in the tkVideoPlayer library
        self.video.bind("<<Loaded>>", lambda e: e.widget.config(width=640, height=480))
        
        # Toolbar
        self.progressBar = ProgressBar(self, height=20, width=640, video=self.video, bg='black')
        self.toolBar = tk.Frame(self)
        self.pauseButton = tk.Button(self.toolBar, text='Pause', 
                                     command=self.pause_button_click)
        self.nextVideoButton = tk.Button(self.toolBar, text='Next video', 
                                         command=self.next_video)
        self.previousVideoButton = tk.Button(self.toolBar, text='Previous video', 
                                             command=self.previous_video)

        # Progress bar & buttons' frame
        self.progressBar.grid(row=1, column=0)
        self.toolBar.grid(row=2, column=0)

        # Buttons
        padx = 5
        self.previousVideoButton.grid(row=0, column=0, padx=padx)
        self.pauseButton.grid(row=0, column=1, padx=padx)
        self.nextVideoButton.grid(row=0, column=2, padx=padx)

        self.video.grid(row=0, column=0)
        self.video.load(self.videos_list[0])
        self.video.play()

    # Called when (un)pause button is clicked
    def pause_button_click(self):
        if (not self.video.is_paused()):
            self.video.pause()
            self.pauseButton.config(text='Unpause')
            
        else:
            self.video.play()
            self.pauseButton.config(text='Pause')

    # Loads video using self.video_index
    def load_video(self):
        self.video.load(self.videos_list[self.video_index])
        timer = threading.Timer(0.1, lambda: self.video.play()) # Waits a bit to ensure previous video was closed
        timer.start()
        self.pauseButton.config(text='Pause')

    # Load next video
    def next_video(self):
        self.video_index = min(self.video_index + 1, len(self.videos_list) - 1)
        self.load_video()
        
        
    # Load previous video
    def previous_video(self):
        self.video_index = max(self.video_index - 1, 0)
        self.load_video()
    
class ProgressBar(tk.Frame):
    def __init__(self, master, height, width, video: TkinterVideo, *args, **kwargs):
        super().__init__(master, height=height, width=width, *args, **kwargs)

        self.height = height
        self.width = width
        
        self.redLine = tk.Frame(self, height=self.height * 0.3, bg='red')
        self.duration = 0
        self.video = video
        self.video.bind('<<Duration>>', self.set_duration)
        self.video.bind('<<SecondChanged>>', self.update)
        self.video.bind('<<Ended>>', self.video_ended)

        self.pack_propagate(False) # Prevent shrinking the progress bar to fit the redLine
        self.redLine.pack(side='left')

    # Fix for a bug in TkinterVideo libary
    def video_ended(self, event):
        self.redLine.config(width=self.width)

    # Update the total duration when a new video is loaded
    def set_duration(self, event):
        self.duration = self.video.video_info()['duration']
        self.redLine.config(width=0)
        
    # Update the red line to match the current progress
    def update(self, event):
        if (self.duration != 0):
            progress = self.video.current_duration() / self.duration # Between 0 and 1
            #print(self.video.current_duration(), self.duration)
        else:
            progress = 0
        new_width = int(self.width * progress)
        self.redLine.config(width=new_width)





# Basic placeholder for features that aren't implemented yet
class Placeholder(tk.Frame):
    def __init__(self, master, height=300, width=300, *args, **kwargs):
        super().__init__(master, height=height, width=width, *args, **kwargs)

def main():
    window = MainApp()
    window.mainloop()

if __name__ == '__main__':
    main()