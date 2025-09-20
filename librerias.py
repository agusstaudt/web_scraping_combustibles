# web scraping
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

# procesamiento de imágenenes
import cv2
import numpy as np
from PIL import Image
import pytesseract

# procesamiento de datos
import pandas as pd
import json

# sistema
import os 
import glob

# mysql
import pymysql
from dotenv import load_dotenv

# manejo de fechas
from datetime import datetime

# operaciones de listas y tuplas
from itertools import product

