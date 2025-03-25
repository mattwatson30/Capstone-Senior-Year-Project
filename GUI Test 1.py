


#*****************CLASSES/ SETUP*****************
import sys #system params
import time #used for delays (like time.sleep())
import serial #used to communicate with the arduino over COM Ports
import serial.tools.list_ports #lists available serial ports on the computer

#we also need threading:
#   - threading is used here so the GUI doesnt freeze when reading from the arduino
#   - this allows conncurrent processes
import threading

#import widgets for pyQt6
#   - pyQT6 is the Python version of the C++ Qt 6 GUI framework
#   - Qt is written in C++, pyQt6 is the python wrapper
from PyQt6.QtWidgets import (
    QApplication,   #used for GUI general startup/ stop
    QMainWindow,    #used to frame the app with a main window
    QWidget,        #used for widget layout 
    QVBoxLayout,    #stacks widgets vertically
    QLabel,         #displays text
    QComboBox,      #dropdown lists
    QPushButton,    #button in the GUI that a user can click
    QLineEdit,      #single line input
    QTextEdit,      #multiple line output (the terminal in the app)
    QFrame          #container used to group widgets (style)
)

#pyqtSignal: signals (events) between threads running and the GUI
#Qobject: needed for signal emmission (base class for Qt objects)
from PyQt6.QtCore import pyqtSignal, QObject


#globals
arduino = None
selected_mode = "Manual Mode" #defaulted mode is manual
selected_pattern = "L1" #default pattern is L1
selected_flash_rate = 1 #default flash rate is 1 Hz
selected_flash_duration = 1 #default duration is 1s
selected_COMport = "None" #no COM port originally selected


#******************CLASS DEFINITIONS*****************
"""
in our code, we have 2 classes:
1) serialclass:
    -this class is responsible for reading serial data from the arduino,
     without slowing or stopping the GUI
    -this class was created as when you read from the serial port, we stop/ wait for
     data, which causes the GUI to freeze if we were to read from serial directly in
     the main GUI thread
    -this lets the GUI be responsive to the user while reading serial data in the
     background
    -we use signalling to communicate between threads
  
2) systemGUI
    -the 'systemGUI' class creates a GUI for the system where the user can change
     system parameters:
        - COM port selection
        - Mode selection (manual mode or trigger mode)
        - Flashing pattern
        - Flashing frequency and duration
        - Start button to send packetized system parameters to the arduino
        - View output from arduino (serial monitor)
"""

# 'serialclass' class that is used to read serial data from arduino
#        - note that it inherits from QObject (base class for Qt objects)
#          we need to use QObject for emiting signals
# general problem this solves:
#        - if we want to read serial data from the arduino in the main GUI
#          thread, them the app would freeze waiting for data
#        - this is because arduino.readline() waits/ blocks until something
#          comes through the serial port
class serialclass(QObject):

    #pyqtSignal is used for communication between threads
    #   data_received_signal is a signal that has a string when its emmited
    #   we use this signal to send serial messages to the GUI
    data_received_signal = pyqtSignal(str)

    #constructor that creates a serialclass object
    def __init__(self):

        #calls the QObject (parent class) constructor
        super().__init__()

        # self.running: this sets a flag that controls the loop (starts/ stops it)
        # in the background thread that is checking for serial data from the arduino. 
        # This is used in the 'readserialmethod' method (below)
        # which basically does:
        #       while self.running
        #           read from arduino .....
        # (ensures that we are constantly checking for data from the arduino using a thread)
        self.running = True

    #METHOD #1: readserialmethod
    #   this method reads the serial data on the COM port from the arduino
    #   this runs in a background thread and basically polls the COM port
    def readserialmethod(self):

        #run until self.running is false (POLL)
        while self.running:

            #only run id the arduino is connected and the COM port is open
            if arduino and arduino.is_open:
                try:
                    #read a line of text from the arduino into the 'line' variable
                    #"utf-8" converts the bytes from the arduino to a string and '.strip()' removes newlines
                    line = arduino.readline().decode("utf-8").strip()
                    
                    #if a line of data was read
                    if line:
                        # emit the 'data_received' signal to the GUI with the line that was read,
                        # indicating that it was from the arduino. This signal is connected to the 
                        # main GUI code with the self.worker.data_received.connect(self.log_message)
                        # (i.e. we call log_message() whenever we receive data)
                        self.data_received_signal.emit(f"Arduino: {line}")

                #otherwise failure occured
                except serial.SerialException:
                    self.data_received_signal.emit("error occured when reading the serial data!!.")
                    break

            #add a little delay so we arent constantly polling
            time.sleep(0.1)


# the 'systemGUI' class creates a GUI for the system where the user can change
# system parameters:
#   - COM port selection
#   - Mode selection (manual mode or trigger mode)
#   - Flashing pattern
#   - Flashing frequency and duration
#   - Start button to send packetized system parameters to the arduino
#   - View output from arduino (serial monitor)

# note that this class inherits from QMainWindow (from PyQt) (main GUI)
class systemGUI(QMainWindow):

    #constructor method used when a systemGUI method is created
    def __init__(self):
        
        #note that below calls the parent class 'QMainWindow' constructor
        super().__init__()



        #**********************SETUP/ LAYOUT**********************
        
        #set window title and the size of the window
        self.setWindowTitle("LED Control System for the Quinn Laboratory")
        self.setGeometry(300, 100, 500, 600)

        #background colour here is light gray
        self.setStyleSheet("background-color: #f5f5f5;")

        #layout setup:
        #QVBoxLayout stacks the widgets from top to bottom
        vertically_stacked_layout = QVBoxLayout()
        #container is a QWidget that has everything in it
        container = QWidget()
        container.setLayout(vertically_stacked_layout)
        #below tells pyQt that container is the main area
        self.setCentralWidget(container)


        #*******************COM PORT CONNECTION*******************
        
        #create a label called 'COMlabel' for the selection of the COM port
        self.COMlabel = QLabel("Select the COM port (USB port) that the Arduino is connected to:")
        #add it to the main layout (verically stacked as we are usuing QVBoxLayout())
        vertically_stacked_layout.addWidget(self.COMlabel)

        # create a variable called the COMport_dropdownbox that creates a dropdown
        # box to select the COM port (using the QComboBox widget from PyQt6)
        self.COMport_dropdownbox = QComboBox()
        # call the get_available_COM_ports function to get the ports available
        self.COMport_dropdownbox.addItems(self.get_available_COM_ports())
        # add the dropdown under the label
        vertically_stacked_layout.addWidget(self.COMport_dropdownbox)
       
        # add a 'connect' button to connect to the serial COM port (below the dropdown)
        self.connect_button = QPushButton("CONNECT")
        # call the 'connect_to_COM_port' function to connect to the selected com port
        self.connect_button.clicked.connect(self.connect_to_COM_port)
        # add 'connect' button below the dropdown
        vertically_stacked_layout.addWidget(self.connect_button)

        #*********************SELECT TRIGGERING MODE************************
        
        # select the triggering mode (below the COM port selection)
        self.triggeringmode_label = QLabel("Select the triggering mode:")
        vertically_stacked_layout.addWidget(self.triggeringmode_label)

        #add two button widgets below the triggering mode label that allow you to choose manual or triggering mode:
        #1) manual mode: 
        #       click the start button on the GUI and the system runs:
        self.manual_triggering_mode = QPushButton("Manual Mode")
        # call the 'set_triggering_mode' function and pass 'Manual Mode' into it
        self.manual_triggering_mode.clicked.connect(lambda: self.set_triggering_mode("Manual Mode"))
        vertically_stacked_layout.addWidget(self.manual_triggering_mode)
        
        #2) external trigger mode/ 'Trigger mode':  
        #       the system runs once the user clicks the start button and 
        #       a trigger form the camera causes the LED system to start
        self.external_trigger_mode = QPushButton("Trigger Mode")
        # call the 'set_triggering_mode' function and pass 'Trigger Mode' into it
        self.external_trigger_mode.clicked.connect(lambda: self.set_triggering_mode("Trigger Mode"))
        vertically_stacked_layout.addWidget(self.external_trigger_mode)



        #*********************SELECT FLASH PATTERN************************
        # add a label under the triggering mode that allows you to choose the LED flash pattern
        # we have four different possible patterns 
        # Note: L1 is LED1 and L2 is LED2 in an LED bank of 2 LED's:
        #   1) L1
        #   2) L1 L2
        #   3) L1 L1 L2
        #   4) L1 L1 L1 L2
        
        self.flashpattern_label = QLabel("Choose LED Flash Pattern:")
        vertically_stacked_layout.addWidget(self.flashpattern_label)

        #pattern 1 (L1):
        #create a pushbutton with label for pattern 1
        self.flashpattern_1 = QPushButton("Pattern 1: L1")
        #update current pattern selection (lambda function that calls the set flashpattern when button is clicked)
        self.flashpattern_1.clicked.connect(lambda: self.set_flashpattern("L1"))
        #add button widget for pattern 1
        vertically_stacked_layout.addWidget(self.flashpattern_1)

        #pattern 2 (L1 L2):
        #create a pushbutton with label for pattern 2
        self.flashpattern_2 = QPushButton("Pattern 2: L1:L2")
        #update current pattern selection (lambda function that calls the set flashpattern when button is clicked)
        self.flashpattern_2.clicked.connect(lambda: self.set_flashpattern("L1:L2"))
        #add button widget for pattern 2
        vertically_stacked_layout.addWidget(self.flashpattern_2)

        #pattern 3 (L1 L1 L2):
        self.flashpattern_3 = QPushButton("Pattern 3: L1:L1:L2")
        #update current pattern selection (lambda function that calls the set flashpattern when button is clicked)
        self.flashpattern_3.clicked.connect(lambda: self.set_flashpattern("L1:L1:L2"))
        #add button widget for pattern 3        
        vertically_stacked_layout.addWidget(self.flashpattern_3)

        #pattern 4 (L1 L1 L1 L2):
        self.flashpattern_4 = QPushButton("Pattern 4: L1:L1:L1:L2")
        #update current pattern selection (lambda function that calls the set flashpattern when button is clicked)
        self.flashpattern_4.clicked.connect(lambda: self.set_flashpattern("L1:L1:L1:L2"))
        #add button widget for pattern 4
        vertically_stacked_layout.addWidget(self.flashpattern_4)




        #*********************SELECT FLASH RATE/ DURATION************************
        
        #FLASH RATE:
        #create label under the flash pattern for the flash rate input
        self.flashrate_label = QLabel("Flash Rate (Hz):")
        vertically_stacked_layout.addWidget(self.flashrate_label)

        #create a text box input (use QLineEdit() from PyQt) and add it below the flash rate label
        self.flash_rate_input = QLineEdit()
        vertically_stacked_layout.addWidget(self.flash_rate_input)

        #FLASH DURATION:
        #create label under the flash rate for the flash duration input
        self.duration_label = QLabel("Duration (Seconds):")
        vertically_stacked_layout.addWidget(self.duration_label)

        #create a text box input (use QLineEdit() from PyQt) and add it below the flash duration label
        self.duration_input = QLineEdit()
        vertically_stacked_layout.addWidget(self.duration_input)





        #********************PREVIEW THE SETTINGS FROM ABOVE*******************
        #add a label for presenting the settings that were selected
        self.preview_label = QLabel("Settings Preview:")
        vertically_stacked_layout.addWidget(self.preview_label)

        #create a QFrame box to group all of the settings together
        self.settings_preview_frame = QFrame()
        #give it a border
        self.settings_preview_frame.setFrameShape(QFrame.Shape.Box)
        self.settings_preview_frame.setStyleSheet("padding: 5px;")
        #use a verticle stack format (QVBoxLayout() as before) inside the QFrame box
        self.settings_preview_verticle_layout = QVBoxLayout()
        self.settings_preview_frame.setLayout(self.settings_preview_verticle_layout)

        #Display the currently selected COM port (global variable: selected_COMport)
        self.preview_COM_port = QLabel(f"COM Port: {selected_COMport}")
        self.settings_preview_verticle_layout.addWidget(self.preview_COM_port)

        #Display the currently selected flashing mode (global variable: selected_mode)
        self.preview_mode = QLabel(f"Mode: {selected_mode}")
        self.settings_preview_verticle_layout.addWidget(self.preview_mode)

        #Display the currently selected LED pattern (global variable: selected_pattern)
        self.preview_pattern = QLabel(f"Pattern: {selected_pattern}")
        self.settings_preview_verticle_layout.addWidget(self.preview_pattern)

        #Display the currently selected flash rate (global variable: flash_rate)
        self.preview_rate = QLabel(f"Flash Rate: {selected_flash_rate} Hz")
        self.settings_preview_verticle_layout.addWidget(self.preview_rate)
        
        #Display the currently selected flash duration (global variable: selected_flash_duration)
        self.preview_duration = QLabel(f"Duration: {selected_flash_duration} sec")
        self.settings_preview_verticle_layout.addWidget(self.preview_duration)

        #add the created frame to the GUI
        vertically_stacked_layout.addWidget(self.settings_preview_frame)



        #*************************START BUTTON************************
        #this button deploys the configuration packet to the arduino
        self.start_button = QPushButton("Start Flashing")
        #call the 'send_configuration_packet' function to deploy the configuration packet
        self.start_button.clicked.connect(self.send_configuration_packet)
        #add the start button to the GUI
        vertically_stacked_layout.addWidget(self.start_button)



        #*************************SERIAL MONITOR***********************
        #add a label for the serial monitor
        self.serial_monitor_label = QLabel("Serial Monitor:")
        vertically_stacked_layout.addWidget(self.serial_monitor_label)

        #create a multi-line widget using QTextEdit
        self.serial_monitor = QTextEdit()
        #make the serial monitor read-only and add it to the screen
        self.serial_monitor.setReadOnly(True)
        vertically_stacked_layout.addWidget(self.serial_monitor)

        
        #********************SET UP THREADS FOR SERIAL****************
        #create an instance of the serialclass class that handles the threads
        self.serialthreadhandler = serialclass()
        #connect the 'data_received_signal' for this instance to the 'log_message()' method
        #when this serial thread receives new data from the COM port, it connects the signal
        #to the log_message function (thread safe)
        self.serialthreadhandler.data_received_signal.connect(self.add_message_to_serial_monitor)


    #function/ method to get the COM ports (method inside GUI class)
    #arguments: self (belongs to GUI class)
    #returns: list of strings (like "COM3" or "COM4")
    def get_available_COM_ports(self):
        #call pyserial function to scan system for all available serial ports
        ports = serial.tools.list_ports.comports()
        #return the list of port name's (port.device) like "COM3" or "COM4"
        return [port.device for port in ports]


    #function/ method to connect to selected COM port
    #args: self (belongs to GUI class)
    #returns
    def connect_to_COM_port(self):
        #use the globals for the arduino and selected COM port
        global arduino, selected_COMport
        #grab the currently selected port from the dropdown in the GUI
        selected_COMport = self.COMport_dropdownbox.currentText()

        #check if the global arduino object exists (not 'None') 
        #and the serial connection is currently open
        if arduino and arduino.is_open:
            #if both true, close the existing serial connection to the arduino
            #now we can open a new connection on the selected port
            arduino.close()

        #Note: try-except handles errors that may occur when attempting to connect to a serial port
        #try to connect to the arduino
        try:
            #create serial connection to arduino (9600 baud rate)
            #timeout = 1 means that if we dont get data after 1s we stop waiting for connection
            arduino = serial.Serial(selected_COMport, 9600, timeout=1)

            #give arduino 2s to reset and initialize as we just opened a serial connection
            time.sleep(2)

            #clear leftover data/ flush buffer
            arduino.reset_input_buffer()

            #write that connection is successful to the serial monitor on the GUI
            self.add_message_to_serial_monitor(f"Connected to {selected_COMport}")
            
            #create new thread to continously read serial data from the arduino
            #daemon = true means that the thread stops when the program exits
            #lets us read the new connection in the background without affecting the GUI
            threading.Thread(target=self.serialthreadhandler.readserialmethod, daemon=True).start()  # Start thread
        
        #we could not connect to the arduino (error):
        except serial.SerialException:
            self.add_message_to_serial_monitor("Failed to connect to the microcontroller! Check the connection to the COM port and ensure nothing else is accessing it.")

        #update the settings preview panel on the GUI to display the configuration info
        self.update_configuration_preview()


    #function/method to set the triggering mode
    #args: self (belongs to GUI class), mode (a string that is either 'Trigger Mode' or 'Manual Mode')
    def set_triggering_mode(self, mode):
        #use the global variable
        global selected_mode
        selected_mode = mode
        #update the settings preview panel on the GUI to display the configuration info
        self.update_configuration_preview()

    #function/method to set the flashing pattern
    #args: self (belongs to GUI class), pattern (a string: either 'L1', 'L1:L2', 'L1:L1:L2' or 'L1:L1:L1:L2')
    def set_flashpattern(self, pattern):
        #use the global variable
        global selected_pattern
        selected_pattern = pattern 
        #update the settings preview panel on the GUI to display the configuration info
        self.update_configuration_preview()


    #function/method to send the configuration packet
    #args: self (belongs to GUI class)
    #this sends the configuration data from the GUI in the form of
    #integers to the arduino through serial communication
    #Packet format:
    #    SET {mode - int} {flash rate - int} {flash duration - int} {pattern - int}
    #    ex: SET 2 4 30 2
    #    - Mode: 1 (Manual Mode), 2 (Triggering Mode)
    #    - Flash Rate: Positive Number (> 0)    [Hz]
    #    - Flash Duration: Positive Number (> 0)    [s]
    #    - Pattern: "L1" = 1, "L1:L2" = 2, "L1:L1:L2" = 3, "L1:L1:L1:L2" = 4
    def send_configuration_packet(self):

        #we are using the global variables
        global selected_flash_rate, selected_flash_duration

        #try to send the configuration data from the GUI
        #we are using the try-except clause as the user might
        #enter invalid data like a letter or something for the flash rate, etc.
        try:
            #grabs the flash rate from the box and tries to convert it to an integer
            selected_flash_rate = int(self.flash_rate_input.text())
            #grabs the flash duration from the box and tries to convert it to an integer
            selected_flash_duration = int(self.duration_input.text())

            #cannot use non-positive flash rate/ duration values
            if selected_flash_rate <= 0 or selected_flash_duration <= 0:
                self.add_message_to_serial_monitor("Enter valid values (that are greater or equal to zero) for the flash rate/ duration!")
                #exit method
                return

            #define the pattern index and the corresponding integer ID that is to be sent in the configuration packet
            pattern_index = {
                "L1": 1,
                "L1:L2": 2,
                "L1:L1:L2": 3,
                "L1:L1:L1:L2": 4
            }[selected_pattern]

            #packetize the data to be sent to the arduino
            #packet has form "SET {mode - int} {flash rate - int} {flash duration - int} {pattern - int}"
            configuration_packet = f"SET {1 if selected_mode == 'Manual Mode' else 2} {selected_flash_rate} {selected_flash_duration} {pattern_index}\n"
            
            #send the packet to the arduino (if the arduino object exists and the serial port is connected)
            if arduino and arduino.is_open:
                #transmit the packet
                #.encode converts the string to bytes
                arduino.write(configuration_packet.encode())
                #print to the serial monitor that we successfully sent the packet
                self.add_message_to_serial_monitor(f"Successfully sent: {configuration_packet.strip()} to the arduino")
           
            #otherwise, an error occured
            else:
                self.add_message_to_serial_monitor("Error sending configuration data to the arduino!")

        #if an error occurs (the user enters a letter or another invalid input)
        except ValueError:
            #add an invalid input message to the serial monitor
            self.add_message_to_serial_monitor("Invalid Input!")
        
        
        #update the settings preview panel on the GUI to display the configuration info
        self.update_configuration_preview()

    #function/method to add a new message to the bottom of the serial monitor
    #args: self (belongs to GUI class), message (a string that will be displayed on the monitor)
    def add_message_to_serial_monitor(self, message):
        #append the message to the bottom of the serial monitor
        self.serial_monitor.append(message)

    #function/method to update the GUI's configuration preview
    #args: self (belongs to GUI class)
    #note that this displays the current globals
    def update_configuration_preview(self):
        self.preview_COM_port.setText(f"COM Port: {selected_COMport}")
        self.preview_mode.setText(f"Mode: {selected_mode}")
        self.preview_pattern.setText(f"Pattern: {selected_pattern}")
        self.preview_rate.setText(f"Flash Rate: {selected_flash_rate} Hz")
        self.preview_duration.setText(f"Duration: {selected_flash_duration} sec")



#****************MAIN*****************
if __name__ == "__main__":

    #initialize the PyQt app
    pyQtapp = QApplication(sys.argv)

    #create an instance of the main window class (called 'mainwindow')
    mainwindow = systemGUI()
    #make this window visible on the screen
    mainwindow.show()

    #done
    sys.exit(pyQtapp.exec())
