#!/usr/bin/python3.6
# -*- coding: utf-8 -*-
__author__ = 'xiwei'


import click
import time
import io
import os
import json
import requests
import numpy as np

from queue import Queue, Empty
from threading import Thread

from lxml import etree
from PIL import Image as PILImage

PAGE_SIZE = 10

XPATH = '//*[@class="iuscp varh"]/div[1]/a[1]'
URL = 'https://cn.bing.com/images/async?q={keyword}%20png&first={first}&count={page_size}'
CHARS = np.asarray(list(' .,:;ish&@'))


class Image:

    def __init__(self, buffer, title):
        self.buffer = buffer
        self.title: str = title
        self._pil = PILImage.open(io.BytesIO(buffer))

    def array(self, width, height):
        img = np.sum(np.asarray(self._pil.resize((width, height))), axis=2)
        img -= img.min()
        img = (1.0 - img / img.max()) * (CHARS.size - 1)
        _array = []
        for r in CHARS[img.astype(int)]:
            _array.append("".join(r))
        _array[-1] = self.title.center(width, ' ')
        return _array


class Crawler(Thread):
    def __init__(self, keyword, size, buffer, count):
        super().__init__(name='Crawler', daemon=True)
        self.keyword = keyword
        self.size = size
        self.count = count
        self.page = 0
        self.queue = Queue(buffer)

    def _url(self):
        yield URL.format(keyword=self.keyword, first=self.page * PAGE_SIZE, page_size=PAGE_SIZE)
        self.page += 1

    def _validate(self, murl):
        headers = requests.head(murl).headers
        if headers.get('content-type') == 'image/png' and int(headers.get('content-length')) <= self.size * 1024:
            return True

    def run(self):
        while True:
            for url in self._url():
                html = requests.get(url).text
                items = etree.HTML(html).xpath(XPATH)
                for item in items:
                    try:
                        m = json.loads(item.get('m'))
                        murl = m.get('murl')
                        if self._validate(murl):
                            self.queue.put(Image(requests.get(murl).content, title=f"left: {self.count}, url:{murl}"))
                            self.count -= 1
                    except Exception as e:
                        continue
                    if self.count <= 0:
                        return

    def __next__(self) -> Image:
        while True:
            try:
                return self.queue.get(timeout=1)
            except Empty:
                if self.count <= 0:
                    raise StopIteration
                else:
                    continue

    def __iter__(self):
        return self


class Display:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.right: list = None
        self.left: list = None
        
    def add(self, image: Image):
        self.left, self.right = image.array(self.width, self.height), self.left

    def _play_frame(self, array):
        self.clean()
        print('\n'.join(array))

    def play(self):
        if self.left:
            pos = 0
            while pos < self.width:
                if self.right:
                    frame = map(
                        lambda i: self.left[i][self.width - pos:-1] + self.right[i][0:self.width - pos],
                        range(0, self.height)
                    )
                else:
                    frame = map(
                        lambda row: row[self.width - pos:-1],
                        self.left
                    )
                self._play_frame(frame)
                time.sleep(0.1)
                pos += 1

    @staticmethod
    def clean():
        os.system('cls' if os.name == 'nt' else 'clear')


@click.command()
@click.argument('keyword')
@click.option('--width', '-w', default=100, type=click.INT, help='Image width')
@click.option('--height', '-h', default=40, type=click.INT, help='Image height')
@click.option('--count', '-c', default=87, type=click.INT, help='Image count')
@click.option('--size', '-s', default=100, type=click.INT, help='Image max size (KB)')
@click.option('--buffer', '-b', default=10, type=click.INT, help='Images buffer size')
def show(keyword, width, height, count, size, buffer):
    crawler = Crawler(keyword, size, buffer, count)
    crawler.start()
    display = Display(width, height)
    for image in crawler:
        display.add(image)
        display.play()


if __name__ == '__main__':
    show()
