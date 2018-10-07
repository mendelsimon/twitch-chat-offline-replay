import os
from tkinter import Tk, BOTH, TOP, LEFT, RIGHT, X, S, HORIZONTAL, Canvas, VERTICAL, Y, BOTTOM, N, W, NSEW, Toplevel, \
    SOLID, Text, IntVar, StringVar, BooleanVar, DoubleVar, DISABLED, END, WORD, PhotoImage, TclError, NORMAL
from tkinter.ttk import Frame, Button, Scale, Scrollbar, Label, Checkbutton, Separator, Style, Entry, Progressbar
from tkinter.font import Font, BOLD
from chat_downloader import get_emote, video_exists, parse_url, ChatDownloader, UNICODE_MATCHER, CACHE_FOLDER
import re
from PIL import Image, ImageTk

from message_store import MessageStore

DEFAULT_FONT_SIZE: int = 13


class ChatPlayer(Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master.title("Chat Player")
        self.pack(fill=BOTH, expand=True)

        # Variables

        self.font_size_var: IntVar = IntVar(value=DEFAULT_FONT_SIZE)
        self.time_display_var: StringVar = StringVar(value='0:00:00')
        self.speed_display_var: StringVar = StringVar(value='1.00')
        self.seconds_elapsed_var: DoubleVar = DoubleVar(value=0)
        self.autoscroll_var: BooleanVar = BooleanVar(value=True)
        self.paused_var: BooleanVar = BooleanVar(value=True)
        self.always_on_top_var: BooleanVar = BooleanVar(value=False)
        self.pause_button_text_var: StringVar = StringVar(value='⏵')
        self.search_regex_var: BooleanVar = BooleanVar(value=False)
        self.search_case_sensitive_var: BooleanVar = BooleanVar(value=False)
        self.search_count_var: IntVar = IntVar()

        # Style
        self.chat_font = Font(family="Helvetica", size=self.font_size_var.get())

        # Gui

        # self.chat_frame_container = Scrollable(self, outer_kwargs={'padding': 0})
        # self.chat_frame_container.pack(side=TOP, fill=BOTH, expand=True)
        # self.chat_frame = self.chat_frame_container.frame

        self.chat_text = ChatText(self, undo=False, wrap=WORD, padx=6)
        self.chat_text.search_frame.regex_check.configure(variable=self.search_regex_var)
        self.chat_text.search_frame.case_check.configure(variable=self.search_case_sensitive_var)

        self.options_frame = OptionsFrame(self, pad=2)
        self.options_frame.autoscroll_check.configure(variable=self.autoscroll_var)
        self.options_frame.font_size_label.configure(textvariable=self.font_size_var)
        self.speed_control_frame = self.options_frame.speed_control_frame
        self.speed_control_frame.speed_label.configure(textvariable=self.speed_display_var)

        self.time_frame = TimeFrame(self, height=150)
        self.time_frame.play_pause_button.configure(textvariable=self.pause_button_text_var)
        self.time_frame.time_elapsed_label.configure(textvariable=self.time_display_var)
        self.time_frame.time_scale.configure(variable=self.seconds_elapsed_var)

        self.time_frame.pack(side=BOTTOM, fill=X, anchor=S)
        Separator(self, orient=HORIZONTAL).pack(side=BOTTOM, anchor=W, fill=X)
        self.options_frame.pack(side=BOTTOM, fill=X, anchor=S)
        self.options_frame.always_on_top_check.configure(variable=self.always_on_top_var)
        Separator(self, orient=HORIZONTAL).pack(side=BOTTOM, fill=X, anchor=W)
        # Separator(self, orient=HORIZONTAL).pack(side=TOP, anchor=N, fill=X, pady=(5, 0), ipady=0)
        self.chat_text.pack(side=TOP, fill=BOTH, expand=True)
        self.master.attributes('-topmost', True)
        self.master.attributes('-topmost', False)


class SpeedControlFrame(Frame):
    def __init__(self, master, **kwargs):
        Frame.__init__(self, master, **kwargs)
        BUTTON_WIDTH = 3
        self.speed_minus_1_button = Button(self, text='<<', width=BUTTON_WIDTH, takefocus=False)
        self.speed_minus_point_1_button = Button(self, text='<', width=BUTTON_WIDTH, takefocus=False)
        self.speed_label = Label(self, text='1.10', padding=(6, 2, 6, 2), relief=SOLID, borderwidth=1)
        self.speed_plus_point_1_button = Button(self, text='>', width=BUTTON_WIDTH, takefocus=False)
        self.speed_plus_1_button = Button(self, text='>>', width=BUTTON_WIDTH, takefocus=False)

        self.speed_minus_1_button.pack(side=LEFT)
        self.speed_minus_point_1_button.pack(side=LEFT)
        self.speed_label.pack(side=LEFT, padx=4)
        self.speed_plus_point_1_button.pack(side=LEFT)
        self.speed_plus_1_button.pack(side=LEFT)


class OptionsFrame(Frame):
    def __init__(self, master, **kwargs):
        Frame.__init__(self, master)

        self.autoscroll_check = Checkbutton(self, text='Autoscroll', takefocus=False)
        self.autoscroll_check.pack(side=LEFT, anchor=W, padx=8)

        Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, pady=2)

        Label(self, text='Size:').pack(side=LEFT, padx=(8, 3))
        self.font_down_button = Button(self, text='-', width=3, takefocus=False)
        self.font_down_button.pack(side=LEFT)
        self.font_size_label = Label(self, text='24', padding=(6, 2, 6, 2), relief=SOLID, borderwidth=1)
        self.font_size_label.pack(side=LEFT, padx=4)
        self.font_up_button = Button(self, text='+', width=3, takefocus=False)
        self.font_up_button.pack(side=LEFT, padx=(0, 8))

        Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, pady=2)

        Label(self, text='Speed:').pack(side=LEFT, padx=(8, 3))
        self.speed_control_frame = SpeedControlFrame(self)
        self.speed_control_frame.pack(side=LEFT, padx=(0, 8))

        Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, pady=2)
        self.always_on_top_check = Checkbutton(self, text='Top', takefocus=False)
        self.always_on_top_check.pack(side=LEFT, padx=(8, 0))


class TimeFrame(Frame):
    def __init__(self, master, **kwargs):
        Frame.__init__(self, master, **kwargs)
        s = Style()
        s.configure('play_pause.TButton', font=('Helvetica', 18))
        self.play_pause_button = Button(self, width=3, takefocus=False, style='play_pause.TButton')
        self.play_pause_button.pack(side=LEFT, padx=8, pady=8, ipady=4)

        Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, pady=4)

        self.time_elapsed_label = Label(self, relief=SOLID, borderwidth=1, padding=3)
        self.time_elapsed_label.pack(side=LEFT, padx=8)
        self.time_scale = ClickableScale(self, orient=HORIZONTAL, takefocus=False)
        self.time_scale.pack(side=LEFT, fill=BOTH, expand=True)
        self.end_time_label = Label(self, text='1:20:18', relief=SOLID, borderwidth=1, padding=3)
        self.end_time_label.pack(side=LEFT, padx=8)
        # Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, pady=4)


class ChatText(Text):
    def __init__(self, master, **kwargs):
        self.master = Frame(master)
        self.font = Font(family="Helvetica", size=DEFAULT_FONT_SIZE)
        self.font_bold = Font(family="Helvetica", size=DEFAULT_FONT_SIZE, weight=BOLD)
        Text.__init__(self, self.master, font=self.font, state=DISABLED, **kwargs)
        self.scrollbar = Scrollbar(self.master, orient=VERTICAL, command=self.yview)
        self.search_frame = SearchFrame(self.master)
        self.configure(yscrollcommand=self.scrollbar.set)
        self.images: list = []

    def pack(self, **kwargs):
        self.master.pack(**kwargs)
        self.search_frame.pack(side=BOTTOM, fill=X)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        Text.pack(self, side=LEFT, fill=BOTH, expand=True)

    def repack(self):
        self.search_frame.pack_forget()
        self.scrollbar.pack_forget()
        Text.pack_forget(self)
        self.search_frame.pack(side=BOTTOM, fill=X)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        Text.pack(self, side=LEFT, fill=BOTH, expand=True)

    def append_message(self, username: str, fragments: list, color: str, autoscroll: bool = True):
        self.configure(state=NORMAL)
        self.tag_configure(username, foreground=color, font=self.font_bold)
        self.insert(END, username, username)
        self.insert(END, ' : ')
        for fragment in fragments:
            if 'emoticon' in fragment:
                emote_id = fragment.get('emoticon').get('emoticon_id')
                image_path = get_emote(emote_id)
                image = ImageTk.PhotoImage(Image.open(image_path))
                self.image_create(END, image=image, padx=2, pady=2)
                self.images.append(image)
            else:
                self.insert(END, fragment.get('text'), fragment.get('tag'))
        if autoscroll:
            self.yview_moveto(1.0)
        self.insert(END, '\n')
        self.configure(state=DISABLED)

    def clear(self):
        self.configure(state=NORMAL)
        self.delete(1.0, END)
        self.configure(state=DISABLED)


class SearchFrame(Frame):
    def __init__(self, master, **kwargs):
        Frame.__init__(self, master, **kwargs)
        Separator(self, orient=HORIZONTAL).pack(side=TOP, fill=X)
        self.close = Button(self, text='x', width=3, takefocus=False)
        self.close.pack(side=RIGHT)
        self.entry = Entry(self)
        self.entry.pack(side=LEFT, padx=8)
        self.prev = Button(self, text="<", width=3, takefocus=False)
        self.prev.pack(side=LEFT)
        self.next = Button(self, text=">", width=3, takefocus=False)
        self.next.pack(side=LEFT)
        Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, pady=2, padx=(6, 4))
        self.regex_check = Checkbutton(self, text='Regex', takefocus=False)
        self.regex_check.pack(side=LEFT)
        self.case_check = Checkbutton(self, text='Case Sensitive', takefocus=False)
        self.case_check.pack(side=LEFT, padx=5)


class ClickableScale(Scale):
    def __init__(self, master, **kwargs):
        Scale.__init__(self, master, **kwargs)
        self.bind('<Button-1>', self.on_click)

    def on_click(self, event):
        self.event_generate('<Button-3>', x=event.x, y=event.y)
        return 'break'


class DownloadPopup(Toplevel):
    def __init__(self, master, info: dict, message_store: MessageStore, video_id: str = None):
        Toplevel.__init__(self, master)
        self.bind('<Escape>', lambda _: self.cancel())
        self.bind('<Return>', lambda _: self.ok())
        self.title('Get VOD')
        self.transient(master)
        self.grab_set()

        self.info: dict = info
        self.message_store: MessageStore = message_store
        self.chat_downloader: ChatDownloader = None

        self.updated_info: bool = False
        self.status_var = StringVar(value='...')
        self.content = Frame(self)
        self.content.pack(padx=20, pady=15)
        self.video_title_var = StringVar(value='')
        self.download_info_var = StringVar(value='')
        self.eta_var = StringVar(value='')
        Label(self.content, text='Enter a VOD URL or video ID:').pack(side=TOP, anchor=W, pady=(0, 5))
        self.entry = Entry(self.content, width=50)
        self.entry.pack(side=TOP, padx=2, pady=(0, 5))
        Label(self.content, textvariable=self.status_var).pack(side=TOP, anchor=W, pady=(0, 5))

        self.progress_var = IntVar(value=0)
        self.progress = Progressbar(self.content, variable=self.progress_var, maximum=1)
        self.progress.pack(side=TOP, fill=X, padx=2)

        Label(self.content, textvariable=self.video_title_var).pack(side=TOP, anchor=W, pady=(0, 5))
        Label(self.content, textvariable=self.download_info_var).pack(side=TOP, anchor=W, pady=(0, 5))
        Label(self.content, textvariable=self.eta_var).pack(side=TOP, anchor=W, pady=(0, 5))

        self.overwrite_cache_var = BooleanVar(value=False)
        self.overwrite_cache_check = Checkbutton(self.content, text='Overwrite cache',
                                                 variable=self.overwrite_cache_var)
        self.overwrite_cache_check.pack(side=TOP, anchor=W, pady=(0, 5))

        self.button = Button(self.content, text='OK', command=self.ok)
        self.button.pack(side=TOP)
        self.update()
        x_coord = self.master.winfo_x() + (self.master.winfo_width() // 2) - (self.winfo_width() // 2)
        y_coord = self.master.winfo_y() + (self.master.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f'{self.winfo_width()}x{self.winfo_height()}+{x_coord}+{y_coord}')
        self.entry.focus_set()
        self.protocol('WM_DELETE_WINDOW', self.cancel)

        if video_id:
            self.entry.insert(0, video_id)
            self.overwrite_cache_check.focus_set()

            chat_filename: str = os.path.join(CACHE_FOLDER, f'chat-{video_id}.json')
            if not os.path.exists(chat_filename):
                self.ok()

    def cancel(self):
        if self.chat_downloader:
            self.chat_downloader.kill()
        self.info.clear()
        self.info.update({'title': 'Chat Player'})
        self.destroy()

    def ok(self):
        self.button.config(state=DISABLED)
        self.overwrite_cache_check.config(state=DISABLED)
        self.status_var.set('Validating...')
        self.after(1, self.validate)

    def validate(self):
        video_id: str = self.entry.get()
        if 'http' in video_id or 'twitch.tv' in video_id:
            video_id = parse_url(video_id)
        if len(video_id) > 0 and video_exists(video_id):
            self.chat_downloader = ChatDownloader(video_id, overwrite_cache=self.overwrite_cache_var.get())
            self.chat_downloader.start()
            self.after(1, self.download)
        else:
            self.status_var.set('Error: Invalid URL or video ID.')
            self.button.config(state=NORMAL)

    def download(self):
        if not self.chat_downloader.info:
            self.status_var.set('Getting info')
            self.after(100, self.download)
        elif not self.chat_downloader.messages:
            if not self.updated_info:
                self.status_var.set('Downloading chat')
                self.info.update(self.chat_downloader.info)
                self.video_title_var.set(self.info.get('title'))
                self.updated_info = True
            self.progress_var.set(self.chat_downloader.progress)
            self.download_info_var.set(
                f'{self.chat_downloader.num_messages} messages downloaded. '
                f'Duration {self.chat_downloader.duration_done_str}/{self.chat_downloader.duration_str}.')
            self.eta_var.set(f'ETA: {self.chat_downloader.eta_str}')
            self.after(100, self.download)
        else:
            self.message_store.set_messages(self.chat_downloader.messages)
            self.destroy()


class ErrorMessage(Toplevel):
    def __init__(self, message: str):
        Toplevel.__init__(self)
        self.text = Text(self)
        self.text.pack(side=TOP, fill=BOTH)
        self.text.insert(END, message)
        self.text.config(state=DISABLED)
        self.grab_set()
        self.button = Button(self, text='Exit', command=self.master.destroy)
        self.button.pack(side=BOTTOM, anchor=S, pady=10)
        self.lift()
        self.attributes("-topmost", True)


def replace_unicode(match):
    char = match.group()
    assert ord(char) > 0xffff
    encoded = char.encode('utf-16-le')
    return (
            chr(int.from_bytes(encoded[:2], 'little')) +
            chr(int.from_bytes(encoded[2:], 'little')))


def run_gui(geometry="800x600"):
    root = Tk()
    root.geometry = geometry
    app = ChatPlayer(root)
    app.bind_all('<Escape>', lambda _: app.quit())
    root.mainloop()


if __name__ == '__main__':
    run_gui()
