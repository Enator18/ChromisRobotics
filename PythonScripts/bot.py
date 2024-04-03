#from flask import Flask, jsonify, request, render_template
import flask
import serial
import os
import time
from adafruit_pca9685 import PCA9685
import busio
from board import SCL, SDA
from gpiozero import Motor
import math
from adafruit_servokit import ServoKit
kit = ServoKit(channels=16)

arm_pitch_motor = Motor(17, 27)
arm_roll_motor = Motor(12, 13, pwm = True)

i2c_bus = busio.I2C(SCL, SDA)
pca = PCA9685(i2c_bus)
pca.frequency = 50

drive_speed = 25

old_time = -1
new_time = 0


app = flask.Flask("RobotServer")
@app.route("/")
# gpio.setmode(gpio.BOARD)
# gpio.setup(37,)

def send():
    new_time = time.time()
    delta = new_time - old_time

    if old_time == -1:
        delta = 0

    old_time = new_time


    #turn the url queries into a dictionary
    os.system('clear')
    all_args = flask.request.args.to_dict()
    time.sleep(0.1)

    #Controller 1
    joy1x = 0
    joy1y = 0
    joy2x = 0
    joy2y = 0
    trigger = -1
    bumper_left = False
    bumper_right = False

    #Controller 2
    bumper_2_left = False
    bumper_2_right = False
    trigger_2_left = 0.0
    trigger_2_right = 0.0
    c2joy1y = 0.0

    for arg in all_args:
        #print all the keys then : then the values
        print(arg,":",all_args[arg])

        if arg == "axis-0-0": #C1 Left joystick X axis
            joy1x = round(float(all_args[arg]), 3)
        if arg == "axis-1-0": #C1 Left joystick Y axis
            joy1y = round(float(all_args[arg]), 3)
        if arg == "axis-2-0": #C1 Right joystick y axis
            joy2x = round(float(all_args[arg]), 3)
        if arg == "axis-3-0": #C1 Right joystick y axis
            joy2y = round(float(all_args[arg]), 3)
        if arg == "axis-5-0": #C1 Right trigger
            trigger = round(float(all_args[arg]), 3)
        if arg == "axis-1-1": #C2 Left Joystick, y axis
            c2joy1y = round(float(all_args[arg]), 3)
        if arg == "axis-2-1":
            trigger_2_left = round(float(all_args[arg]), 3)
        if arg == "axis-5-1":
            trigger_2_right = round(float(all_args[arg]), 3)
        if arg == "button-4-0": #C1 Left bumper
            bumper_left = (all_args[arg] == "True")
        if arg == "button-5-0": #C1 Right bumper
            bumper_right = (all_args[arg] == "True")
        if arg == "button-4-1": #C2 Left bumper
            bumper_2_left = (all_args[arg] == "True")
        if arg == "button-5-1": #C2 Right bumper
            bumper_2_right = (all_args[arg] == "True")
        
    #Organize inputs
    #Trick with tuples: a,b = value to set for a, value to set for b
    joy1x,joy1y = deadzone(joy1x,joy1y,0.1)
    joy2x,joy2y = deadzone(joy2x,joy2y,0.1)
    #must return something, doesn't really matter what
    drive_percent = drive_speed * ((trigger * 0.5) + 1.5)
    if bumper_left:
        drive_percent = 5
    if bumper_right:
        drive_percent = 60
    
    thrust_left = min(1, max(-1, joy1y + joy1x)) * drive_percent
    thrust_right = min(1, max(-1, joy1y - joy1x)) * drive_percent
    thrust_up = joy2y * drive_speed

    #print(str(joy1x) + ", " + str(joy1y))

    #Drive thrusters
    set_thruster_speed(0, thrust_left)
    set_thruster_speed(1, thrust_right)
    set_thruster_speed(2, thrust_up)
    set_thruster_speed(3, thrust_up)

    #Tilt arm
    if bumper_2_left:
        arm_roll_motor.backward()
    elif bumper_2_right:
        arm_roll_motor.forward()
    else:
        arm_roll_motor.stop()

    #Pitch arm
    if c2joy1y > 0.1:
        arm_pitch_motor.forward(c2joy1y)
    elif c2joy1y < 0.1:
        arm_pitch_motor.backward(abs(c2joy1y))
    else:
        arm_pitch_motor.stop()

    
    #Open/Close Hand
    if trigger_2_left > -1:
        move_servo(4, -30 * ((trigger_2_left * 0.5) + 0.5), 0, 180, delta)

    if trigger_2_right > -1:
        move_servo(4, 30 * ((trigger_2_left * 0.5) + 0.5), 0, 180, delta)

    return all_args
def deadzone(x,y,length):
    dist = math.sqrt((x*x) + (y*y))
    if(dist<length):
        return 0, 0
    #return (1.0/(1.0-length))*(x-length),(1.0/(1.0-length))*(y-length)
    return (x/dist) * ((dist - length) / (1 - length)), (y/dist) * ((dist - length) / (1 - length))
#Thruster index 0-3
#Speed -100 to 100
def set_thruster_speed(thruster, speed):
    capped_speed = min(100, max(-100, speed)) * -1
    pca.channels[thruster].duty_cycle = int((13.107 * capped_speed) + 4915.125)

def move_servo(channel, value, low, high, delta):
    clamped = min(high, max(kit.servo[channel].angle + (value * delta), low))
    kit.servo[channel].angle = clamped



if __name__ == "__main__":
    for n in range(4):
        pca.channels[n].duty_cycle = 4915
    time.sleep(7)
    app.run(host='0.0.0.0', debug=False)