import tkinter as tk
from tkVideoPlayer import TkinterVideo
import os
import threading
import tkinter.filedialog
import tkinter.messagebox
import pathlib
import math

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
        self.VIDEO_HEIGHT = 432
        self.VIDEO_WIDTH = 768

        self.video_index = 0
        self.videos_list = ["videos/" + file for file in os.listdir('./videos')]

        self.video = TkinterVideo(self, height=1, width=1, scaled=True)
        # Fix for a bug in the tkVideoPlayer library
        self.video.bind("<<Loaded>>", lambda e: e.widget.config(width=self.VIDEO_WIDTH, height=self.VIDEO_HEIGHT))
        
        # Toolbar and progress bar
        self.progressBar = ProgressBar(self, height=20, width=self.VIDEO_WIDTH, video=self.video, bg='black')
        self.toolBar = tk.Frame(self)
        self.pauseButton = tk.Button(self.toolBar, text='Pause', 
                                     command=self.pause_button_click, width=8)
        self.nextVideoButton = tk.Button(self.toolBar, text='Next video', 
                                         command=self.next_video)
        self.previousVideoButton = tk.Button(self.toolBar, text='Previous video', 
                                             command=self.previous_video)
        self.loadButton = tk.Button(self, text='Load video',
                                    command=self.choose_video)

        # Progress bar & buttons' frame
        self.progressBar.grid(row=1, column=0)
        self.toolBar.grid(row=2, column=0)

        # Buttons
        padx = 5
        self.loadButton.grid(row=2, column=0, padx=padx, sticky='W')
        self.previousVideoButton.grid(row=0, column=1, padx=padx)
        self.pauseButton.grid(row=0, column=2, padx=padx)
        self.nextVideoButton.grid(row=0, column=3, padx=padx)

        self.video.grid(row=0, column=0)
        self.video.load(self.videos_list[0])
        self.video.play()

    # Pause the video
    def pause(self):
        self.video.pause()
        self.pauseButton.config(text='Unpause')

    # Unpause the video
    def unpause(self):
        self.video.play()
        self.pauseButton.config(text='Pause')

    # (Un)pause button is clicked
    def pause_button_click(self):
        if (not self.video.is_paused()):
            self.pause()
        else:
            self.unpause()

    # Opens pop-up window for user to choose the video
    def choose_video(self):
        path = tkinter.filedialog.askopenfilename(
            title="Load video",
            initialdir=str(pathlib.Path(__file__).parent.resolve()) + '/videos',
            filetypes=[('mp4', '*.mp4')])
        
        if (not path): # User closed the window
            return
        
        path = path.split('/')
        if (path[-2] != 'videos'):
            tkinter.messagebox.showerror(title="Error", 
                                          message="Select file in the 'videos' folder")
            return

        path = path[-2] + '/' + path[-1]
        self.video_index = self.videos_list.index(path)
        self.load_video()

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
        self.user_paused = False
        self.click_in_progress = False

        self.height = height
        self.width = width
        
        self.redLine = tk.Frame(self, height=self.height * 0.3, bg='red')
        self.duration = 0
        self.video = video
        self.video.bind('<<Duration>>', self.set_duration)
        self.video.bind('<<SecondChanged>>', self.update)
        self.video.bind('<<Ended>>', self.video_ended)

        # For when progress bar is clicked
        self.bind('<B1-Motion>', self.bar_clicked)
        self.bind('<ButtonRelease-1>', self.mouse_released)
        self.redLine.bind('<B1-Motion>', self.bar_clicked)
        self.redLine.bind('<ButtonRelease-1>', self.mouse_released)

        self.pack_propagate(False) # Prevent the progress bar shrinking to fit the redLine
        self.redLine.pack(side='left')

    # Fix for a bug in TkinterVideo library
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
        else:
            progress = 0
        new_width = int(self.width * progress)
        self.redLine.config(width=new_width)

    # Clicked on a progress bar
    def bar_clicked(self, event):
        if (not self.click_in_progress):
            self.click_in_progress = True
            self.user_paused = self.video.is_paused()

        progress = event.x / self.width
        progress = max(0, progress)
        progress = min(self.width, progress)

        self.video.seek(math.ceil(self.duration * progress))
        self.video.play()

        timer = threading.Timer(0.05, lambda: self.video.pause()) # Time to update the frame
        timer.start()
        self.update(None)
        
    # Only when it was clicked on a progress bar
    def mouse_released(self, event):
        if (not self.user_paused):
            timer = threading.Timer(0.1, lambda: self.master.unpause())
            timer.start()
        self.click_in_progress = False

# Basic placeholder for features that aren't implemented yet
class Placeholder(tk.Frame):
    def __init__(self, master, height=300, width=300, *args, **kwargs):
        super().__init__(master, height=height, width=width, *args, **kwargs)

def main():
    window = MainApp()
    window.mainloop()

if __name__ == '__main__':
    main()