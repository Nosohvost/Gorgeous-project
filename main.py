import tkinter as tk

class MainApp(tk.Tk):
    def __init__(self, title='Fox spy', *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resizable(width=False, height=False)
        self.title(title)

        self.menu = MainMenu(self, relief='groove', borderwidth=5, padx=5, pady=5)
        self.menu.grid(row=0, column=1, padx=20, pady=10)

        #Placeholder for quick statistics tab
        self.statisticsTab = Placeholder(self, width=200, height=400, bg='red')
        self.statisticsTab.grid(row=0, column=0)


class MainMenu(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #Creating buttons
        self.plotButton = tk.Button(self, text='Show plot')
        self.videosButton = tk.Button(self, text='Saved videos') 
        self.settingsButton = tk.Button(self, text='Settings')

        self.plotButton.grid(row=0, column=0, ipady=2, pady=4)
        self.videosButton.grid(row=1, column=0, ipady=2, pady=4)
        self.settingsButton.grid(row=2, column=0, ipady=2, pady=4)
        

class Placeholder(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

def main():
    window = MainApp()
    window.mainloop()

if __name__ == '__main__':
    main()