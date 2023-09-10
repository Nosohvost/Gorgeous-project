import tkinter as tk
import tkinter.ttk as ttk
from tkVideoPlayer import TkinterVideo
import os
import threading
import tkinter.filedialog
import tkinter.messagebox
import pathlib
import math
from src import dbutils, camutils, settings
from matplotlib import pyplot as plt
from matplotlib.backends import backend_tkagg as plt_backend
import datetime


class MainApp(tk.Tk):
    def __init__(self, title='Fox spy', *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = settings.Settings()

        rtsp_url = self.settings.get('Camera url')
        self.cam_end = threading.Event()
        self.db = dbutils.Database()
        self.cam = camutils.Camera(rtsp_url, self.db, log=True)
        self.cam_thread = threading.Thread(target=self.cam.start, args=(self.cam_end,))
        if self.settings.get('Autostart camera'):
            self.start_camera()

        # Minimum width & height for the window
        resolution = self.settings.get('Window resolution').split('x')
        MIN_WIDTH = int(resolution[0])
        MIN_HEIGHT = int(resolution[1])
        self.minsize(MIN_WIDTH, MIN_HEIGHT)

        self.resizable(width=False, height=False)
        self.title(title)

        # Create main menu
        self.mainMenu = MainMenu(self, self.settings)
        self.mainMenu.grid(row=0, column=0, sticky='NE')

        # Open statistics menu
        self.currentTab = StatisticsMenu(self, self.settings, self.db)
        self.currentTab.grid(row=0, column=1)

    # Starts the camera if it's not working
    def start_camera(self, restart=False):
        if not self.cam_thread.is_alive():
            self.cam_thread = threading.Thread(target=self.cam.start, args=(self.cam_end,))
            self.cam_end.clear()
            self.cam_thread.start()

    # Stops the camera if it's working
    def stop_camera(self):
        self.cam_end.set()
        if self.cam_thread.is_alive():
            self.cam_thread.join()

    # Restarts the camera
    def restart_camera(self):
        self.stop_camera()
        self.start_camera()

    def open_statistics_menu(self):
        self.currentTab.destroy()
        self.currentTab = StatisticsMenu(self, self.settings, self.db)
        self.currentTab.grid(row=0, column=1)

    def open_video_player(self):
        self.currentTab.destroy()
        self.currentTab = VideoPlayer(self, self.settings)
        self.currentTab.grid(row=0, column=1)

    def open_settings(self):
        self.currentTab.destroy()
        self.currentTab = SettingsMenu(self, self.settings)
        self.currentTab.grid(row=0, column=1)

    # Called when top right corner close button is pressed
    def close(self):
        plt.close('all')
        self.destroy()


# Main menu in top left corner
class MainMenu(tk.Frame):
    def __init__(self, master, settings: settings.Settings, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings

        # Creating buttons
        self.plotButton = tk.Button(self, text='Statistics', command=master.open_statistics_menu)
        self.videosButton = tk.Button(self, text='Saved videos', command=master.open_video_player) 
        self.settingsButton = tk.Button(self, text='Settings', command=master.open_settings)

        self.buttons_pady = 4
        self.buttons_ipady = 2

        self.plotButton.grid(row=0, column=0, ipady=self.buttons_ipady, pady=self.buttons_pady)
        self.videosButton.grid(row=1, column=0, ipady=self.buttons_ipady, pady=self.buttons_pady)
        self.settingsButton.grid(row=2, column=0, ipady=self.buttons_ipady, pady=self.buttons_pady)

class StatisticsMenu(tk.Frame):
    def __init__(self, master, settings: settings.Settings, database: dbutils.Database, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings
        self.db = database
        self.plot_size = (7, 4) # Plot size in inches

        self.plotFrame = tk.Frame(self, width=500, height=500, bg='red')
        self.statsFrame = tk.Frame(self, width=500, height=200, bg='green')
        self.plotFrame.grid(row=0, column=0)
        self.statsFrame.grid(row=1, column=0, pady=30)

        self.create_fig()

        self.plot('Fox', 3600*24, 'r')
        self.plot('Cat', 3600*24, 'b')

    # Get data as a dict of <Date>: <number of occurrences> pairs for both foxes and cats
    # Rounds date to nearest n seconds
    def records_to_dict(self, records, round_sec):
        data = {'Fox': {},
                'Cat': {}}
        for row in records:
            dict = data[row['Label']]
            time = round(int(row['Unix time']) / round_sec) * round_sec # Round the time
            if time not in dict:
                dict[time] = 1
            else:
                dict[time] += 1            

        return data
    
    # Create matplotlib figure, tkinter canvas and toolbar
    def create_fig(self):
        self.fig = plt.figure(figsize=self.plot_size, dpi=100)
        self.fig_canvas = plt_backend.FigureCanvasTkAgg(self.fig, self.plotFrame)
        self.toolbar = plt_backend.NavigationToolbar2Tk(self.fig_canvas, self.plotFrame)

        self.fig_canvas.get_tk_widget().pack()

    # Draw a plot using matplotlib
    # Rounds time to n seconds
    def plot(self, label, round_sec, color):
        # Get data
        records = self.db.read_records()
        records_dict = self.records_to_dict(records, round_sec)
        records_dict = records_dict[label]

        # Determine boundaries of the plot
        min_time = min(records_dict)
        max_time = max(records_dict) 

        # Create x and y axis
        x = []
        y = []
        for time in range(min_time, max_time + 1, round_sec):
            x.append(datetime.datetime.fromtimestamp(time))
            if time not in records_dict:
                y.append(0)
            else:
                y.append(records_dict[time])
        
        plt.plot(x, y, color=color, label=label)
        plt.legend()

        self.fig_canvas.draw()
        self.toolbar.update()
        


class SettingsMenu(tk.Frame):
    def __init__(self, master, settings: settings.Settings, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings

        self.settingsFrame = tk.Frame(self) # Frame containing settings themselves
        self.settingsFrame.grid(row=0, column=0)
        self.bottomFrame = tk.Frame(self) # Frame containing "Apply", "Restart camera" buttons at the bottom
        self.bottomFrame.grid(row=1, column=0, pady=30, sticky='w')

        self.restartInfoLabel = tk.Label(self, pady=8, text='Some changes may take effect only after restart', fg='red')
        self.restartInfoLabel.grid(row=2, column=0, sticky='w')

        self.settingsWidgets = [] # List of pairs of all settings and their respective names
        self.settings_per_column = 6 # Max number of settings per column in settingsFrame
        self.settings_pady = 10
        self.settings_padx = 30


        self.applyButton = tk.Button(self.bottomFrame, text='Apply', command=self.apply_settings)
        self.applyButton.grid(column=0, row=0, padx=self.settings_padx)

        self.restartCamButton = tk.Button(self.bottomFrame, text="Restart camera", command=self.master.restart_camera)
        self.restartCamButton.grid(column=1, row=0)

        self.add_setting(tk.Entry, 'Camera url', width=50)
        self.add_setting(ttk.Combobox, 'Window resolution', width=9, values=["640x480", "800x600", 
                                                                             "1600x900",   "1920x1080"])
        self.add_setting(tk.Checkbutton, 'Autostart camera')

    # Adds a setting to settingsFrame
    def add_setting(self, setting_class: tk.Widget, setting_name, *args, **kwargs):
        # Tweak some arguments based a the setting class
        if setting_class == tk.Checkbutton:
            # Tkinter requires a variable assigned to Checkbutton instances
            var = tk.IntVar()
            kwargs['variable'] = var

        # Create a frame and a label for the setting
        frame = tk.Frame(self.settingsFrame)
        label = tk.Label(frame, text=setting_name + ':\t')
        label.grid(row=0, column=0, padx=5)
    
        setting_instance = setting_class(frame, *args, **kwargs) # Create an instance of tkinter widget
        setting_instance.grid(row=0, column=1)

        # Get number of settings to calculate row & column and place the widget
        n = len(self.settingsWidgets) 
        column = n // self.settings_per_column
        row = n % self.settings_per_column
        

        # Insert current setting value
        if setting_class == tk.Entry:
            setting_instance.insert(0, self.settings.get(setting_name))

        if setting_class == tk.Checkbutton:
            var.set(self.settings.get(setting_name))
            setting_instance = var # Access to Checkbutton is provided via linked variables, so only those are needed
        
        if setting_class == ttk.Combobox:
            setting_instance.set(self.settings.get(setting_name))

        frame.grid(row=row, column=column, padx=self.settings_padx, pady=self.settings_pady, sticky='w')

        self.settingsWidgets.append((setting_instance, setting_name))

    # Collect values in entries and save them
    def apply_settings(self):
        for widget, setting_name in self.settingsWidgets:
            self.settings.set(setting_name, widget.get())
        self.settings.apply()

# Toolbar and video itself
class VideoPlayer(tk.Frame):
    def __init__(self, master, settings: settings.Settings, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings

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
    window.protocol('WM_DELETE_WINDOW', window.close)
    window.mainloop()

if __name__ == '__main__':
    main()