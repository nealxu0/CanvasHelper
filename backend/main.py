import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LinearRegression  # example
from utils.canvas_parser import parse_canvas_assignment, summarize_assignments
import requests
