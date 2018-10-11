import traceback

from gui import ChatPlayer, DownloadPopup, DEFAULT_FONT_SIZE, ErrorMessage
from chat_downloader import ChatDownloader, parse_url, video_exists
from clock import Clock
from tkinter import Tk, END, UNITS
from message_store import MessageStore
import sys

TICK_MS = 50


class GuiController:
    def __init__(self, video_id=None, geometry='530x991+1913+0'):
        self.gui_root: Tk = Tk()
        self.geometry = geometry
        self.gui_root.geometry(self.geometry)
        self.gui: ChatPlayer = ChatPlayer(self.gui_root)
        self.previous_tick: float = 0
        self.scrubbing: bool = False
        self.search_open: bool = True
        self.search_focused: bool = False
        self.new_search: bool = False
        self.clock: Clock = Clock()
        self.clock.start()
        self.clock.pause()
        self.info: dict = {'title': 'Chat Player'}
        self.message_store: MessageStore = MessageStore([])
        self.duration: int = 0
        self.gui_root.bind_all('<Control-n>', lambda _: self._configure_vid_info())
        self.gui_root.bind_all('<Control-w>', lambda _: self.exit())
        self.gui_root.bind_all('<Pause>', lambda _: self.exit())
        self.gui_root.bind_all('<Escape>', lambda _: self.toggle_search() if self.search_open else None)
        if self.search_open:
            self.toggle_search()
        self._configure_vid_info(video_id)

    def _configure_vid_info(self, video_id=None):
        self.get_input(self.info, self.message_store, video_id)
        self.skip_to_time(0)
        if self.message_store.messages:
            self.duration: int = self.info.get('length')
            self._configure_gui()

    def _configure_gui(self):
        self.gui_root.title(self.info.get('title'))

        def ctrl_f(_=None):
            if not self.search_open:
                self.toggle_search()
            else:
                self.gui.chat_text.search_frame.entry.focus_set(),
                self.gui.chat_text.search_frame.entry.select_range(0, END)

        self.gui_root.bind_all('<Control-f>', ctrl_f)
        self.gui_root.bind_all('<Control-MouseWheel>', lambda event: self.update_font_size(event.delta // 120))
        self.gui_root.bind_all('<MouseWheel>', self.wheel_event)
        self.gui_root.protocol("WM_DELETE_WINDOW", self.exit)
        self.key_binds: dict = {
            '<space>': lambda _: self.toggle_pause(),
            '<Home>': lambda _: self.skip_to_time(0),
            '<End>': lambda _: (
                self.gui.chat_text.see(END), self.gui.autoscroll_var.set(True)),
            'a': lambda _: self.gui.autoscroll_var.set(not self.gui.autoscroll_var.get()),
            't': lambda _: self.set_always_on_top(state=not self.gui.always_on_top_var.get()),
            'f': ctrl_f,
            's': lambda _: self.update_speed(-0.1),
            'S': lambda _: self.update_speed(-1),
            'D': lambda _: self.update_speed(1),
            'd': lambda _: self.update_speed(0.1),
            'r': lambda _: self.update_speed(1, absolute=True),
            'e': lambda _: self.update_speed(2, absolute=True),
            'z': lambda _: self.skip_to_time(self.gui.seconds_elapsed_var.get() - 5),
            'x': lambda _: self.skip_to_time(self.gui.seconds_elapsed_var.get() + 5),
            'Z': lambda _: self.skip_to_time(self.gui.seconds_elapsed_var.get() - 5),
            'X': lambda _: self.skip_to_time(self.gui.seconds_elapsed_var.get() + 5),
            '<Left>': lambda _: self.skip_to_time(self.gui.seconds_elapsed_var.get() - 10),
            '<Right>': lambda _: self.skip_to_time(self.gui.seconds_elapsed_var.get() + 10),
            '<j>': lambda _: self.skip_to_time(self.gui.seconds_elapsed_var.get() - 10),
            '<k>': lambda _: self.toggle_pause(),
            '<l>': lambda _: self.skip_to_time(self.gui.seconds_elapsed_var.get() + 10),
            '+': lambda _: self.update_font_size(1),
            '-': lambda _: self.update_font_size(-1)
        }
        for key, binding in self.key_binds.items():
            self.gui_root.bind_all(key, lambda evt, func=binding: func(evt) if not self.search_focused else None)

        self.gui.chat_text.search_frame.entry.bind('<FocusIn>', lambda _: self.focus_search(True))
        self.gui.chat_text.search_frame.entry.bind('<FocusOut>', lambda _: self.focus_search(False))
        self.gui.chat_text.search_frame.entry.bind('<Return>', lambda _: self.search(backwards=True))
        self.gui.chat_text.search_frame.entry.bind('<Shift-Return>', lambda _: self.search(backwards=False))
        self.gui.chat_text.search_frame.prev.configure(command=lambda: self.search(backwards=True))
        self.gui.chat_text.search_frame.next.configure(command=lambda: self.search(backwards=False))

        self.gui.time_frame.play_pause_button.configure(command=lambda: self.toggle_pause())
        self.gui.time_frame.end_time_label.configure(text=format_seconds(self.duration))
        self.gui.time_frame.time_scale.configure(to=self.duration)
        self.gui.time_frame.time_scale.configure(
            command=lambda _: self.skip_to_time(self.gui.seconds_elapsed_var.get()))
        self.gui.time_frame.time_scale.bind('<Button-3>', lambda _: self.scrub(True))
        self.gui.time_frame.time_scale.bind('<ButtonRelease-1>', lambda _: self.scrub(False))
        self.gui.speed_control_frame.speed_label.bind('<Button-1>', lambda _: self.update_speed(1, absolute=True))
        self.gui.options_frame.font_down_button.configure(command=lambda: self.update_font_size(-1))
        self.gui.options_frame.font_size_label.bind('<Button-1>',
                                                    lambda _: self.update_font_size(DEFAULT_FONT_SIZE, absolute=True))
        self.gui.options_frame.font_up_button.configure(command=lambda: self.update_font_size(1))
        self.gui.speed_control_frame.speed_minus_1_button.configure(command=lambda: self.update_speed(-1))
        self.gui.speed_control_frame.speed_minus_point_1_button.configure(
            command=lambda: self.update_speed(-0.1))
        self.gui.speed_control_frame.speed_plus_point_1_button.configure(
            command=lambda: self.update_speed(0.1))
        self.gui.speed_control_frame.speed_plus_1_button.configure(command=lambda: self.update_speed(1))
        self.gui.options_frame.always_on_top_check.configure(command=self.set_always_on_top)
        self.gui.chat_text.search_frame.close.configure(command=self.toggle_search)

        if not self.gui.paused_var.get():
            self.toggle_pause()

        if self.search_open:
            self.toggle_search()
        self.gui.after(TICK_MS, self.tick_clock)

    def tick_clock(self):
        if not self.gui.paused_var.get() and not self.scrubbing:
            current_tick = self.clock.elapsed_time
            if current_tick > self.duration:
                # self.skip_to_time(0)
                self.toggle_pause()
                current_tick = 0
            self.set_time(current_tick)
            if not self.previous_tick:
                messages = self.message_store.get(current_tick, current_tick, earlier_messages=50)
            else:
                messages = self.message_store.get(self.previous_tick, current_tick)

            self.gui_root.after(1, lambda: self.display_messages(messages))
            self.previous_tick = current_tick
        self.gui.after(TICK_MS, self.tick_clock)

    def scrub(self, state: bool):
        self.scrubbing = state

    def focus_search(self, state: bool):
        self.search_focused = state

    def set_time(self, seconds: float):
        if seconds >= 0:
            self.clock.set_elapsed_time(seconds)
            self.gui.seconds_elapsed_var.set(seconds)
            self.gui.time_display_var.set(format_seconds(seconds))

    def skip_to_time(self, seconds: float):
        if 0 <= seconds <= self.duration:
            self.gui.chat_text.clear()
            self.set_time(seconds)
            self.previous_tick = None
        else:
            self.skip_to_time(0.0)

    def update_font_size(self, size: int, absolute: bool = False):
        if absolute and size >= 6:
            self.gui.font_size_var.set(size)
            self.gui.chat_text.font.configure(size=size)
            self.gui.chat_text.font_bold.configure(size=size)
        else:
            # Prevent the size from getting too small
            new_size = self.gui.font_size_var.get() + size
            if new_size >= 6:
                self.gui.font_size_var.set(new_size)
                self.gui.chat_text.font.configure(size=new_size)
                self.gui.chat_text.font_bold.configure(size=new_size)

    def update_speed(self, speed: float, absolute: bool = False):
        if absolute:
            if speed > 0:
                self.gui.speed_display_var.set(f'{speed:.2f}')
                self.clock.speed = speed
        else:
            new_speed = float(self.gui.speed_display_var.get()) + speed
            if new_speed > 0:
                self.gui.speed_display_var.set(f'{new_speed:.2f}')
                self.clock.speed += speed

    def toggle_pause(self):
        self.gui.paused_var.set(not self.gui.paused_var.get())
        paused = self.gui.paused_var.get()
        if paused:
            self.clock.pause()
            self.gui.pause_button_text_var.set('⏵')
        else:
            self.clock.resume()
            self.gui.pause_button_text_var.set('⏸')

    def toggle_search(self):
        self.set_new_search()
        if self.search_open:
            self.gui.chat_text.search_frame.pack_forget()
            self.gui.chat_text.search_frame.entry.delete(0, END)
            self.gui.chat_text.tag_remove('search_result', 1.0, END)
            self.gui.chat_text.focus_set()
            self.search_open = False
        else:
            self.gui.chat_text.repack()
            self.gui.chat_text.search_frame.entry.focus_set()
            self.search_open = True

    def search(self, backwards=True):
        term = self.gui.chat_text.search_frame.entry.get()
        if term:
            search_pos = END
            ranges = self.gui.chat_text.tag_ranges('search_result')
            if not self.new_search and ranges:
                search_pos = ranges[0] if backwards else ranges[-1]
            self.new_search = False
            self.gui.chat_text.tag_remove('search_result', 1.0, END)
            pos = self.gui.chat_text.search(term, search_pos, backwards=backwards, count=self.gui.search_count_var,
                                            regexp=self.gui.search_regex_var.get(),
                                            nocase=not self.gui.search_case_sensitive_var.get())
            if pos:
                self.gui.chat_text.tag_add('search_result', pos, f'{pos}+{self.gui.search_count_var.get()}c')
                self.gui.chat_text.see(float(pos) - (2 if backwards else 0))  # Scroll up a bit for context
                self.gui.chat_text.see(pos)
                self.gui.autoscroll_var.set(False)

    def set_new_search(self):
        self.new_search = True
        return True

    def wheel_event(self, _):
        """Turn autoscroll off if scrolled away from the bottom,
        and turn it back on when scrolled down to the bottom"""
        if self.gui.chat_text.yview()[1] == 1.0:
            self.gui.autoscroll_var.set(True)
        else:
            self.gui.autoscroll_var.set(False)

    def set_always_on_top(self, state: bool = None):
        if not state:
            state = 'true' if self.gui.always_on_top_var.get() else 'false'
        self.gui_root.attributes('-topmost', state)

    def display_messages(self, messages: list):
        for message in messages:
            self.display_message(message)

    def display_message(self, message_dict: dict):
        username = message_dict.get('name')
        fragments = message_dict.get('fragments')
        color = message_dict.get('color')
        self.gui.chat_text.append_message(username, fragments, color, autoscroll=self.gui.autoscroll_var.get())

    def run(self, geometry=None):
        self.gui_root.geometry(self.geometry if not geometry else geometry)
        self.gui_root.mainloop()

    def exit(self):
        self.clock.stop()
        self.gui_root.quit()

    def get_input(self, info: dict, message_store: MessageStore, video_id=None):
        popup = DownloadPopup(self.gui_root, info, message_store, video_id)
        self.gui_root.wait_window(popup)


def format_seconds(total_seconds: float) -> str:
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds - hours * 3600) // 60)
    seconds = int(total_seconds % 60)
    return f'{hours}:{minutes:0>2}:{seconds:0>2}'


def main(video_id=None):
    if video_id and 'twitch.tv' in video_id:
        video_id = parse_url(video_id)

    controller = GuiController(video_id)
    controller.run()


if __name__ == '__main__':
    try:
        video_id: str = None
        if len(sys.argv) > 1:
            video_id = sys.argv[1]

        main(video_id)
    except:
        trace: str = traceback.format_exc()
        popup = ErrorMessage(trace)
        popup.mainloop()
        with open('chatplayerlog.txt', 'w') as log:
            log.write(f'EXCEPTION: {trace}')
