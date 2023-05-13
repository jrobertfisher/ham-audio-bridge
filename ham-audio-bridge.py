# HAM Audio Bridge
# Written by Rob Fisher - KI5QPY
# Release Notes v1.0.1 - 5/13/2023
#   Added Squelch on the speaker function.
#   Reduced the speaker and mic output gain from 2 to 1.
#   Closes active threads on exit.

import pyaudio
import tkinter as tk
from tkinter import ttk
import threading
import numpy as np; #print(np.__file__)
import serial
#import traceback
#import scipy.signal
#from pydub import AudioSegment

class AudioBridge():
    def __init__(self):
        # Initialize PyAudio object
        self.pa_speakers = pyaudio.PyAudio()
        self.pa_mic = pyaudio.PyAudio()
        self.stop_flag = False
        self.stop_flag2 = False
        self.is_ptt_pressed = False
        self.input_device_index = None
        self.output_device_index = None
        self.input_channels_speakers = None
        self.output_channels_speakers = None
        self.input_channels_mic = None
        self.output_channels_mic = None
        self.input_stream_speakers = None
        self.output_stream_speakers = None
        self.audio_thread_speakers = None
        self.input_stream_mic = None
        self.output_stream_mic = None
        self.audio_thread_mic = None
        self.ser = None
        self.squelch = 0.00
        self.sample_rate_speakers = 48000

        # Create GUI window
        self.window = tk.Tk()
        self.window.title("HAM Audio Bridge v1.0 by KI5QPY")

        # Create labels for input and output devices (Bridge to Speakers)
        tk.Label(self.window, text="Input Device:").grid(row=0, column=0, padx=5, pady=5)
        tk.Label(self.window, text="Output Device:").grid(row=1, column=0, padx=5, pady=5)

        # Create dropdowns for input and output devices (Bridge to Speakers)
        self.input_var_speakers = tk.StringVar()
        self.output_var_speakers = tk.StringVar()
        self.input_dropdown_speakers = tk.OptionMenu(self.window, self.input_var_speakers, *self.get_audio_devices_speakers(), command=self.on_device_select_speakers)
        self.output_dropdown_speakers = tk.OptionMenu(self.window, self.output_var_speakers, *self.get_audio_devices_speakers(), command=self.on_device_select_speakers)
        self.input_dropdown_speakers.grid(row=0, column=1, padx=5, pady=5, sticky="W")
        self.output_dropdown_speakers.grid(row=1, column=1, padx=5, pady=5, sticky="W")

        # Create start and stop buttons (Bridge to Speakers)
        self.start_stop_label_speakers = tk.Label(self.window, text="Speaker Bridge")
        self.start_stop_label_speakers.grid(row=0, column=2, sticky="W")
        self.start_button_speakers = tk.Button(self.window, text="Start", command=lambda: self.start_speakers())
        self.stop_button_speakers = tk.Button(self.window, text="Stop", command=lambda: self.stop_all())
        self.start_button_speakers.grid(row=1, column=2, padx=5, pady=5, sticky="W")
        self.stop_button_speakers.grid(row=1, column=2, padx=50, pady=5, sticky="W")
        self.stop_button_speakers.config(state=tk.DISABLED)

        # Set default audio devices (Bridge to Speakers)
        self.input_var_speakers.set(str(self.get_default_input_device_speakers()))
        self.output_var_speakers.set(str(self.get_default_output_device_speakers()))

        # Create labels for input and output devices (Bridge to Mic)
        tk.Label(self.window, text="Input Device:").grid(row=4, column=0, padx=5, pady=5)
        tk.Label(self.window, text="Output Device:").grid(row=5, column=0, padx=5, pady=5)

        # Create dropdowns for input and output devices (Bridge to Mic)
        self.input_var_mic = tk.StringVar()
        self.output_var_mic = tk.StringVar()
        self.input_dropdown_mic = tk.OptionMenu(self.window, self.input_var_mic, *self.get_audio_devices_mic(), command=self.on_device_select_mic)
        self.output_dropdown_mic = tk.OptionMenu(self.window, self.output_var_mic, *self.get_audio_devices_mic(), command=self.on_device_select_mic)
        self.input_dropdown_mic.grid(row=4, column=1, padx=5, pady=5, sticky="W")
        self.output_dropdown_mic.grid(row=5, column=1, padx=5, pady=5, sticky="W")

        # Create start and stop buttons (Bridge to Mic)
        self.start_stop_label_mic = tk.Label(self.window, text="Mic Bridge")
        self.start_stop_label_mic.grid(row=4, column=2, sticky="W")
        self.start_button_mic = tk.Button(self.window, text="Start", command=lambda: self.start_mic())
        self.stop_button_mic = tk.Button(self.window, text="Stop", command=lambda: self.stop_all())
        self.start_button_mic.grid(row=5, column=2, padx=5, pady=5, sticky="W")
        self.stop_button_mic.grid(row=5, column=2, padx=50, pady=5, sticky="W")
        self.stop_button_mic.config(state=tk.DISABLED)

        # Set default audio devices (Bridge to Mic)
        self.input_var_mic.set(str(self.get_default_input_device_mic()))
        self.output_var_mic.set(str(self.get_default_output_device_mic()))

        ttk.Separator(self.window, orient='horizontal').grid(row=3, columnspan=5, padx=8, sticky="EW")

        # Create COM Port dropdown
        self.com_port_label = tk.Label(self.window, text="COM Port:")
        self.com_port_label.grid(row=6, column=0)
        self.com_port_var = tk.StringVar(self.window)
        self.com_port_var.set("COM4") # Set default com port
        self.com_port_dropdown = tk.OptionMenu(self.window, self.com_port_var, "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "COM10")
        self.com_port_dropdown.grid(row=6, column=1, pady=5, sticky="W")

        # Create Baud Rate dropdown
        self.baud_rate_label = tk.Label(self.window, text="Baud Rate:")
        self.baud_rate_label.grid(row=6, column=1, pady=5, padx=90, sticky="W")
        self.baud_rate_var = tk.IntVar(self.window)
        self.baud_rate_var.set(9600) # Set default baud rate
        self.baud_rate_dropdown = tk.OptionMenu(self.window, self.baud_rate_var, 9600, 19200, 38400, 57600, 115200)
        self.baud_rate_dropdown.grid(row=6, column=1, pady=5, padx=(150,0), sticky="W")

        # Create Squelch slider to reduce quiet noise.
        self.squelch_label = tk.Label(self.window, text="Squelch:")
        self.squelch_label.grid(row=7, column=1, pady=5, padx=90, sticky="W")
        self.squelch_var = tk.DoubleVar()
        self.squelch_var.set(0.01)
        self.squelch_slider = ttk.Scale(self.window, from_=0.00032, to=0.01, variable=self.squelch_var, orient=tk.HORIZONTAL, length=70, command=self.update_squelch)
        self.squelch_slider.grid(row=7, column=1, pady=5, padx=(150,0), sticky="W")

        # Create transmit button
        self.transmit_label = tk.Label(self.window, text="Push to talk:")
        self.transmit_label.grid(row=7, column=0)
        self.transmit = tk.Button(self.window, text='     Transmit ')
        self.transmit.config(state=tk.DISABLED)
        self.transmit.bind('<ButtonPress>', lambda event: self.send_ptt_command(event, True))
        self.transmit.bind('<ButtonRelease>', lambda event: self.send_ptt_command(event, False))
        self.transmit.grid(row=7, column=1, pady=5, sticky="W")
        self.red_light = tk.Label(self.window, bg="#F0F0F0", width=1, height=1, bd=0, highlightthickness=1, highlightbackground="gray", relief="solid")
        self.red_light.grid(row=7, column=1, stick="W", padx=5, pady=5)

        # Start GUI loop
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()

    def stop_all(self):
        self.stop_speakers()
        self.stop_mic()

    def get_audio_devices_speakers(self):
        # Get list of audio device indices
        devices_speakers = []
        for i in range(self.pa_speakers.get_device_count()):
            info = self.pa_speakers.get_device_info_by_index(i)
            #devices.append(f"{info['index']}, {info['name']}")
            input_channels_speakers = info['maxInputChannels']
            output_channels_speakers = info['maxOutputChannels']
            devices_speakers.append(f"{info['index']}, {info['name']}, Input channels: {input_channels_speakers}, Output channels: {output_channels_speakers}")
        return devices_speakers
    
    def get_audio_devices_mic(self):
        # Get list of audio device indices
        devices_mic = []
        for i in range(self.pa_mic.get_device_count()):
            info = self.pa_mic.get_device_info_by_index(i)
            #devices.append(f"{info['index']}, {info['name']}")
            input_channels_mic = info['maxInputChannels']
            output_channels_mic = info['maxOutputChannels']
            devices_mic.append(f"{info['index']}, {info['name']}, Input channels: {input_channels_mic}, Output channels: {output_channels_mic}")
        return devices_mic
    
    def get_default_input_device_speakers(self):
        # Get default input device info
        device_info_speakers = self.pa_speakers.get_default_input_device_info()
        
        # Return device name with index number
        return f"{device_info_speakers['index']}, {device_info_speakers['name']}"

    def get_default_output_device_speakers(self):
        # Get default input device info
        device_info_speakers = self.pa_speakers.get_default_output_device_info()

        # Return device name with index number
        return f"{device_info_speakers['index']}, {device_info_speakers['name']}"
    
    def get_default_input_device_mic(self):
        # Get default input device info
        device_info_mic = self.pa_mic.get_default_input_device_info()
        
        # Return device name with index number
        return f"{device_info_mic['index']}, {device_info_mic['name']}"

    def get_default_output_device_mic(self):
        # Get default input device info
        device_info_mic = self.pa_mic.get_default_output_device_info()

        # Return device name with index number
        return f"{device_info_mic['index']}, {device_info_mic['name']}"

    def on_device_select_speakers(self, event):
        # Called when a dropdown selection is made
        pass

    def on_device_select_mic(self, event):
        # Called when a dropdown selection is made
        pass

    def start_speakers(self):
        try:
            # Get selected device indices
            self.input_device_index = int(self.input_var_speakers.get().split(',')[0])
            self.output_device_index = int(self.output_var_speakers.get().split(',')[0])

            # Debug to test if device index is passing correctly
            #print(self.input_device_index)
            #print(self.output_device_index)

            # Get max input and output channels
            input_info_speakers = self.pa_speakers.get_device_info_by_index(self.input_device_index)
            output_info_speakers = self.pa_speakers.get_device_info_by_index(self.output_device_index)
            self.input_channels_speakers = input_info_speakers['maxInputChannels']
            self.output_channels_speakers = output_info_speakers['maxOutputChannels']

            # Create new PyAudio object
            self.pa_speakers = pyaudio.PyAudio()
            self.input_stream_speakers = self.pa_speakers.open(format=pyaudio.paFloat32, channels=self.input_channels_speakers, rate=self.sample_rate_speakers, #rate=44100
                                            input=True, input_device_index=self.input_device_index,
                                            frames_per_buffer=1024)
            self.output_stream_speakers = self.pa_speakers.open(format=pyaudio.paFloat32, channels=self.output_channels_speakers, rate=self.sample_rate_speakers, #rate=44100
                                            output=True, output_device_index=self.output_device_index,
                                            frames_per_buffer=1024)
            self.stop_button_speakers.config(state=tk.NORMAL)
            self.start_button_speakers.config(state=tk.DISABLED)

            # Start audio loop in a separate thread
            self.stop_flag = False
            self.audio_thread_speakers = threading.Thread(target=self.run_audio_loop_speakers)
            self.audio_thread_speakers.start()
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()

    def stop_speakers(self):
        # Stop audio bridge
        self.stop_flag = True
        self.audio_thread_speakers.join()
        self.input_stream_speakers.stop_stream()
        self.input_stream_speakers.close()
        self.output_stream_speakers.stop_stream()
        self.output_stream_speakers.close()
        self.start_button_speakers.config(state=tk.NORMAL)
        self.stop_button_speakers.config(state=tk.DISABLED)

    def run_audio_loop_speakers(self):
        while not self.stop_flag:
            # Read audio data from input stream
            input_data_speakers = self.input_stream_speakers.read(1024)
            # Convert input data to numpy array
            input_np_speakers = np.frombuffer(input_data_speakers, dtype=np.float32)
            # Reshape numpy array based on input channels
            input_np_speakers = input_np_speakers.reshape(-1, self.input_channels_speakers)
            # Process audio data
            output_np_speakers = self.process_audio_speakers(input_np_speakers)
            # Reshape output numpy array based on output channels
            output_np_speakers = output_np_speakers.reshape(-1, self.output_channels_speakers)
            # Convert output data to bytes
            output_data_speakers = output_np_speakers.tobytes()
            # Write output data to output stream
            self.output_stream_speakers.write(output_data_speakers)

        # Clean up
        self.input_stream_speakers.stop_stream()
        self.input_stream_speakers.close()
        self.output_stream_speakers.stop_stream()
        self.output_stream_speakers.close()
        self.pa_speakers.terminate()

    # def process_audio_speakers(self, input_np_speakers): #might need to change to "input_np_speakers"
    #     # Get number of input and output channels
    #     input_channels_speakers = input_np_speakers.shape[1]
    #     output_channels_speakers = self.output_channels_speakers
        
    #     # Convert input numpy array if number of channels doesn't match
    #     if input_channels_speakers != output_channels_speakers:
    #         if input_channels_speakers == 1 and output_channels_speakers == 2:
    #             # If input has 1 channel and output has 2 channels, duplicate the channel
    #             input_np_speakers = np.tile(input_np_speakers, (1, 2))
    #         elif input_channels_speakers == 2 and output_channels_speakers == 1:
    #             # If input has 2 channels and output has 1 channel, average the channels
    #             input_np_speakers = np.mean(input_np_speakers, axis=1, keepdims=True)
        
    #     # Process the input numpy array and return the output numpy array
    #     output_np_speakers = input_np_speakers * 2.0
    #     return output_np_speakers

    def update_squelch(self, event=None):
        self.squelch = self.squelch_var.get()

    def process_audio_speakers(self, input_np_speakers):
        # Get number of input and output channels
        input_channels_speakers = input_np_speakers.shape[1]
        output_channels_speakers = self.output_channels_speakers

        # Convert input numpy array if number of channels doesn't match
        if input_channels_speakers != output_channels_speakers:
            if input_channels_speakers == 1 and output_channels_speakers == 2:
                # If input has 1 channel and output has 2 channels, duplicate the channel
                input_np_speakers = np.tile(input_np_speakers, (1, 2))
            elif input_channels_speakers == 2 and output_channels_speakers == 1:
                # If input has 2 channels and output has 1 channel, average the channels
                input_np_speakers = np.mean(input_np_speakers, axis=1, keepdims=True)

        # Apply a high-pass filter - not working well
        #b_hp, a_hp = scipy.signal.butter(2, 120, 'highpass', fs=self.sample_rate_speakers)
        #input_np_speakers = scipy.signal.lfilter(b_hp, a_hp, input_np_speakers)

        # Apply a low-pass filter - not working well
        #b_lp, a_lp = scipy.signal.butter(2, 10000, 'lowpass', fs=self.sample_rate_speakers)
        #input_np_speakers = scipy.signal.lfilter(b_lp, a_lp, input_np_speakers)

        # Apply a noise gate to the input numpy array
        output_np_speakers = np.where(np.abs(input_np_speakers) < self.squelch, 0, input_np_speakers)

        # Scale the output numpy array
        output_np_speakers *= 1.0

        return output_np_speakers
    
    def start_mic(self):
        try:
            # Get selected device indices
            self.input_device_index = int(self.input_var_mic.get().split(',')[0])
            self.output_device_index = int(self.output_var_mic.get().split(',')[0])

            # Debug to test if device index is passing correctly
            #print(self.input_device_index)
            #print(self.output_device_index)

            # Get max input and output channels
            input_info = self.pa_mic.get_device_info_by_index(self.input_device_index)
            output_info = self.pa_mic.get_device_info_by_index(self.output_device_index)
            self.input_channels_mic = input_info['maxInputChannels']
            self.output_channels_mic = output_info['maxOutputChannels']

            # Create new PyAudio object
            self.pa_mic = pyaudio.PyAudio()
            self.input_stream_mic = self.pa_mic.open(format=pyaudio.paFloat32, channels=self.input_channels_mic, rate=self.sample_rate_speakers,
                                            input=True, input_device_index=self.input_device_index,
                                            frames_per_buffer=1024)
            self.output_stream_mic = self.pa_mic.open(format=pyaudio.paFloat32, channels=self.output_channels_mic, rate=self.sample_rate_speakers,
                                            output=True, output_device_index=self.output_device_index,
                                            frames_per_buffer=1024)
            self.stop_button_mic.config(state=tk.NORMAL)
            self.start_button_mic.config(state=tk.DISABLED)

            # Start audio loop in a separate thread
            self.stop_flag = False
            self.audio_thread_mic = threading.Thread(target=self.run_audio_loop_mic)
            self.audio_thread_mic.start()
            
            # Enable Transmit button
            self.transmit.config(state=tk.NORMAL)
            self.red_light.configure(bg="#00C800") #Green
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()

    def stop_mic(self):
        # Stop audio bridge
        self.stop_flag = True
        self.audio_thread_mic.join()
        self.input_stream_mic.stop_stream()
        self.input_stream_mic.close()
        self.output_stream_mic.stop_stream()
        self.output_stream_mic.close()
        #self.pa_mic.terminate() # Close PyAudio object
        #self.pa_mic.terminate()
        self.start_button_mic.config(state=tk.NORMAL)
        self.stop_button_mic.config(state=tk.DISABLED)
        self.red_light.configure(bg="#F0F0F0") #Gray
        self.transmit.config(state=tk.DISABLED)

    def run_audio_loop_mic(self):
        while not self.stop_flag:
            # Read audio data from input stream
            input_data_mic = self.input_stream_mic.read(1024)

            # Convert input data to numpy array
            input_np_mic = np.frombuffer(input_data_mic, dtype=np.float32)

            # Reshape numpy array based on input channels
            input_np_mic = input_np_mic.reshape(-1, self.input_channels_mic)

            # Process audio data
            output_np_mic = self.process_audio_mic(input_np_mic)

            # Reshape output numpy array based on output channels
            output_np_mic = output_np_mic.reshape(-1, self.output_channels_mic)

            # Convert output data to bytes
            output_data_mic = output_np_mic.tobytes()

            # Write output data to output stream
            self.output_stream_mic.write(output_data_mic)

        # Clean up
        self.input_stream_mic.stop_stream()
        self.input_stream_mic.close()
        self.output_stream_mic.stop_stream()
        self.output_stream_mic.close()
        self.pa_mic.terminate()

    def process_audio_mic(self, input_np_mic):
        # Get number of input and output channels
        input_channels_mic = input_np_mic.shape[1]
        output_channels_mic = self.output_channels_mic
        
        # Convert input numpy array if number of channels doesn't match
        if input_channels_mic != output_channels_mic:
            if input_channels_mic == 1 and output_channels_mic == 2:
                # If input has 1 channel and output has 2 channels, duplicate the channel
                input_np_mic = np.tile(input_np_mic, (1, 2))
            elif input_channels_mic == 2 and output_channels_mic == 1:
                # If input has 2 channels and output has 1 channel, average the channels
                input_np_mic = np.mean(input_np_mic, axis=1, keepdims=True)
        
        # Process the input numpy array and return the output numpy array
        output_np_mic = input_np_mic * 1.0

        return output_np_mic

    def transmit_clicked(self):
        if self.transmit['state'] == tk.NORMAL:
            # Change color of red light
            self.red_light.configure(bg="#FF0023") #Red
            self.send_ptt_command

    def send_ptt_command(self, event, ptt_on):
       # Check if the transmit button is enabled
        if ptt_on:
            # Connect to Digirig over serial port
            if not self.is_ptt_pressed:
                if self.transmit['state'] == tk.NORMAL:
                    self.ser = serial.Serial(port=self.com_port_var.get(), baudrate=self.baud_rate_var.get())
                    self.red_light.configure(bg="#FF0023") #Red
                    #self.ser.write(b'PTT ON') # replace 'PTT ON' with the appropriate command for your Digirig                    
                else:
                    #do nothing if the transmit button is disabled
                    pass
        else:
            #self.ser.write(b'PTT OFF') # replace 'PTT OFF' with the appropriate command for your Digirig
            # Close the serial connection after exiting the mainloop
            #self.ser.close()
            if self.transmit['state'] ==tk.DISABLED:
                self.red_light.configure(bg="#F0F0F0") #Gray
            else:
                self.red_light.configure(bg="#00C800") #Green
            self.ser = None

# def cleanup():
#     for thread in threading.enumerate():
#         if thread.is_active():
#                 thread.stop()

    def on_close(self):
        # global bridge
        # if bridge is not None:
        self.stop_flag = True
        self.stop_speakers()
        self.stop_mic()
        self.window.destroy()

if __name__ == "__main__":
    bridge = AudioBridge()