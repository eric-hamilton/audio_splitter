import os
import sys
import re
import librosa
import soundfile as sf

class Splitter:
    def __init__(self):
        self.amplitude_threshold = 10
        self.silence_threshold_ms = 100
        self.file_path = None
        self.sample_rate = None
        self.data = None
        self.clip_times = []
        self.file_extension = ".wav"
        self.padding = 0

    def load_file(self, file_path):
        try:
            self.file_path = file_path
            self.data, self.sample_rate = librosa.load(file_path, sr=None)
            self.file_extension = os.path.splitext(file_path)[1]
            print(f"Loaded {file_path} successfully.\n")
        except Exception as e:
            print(f"Could not load file: {e}")
            input("Press Enter to quit")
            sys.exit()

    def run(self):
        if not self.file_path:
            sys.exit()

        self.prompt_silence_thresh()
        self.prompt_amp_thresh()
        print("Scanning file...")
        self.split_clip_on_silence()

        print(f"\nFound {len(self.clip_times)} clips.")
        if self.prompt_continue():
            naming_convention = self.prompt_naming_convention()
            prefix = self.prompt_prefix()
            self.prompt_padding()
            
            print("Writing files.")
            self.write_files(naming_convention, prefix)
            print("Done!")
            name_suffix=""
            if naming_convention == "sequential":
                name_suffix="_xx"
            elif naming_convention == "timestamps":
                name_suffix="_x_x--x_x"
            
            
            
            print(f"Files saved as {os.getcwd()}\\output\\{prefix}{name_suffix}{self.file_extension}")
        else:
            self.run()
    def prompt_padding(self):
        while True:
            print("Add padding? Input in milliseconds\n")
            padding = input()
            if not padding:
                self.padding = 0
                return
            else:
                if padding.isdigit():
                    self.padding = int(padding)
                    return
                elif padding.lower() in ["no", "n"]:
                    self.padding = 0
                    return
                else:
                    print("Padding value must be a digit")
                
    def prompt_prefix(self):
        while True:
            print("\nType File Prefix.\n")
            prefix = input()
            if not prefix:
                return "output"
            elif self.is_valid_prefix(prefix):
                return prefix
            else:
                print("Invalid Prefix")

    def prompt_amp_thresh(self):
        while True:
            print("Select Amplitude Threshold. (0 - 1000)")
            amp_thresh = input(f"Current: {self.amplitude_threshold}\n")
            if not amp_thresh:
                return
            if amp_thresh.isdigit():
                if 0 <= int(amp_thresh) <= 1000:
                    self.amplitude_threshold = int(amp_thresh)
                    print()
                    return
                else:
                    print("Must be in range (0-1000)")
            else:
                print("Must be an integer")

    def prompt_silence_thresh(self):
        while True:
            print("Select Silence Threshold in milliseconds")
            sil_thresh = input(f"Current: {self.silence_threshold_ms}\n")
            if not sil_thresh:
                return
            if sil_thresh.isdigit():
                if int(sil_thresh) >= 0:
                    self.silence_threshold_ms = int(sil_thresh)
                    print()
                    return
                else:
                    print("Must be a positive integer.")
            else:
                print("Must be a positive integer.")

    def prompt_input_file(self):
        while True:
            print("Input filename. Ctrl+C to quit.")
            filename = input()
            if not filename:
                sys.exit()
            if os.path.exists(filename):
                self.load_file(filename)
                return
            else:
                print(f"Could not find file: {filename}\n")

    def prompt_naming_convention(self):
        while True:
            print("Choose a naming convention:")
            print("1: Sequential")
            print("2: Timestamps")
            response = input("Choose a number: ")
            if not response:
              # default to sequential
                return "sequential"
            elif response == "1":
                return "sequential"
            elif response == "2":
                return "timestamps"
            else:
                print("\nInvalid response")

    def split_clip_on_silence(self):
        """Populate the start and end times of audio based on the given thresholds
        """
        silence_threshold_samples = int(self.silence_threshold_ms * self.sample_rate / 1000)
        sample_index = 0
        recording = False
        silence_index = 0
        start_index = None
        end_index = None

        self.clip_times = []

        running = True
        while running:
            try:
                amplitude = abs(self.data[sample_index]) * 1000
            except IndexError as e:
                running = False
                silence_index = silence_threshold_samples + 1
                amplitude = 0

            if not recording:                
                if amplitude >= self.amplitude_threshold:
                    recording = True
                    start_index = sample_index
                    silence_index = 0
            else:
                if amplitude < self.amplitude_threshold:
                    if silence_index >= silence_threshold_samples:
                        end_index = sample_index
                        self.clip_times.append((start_index, end_index))
                        recording = False
                        start_index = None
                        end_index = None
                        silence_index = 0
                    else:
                        silence_index += 1
                else:
                    silence_index = 0

            sample_index += 1

    def write_files(self, naming_convention, prefix):
        # Make output folder if it doesn't exist
        if not os.path.exists("output"):
            os.makedirs("output")
        
        # Calculate padding samples
        padding = 0
        if self.padding:
            padding = int(self.padding * self.sample_rate / 1000)            
            
        for clip_index, (start, end) in enumerate(self.clip_times):
            start_padding = start - padding
            end_padding = end + padding
            
            
            start_padding = max(0, start_padding)
            end_padding = min(len(self.data), end_padding)
            if start_padding >= end_padding:
                print("Skipping file with no length")
                continue
            clip_data = self.data[start_padding:end_padding]
            if naming_convention == "sequential":
                filename = f"output/{prefix}_{clip_index+1}{self.file_extension}"
            elif naming_convention == "timestamps":                
                filename = self.get_filename(prefix, start, end)
            self.save_file(filename, clip_data)

    def get_string_from_sample_index(self, index):
        return str(round(index / self.sample_rate, 2)).replace(".", "_")

    def get_filename(self, prefix, start_time, end_time):
        start_time = self.get_string_from_sample_index(start_time)
        end_time = self.get_string_from_sample_index(end_time)
        return f"output/{prefix}_{start_time}--{end_time}{self.file_extension}"

    def save_file(self, filename, recorded_data):
        sf.write(filename, recorded_data, self.sample_rate)

    def is_valid_prefix(self, prefix):
        disallowed_chars = r'[\\/:\*\?"<>\|]'  # Slashes, backslashes, colons, asterisks, question marks, angle brackets, pipe
        if re.search(disallowed_chars, prefix):
            return False
        return True

    def prompt_continue(self):
        while True:
            print("Continue - \"y\", Try Again - \"n\"")
            response = input()
            if not response:
                # default to continue
                return True
            elif response.lower() in ["yes", "y"]:
                return True
            elif response.lower() in ["no", "n"]:
                print()
                return False
            else:
                print("Invalid response")

if __name__ == "__main__":
    splitter = Splitter()
    if len(sys.argv) == 1:
        splitter.prompt_input_file()
        splitter.run()
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
        if os.path.exists(filename):
            splitter.load_file(filename)
            splitter.run()
        else:
            print(f"Error: File '{filename}' not found.")
    else:
        print("Usage: python splitter.py <input_file>")
