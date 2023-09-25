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
import time as time_lib
import matplotlib.dates as plt_dates
import numpy as np

INF = int(1e20)

class MainApp(tk.Tk):
    def __init__(self, title='Fox spy', *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = settings.Settings()

        self.cam_end = threading.Event()
        self.db = dbutils.Database()
        self.cam_thread = None
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
    def start_camera(self):
        if self.cam_thread == None or not self.cam_thread.is_alive():
            rtsp_url = self.settings.get("Camera url")
            start_time = datetime.datetime.strptime(self.settings.get("Camera start time"), "%H:%M")
            end_time = datetime.datetime.strptime(self.settings.get("Camera end time"), "%H:%M")
            self.cam = camutils.Camera(rtsp_url, self.db, start_time, end_time, log=True)

            self.cam_thread = threading.Thread(target=self.cam.start, args=(self.cam_end,))
            self.cam_end.clear()
            self.cam_thread.start()

    # Stops the camera if it's working
    def stop_camera(self):
        self.cam_end.set()
        if self.cam_thread != None and self.cam_thread.is_alive():
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
        # Close plot and tkinter window
        plt.close('all')
        self.destroy()
        # End camera thread
        if self.cam_thread:
            self.cam_end.set()
            self.cam_thread.join()


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
        self.labels = ['Fox', 'Cat']
        self.y_axs = []

        self.plotFrame = tk.Frame(self, width=500, height=500)
        self.settingsWidgets = SettingsWidgets(self, settings, 4, 2, 5)
        self.statsLabels = Statistics(self, self.labels, 4, 8, 20)
        self.bottomFrame = tk.Frame(self)

        pady = 0
        self.plotFrame.grid(row=0, column=0, pady=pady)
        self.settingsWidgets.grid(row=1, column=0, pady=pady, sticky='w')
        self.statsLabels.grid(row=2, column=0, pady=pady, sticky='w')
        self.bottomFrame.grid(row=3, column=0)

        self.applyButton = tk.Button(self.bottomFrame, text='Update', command=self.update)
        self.applyButton.grid(row=0, column=0, sticky='w')

        # Add settings
        self.settingsWidgets.add_setting(tk.Checkbutton, "Grid", "Show grid")
        self.settingsWidgets.add_setting(tk.Checkbutton, "Show Fox", "Show foxes")
        self.settingsWidgets.add_setting(tk.Checkbutton, "Show Cat", "Show cats")
        self.settingsWidgets.add_setting(tk.Checkbutton, "Show average")
        self.settingsWidgets.add_setting(ttk.Combobox, "Time periods", values=["Hours",
                                                                               "Days",
                                                                               "Weeks",
                                                                               "Months"], state="readonly")
        self.settingsWidgets.add_setting(tk.Entry, "Plot start", "Start date (dd/mm/yy)", width=8)
        self.settingsWidgets.add_setting(tk.Entry, "Plot end", "End date (dd/mm/yy)", width=8)
        self.settingsWidgets.add_setting(tk.Label, None, text="Leave start/end dates empty\nto include everything", fg='red')

        # Add stats
        self.statsLabels.add_stat("Mean", np.mean)
        self.statsLabels.add_stat("Median", np.median)
        self.statsLabels.add_stat("Max", np.max)
        self.statsLabels.add_stat("Total", np.sum)

        self.create_fig()
        self.update()

    # Update all settings and the graph
    def update(self):
        self.settingsWidgets.apply_settings() 
        self.fig.clear()
        self.plot()
        self.statsLabels.update_stats(self.y_axs)


    # Get data as a dict of <Date>: <number of occurrences> pairs for both foxes and cats
    # Rounds date to nearest n seconds and averages across m second periods
    def records_to_dict(self, records, round_sec, average_period, start=None, end=None):
        data = {}
        # Include everything if not stated otherwise
        if start == None:
            start = INF
            for row in records:
                start = min(start, int(row['Unix time']))
        if end == None:
            end = time_lib.time()
        
        # Check that averaging is turned on
        if average_period != INF:
            average_divisor = (end - start) / average_period
        else:
            average_divisor = 1

        for label in self.labels:
            # Add 1 dummy value so no dictionaries are empty
            dummy_time = round(time_lib.time() / round_sec) * round_sec # Round the time
            dummy_time %= average_period
            data[label] = {dummy_time: 0}
        for row in records:
            unix_time = int(row['Unix time'])
            # Skip if out of needed time period
            if unix_time < start or end < unix_time:
                continue
            dict = data[row['Label']]
            time = round(unix_time / round_sec) * round_sec # Round the time
            time %= average_period
            if time not in dict:
                dict[time] = 0
            dict[time] += 1 / average_divisor
        
        return data
    
    # Create matplotlib figure, tkinter canvas and toolbar
    def create_fig(self):
        self.fig = plt.figure(figsize=self.plot_size, dpi=100)
        plt.plot() # Create axes
        self.fig_canvas = plt_backend.FigureCanvasTkAgg(self.fig, self.plotFrame)
        self.toolbar = plt_backend.NavigationToolbar2Tk(self.fig_canvas, self.plotFrame)
        
        self.fig.subplots_adjust(bottom=0.2) # Allocate more space for labels
        self.fig_canvas.get_tk_widget().pack() # Place the matplotlib widget in tkinter window

    # Returns unix time from human-readable time format
    def str_time_to_unix(self, time):
        if time == "":
            return None
        else:
            date = datetime.datetime.strptime(time, "%d/%m/%y") # datetime object
            unix = time_lib.mktime(date.timetuple())
            return unix

    # Draw a plot using matplotlib
    # Rounds time to n seconds
    def plot(self):
        start = self.str_time_to_unix(self.settings.get("Plot start"))
        end = self.str_time_to_unix(self.settings.get("Plot end"))

        colors = ['r', 'b', 'g', 'y'] # Colors for plots
        periods = ["Hours", "Days", "Weeks", "Months", "Years"]
        periods_to_seconds = {"Hours" : 3600,
                              "Days"  : 3600 * 24,
                              "Weeks" : 3600 * 24 * 7,
                              "Months": 3600 * 24 * 30,
                              "Years" : 3600 * 24 * 365}
        time_periods = self.settings.get("Time periods")
        round_sec = periods_to_seconds[time_periods]
        if (self.settings.get("Show average")):
            # Pick one period above. For example, hours will be averaged across all days
            average_period_str = periods[periods.index(time_periods) + 1]
            average_period = periods_to_seconds[average_period_str]
        else:
            average_period = INF

        # Get data
        records = self.db.read_records()
        records_dict = self.records_to_dict(records, round_sec, average_period, start, end)

        # Determine boundaries of the plot
        min_time = INF
        max_time = -1
        for label_dict in records_dict.values():
            min_time = min(min_time, min(label_dict))
            max_time = max(max_time, max(label_dict))


        x = [] # Single x axis
        y_axs = {} # Multiple y axes for each label
        for label in records_dict:
            y_axs[label] = []

        # Fill x and y axes
        for time in range(min_time, max_time + 1, round_sec):
            x.append(datetime.datetime.fromtimestamp(time))
            for label in records_dict:
                if time not in records_dict[label]:
                    y_axs[label].append(0) # Add 0 if no animals were detected at that time
                else:
                    y_axs[label].append(records_dict[label][time]) # Add number of animals detected at that time
        
        self.plots = {}
        for i, label in enumerate(records_dict):
            show = self.settings.get("Show " + label)
            if show:
                self.plots[label], = plt.plot(x, y_axs[label], color=colors[i], label=label)
        self.y_axs = y_axs

        # Toggle grid
        mode = self.settings.get('Grid')
        plt.grid(mode)
    
        ax = self.fig.axes[0]
        ax.xaxis.set_major_formatter(plt_dates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
        plt.legend()
        self.fig_canvas.draw()
        self.toolbar.update()


class SettingsMenu(tk.Frame):
    def __init__(self, master, settings: settings.Settings, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings

        settings_per_column = 6 # Max number of settings per column in settingsFrame
        settings_pady = 8
        settings_padx = 8

        settingsFrame = SettingsWidgets(self, settings, settings_per_column, settings_pady, settings_padx) # Frame containing settings themselves
        settingsFrame.grid(row=0, column=0)
        bottomFrame = tk.Frame(self) # Frame containing "Apply", "Restart camera" buttons at the bottom
        bottomFrame.grid(row=1, column=0, pady=30, sticky='w')

        restartInfoLabel = tk.Label(self, pady=8, text='Some changes may take effect only after restart', fg='red')
        restartInfoLabel.grid(row=2, column=0, sticky='w')

        applyButton = tk.Button(bottomFrame, text='Apply', command=settingsFrame.apply_settings)
        applyButton.grid(column=0, row=0, padx=settings_padx)

        restartCamButton = tk.Button(bottomFrame, text="Restart camera", command=self.master.restart_camera)
        restartCamButton.grid(column=1, row=0)

        settingsFrame.add_setting(tk.Entry, 'Camera url', width=50)
        settingsFrame.add_setting(ttk.Combobox, 'Window resolution', width=9, values=["640x480", 
                                                                                      "800x600", 
                                                                                      "1600x900",  
                                                                                      "1920x1080"])
        settingsFrame.add_setting(tk.Checkbutton, 'Autostart camera')
        settingsFrame.add_setting(tk.Entry, 'Camera start time', 'Camera start time (hh:mm)', width=5)
        settingsFrame.add_setting(tk.Entry, 'Camera end time', 'Camera end time (hh:mm)', width=5)


# Frame with settings and convenient functions for creating them
class SettingsWidgets(tk.Frame):
    def __init__(self, master, settings: settings.Settings, 
                 settings_per_column, pady, padx,
                 *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.settings = settings

        self.settingsWidgets = [] # List of pairs of all settings and their respective names
        self.settings_per_column = settings_per_column # Max number of settings per column in settingsFrame
        self.settings_pady = pady
        self.settings_padx = padx

    # Adds a setting to settingsFrame
    def add_setting(self, setting_class: tk.Widget, setting_name, text=None, *args, **kwargs):
        if text == None:
            text = setting_name

        # Tweak some arguments based a the setting class
        if setting_class == tk.Checkbutton:
            # Tkinter requires a variable assigned to Checkbutton instances
            var = tk.IntVar()
            kwargs['variable'] = var

        # Get number of settings to calculate row & column and place the widget
        n = len(self.settingsWidgets) 
        column = n // self.settings_per_column
        row = n % self.settings_per_column

        # If it is a label, skip all other steps
        if setting_class == tk.Label:
            label = setting_class(self, text=text, *args, **kwargs)
            label.grid(row=row, column=column)
            return

        # Create a frame and a label for the setting
        frame = tk.Frame(self)
        label = tk.Label(frame, text=text + ':\t')
        label.grid(row=0, column=0, padx=5)
    
        setting_instance = setting_class(frame, *args, **kwargs) # Create an instance of tkinter widget
        setting_instance.grid(row=0, column=1)

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

class Statistics(tk.Frame):
    def __init__(self, master, labels,
                 stats_per_column, pady, padx,
                 *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.labels = labels
        self.stats_per_column = stats_per_column # Max number of settings per column in settingsFrame
        self.pady = pady
        self.padx = padx

        self.stats = [] # List of tuples (tk.Label, label, func)

    def add_stat(self, name, func):
        # Calculate row & column for the widget
        n = len(self.stats) 
        column = n // self.stats_per_column
        row = n % self.stats_per_column

        # Create a frame & stat label
        frame = tk.Frame(self)
        nameLabel = tk.Label(frame, text=name + ': ') # Stat name (e.g mean/median)
        nameLabel.grid(row=0,column=0, sticky='w')
        # Create stat for all labels (cats, foxes, etc)
        for i, label in enumerate(self.labels):
            labelLabel = tk.Label(frame, text=' ' * 5 + label + ':') # Label name (e.g cat/fox)
            stat = tk.Label(frame) # Actual number
            labelLabel.grid(row=i + 1, column=0, sticky='w')
            stat.grid(row=i + 1, column=1, sticky='w')
            self.stats.append((stat, label, func))

        frame.grid(row=row, column=column, padx=self.padx, pady=self.pady, sticky='w')

    # Update values for all stats
    def update_stats(self, y_axs):
        for stat, label, func in self.stats:
            number = round(func(y_axs[label]), 2)
            stat.config(text=str(number))

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
    
# Progress bar below the video to navigate it using mouse
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