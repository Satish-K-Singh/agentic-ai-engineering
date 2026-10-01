#This VS code is having copilot. 
import json
import logging
import time

import redis
from prometheus_client import start_http_server

from app.agents.graph import 