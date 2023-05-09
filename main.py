import tkinter as tk

class MainApp(tk.Tk):
    def __init__(self, title='Fox spy', *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Minimum width & height for the window
        self.MIN_WIDTH = 150
        self.MIN_HEIGHT = 150
        self.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)

        self.resizable(width=True, height=True)
        self.title(title)

        # Create main menu
        self.mainMenu = MainMenu(self)
        self.mainMenu.grid(row=0, column=0)


    def open_statistics_menu(self):
        pass

    def open_video_player(self):
        pass

    def open_settings(self):
        pass

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
    pass
        
# Basic placeholder for features that aren't implemented yet
class Placeholder(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

def main():
    window = MainApp()
    window.mainloop()

if __name__ == '__main__':
    main()