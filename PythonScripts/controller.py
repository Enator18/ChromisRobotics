global signals
global signal_pairs
global screen
chromis_teal = (0, 200, 180)
shark_attack = (100, 15, 10)
black = (0,0,0)
white = (255,255,255)
purple = (80,15,130)
if __name__ == "__main__":
    import serial
    import requests
    import urllib.parse
    import pygame
    import pygame.joystick as ctrl
    import os

    pygame.init()
    screen = pygame.display.set_mode((500, 700))
    pygame.display.set_caption("ROV Control")
    pygame.display.init()
    clock = pygame.time.Clock()
    wifi = False

    #Which controller does what
    bindings = [-1, -1]


    ctrl.init()
    try:
        joy = ctrl.Joystick(0)
        joy.init()
        print("Detected controller 1: "+ str(joy.get_name()))
        try:
            joy2 = ctrl.Joystick(1)
            joy2.init()
            print("Detected controller 2: "+str(joy2.get_name()))
        except:
            print("ONLY ONE CONTROLLER")
            joy2 = {}
    except:
        print("NO CONTROLLER")
        joy = {}

    running = True
    #IP of raspberry pi DO NOT FORGET
    rovIP = "192.168.1.20"
    signals = []
    signal_pairs = {
    1:"arm_open",
    2:"arm_close",
    3:"arm_clockwise",
    4:"arm_counter_clockwise",
    }
    config = {}
    config_old = {}
    
    def sort_dict(dictionary):
        keys = [key for key in dictionary.keys()]
        if len(keys) > 0:
            keys.sort()
            new_dict = {key:dictionary[key] for key in keys}
            return new_dict
        else:
            return {}
    def clear_arr():
        global signals
        signals = []
    def send_signals():
        if wifi:
            query = {str(i):config[i] for i in config.keys()}
            #turn it into a url
            query = urllib.parse.urlencode(query)
            #check if we get an error
            try:
                #build the whole url
                r = requests.get("http://" + rovIP + ":5000" + "/?" + query)
                #we sent the signals, ready to accept new ones
                # signals = []
            except Exception as e:
                print(str(e))
        else:
            print_dict(config)
    def get_signals():
        print_signals()
        return input()
    def print_signals():
        print("Enter key to indicate signal")
        for i in signal_pairs.keys():
            print(str(i)+":"+signal_pairs[i])
        print("Or send to send")
    def print_dict(dictionary):
        os.system('cls')
        for key in dictionary.keys():
            print(str(key)+":"+str(dictionary[key]))
    def add(signal):
        signals.append(signal)
    def handle_input():
        typed = get_signals()
        if typed != "send":
            add(int(typed))
            typed = get_signals()
        else:
            send_signals()
    while running:
        # 0, 200, 180: Chromis Teal
        screen.fill(chromis_teal)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN or event.type == pygame.JOYBUTTONUP or event.type == pygame.JOYAXISMOTION or event.type == pygame.JOYHATMOTION:
                if bindings[event.instance_id] == -1:
                    if event.type == pygame.JOYBUTTONDOWN:
                        if event.button == 6:
                            bindings[event.instance_id] = 0
                        elif event.button == 7:
                            bindings[event.instance_id] = 1
                else:
                    gamepad_id = bindings[event.instance_id]
                
                    if event.type == pygame.JOYBUTTONDOWN:
                        config["button-"+str(event.button)+"-"+str(gamepad_id)] = True
                    elif event.type == pygame.JOYBUTTONUP:
                        config["button-"+str(event.button)+"-"+str(gamepad_id)] = False
                    elif event.type == pygame.JOYAXISMOTION:
                        config["axis-"+str(event.axis)+"-"+str(gamepad_id)] = event.value
                    elif event.type == pygame.JOYHATMOTION:
                        config["hat-"+str(event.hat)+"-"+str(gamepad_id)] = event.value

            elif event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    exit()
        if config != config_old:
            config = sort_dict(config)
            send_signals()
            config_old = config.copy()
        # handle_input()
        clock.tick(30)
                


    #ctrl.init()
    #ctrl.Joystick(0).init()
    #while(ctrl.Joystick(0).get_button(3)==0.0):
    #    pass
    #print(ctrl.Joystick(0).get_button(0))


    print("__main__")
    #make a dictionary containing all the signals recieved, and what they should do
