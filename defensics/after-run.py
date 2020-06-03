import os
os.system('python3 ' + os.path.dirname(os.path.realpath(__file__)) +
          '/instrumentation_client.py http://localhost:8000/after-run')
