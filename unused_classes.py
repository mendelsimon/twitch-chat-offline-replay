import re
from tkinter import Text, WORD, END, DISABLED, Canvas, RIGHT, Y, BOTH, LEFT, VERTICAL
from tkinter.ttk import Frame, Scrollbar
from tkinter.font import Font, BOLD

from PIL import ImageTk, Image

from chat_downloader import get_emote

EMOJI_MATCHER: re = re.compile('[\U00010000-\U0010FFFF]')


class Scrollable(Frame):
    def __init__(self, master, outer_kwargs={}):
        Frame.__init__(self, master, **outer_kwargs)
        self.master = master
        self.canvas = Canvas(self, borderwidth=0, highlightthickness=0)
        self.frame = Frame(self.canvas, borderwidth=0)
        self.scrollbar = Scrollbar(self, orient=VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=RIGHT, fill=Y, expand=False)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.canvas.create_window((0, 0), window=self.frame, tag='self.frame')
        self.frame.bind('<Configure>', lambda event: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda event: self.canvas.itemconfig('self.frame', width=event.width))
        self.canvas.bind_all('<MouseWheel>', lambda event: self.canvas.yview_scroll(-2 * event.delta // 120, 'units'))
        self.canvas.yview_moveto(0)

    def scroll_to(self, coord: float):
        self.canvas.yview_moveto(coord)

    def get_coord(self):
        return self.canvas.yview()


class ChatMessage(Text):
    def __init__(self, master, username: str, fragments: dict, color: str, font: Font, autoscroll: bool = True):
        Text.__init__(self, master, height=1, font=font, wrap=WORD)
        self.username: str = username
        self.fragments: dict = fragments
        self.font: Font = font
        self.font_bold: Font = font.copy()
        self.font_bold.configure(weight=BOLD)
        self.color = color
        self.autoscroll = autoscroll
        self.images: list = []

    def pack(self, **kwargs):
        Text.pack(self, **kwargs)
        self.update_idletasks()
        self.tag_configure('username', foreground=self.color, font=self.font_bold)
        self.insert(END, self.username, 'username')
        self.insert(END, ' : ')
        self.insert_fragments()
        self.configure(state=DISABLED)

        if self.autoscroll:
            self.master.master.master.scroll_to(1.0)
            self.master.master.master.event_generate('<MouseWheel>', delta=-120 * 6)
        else:
            coord = self.gui.chat_frame_container.get_coord()
            print(coord)
            # self.gui.chat_frame_container.scroll_to(coord)

    def insert_fragments(self):
        width: int = self.font_bold.measure(self.username + ' : ')
        line_height = self.font.metrics('linespace')
        box_width: int = self.winfo_width()  # - self.font.measure('00000')
        rows: int = 0
        row_height: int = 1
        for fragment in self.fragments:
            if 'emoticon' in fragment:
                emote_id = fragment.get('emoticon').get('emoticon_id')
                image_path = get_emote(emote_id)
                image = ImageTk.PhotoImage(Image.open(image_path))
                image_width = image.width() + 4
                if width + image_width >= box_width:
                    rows += row_height
                    row_height = 1
                    width = image_width
                else:
                    width += image_width
                image_height_in_rows = int(((image.height() + 2) / line_height) + 1)
                if image_height_in_rows > row_height:
                    row_height = image_height_in_rows
                self.image_create(END, image=image, padx=2, pady=2)
                self.images.append(image)
            else:
                text: str = EMOJI_MATCHER.sub(replace_emoji, fragment.get('text'))
                space_width = self.font.measure(' ')
                words = text.split(' ')
                for word in words:
                    word_width = self.font.measure(word)
                    if width + word_width >= box_width:
                        rows += row_height
                        row_height = 1
                        width = word_width
                    else:
                        width += word_width
                    if width + space_width >= box_width:
                        rows += row_height
                        row_height = 1
                        width = space_width
                    else:
                        width += space_width
                self.insert(END, text)
        rows += row_height
        self.configure(height=rows)


def replace_emoji(match):
    char = match.group()
    assert ord(char) > 0xffff
    encoded = char.encode('utf-16-le')
    return (
            chr(int.from_bytes(encoded[:2], 'little')) +
            chr(int.from_bytes(encoded[2:], 'little')))
