from pprint import pprint
import re
from threading import Thread

import requests
from time import sleep, time
import os
import json

CURRENT_SCRIPT_DIR: str = os.path.dirname(os.path.realpath(__file__))
CACHE_FOLDER: str = os.path.join(CURRENT_SCRIPT_DIR, 'downloaded_chats')
EMOTES_FOLDER: str = os.path.join(CACHE_FOLDER, 'emote_cache')

with open(os.path.join(CURRENT_SCRIPT_DIR, 'api_key.txt'), 'r') as key_file:
    HEADERS: dict = {'Client-ID': key_file.read()}
    
BASE_CHAT_URL: str = 'https://api.twitch.tv/v5/videos/{video_id}/comments?cursor={cursor}'
BASE_EMOTE_URL: str = 'https://static-cdn.jtvnw.net/emoticons/v1/{emote_id}/{emote_size}.0'
EMOTE_SIZE = 1
SLEEP_TIME: float = 1

UNICODE_MATCHER: re = re.compile('[\U00010000-\U0010FFFF]')
EMOJI_RANGES = [(0x2139, 0x3299), (0x1F004, 0x1F9E6)]
EMOJI_MATCHER: re = re.compile('[\U00002139-\U00003299\U0001F004-\U0001F9E6]')

color_cache = {}
default_colors = (
    '#FF0000',  # Red
    '#0000FF',  # Blue
    '#00FF00',  # Green
    '#B22222',  # FireBrick
    '#FF7F50',  # Coral
    '#9ACD32',  # YellowGreen
    '#FF4500',  # OrangeRed
    '#2E8B57',  # SeaGreen
    '#DAA520',  # GoldenRod
    '#D2691E',  # Chocolate
    '#5F9EA0',  # CadetBlue
    '#1E90FF',  # DodgerBlue
    '#FF69B4',  # HotPink
    '#8A2BE2',  # BlueViolet
    '#00FF7F'  # SpringGreen
)

bttv_emotes = (
    'OhMyGoodness',
    'PancakeMix',
    'PedoBear',
    'PokerFace',
    'RageFace',
    'RebeccaBlack',
    ':tf:',
    'aPliS',
    'CiGrip',
    'CHAccepted',
    'FuckYea',
    'DatSauce',
    'ForeverAlone',
    'GabeN',
    'HailHelix',
    'HerbPerve',
    'iDog',
    'rStrike',
    'ShoopDaWhoop',
    'SwedSwag',
    'M&Mjc',
    'bttvNice',
    'TopHam',
    'TwaT',
    'WhatAYolk',
    'WatChuSay',
    'Blackappa',
    'DogeWitIt',
    'BadAss',
    'SavageJerky',
    'Kaged',
    'HHydro',
    'TaxiBro',
    'BroBalt',
    'ButterSauce',
    'BaconEffect',
    'SuchFraud',
    'CandianRage',
    'She\'llBeRight',
    'OhhhKee',
    'D:',
    'SexPanda',
    '(poolparty)',
    ':\'(',
    '(puke)',
    'bttvWink',
    'bttvAngry',
    'bttvConfused',
    'bttvCool',
    'bttvHappy',
    'bttvSad',
    'bttvSleep',
    'bttvSurprised',
    'bttvTongue',
    'bttvUnsure',
    'bttvGrin',
    'bttvHeart',
    'bttvTwink',
    'VisLaud',
    '(chompy)',
    'SoSerious',
    'BatKappa',
    'KaRappa',
    'YetiZ',
    'miniJulia',
    'motnahP',
    'sosGame',
    'CruW',
    'RarePepe',
    'iamsocal',
    'haHAA',
    'FeelsBirthdayMan',
    'RonSmug',
    'KappaCool',
    'Zappa',
    'BasedGod',
    'bUrself',
    'ConcernDoge',
    'FapFapFap',
    'FeelsBadMan',
    'FeelsGoodMan',
    'FireSpeed',
    'FishMoley',
    'Hhhehehe',
    'KKona',
    'NaM',
    'OhGod',
    'PoleDoge',
    'tehPoleCat',
    'AngelThump',
    'SourPls',
    'LuL',
    'SaltyCorn',
    'FCreep',
    'VapeNation',
    'ariW',
    'notsquishY',
    'FeelsAmazingMan',
    'DuckerZ',
    'SqShy',
    'Wowee'
)


class ChatDownloader(Thread):
    def __init__(self, video_id: str, verbose=False, overwrite_cache=False):
        super().__init__()
        self.info: dict = {}
        self.title: str = ''
        self.duration: int = 0
        self.duration_str: str = ''
        self.duration_done_str: str = ''
        self.progress: float = 0.0
        self.num_messages: int = 0
        self.messages: list = []
        self.eta_str: str = ''
        self.killed = False

        if video_id and video_id.startswith('v'):
            video_id = video_id[1:]
        self.video_id = video_id
        self.verbose = verbose
        self.overwrite_cache = overwrite_cache

    def run(self):
        self.messages = self.download(self.video_id, self.verbose, self.overwrite_cache)

    def download(self, video_id: str, verbose: bool = False, overwrite_cache: bool = False) -> list:
        self.get_info(video_id, overwrite_cache)
        self.duration = parse_duration(self.info.get('duration'))
        self.title = self.info.get('title')
        self.duration_str = format_seconds(self.duration)
        return self.get_chat(video_id, verbose, overwrite_cache)

    def get_info(self, video_id: str, overwrite_cache: bool = False) -> dict:
        if video_id.startswith('v'):
            video_id = video_id[1:]
        info_filename: str = os.path.join(CACHE_FOLDER, f'info-{video_id}.json')
        if not overwrite_cache and os.path.exists(info_filename):
            with open(info_filename, 'r') as info_cache:
                self.info = json.load(info_cache)
                return self.info

        url: str = f'https://api.twitch.tv/helix/videos?id={video_id}'
        response: dict = requests.get(url, headers=HEADERS).json().get('data')[0]
        response.update({'length': parse_duration(response.get('duration'))})
        self.info = response

        # cache downloaded info
        with open(info_filename, 'w') as info_cache:
            print(f'Caching chat to {info_filename}.')
            json.dump(self.info, info_cache)
        return response

    def get_chat(self, video_id: str = None, verbose=False, overwrite_cache=False) -> list:
        if not video_id:
            video_id = self.video_id
        if video_id.startswith('v'):
            video_id = video_id[1:]
        chat_filename: str = os.path.join(CACHE_FOLDER, f'chat-{video_id}.json')
        if not overwrite_cache and os.path.exists(chat_filename):
            print('Reading cached copy of chat.')
            with open(chat_filename, 'r') as chat_cache:
                return json.load(chat_cache)

        if verbose:
            print('Downloading chat.')

        if not self.info:
            self.info = self.get_info(video_id)
        self.duration = parse_duration(self.info.get('duration'))
        self.title = self.info.get('title')
        self.duration_str = format_seconds(self.duration)
        if verbose:
            print(self.info.get('title') + ': ' + self.info.get('duration'))

        start_time: float = time()
        messages: list = []
        url: str = f'https://api.twitch.tv/v5/videos/{video_id}/comments?content_offset_seconds=0'
        response: dict = requests.get(url, headers=HEADERS).json()
        process_messages(response.get('comments'), messages)
        cursor: str = response.get('_next')
        url = BASE_CHAT_URL.format(video_id=video_id, cursor=cursor)
        while '_next' in response and not self.killed:
            response = requests.get(url, headers=HEADERS).json()
            process_messages(response.get('comments'), messages)

            elapsed_time = time() - start_time
            duration_done = messages[-1].get('offset')
            if duration_done > self.duration:
                self.duration = duration_done
            self.progress = duration_done / self.duration
            eta = (elapsed_time / self.progress) - elapsed_time
            self.eta_str = format_seconds(eta)
            self.num_messages = len(messages)
            self.duration_done_str = format_seconds(duration_done)
            if verbose:
                log: str = f'{self.num_messages} messages. '
                log += f'{self.duration_done_str}/{self.duration_str}. '
                log += f'Time Left: {self.eta_str}.'
                print('\r' + log, end='', flush=True)
            cursor = response.get('_next')
            url = BASE_CHAT_URL.format(video_id=video_id, cursor=cursor)
            # sleep(SLEEP_TIME)

        if self.killed:
            if verbose:
                print('killed')
            return []

        if verbose and not self.killed:
            print('\nDone downloading.')

        # cache downloaded chat
        if not self.killed:
            with open(chat_filename, 'w') as chat_cache:
                print(f'Caching chat to {chat_filename}.')
                json.dump(messages, chat_cache)
        return messages

    def kill(self):
        self.killed = True


def process_messages(raw_messages: list, messages: list):
    for raw_message in raw_messages:
        message = {
            'name': raw_message.get('commenter').get('display_name'),
            'id': raw_message.get('_id'),
            'color': raw_message.get('message').get('user_color'),
            'offset': raw_message.get('content_offset_seconds')
        }
        if not message.get('color'):
            name = message.get('name')
            if name not in color_cache:
                color = default_colors[(ord(name[0]) + ord(name[-1])) % len(default_colors)]
                color_cache.update({name: color})
            message.update({'color': color_cache.get(name)})

        # Insert BTTV emotes
        fragments: list = raw_message.get('message').get('fragments')
        message.update({'fragments': process_fragments(fragments)})
        messages.append(message)


def process_fragments(fragments: list):
    fragments = process_bttv_emotes(fragments)
    fragments = process_emoji(fragments)
    fragments = process_unicode(fragments)
    fragments = process_usernames(fragments)
    return fragments


def process_bttv_emotes(old_fragments: list) -> list:
    fragments: list = []
    for fragment in old_fragments:
        if 'emoticon' not in fragment:
            text: str = fragment.get('text')
            while len(text) > 0 and any(emote in text for emote in bttv_emotes):
                emote_found: str = None
                found_index: int = len(text)  # Earliest
                for emote in bttv_emotes:
                    index = text.find(emote)
                    if -1 < index < found_index:
                        emote_found = emote
                        found_index = index
                if found_index > 0:
                    fragments.append({
                        'text': text[:found_index]
                    })
                fragments.append({
                    'text': emote_found,
                    'emoticon': {
                        'emoticon_id': emote_found
                    }
                })
                text = text[found_index + len(emote_found):]
            if len(text) > 0:
                fragments.append({
                    'text': text
                })
        else:
            fragments.append(fragment)
    return fragments


def process_emoji(old_fragments: list) -> list:
    EMOTE_PREFIX: str = ('apple', 'windows')[1]
    fragments = []
    for fragment in old_fragments:
        if 'emoticon' not in fragment:
            text = fragment.get('text')
            changed: bool = True
            while EMOJI_MATCHER.search(text) and changed:
                changed = False
                for char in text:
                    if any(low <= ord(char) <= high for low, high in EMOJI_RANGES):
                        emote_name = f'{EMOTE_PREFIX}-{char}'
                        emote_filename = f'{emote_name}-{EMOTE_SIZE}.png'
                        if os.path.exists(os.path.join(EMOTES_FOLDER, emote_filename)):
                            changed = True
                            index = text.find(char)
                            if index > 0:
                                fragments.append({
                                    'text': text[:index]
                                })
                            fragments.append({
                                'text': char,
                                'emoticon': {
                                    'emoticon_id': emote_name
                                }
                            })
                            text = text[index + 1:]
            if len(text) > 0:
                fragments.append({
                    'text': text
                })
        else:
            fragments.append(fragment)
    return fragments


def process_unicode(old_fragments: list) -> list:
    fragments = []
    for fragment in old_fragments:
        if 'emoticon' not in fragments:
            new_fragment = fragment.copy()
            new_fragment.update({
                'text': UNICODE_MATCHER.sub(replace_unicode, fragment.get('text'))
            })
            fragments.append(new_fragment)
        else:
            fragments.append(fragment)
    return fragments


def replace_unicode(match):
    char = match.group()
    encoded = char.encode('utf-16-le')
    return (
            chr(int.from_bytes(encoded[:2], 'little')) +
            chr(int.from_bytes(encoded[2:], 'little')))


def process_usernames(old_fragments: list) -> list:
    fragments: list = []
    for fragment in old_fragments:
        if 'emoticon' not in fragment and '@' in fragment.get('text'):
            tokens: list = re.findall(r'\S+|\s+', fragment.get('text'))
            prev_index: int = 0
            for index, token in enumerate(tokens):
                if token.startswith('@') and len(token) > 1:
                    text = ''.join(tokens[prev_index:index])
                    if text:
                        fragments.append({'text': text})
                    fragments.append({'text': token, 'tag': token[1:]})
                    prev_index = index + 1
            text = ''.join(tokens[prev_index:])
            if text:
                fragments.append({'text': text})
        else:
            fragments.append(fragment)
    return fragments


def get_emote(emote_id: str, read_cache=True) -> str:
    emote_id = emote_id.replace(':', 'colon')
    emote_filename: str = os.path.join(EMOTES_FOLDER, f'{emote_id}-{EMOTE_SIZE}.png')
    if emote_id in ('SourPls', '(chompy)'):
        emote_filename = emote_filename.replace('.png', '.gif')
    if read_cache and os.path.exists(emote_filename):
        return emote_filename
    url: str = BASE_EMOTE_URL.format(emote_id=emote_id, emote_size=EMOTE_SIZE)
    image = requests.get(url, headers=HEADERS).content
    with open(emote_filename, 'wb') as emote_file:
        emote_file.write(image)
    return emote_filename


def format_seconds(total_seconds: float) -> str:
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds - hours * 3600) // 60)
    seconds = int(total_seconds % 60)
    return f'{hours}:{minutes:0>2}:{seconds:0>2}'


def parse_duration(duration: str) -> int:
    duration_seconds: int = 0
    if 'h' in duration:
        h_index = duration.find('h')
        hours = int(duration[:h_index])
        duration_seconds += hours * 3600
        duration = duration[h_index + 1:]
    if 'm' in duration:
        m_index = duration.find('m')
        minutes = int(duration[:m_index])
        duration_seconds += minutes * 60
        duration = duration[m_index + 1:]
    if 's' in duration:
        s_index = duration.find('s')
        seconds = int(duration[:s_index])
        duration_seconds += seconds
    return duration_seconds


def parse_url(url: str) -> str:
    if 'player.twitch.tv' in url:
        match = re.search('video=v?([0-9]{5,})', url)[1]
    else:
        match = re.search('v?([0-9]{5,})', url)[1]
    return match


def video_exists(video_id):
    url = f'https://api.twitch.tv/v5/videos/{video_id}'
    status_code = requests.head(url, headers=HEADERS).status_code
    return status_code == 200


def main():
    video_id = input('Enter a URL or video ID > ')
    if 'http' in video_id or 'twitch.tv' in video_id:
        video_id = parse_url(video_id)
    while not video_exists(video_id):
        print('Invalid URL or video ID.')
        video_id = input('Enter a video ID or url > ')
        if 'http' in video_id or 'twitch.tv' in video_id:
            video_id = parse_url(video_id)

    ChatDownloader(video_id, verbose=True, overwrite_cache=True).get_chat()


if __name__ == '__main__':
    main()
