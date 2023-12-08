from flask import Flask, request, jsonify
import numpy as np
import matplotlib.pyplot as plt
import IPython.display as ipd
import librosa
import librosa.display
import scipy.stats
from werkzeug.utils import secure_filename

app = Flask(__name__)
## TODO NEED TO HALF ANALYZE TIME

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {"mp3", "wav"}

# Function to check if a file has an allowed extension
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to convert enharmonic keys
def convert_enharmonic(key):
    """Converts less common enharmonic keys to their more common equivalents."""
    enharmonic_equivalents = {
        'C# major': 'Db major', 'C# minor': 'Db minor',
        'D# major': 'Eb major', 'D# minor': 'Eb minor',
        'F# major': 'Gb major', 'F# minor': 'Gb minor',
        'G# major': 'Ab major', 'G# minor': 'Ab minor',
        'A# major': 'Bb major', 'A# minor': 'Bb minor'
    }
    return enharmonic_equivalents.get(key, key)

@app.route("/api/python", methods=["POST"])


def analyze_audio():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            # Load the audio file with librosa and convert it to mono
            y, sr = librosa.load(
                file,
                sr=None,
                mono=False,
                duration=45,
                offset=0,
                res_type="kaiser_best",
                dtype=np.float32,
            )
            y_mono = librosa.to_mono(y)

        # # Analyze tempo
        # tempo, _ = librosa.beat.beat_track(y=y_mono, sr=sr)

        # Apply Harmonic/Percussive separation
        y_harmonic, y_percussive = librosa.effects.hpss(y_mono)

        # Calculate the onset strength (more robust for some types of music)
        onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr)

        # Analyze tempo using the percussive component and onset strength
        # tempo, _ = librosa.beat.beat_track(y=y_percussive, sr=sr, onset_envelope=onset_env, hop_length=512)
        static_tempo = librosa.feature.tempo(onset_envelope=onset_env, sr=sr)
        
        #Round tempo to nearest whole number
        rounded_tempo = round(static_tempo[0])

        # Create an instance of Tonal_Fragment
        tonal_fragment = Tonal_Fragment(y_mono, sr)

        # Get key information
        key = tonal_fragment.key
        converted_key = convert_enharmonic(key)

        # Print the key information
        tonal_fragment.print_key()

        # Return the analysis results
        result = {
            "tempo": rounded_tempo,
            "key": converted_key,  # Use the converted key
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# class that uses the librosa library to analyze the key that an mp3 is in
# arguments:
#     waveform: an mp3 file loaded by librosa, ideally separated out from any percussive sources
#     sr: sampling rate of the mp3, which can be obtained when the file is read with librosa
#     tstart and tend: the range in seconds of the file to be analyzed; default to the beginning and end of file if not specified
class Tonal_Fragment(object):
    def __init__(self, waveform, sr, tstart=None, tend=None):
        self.waveform = waveform
        self.sr = sr
        self.tstart = tstart
        self.tend = tend

        # Apply Harmonic/Percussive separation
        y_harmonic, _ = librosa.effects.hpss(waveform)

        # Use only the harmonic component for key analysis
        self.y_segment = y_harmonic
        if self.tstart is not None and self.tend is not None:
            self.tstart = librosa.time_to_samples(self.tstart, sr=self.sr)
            self.tend = librosa.time_to_samples(self.tend, sr=self.sr)
            self.y_segment = self.y_segment[self.tstart:self.tend]

        # Using Chroma CENS features
        self.chromograph = librosa.feature.chroma_cens(y=self.y_segment, sr=self.sr, bins_per_octave=36)
        
        
        # chroma_vals is the amount of each pitch class present in this time interval
        self.chroma_vals = []
        for i in range(12):
            self.chroma_vals.append(np.sum(self.chromograph[i]))
        pitches = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        # dictionary relating pitch names to the associated intensity in the song
        self.keyfreqs = {pitches[i]: self.chroma_vals[i] for i in range(12)} 
        
        keys = [pitches[i] + ' major' for i in range(12)] + [pitches[i] + ' minor' for i in range(12)]

        # use of the Krumhansl-Schmuckler key-finding algorithm, which compares the chroma
        # data above to typical profiles of major and minor keys:
        maj_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        min_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

        # finds correlations between the amount of each pitch class in the time interval and the above profiles,
        # starting on each of the 12 pitches. then creates dict of the musical keys (major/minor) to the correlation
        self.min_key_corrs = []
        self.maj_key_corrs = []
        for i in range(12):
            key_test = [self.keyfreqs.get(pitches[(i + m)%12]) for m in range(12)]
            # correlation coefficients (strengths of correlation for each key)
            self.maj_key_corrs.append(round(np.corrcoef(maj_profile, key_test)[1,0], 3))
            self.min_key_corrs.append(round(np.corrcoef(min_profile, key_test)[1,0], 3))

        # names of all major and minor keys
        self.key_dict = {**{keys[i]: self.maj_key_corrs[i] for i in range(12)}, 
                         **{keys[i+12]: self.min_key_corrs[i] for i in range(12)}}
        
        # this attribute represents the key determined by the algorithm
        self.key = max(self.key_dict, key=self.key_dict.get)
        self.bestcorr = max(self.key_dict.values())
        
        # this attribute represents the second-best key determined by the algorithm,
        # if the correlation is close to that of the actual key determined
        self.altkey = None
        self.altbestcorr = None

        for key, corr in self.key_dict.items():
            if corr > self.bestcorr*0.9 and corr != self.bestcorr:
                self.altkey = key
                self.altbestcorr = corr
                
    # prints the relative prominence of each pitch class            
    def print_chroma(self):
        self.chroma_max = max(self.chroma_vals)
        for key, chrom in self.keyfreqs.items():
            print(key, '\t', f'{chrom/self.chroma_max:5.3f}')
                
    # prints the correlation coefficients associated with each major/minor key
    def corr_table(self):
        for key, corr in self.key_dict.items():
            print(key, '\t', f'{corr:6.3f}')
    
    # printout of the key determined by the algorithm; if another key is close, that key is mentioned
    def print_key(self):
        print("likely key: ", max(self.key_dict, key=self.key_dict.get), ", correlation: ", self.bestcorr, sep='')
        if self.altkey is not None:
                print("also possible: ", self.altkey, ", correlation: ", self.altbestcorr, sep='')
    
    # prints a chromagram of the file, showing the intensity of each pitch class over time
    def chromagram(self, title=None):
        C = librosa.feature.chroma_cqt(y=self.waveform, sr=sr, bins_per_octave=24)
        plt.figure(figsize=(12,4))
        librosa.display.specshow(C, sr=sr, x_axis='time', y_axis='chroma', vmin=0, vmax=1)
        if title is None:
            plt.title('Chromagram')
        else:
            plt.title(title)
        plt.colorbar()
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    app.run(debug=True)
