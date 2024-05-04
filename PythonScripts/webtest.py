import flask
import serial
import os
import time
from threading import Thread

count = 10

app = flask.Flask("TestServer")
@app.route('/')
def send():
    return "Hello World: " + str(count)

def start_server():
    app.run(host='0.0.0.0', debug=False)

if __name__ == "__main__":
    t1 = Thread(target=start_server, args=())
    t1.start()
    for x in range(50):
        count += 1
        time.sleep(1)