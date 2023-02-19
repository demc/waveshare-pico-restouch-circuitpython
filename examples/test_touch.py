"""
Example of CircuitPython/Raspberry Pi Pico
to display on 320x240 ST7789 SPI display
with touch detection
"""
import board
import time
import terminalio
import displayio
import busio
import asyncio
from adafruit_display_text import label
from adafruit_st7789 import ST7789
from xpt2046 import Touch
from digitalio import DigitalInOut, Direction
from waveshare_res_touch import WaveshareResTouch, PORTRAIT, LANDSCAPE

# Release any resources currently in use for the displays
displayio.release_displays()

# Use this for landscape
# TFT_WIDTH = 320
# TFT_HEIGHT = 240
# ORIENTATION = LANDSCAPE

# Use this for portrait
TFT_WIDTH = 240
TFT_HEIGHT = 320
ORIENTATION = PORTRAIT


tft_dc = board.GP8
tft_cs = board.GP9
spi_clk = board.GP10
spi_mosi = board.GP11
spi_miso = board.GP12
tft_rst = board.GP15
backlight = board.GP13

waveshare = WaveshareResTouch(width=TFT_WIDTH, height=TFT_HEIGHT, orientation=ORIENTATION)

display = waveshare.DISPLAY
spi = waveshare.spi

root = displayio.Group()
display.show(root)

root.append(label.Label(
    terminalio.FONT, text='Loading...', color=0xffffff,
    anchor_point=(0.5, 0.5), anchored_position=(TFT_WIDTH / 2, TFT_HEIGHT / 2)
))


bitmap = displayio.Bitmap(display.width, display.height, 5)

BLACK = 0
WHITE = 1
RED   = 2
GREEN = 3
BLUE  = 4
palette = displayio.Palette(5)
palette[0] = 0x000000
palette[1] = 0xFFFFFF
palette[2] = 0xFF0000
palette[3] = 0x00FF00
palette[4] = 0x0000FF

for y in range(display.height):
    for x in range(display.width):
        bitmap[x,y] = BLACK
        
tileGrid = displayio.TileGrid(bitmap, pixel_shader=palette, x=0, y=0)
root.append(tileGrid)

     
def draw_cross(x, y, color):
    if y >= 0 and y < display.height:
        for i in range(x-5, x+5):
            if i >= 0 and i < display.width: 
                bitmap[i, y] = color
    
    if x >= 0 and y < display.height:
        for i in range(y-5, y+5):
            if i>=0 and i < display.height:
                bitmap[x, i] = color
                

def handle_touch_down(x, y):
    global bitmap
    draw_cross(x, y, WHITE)


def handle_touch_move(x, y):
    global bitmap
    bitmap[x, y] = GREEN


def handle_touch_up(x, y):
    global bitmap
    draw_cross(x, y, RED)


waveshare.on_touch_down(handle_touch_down)
waveshare.on_touch_move(handle_touch_move)
waveshare.on_touch_up(handle_touch_up)

# Use this callback function to do use the traditional event loop
# def loop():
#     print("Hello")
# 
# waveshare.on_loop(loop)

waveshare.start()

