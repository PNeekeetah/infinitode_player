"""
- we need something to capture our screen at a rate of 1/s ( some sort of video feed of what is on screen)

- we need to be able to recognize placement tiles
- we need to be able to recognize roads
- (optional) we might want to be able to recognize resources
- we might want to recognize portals
- we might need to recognize bases
- we want to create a map in python
- we want to create a bonding box for the map (largest width and height)
- we need to recognize how many coins we have 
- we need to recognize the cost of towers to upgrade them 
- we need to recognize how many lives we have left

- we need pyautogui to click on towers to select them
- we need to place towers
- we need some logic acording to which we place said towers
"""

import cv2 as opencv
import pyautogui
from PIL import ImageGrab
import logging
import numpy as np
import time
from mss import mss
import win32gui

INITIAL_RESOLUTION_WIDTH = 1920 - 0
INITIAL_RESOLUTION_HEIGHT = 1057 - 23

logging.getLogger().setLevel(logging.DEBUG)
logging.debug('This is a debug message')
logging.info('This is an info message')
logging.warning('This is a warning message')
logging.error('This is an error message')
logging.critical('This is a critical message')

def get_game_window_coordinates(window_name):
    """
    This function finds the coordinates of the
    top left corner and the bottom right corner.
    """
    top_left_x = 0 
    top_left_y = 0
    bottom_right_x = 0
    bottom_right_y = 0
    handler_to_window = win32gui.FindWindow(None, window_name)
    if handler_to_window:
        try:
            win32gui.SetForegroundWindow(handler_to_window)
        except:
            logging.warning("Setting window to foreground failed")
        (
            top_left_x, 
            top_left_y, 
            bottom_right_x, 
            bottom_right_y,
        ) = win32gui.GetClientRect(handler_to_window)
        (
            top_left_x, 
            top_left_y,
        ) = win32gui.ClientToScreen(
            handler_to_window, 
            (
                top_left_x, 
                top_left_y,
            )
        )
        (
            bottom_right_x, 
            bottom_right_y,
        ) = win32gui.ClientToScreen(
            handler_to_window, 
            (
                bottom_right_x - top_left_x, 
                bottom_right_y - top_left_y
            )
        )
        logging.info("Coordinates of top and bottom corners")
        logging.info("Top left     : {x}, {y}".format(
                x=top_left_x,
                y=top_left_y,
            )
        )
        logging.info("Bottom right : {x}, {y}".format(
                x=bottom_right_x,
                y=bottom_right_y
            )
        )
    else:
        logging.warning("Handler to window was not found")
    return (
        (top_left_x, top_left_y), 
        (bottom_right_x, bottom_right_y),
    )

def get_game_window_image(window_name):
    """
    This function grabs a picture of the specified 
    window. If the window is not found, an empty
    picture is returned instead.
    """
    (
        (top_left_x, top_left_y),
        (bottom_right_x, bottom_right_y),
    ) = get_game_window_coordinates(window_name)

    image = ImageGrab.grab(
        bbox=(
            top_left_x, 
            top_left_y, 
            top_left_x + bottom_right_x, 
            top_left_y + bottom_right_y,
        )
    )

    return image

def resize_template(template, image_shape):
    """
    The symbols scale with the height of the 
    window. They don't scale with the width 
    of the window. This might be specific 
    solely to Infinitode 2.
    """
    template = opencv.cvtColor(template, opencv.COLOR_BGR2GRAY)
    width, height = template.shape[::-1]
    _, image_height = image_shape
    ratio_height = image_height / INITIAL_RESOLUTION_HEIGHT
    resize_width = int(ratio_height * width)
    resize_height = int(ratio_height * height)
    resized_template = opencv.resize(
        template,
        (
            resize_width,
            resize_height, 
        )
    )
    return resized_template

def template_match(image, template):
    """
    Finds all points where the correlation 
    between the template and the image is 
    highest.
    """
    image = np.array(image)
    bw_image = opencv.cvtColor(image, opencv.COLOR_BGR2GRAY)
    threshold = 0.7
    correlations = opencv.matchTemplate(
        bw_image,
        template,
        opencv.TM_CCOEFF_NORMED
    )
    locations = np.where( correlations >= threshold)    
    return locations

def highlight_region(image, locations, rectangle_shape):
    """
    This function highlights with a red rectangle where 
    the symbol is on screen. The function also highlights
    the center of the symbol with a red rectangle.

    Mostly used for debugging.
    """
    template_height, template_width = rectangle_shape
    image = np.array(image)
    image = opencv.cvtColor(image, opencv.COLOR_RGB2BGR)
    point = None
    center = None
    if len(locations[0]):
        point = (locations[1][0], locations[0][0])       
    if point:
        center = (point[0] + template_width//2, point[1] + template_height//2)
        box_center_tl = (center[0] - 2, center[1] - 2)
        box_center_br = (center[0] + 2, center[1] + 2)
        # highlight symbol
        opencv.rectangle(
            image,
            point,
            (point[0] + template_width, point[1] + template_height), 
            (0,0,255), 
            2
        )
        # highlight center 
        opencv.rectangle(
            image, 
            box_center_tl,
            box_center_br,
            (0,0,255),
            2,
        )
    else:
        logging.warning("No points were found")
    
    click_on_symbol("Infinitode 2", center)   
    logging.debug("Center is {}".format(center))
    return image
 
def find_symbol(image, symbol_name):
    """
    This function takes the name of the symbol which we
    want to find, then it resizes the template to match
    the resolution of the game window. We then perform
    a template match to find all locations where we have
    a correlation.
    Finally, we highlight the symbol on screen and we highlight
    the center of the symbol.
    """
    template = opencv.imread('./symbols/' + symbol_name + ".png")
    template = resize_template(template, (image.width, image.height))
    locations = template_match(image, template)
    highlight_image = highlight_region(image, locations, template.shape)
    highlight_image = np.array(highlight_image)
    opencv.imshow("Highlight", highlight_image)

def click_on_symbol(window_name, symbol_coordinates):
    """
    Clicks at the specified location
    """
    (
        (tl_x, tl_y),
        (_, _)
    ) = get_game_window_coordinates(window_name)
    if ( 
        symbol_coordinates and 
        type(symbol_coordinates) is tuple and 
        len(symbol_coordinates) == 2
    ):
        # for some reason, this works more consistently
        pyautogui.moveTo(
            x=tl_x + symbol_coordinates[0],
            y=tl_y + symbol_coordinates[1],
        )
        pyautogui.click(button="left")
        pyautogui.scroll(-1600)
    else:
        logging.warning("No coordinates passed")

while True:
    image = get_game_window_image('Infinitode 2')
    find_symbol(image, "newgame")
    if opencv.waitKey(5000) == ord('q'):
        break


    