#from flask import Flask, jsonify, request, render_template
import flask
import serial
import os
import time
from threading import Thread
from adafruit_pca9685 import PCA9685
import busio
from board import SCL, SDA
from gpiozero import Motor
import math
from adafruit_servokit import ServoKit
kit = ServoKit(channels=16)

arm_roll_motor = Motor(17, 27)
arm_pitch_motor = Motor(12, 13, pwm = True)

i2c_bus = busio.I2C(SCL, SDA)
pca = PCA9685(i2c_bus)
pca.frequency = 50

drive_speed = 40
up_speed = 60
down_speed = 40
hand_speed = 30
crawl_speed = 5
sprint_speed = 80

open_angle = 95 #Engineers - FIX THIS
closed_angle = 60
semi_angle = 80
servo_channel = 6

old_time = -1

DEFAULT = 0
RECORDING = 1
PLAYBACK = 2

state = DEFAULT

recorded_inputs = []

stop_playback = False

playback_thread = None
servo_loop_thread = None

servo_speed = 0


app = flask.Flask("RobotServer")
@app.route("/")
# gpio.setmode(gpio.BOARD)
# gpio.setup(37,)

def send():
    global old_time
    global recorded_inputs
    global stop_playback
    
    new_time = time.time()
    delta = new_time - old_time

    if old_time == -1:
        delta = 0

    old_time = new_time


    #Turn the url queries into a dictionary.
    os.system('clear')
    all_args = flask.request.args.to_dict()
    time.sleep(0.1)

    all_args["delta"] = delta

    #Stop Record/Playback Button
    if all_args["button-2-0"] and all_args["button-2-0"] == "True":
        state = DEFAULT
        stop_playback = True
        if playback_thread:
            playback_thread.join()

    #Record Button
    elif all_args["button-1-0"] and all_args["button-1-0"] == "True" and state == DEFAULT:
        state = RECORDING
        recorded_inputs = {}

    #Start Playback Button
    elif all_args["button-3-0"] and all_args["button-3-0"] == "True" and state != PLAYBACK:
        state = PLAYBACK
        stop_playback = False
        playback_thread = Thread(target=playback,args=())
        playback_thread.start()
        #Start Playback Thread

    #Record inputs if in recording mode.
    if state == RECORDING:
        recorded_inputs.append(all_args)
    
    #If not in autonomous mode, update using pilot inputs.
    if state != PLAYBACK:
        update(all_args)

    return state

def servo_loop():
    current_time = time.time()
    while True:
        delta = time.time() - current_time
        current_time = time.time()
        servo_thread = Thread(target=move_servo, args=(servo_channel, servo_speed, closed_angle, open_angle, delta))
        servo_thread.start()
        time.sleep(0.03125)
        servo_thread.join()


def playback():
    for args in recorded_inputs:
        if stop_playback:
            return
        time.sleep(args["delta"])
        update(args)

def update(all_args):
    global servo_speed
    delta = all_args["delta"]
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
    button_2_x = False
    button_2_b = False
    button_2_y = False

    #Read inputs from the dictionary.
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
        if arg == "axis-4-1":
            trigger_2_left = round(float(all_args[arg]), 3)
        if arg == "axis-5-1":
            trigger_2_right = round(float(all_args[arg]), 3)
        if arg == "button-4-0": #C1 Left bumper
            bumper_left = (all_args[arg] == "True")
        if arg == "button-5-0": #C1 Right bumper
            bumper_right = (all_args[arg] == "True")
        if arg == "button-1-1":
            button_2_b = (all_args[arg] == "True")
        if arg == "button-2-1":
            button_2_x = (all_args[arg] == "True")
        if arg == "button-3-1":
            button_2_y = (all_args[arg] == "True")
        if arg == "button-4-1": #C2 Left bumper
            bumper_2_left = (all_args[arg] == "True")
        if arg == "button-5-1": #C2 Right bumper
            bumper_2_right = (all_args[arg] == "True")
        
    #Organize inputs
    #Trick with tuples: a,b = value to set for a, value to set for b
    joy1x,joy1y = deadzone(joy1x,joy1y,0.1)
    joy2x,joy2y = deadzone(joy2x,joy2y,0.1)
    
    #Set Thruster Speeds
    drive_percent = drive_speed * ((trigger * 0.25) + 1.25)
    if bumper_left:
        drive_percent = crawl_speed
    elif bumper_right:
        drive_percent = sprint_speed
    
    thrust_left = min(1, max(-1, joy1y + joy1x)) * drive_percent
    thrust_right = min(1, max(-1, joy1y - joy1x)) * drive_percent

    if (joy2y >= 0):
        thrust_up = joy2y * up_speed
    else:
        thrust_up = joy2y * down_speed

    #Drive thrusters
    print("thrust_left: "+str(thrust_left)+"\nthrust_right: "+str(thrust_right))
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
        arm_pitch_motor.backward(c2joy1y)
    elif c2joy1y < 0.1:
        arm_pitch_motor.forward(abs(c2joy1y))
    else:
        arm_pitch_motor.stop()

    
    #Open/Close Hand
    if button_2_b:
        kit.servo[servo_channel].angle = open_angle
        servo_speed = 0
    elif button_2_x:
        kit.servo[servo_channel].angle = closed_angle
        servo_speed = 0
    elif button_2_y:
        kit.servo[servo_channel].angle = semi_angle
        servo_speed = 0
    elif trigger_2_left > -1:
        move_servo(servo_channel, -hand_speed * ((trigger_2_left * 0.5) + 0.5), closed_angle, open_angle, delta)
        servo_speed = -hand_speed * ((trigger_2_left * 0.5) + 0.5)

    elif trigger_2_right > -1:
        move_servo(servo_channel, hand_speed * ((trigger_2_right * 0.5) + 0.5), closed_angle, open_angle, delta)
        servo_speed = hand_speed * ((trigger_2_right * 0.5) + 0.5)
    else:
        servo_speed = 0

    

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
    print("Moving Servo!!!")
    clamped = min(high, max(kit.servo[channel].angle + (value * delta), low))
    print(clamped)
    kit.servo[channel].angle = clamped



if __name__ == "__main__":

    servo_loop_thread = Thread(target=servo_loop, args=())
    servo_loop_thread.start()

    for n in range(4):
        pca.channels[n].duty_cycle = 4915
    time.sleep(7)
    app.run(host='0.0.0.0', debug=False)