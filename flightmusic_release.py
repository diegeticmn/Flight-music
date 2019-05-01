import urllib.request
import ssl
import pandas as pd
from bokeh.plotting import figure,ColumnDataSource
from bokeh.models import HoverTool,WMTSTileSource,LinearColorMapper,LabelSet
from bokeh.palettes import RdYlBu11 as palette
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.tile_providers import CARTODBPOSITRON_RETINA
from bokeh.application.handlers.function import FunctionHandler
import numpy as np
from tornado.ioloop import IOLoop

from opensky_api import OpenSkyApi
import scipy.signal
import pygame, pygame.sndarray

ssl._create_default_https_context = ssl._create_unverified_context
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]

pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=4096)

#*****SOUND FUNCTIONS ADOPTED FROM http://shallowsky.com/blog/programming/python-play-chords.html ******
def play_for(sample_wave, ms):
    sound = pygame.sndarray.make_sound(sample_wave)
    sound.play(-1)
    pygame.time.delay(ms)
    sound.fadeout(25)

sample_rate = 44100

def sine_wave(hz, peak, n_samples=sample_rate):
    length = sample_rate / float(hz)
    omega = np.pi * 2 / length
    xvalues = np.arange(int(length)) * omega
    onecycle = peak * np.sin(xvalues)
    return np.resize(onecycle, (n_samples,)).astype(np.int16)

def square_wave(hz, peak, duty_cycle=.5, n_samples=sample_rate):
    """Compute N samples of a sine wave with given frequency and peak amplitude.
       Defaults to one second.
    """
    t = numpy.linspace(0, 1, 500 * 440/hz, endpoint=False)
    wave = scipy.signal.square(2 * numpy.pi * 5 * t, duty=duty_cycle)
    wave = numpy.resize(wave, (n_samples,))
    return (peak / 2 * wave.astype(numpy.int16))

def make_chord(hz, ratios, waveform=None):
    """Make a chord based on a list of frequency ratios
       using a given waveform (defaults to a sine wave).
    """
    sampling = 4096
    if not waveform:
        waveform = sine_wave
    chord = waveform(hz, sampling)
    for r in ratios[1:]:
        chord = sum([chord, waveform(hz * r / ratios[0], sampling)])
    return chord

def major_triad(hz, waveform=None): #CALL AS: play_for(major_triad(hz, sine_wave), length)
    return make_chord(hz, [4, 5, 6], waveform)

#****END SOUND FUNCTIONS*****

#******FLIGHT TRACKING FUNCTIONS******

# COORDINATE CONVERSION FUNCTION
def wgs84_to_web_mercator(df, lon="lon", lat="lat"):
    k = 6378137
    df["x"] = df[lon] * (k * np.pi/180.0)
    df["y"] = np.log(np.tan((90 + df[lat]) * np.pi/360.0)) * k
    return df

#Main flight tracker
def flight_track(doc):
    plot_data = ColumnDataSource({'lat':[],'lon':[], 'x':[],'y':[]})

    def update():

        lat = []
        lon = []
        api = OpenSkyApi() #retrieve flight data from https://opensky-network.org/apidoc/index.html
        states = api.get_states(bbox=(41,49,-94,-76)) #Create coordinate box of flights to track - min lat, max lat, min lon, max lon

        for s in states.states:
            lat.append(s.latitude)
            lon.append(s.longitude)

        dict = {'lat':lat, 'lon':lon}
        flight_data = pd.DataFrame(dict)

        wgs84_to_web_mercator(flight_data)
        flight_data=flight_data.fillna('No Data')
        n_roll=len(flight_data.index)
        plot_data.stream(flight_data.to_dict(orient='list'),n_roll)

        roundedlist = []
        for x in lon:
            rounded=round(x)
            roundedlist.append(rounded)
            roundedlist = list(dict.fromkeys(roundedlist))

        #This for loop plays notes - choose notes based on latitude or longitude coordinates you select
        for x in roundedlist:
            if x == -91:
                play_for(sine_wave(220, 4096), 250) #play_for(wave_type(hz of tone, sample rate), note length) - A3 1/8 note at 120 bpm
            elif x == -89:
                play_for(sine_wave(246.94, 4096), 250) #B3
            elif x == -87:
                play_for(sine_wave(261.63, 4096), 250) #C4
            elif x == -85:
                play_for(sine_wave(293.66, 4096), 250) #D4
            elif x == -83:
                play_for(sine_wave(329.63, 4096), 250) #E4
            elif x == -81:
                play_for(sine_wave(349.23, 4096), 250) #F4
            elif x == -79:
                play_for(sine_wave(392.00, 4096), 250) #G4
            elif x == -77:
                play_for(sine_wave(440, 4096), 250) #A4

    doc.add_periodic_callback(update, 1000) #whole note at 120 bpm is 2000 - selects how often to check flight data

    #PLOT COMMANDS
    x_range,y_range=([-10328142.598007,-8384234.313173], [5140724.564177,6248813.053970]) #PLACEMENT OF MAP ON LAUNCH - Convert coordinates at https://epsg.io/map#srs=3857&x=19517736.550798&y=9323482.961128&z=1&layer=streets
    p=figure(x_range=x_range,y_range=y_range,x_axis_type='mercator',y_axis_type='mercator',sizing_mode='scale_width',plot_height=300)
    color_mapper = LinearColorMapper(palette=palette)
    p.add_tile(CARTODBPOSITRON_RETINA)
    p.circle('x','y',source=plot_data,fill_color='blue',hover_color='yellow',size=10,fill_alpha=0.8,line_width=0.5)

    doc.title='Great Lakes' #TITLE OF PAGE IN BROWSER
    doc.add_root(p)

#MAIN LAUNCH COMMANDS
apps = {'/': Application(FunctionHandler(flight_track))}
server = Server(apps, port=0) #define an unused port
server.start()
server.show('/')
loop = IOLoop.current()
loop.start()
server.stop()
