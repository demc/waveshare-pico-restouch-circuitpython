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

PORTRAIT = 0
LANDSCAPE = 1

# Touchscreen pins
TFT_DC = board.GP8
TFT_CS = board.GP9
TFT_RST = board.GP15
BACKLIGHT = board.GP13

# SPI bus pins.
SPI_CLK = board.GP10
SPI_MOSI = board.GP11
SPI_MISO = board.GP12

# XPT2046 pins.
TOUCH_CS = board.GP16

# SDCard pins
SD_CS = board.GP22

# Touch calibration.
TOUCH_X_MIN = 130
TOUCH_X_MAX = 1943
TOUCH_Y_MIN = 161
TOUCH_Y_MAX = 1948

# Touch handling constants.
EVENT_NONE = const(0)
EVENT_PEN_DOWN = const(1)
EVENT_PEN_UP   = const(2)
EVENT_PEN_MOVE = const(3)
DEBOUNCE_COUNT = const(3) # debounce count?
TASK_INTERVAL = 0.010 # 10ms

touchSt_Idle_0     = const(0)
touchSt_DnDeb_1    = const(1)
touchSt_Touching_2 = const(2)
touchSt_UpDeb_3    = const(3)


class WaveshareResTouch:

    def __init__(
        self,
        width=240,
        height=320,
        orientation=PORTRAIT,
    ):
        self.width = width
        self.height = height
        
        self.orientation = orientation
        rotation = 0 if orientation == PORTRAIT else 90
        
        # Shared SPI bus. Used for TFT, XPT2046, and SDCard.
        self.spi = busio.SPI(SPI_CLK, SPI_MOSI, SPI_MISO)
        
        # Configure screen.
        self.display_bus = displayio.FourWire(
            self.spi,
            command=TFT_DC,
            chip_select=TFT_CS,
            reset=TFT_RST
        )
        self.DISPLAY = ST7789(
            self.display_bus,
            width=width,
            height=height,
            rotation=rotation,
            backlight_pin=BACKLIGHT
        )
        
        # Configure xpt2046.
        self.touch = Touch(
            self.spi,
            cs=TOUCH_CS,
            width=self.width,
            height=self.height,
            rotation=rotation,
            x_min=TOUCH_X_MIN, x_max=TOUCH_X_MAX,
            y_min=TOUCH_Y_MIN, y_max=TOUCH_Y_MAX
        )
        
        # Touch state.
        self.detect_touch_task = None
        self.touch_event = EVENT_NONE
        self.touch_state = touchSt_Idle_0
        self.touched_x = None
        self.touched_y = None
        self.touch_debounce = DEBOUNCE_COUNT
        self.touching = False
        
        # Touch handlers.
        self.touch_down_handler = None
        self.touch_move_handler = None
        self.touch_up_handler = None
        
        # Loop handler.
        self.loop_handler = None


    async def _init_touch_handling(self):
        self.detect_touch_task = asyncio.create_task(
            self._detect_touch_event(
                self.touch_down_handler,
                self.touch_move_handler,
                self.touch_up_handler
            )
        )
        
        self.loop_task = asyncio.create_task(
            self._run_loop()  
        )
    
        await asyncio.gather(self.detect_touch_task, self.loop_task)
    
    
    async def _run_loop(self):
        if self.loop_handler:
            while True:
                self.loop_handler()
                await asyncio.sleep(TASK_INTERVAL)
            
                
    async def _detect_touch_event(self, touch_down, touch_move, touch_up):       
        while True:
            # Attempt to detect touch.
            self._check_for_touch_event()
            
            # Handle touch event (if it exists).
            if self.touch_event != EVENT_NONE:
                if self.touch_event == EVENT_PEN_DOWN:
                    if touch_down:
                        touch_down(self.touched_x, self.touched_y)
                
                if self.touch_event == EVENT_PEN_UP:
                    if touch_up:
                        touch_up(self.touched_x, self.touched_y)
                
                if self.touch_event == EVENT_PEN_MOVE:
                    if touch_move:
                        touch_move(self.touched_x, self.touched_y)
                    
                self.touch_event = EVENT_NONE

            await asyncio.sleep(TASK_INTERVAL)
         
    
    def _get_touch(self):
        xy = self.touch.raw_touch()

        if xy == None:
            return None

        # Interpolates with proper rotation applied.
        # XY are not yet flipped though.
        normalizedX, normalizedY = self.touch.normalize(*xy)
        
        if self.orientation == LANDSCAPE:
            return (normalizedY, self.height - normalizedX)
        
        return (normalizedX, normalizedY)
    
        
    def _check_for_touch_event(self):
        validXY = self._get_touch()
        
        if self.touch_state == touchSt_Idle_0:
            if validXY != None:
                self.touch_debounce = DEBOUNCE_COUNT
                self.touch_state = touchSt_DnDeb_1
        
        elif self.touch_state == touchSt_DnDeb_1:
            if validXY != None:
                self.touch_debounce = self.touch_debounce - 1
                if self.touch_debounce == 0:
                    self.touch_state = touchSt_Touching_2
                    self.touch_event = EVENT_PEN_DOWN
                    self.touched_x = validXY[0]
                    self.touched_y = validXY[1]
                    self.touching = True
            else:
                self.touch_state = touchSt_Idle_0
                
        elif self.touch_state == touchSt_Touching_2:
            if validXY != None:
                self.touched_x = validXY[0]
                self.touched_y = validXY[1]
                self.touch_event = EVENT_PEN_MOVE
            else:
                self.touch_debounce = DEBOUNCE_COUNT
                self.touch_state = touchSt_UpDeb_3
                
        elif self.touch_state == touchSt_UpDeb_3:
            if validXY != None:
                self.touch_state = touchSt_Touching_2
            else:
                self.touch_debounce = self.touch_debounce - 1
                if self.touch_debounce == 0:
                    self.touch_state = touchSt_Idle_0
                    self.touch_event = EVENT_PEN_UP
                    self.touching = False
        

    def on_touch_down(self, handler):
        self.touch_down_handler = handler
        
    
    def on_touch_move(self, handler):
        self.touch_move_handler = handler
    
    
    def on_touch_up(self, handler):
        self.touch_up_handler = handler
    
    def on_loop(self, handler):
        self.loop_handler = handler
    
    def start(self):
        asyncio.run(self._init_touch_handling())


