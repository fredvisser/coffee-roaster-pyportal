import time
import board
import microcontroller
import displayio
import busio
from adafruit_bus_device.i2c_device import I2CDevice
from analogio import AnalogIn
# import neopixel
import adafruit_adt7410
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_button import Button
import adafruit_touchscreen
from adafruit_pyportal import PyPortal

# -- Variables --- #
setpoint_temp = 25
current_temp = 0
io_board_state = -1

# Temp conversation
def CtoF(tempC):
    return tempC * 1.8 + 32

def FtoC(tempF):
    return (tempF -32) / 1.8

# ------------- Inputs and Outputs Setup ------------- #
try:  # attempt to init. the temperature sensor
    i2c_bus = busio.I2C(board.SCL, board.SDA)
    device = I2CDevice(i2c_bus, 0x08)
    with device:
        device.write(bytes([0x05]))
        result = bytearray(1)
        device.readinto(result)
        setpoint_temp = CtoF(result[0])
        print(result)
    # adt = adafruit_adt7410.ADT7410(i2c_bus, address=0x48)
    # adt.high_resolution = True
except ValueError:
    # Did not find ADT7410. Probably running on Titano or Pynt
    print('failed to connect to roaster daughter card')
    # adt = None

# init. the light sensor
light_sensor = AnalogIn(board.LIGHT)

# pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=1)
WHITE = 0xffffff
RED = 0xff0000
YELLOW = 0xffff00
GREEN = 0x009051
BLUE = 0x0000ff
PURPLE = 0xff00ff
BLACK = 0x000000
DARK_GREY = 0x424242

# ---------- Sound Effects ------------- #
soundDemo = '/sounds/sound.wav'
soundBeep = '/sounds/beep.wav'
soundTab = '/sounds/tab.wav'

# ------------- Other Helper Functions------------- #
# Helper for cycling through a number set of 1 to x.
def numberUP(num, max_val):
    num += 1
    if num <= max_val:
        return num
    else:
        return 1

# ------------- Screen Setup ------------- #
pyportal = PyPortal()
display = board.DISPLAY
display.rotation = 180

# Backlight function
# Value between 0 and 1 where 0 is OFF, 0.5 is 50% and 1 is 100% brightness.
def set_backlight(val):
    val = max(0, min(1.0, val))
    board.DISPLAY.auto_brightness = False
    board.DISPLAY.brightness = val

# Set the Backlight
set_backlight(0.3)

# Touchscreen setup

# ------Rotate 180:
screen_width = 320
screen_height = 240
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XR, board.TOUCH_XL,
                                      board.TOUCH_YU, board.TOUCH_YD,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(screen_width, screen_height))

# ------------- Display Groups ------------- #
splash = displayio.Group()  # The Main Display Group
mainView = displayio.Group()  # Group for Main View objects
configView = displayio.Group()  # Group for Config View objects
roastView = displayio.Group()  # Group for Roasting View objects
coolView = displayio.Group()  # Group for Cooling View objects

def hideLayer(hide_target):
    try:
        splash.remove(hide_target)
    except ValueError:
        pass

def showLayer(show_target):
    try:
        time.sleep(0.1)
        splash.append(show_target)
    except ValueError:
        pass

# ------------- Setup for Images ------------- #

# Display an image until the loop starts
pyportal.set_background('/images/loading.bmp')


bg_group = displayio.Group()
splash.append(bg_group)


# icon_group = displayio.Group()
# icon_group.x = 180
# icon_group.y = 120
# icon_group.scale = 1
# configView.append(icon_group)

# This will handel switching Images and Icons
def set_image(group, filename):
    """Set the image file for a given goup for display.
    This is most useful for Icons or image slideshows.
        :param group: The chosen group
        :param filename: The filename of the chosen image
    """
    print("Set image to ", filename)
    if group:
        group.pop()

    if not filename:
        return  # we're done, no icon desired

    # CircuitPython 6 & 7 compatible
    image_file = open(filename, "rb")
    image = displayio.OnDiskBitmap(image_file)
    image_sprite = displayio.TileGrid(image, pixel_shader=getattr(image, 'pixel_shader', displayio.ColorConverter()))

    # # CircuitPython 7+ compatible
    # image = displayio.OnDiskBitmap(filename)
    # image_sprite = displayio.TileGrid(image, pixel_shader=image.pixel_shader)

    group.append(image_sprite)

set_image(bg_group, "/images/background.bmp")

# ---------- Text Boxes ------------- #
# Set the font and preload letters
font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")
font.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()')

font_24 = bitmap_font.load_font("/fonts/Helvetica-24.bdf")
font_24.load_glyphs(b'F1234567890')

font_42 = bitmap_font.load_font("/fonts/Helvetica-42.bdf")
font_42.load_glyphs(b'F1234567890')

font_96_bold = bitmap_font.load_font("/fonts/Helvetica-Bold-96.bdf")
font_96_bold.load_glyphs(b'F1234567890')

# Text labels

config_temp_label = Label(font_42, text='{:.0f}°F'.format(setpoint_temp), color=WHITE)
config_temp_label.x = 100
config_temp_label.y = 90
configView.append(config_temp_label)

roast_temp_label = Label(font_96_bold, text="Current roasting temp", color=RED)
roast_temp_label.x = 50
roast_temp_label.y = 75
roastView.append(roast_temp_label)

cooling_temp_label = Label(font_96_bold, text="Current cooling temp", color=BLUE)
cooling_temp_label.x = 50
cooling_temp_label.y = 75
coolView.append(cooling_temp_label)

# ---------- Display Buttons ------------- #

# We want two big buttons at the bottom of the screen
BIG_BUTTON_HEIGHT = 75
BIG_BUTTON_WIDTH = 160
BIG_BUTTON_Y = int(screen_height-BIG_BUTTON_HEIGHT)

# This group will make it easy for us to read a button press later.
buttons = []

# Main User Interface Buttons
config_temp_button = Button(x=20, y=30,
                      width=280, height=100,
                      label='{:.0f}°F'.format(setpoint_temp), label_font=font_96_bold, label_color=WHITE,
                      fill_color=DARK_GREY, outline_color=DARK_GREY,
                      selected_fill=DARK_GREY, selected_outline=DARK_GREY,
                      selected_label=WHITE)
buttons.append(config_temp_button)  # adding this button to the buttons group

start_roast_button = Button(x=BIG_BUTTON_WIDTH, y=BIG_BUTTON_Y,
                  width=BIG_BUTTON_WIDTH, height=BIG_BUTTON_HEIGHT,
                  label="Start Roast", label_font=font_24, label_color=WHITE,
                  fill_color=GREEN, outline_color=GREEN,
                  selected_fill=GREEN, selected_outline=GREEN,
                  selected_label=WHITE)
buttons.append(start_roast_button)  # adding this button to the buttons group

mainView.append(config_temp_button)
mainView.append(start_roast_button)

# Make a button to change the icon image on view2
decrement_temp_button = Button(x=20, y=60,
                     width=60, height=60,
                     label="-", label_font=font_42, label_color=WHITE,
                     fill_color=DARK_GREY, outline_color=DARK_GREY,
                     selected_fill=DARK_GREY, selected_outline=DARK_GREY,
                     selected_label=WHITE)
buttons.append(decrement_temp_button)  # adding this button to the buttons group

increment_temp_button = Button(x=240, y=60,
                     width=60, height=60,
                     label="+", label_font=font_42, label_color=WHITE,
                     fill_color=DARK_GREY, outline_color=DARK_GREY,
                     selected_fill=DARK_GREY, selected_outline=DARK_GREY,
                     selected_label=WHITE)
buttons.append(increment_temp_button)  # adding this button to the buttons group

set_temp_button = Button(x=BIG_BUTTON_WIDTH, y=BIG_BUTTON_Y,
                  width=BIG_BUTTON_WIDTH, height=BIG_BUTTON_HEIGHT,
                  label="Set Temp", label_font=font_24, label_color=WHITE,
                  fill_color=GREEN, outline_color=GREEN,
                  selected_fill=GREEN, selected_outline=GREEN,
                  selected_label=WHITE)
buttons.append(set_temp_button)  # adding this button to the buttons group

cancel_config_button = Button(x=0, y=BIG_BUTTON_Y,
                  width=BIG_BUTTON_WIDTH, height=BIG_BUTTON_HEIGHT,
                  label="Cancel", label_font=font_24, label_color=WHITE,
                  fill_color=DARK_GREY, outline_color=DARK_GREY,
                  selected_fill=DARK_GREY, selected_outline=DARK_GREY,
                  selected_label=WHITE)
buttons.append(cancel_config_button)  # adding this button to the buttons group

# Add config buttons to configView group
configView.append(decrement_temp_button)
configView.append(increment_temp_button)
configView.append(set_temp_button)
configView.append(cancel_config_button)

# Buttons for roastView
stop_roast_button = Button(x=0, y=165,
                      width=170, height=75,
                      label="Stop Roast", label_font=font_24, label_color=WHITE,
                      fill_color=RED, outline_color=RED,
                      selected_fill=RED, selected_outline=RED,
                      selected_label=WHITE)
buttons.append(stop_roast_button)  # adding this button to the buttons group

# Add this button to roastView Group
roastView.append(stop_roast_button)

# Buttons for coolView
stop_cooling_button = Button(x=0, y=165,
                      width=170, height=75,
                      label="Stop Cooling", label_font=font_24, label_color=WHITE,
                      fill_color=BLUE, outline_color=BLUE,
                      selected_fill=BLUE, selected_outline=BLUE,
                      selected_label=WHITE)
buttons.append(stop_cooling_button)  # adding this button to the buttons group

# Add this button to coolView Group
coolView.append(stop_cooling_button)

#pylint: disable=global-statement
def switch_view(what_view):
    global view_live
    if what_view == 1:
        showLayer(mainView)
        hideLayer(configView)
        hideLayer(roastView)
        hideLayer(coolView)
        view_live = 1
        print("mainView On")
    elif what_view == 2:
        # global icon
        hideLayer(mainView)
        showLayer(configView)
        hideLayer(roastView)
        hideLayer(coolView)
        view_live = 2
        print("configView On")
    elif what_view == 3:
        hideLayer(mainView)
        hideLayer(configView)
        showLayer(roastView)
        hideLayer(coolView)
        view_live = 3
        print("roastView On")
    else:
        hideLayer(mainView)
        hideLayer(configView)
        hideLayer(roastView)
        showLayer(coolView)
        view_live = 4
        print("coolView On")
#pylint: enable=global-statement

# Set veriables and startup states
showLayer(mainView)
hideLayer(configView)
hideLayer(roastView)
hideLayer(coolView)

view_live = 1

board.DISPLAY.show(splash)

device = I2CDevice(i2c_bus, 0x08)

def startRoast(dev, temp):
    try:
        with dev:
            print('startRoast with ', temp)
            print('startRoast @ ', int(FtoC(temp)))
            message = [0x02] # roast command
            message.append(int(FtoC(temp))) # roast temp
            dev.write(bytes(message))
            result = bytearray(1)
            dev.readinto(result)
            if result[0] != 0x33:
                print('Start roast command failed')
    except ValueError:
        print('Start roast failed')

def stopRoast(dev):
    try:
        with dev:
            dev.write(bytes([0x03]))
            result = bytearray(1)
            dev.readinto(result)
            if result[0] != 0x34:
                print('Stop roast command failed')
    except ValueError:
        print('Stop Roast failed')

def stopCooling(dev):
    try:
        with dev:
            dev.write(bytes([0x04]))
            result = bytearray(1)
            dev.readinto(result)
            if result[0] != 0x35:
                print('Stop cooling command failed')
    except ValueError:
        print('Stop cooling failed')

# ------------- Code Loop ------------- #
i = 0
while True:
    touch = ts.touch_point
    light = light_sensor.value

    # ------------- Handle Button Press Detection  ------------- #
    if touch:  # Only do this if the screen is touched
        # loop with buttons using enumerate() to number each button group as i
        for i, b in enumerate(buttons):
            if b.contains(touch):  # Test each button to see if it was pressed
                print('button%d pressed' % i)
                if i == 0 and view_live == 1:  # Enter configView from mainView
                    pyportal.play_file(soundTab)
                    config_setpoint = setpoint_temp
                    switch_view(2)
                    while ts.touch_point:
                        pass
                if i == 1 and view_live == 1:  # Start roast from mainView
                    pyportal.play_file(soundTab)
                    startRoast(device, setpoint_temp)
                    # switch_view(3)
                    # Add logic
                    while ts.touch_point:
                        pass
                if i == 2 and view_live == 2:  # Decrement if configView
                    pyportal.play_file(soundTab)
                    print('Decrement button')
                    config_setpoint = config_setpoint - 1
                    config_temp_label.text='{:.0f}°F'.format(config_setpoint)
                    while ts.touch_point:
                        pass
                if i == 3 and view_live == 2:  # Increment if configView
                    pyportal.play_file(soundTab)
                    print('Increment button')
                    config_setpoint = config_setpoint + 1
                    config_temp_label.text='{:.0f}°F'.format(config_setpoint)
                    while ts.touch_point:
                        pass
                if i == 4 and view_live == 2:  # Set Temp button if configView
                    pyportal.play_file(soundTab)
                    print('Set temp button')
                    switch_view(1)
                    setpoint_temp = config_setpoint
                    config_temp_button.label = '{:.0f}°F'.format(setpoint_temp)
                    while ts.touch_point:
                        pass
                if i == 5 and view_live == 2:  # Cancel config button if configView
                    pyportal.play_file(soundTab)
                    print('Cancel config button')
                    switch_view(1)
                    # Add logic
                    while ts.touch_point:
                        pass
                if i == 6 and view_live == 3:  # Stop roast
                    pyportal.play_file(soundTab)
                    print('Stop roast button')
                    stopRoast(device)
                    # switch_view(1)
                    while ts.touch_point:
                        pass
                if i == 7 and view_live == 4:  # Stop cooling
                    pyportal.play_file(soundTab)
                    print('Stop cooling button')
                    stopCooling(device)
                    # switch_view(1)
                    while ts.touch_point:
                        pass

    if i % 10 == 1:      # if the number is odd
        i = i + 1
        continue
    i = 0
    try:
        with device:
            device.write(bytes([0x01]))
            result = bytearray(2)
            device.readinto(result)
            current_temp = CtoF(result[0])
            io_board_state = result[1]

        roast_temp_label.text = '{:.0f}°F'.format(current_temp)
        cooling_temp_label.text = '{:.0f}°F'.format(current_temp)

        if io_board_state == 2 and view_live == 1:
            switch_view(3) # roastView
        elif io_board_state == 3 and view_live == 3:
            switch_view(4) # coolView
        elif io_board_state == 0 and (view_live == 3 or view_live == 4):
            switch_view(1) # mainView
    except ValueError:
        roast_temp_label.text = 'XX°F'
        cooling_temp_label.text = 'XX°F'
        print("ValueError")
        print(ValueError)
        pass
    except:
        print("unhandled exception")
        pass
