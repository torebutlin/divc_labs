import pydvma as dvma
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.rcParams.update({'font.size': 12,'font.family':'serif'})
import ipywidgets as widgets
from ipywidgets import Layout, Output
from IPython.display import display
import threading
import time


# =====================================================================
# Setup level check: student-facing live level meter for the noise
# measurement. Advisory only — it never blocks the lab.
# =====================================================================

# PLACEHOLDER targets until calibrated against the lab rig: per-channel
# RMS in volts, with a +/-5% acceptance band. Adjust these once the
# correct noise-generator level for the cantilever rig is known.
NOISE_TARGET_RMS = 0.2
NOISE_RMS_TOL = 0.05


def level_verdict(rms, target, tol=NOISE_RMS_TOL):
    """Classify one channel's RMS level against the target band.

    Returns (colour, message): colour is 'ok' (within the +/-tol band),
    'close' (within 3x the band) or 'off'; the message says which way
    to adjust the level. Pure function, so it is directly testable.
    """
    rel = (rms - target) / target
    if abs(rel) <= tol:
        return 'ok', 'level OK'
    msg = 'turn level UP' if rel < 0 else 'turn level DOWN'
    return ('close' if abs(rel) <= 3 * tol else 'off'), msg


class check_setup():
    """Live RMS level check for the noise measurement.

    Run this with the excitation selector on "Noise":

        lab.check_setup(settings)

    One bar per channel shows the live RMS against the shaded green
    target band (target +/- 5%). Adjust the noise generator level until
    every bar reads green, then press Stop. The check is advisory only:
    it never blocks the rest of the lab, and can be restarted at any
    time with the same button.

    Arguments: settings is the same MySettings used for the noise
    measurement; target_rms is a single value or one per channel
    (volts RMS — the module-level defaults are placeholders until the
    rig is calibrated); tol is the fractional acceptance band;
    window_s is the RMS averaging window in seconds.
    """

    COLOURS = {'ok': '#2ca02c', 'close': '#ff7f0e', 'off': '#d62728'}

    def __init__(self, settings, target_rms=NOISE_TARGET_RMS,
                 tol=NOISE_RMS_TOL, window_s=0.5):

        self.settings = settings
        self.tol = tol
        n = settings.channels
        targets = np.atleast_1d(np.asarray(target_rms, dtype=float))
        if targets.size == 1:
            targets = np.repeat(targets, n)
        if targets.size != n:
            raise ValueError('target_rms needs 1 value or one per '
                             'channel ({}), got {}'.format(n, targets.size))
        self.targets = targets
        self.n_window = max(1, int(window_s * settings.fs))

        self.out = Output()
        self.button = widgets.Button(description='Stop check',
                                     layout=Layout(width='25%'))
        self.button.button_style = 'warning'
        self.button.style.font_weight = 'bold'
        display(widgets.HBox([self.button]))

        try:
            dvma.start_stream(settings)
            self.rec = dvma.streams.REC
        except:
            self.rec = None
            print('Data stream not initialised.')
            print('Possible reasons: pyaudio or PyDAQmx not installed, or acquisition hardware not connected.')
            print('Please note that it won''t be possible to log data.')

        # one horizontal bar per channel, with the green target band
        # drawn behind it
        self.fig, self.ax = plt.subplots(1, 1,
                                         figsize=(9, 1.2 + 0.7 * n),
                                         dpi=100)
        ypos = np.arange(n)
        self.bars = self.ax.barh(ypos, np.zeros(n), height=0.6,
                                 color=self.COLOURS['off'])
        for k in range(n):
            lo = self.targets[k] * (1 - tol)
            hi = self.targets[k] * (1 + tol)
            self.ax.add_patch(plt.Rectangle((lo, k - 0.4), hi - lo, 0.8,
                                            color=self.COLOURS['ok'],
                                            alpha=0.3, zorder=0))
        self.xmax = 2.0 * float(np.max(self.targets))
        self.ax.set_xlim([0, self.xmax])
        self.ax.set_yticks(ypos)
        self.ax.set_yticklabels(['channel {}'.format(k) for k in range(n)])
        self.ax.invert_yaxis()
        self.ax.set_xlabel('RMS (V)')
        self.ax.set_title('adjust noise level until all bars are green')
        # per-channel readout to the right of the axes
        trans = matplotlib.transforms.blended_transform_factory(
            self.ax.transAxes, self.ax.transData)
        self.labels = [self.ax.text(1.02, k, '', transform=trans,
                                    va='center', fontsize=11)
                       for k in range(n)]
        self.fig.subplots_adjust(right=0.7)

        self.button.on_click(self.toggle)
        self.running = False
        if self.rec is not None:
            self._start_loop()

        display(self.out)

    def toggle(self, b):
        if self.running:
            self.running = False
            self.button.description = 'Restart check'
            self.button.button_style = 'success'
        elif self.rec is not None:
            self._start_loop()

    def _start_loop(self):
        self.running = True
        self.button.description = 'Stop check'
        self.button.button_style = 'warning'
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            try:
                time_data = dvma.stream_snapshot(self.rec)
                y = np.asarray(time_data.time_data)[-self.n_window:, :]
                rms = np.sqrt(np.mean(y ** 2, axis=0))
            except Exception as e:
                self.out.clear_output(wait=False)
                with self.out:
                    print('level check stopped: {}'.format(e))
                self.running = False
                break
            for k, bar in enumerate(self.bars):
                colour, msg = level_verdict(rms[k], self.targets[k],
                                            self.tol)
                bar.set_width(min(rms[k], self.xmax))
                bar.set_color(self.COLOURS[colour])
                self.labels[k].set_text('{:.3f} V — {}'.format(rms[k],
                                                               msg))
            self.fig.canvas.draw_idle()
            time.sleep(0.25)


class measure_stepped_sine():
    def __init__(self,settings):
        
        self.settings = settings
        
        # the 'out' construction is to refresh the text output at each update 
        # to stop text building up in the widget display
        self.out = Output()
        
        words = ['Measure', 'Delete Last Measurement', 'Save Data', 'Save Fig']
        self.buttons = [widgets.Button(description=w,layout=Layout(width='25%')) for w in words]
        self.buttons[0].button_style = 'success'
        self.buttons[0].style.font_weight = 'bold'
        self.buttons[1].button_style = 'warning'
        self.buttons[1].style.font_weight = 'bold'
        self.buttons[2].button_style = 'primary'
        self.buttons[2].style.font_weight = 'bold'
        self.buttons[3].button_style = 'primary'
        self.buttons[3].style.font_weight = 'bold'
        display(widgets.HBox(self.buttons))
        
        try:
            dvma.start_stream(settings)
            self.rec = dvma.streams.REC
        except:
            print('Data stream not initialised.')
            print('Possible reasons: pyaudio or PyDAQmx not installed, or acquisition hardware not connected.')
            print('Please note that it won''t be possible to log data.')
        
        
        
            
            
        self.f = np.array([])
        self.G = np.array([])
        self.fig,self.ax = plt.subplots(1,1,figsize=(9,5),dpi=100)
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel('Amplitude (dB)')
        self.ax.grid()
        self.ax.set_xlim([0,500])
        self.ax.set_ylim([-50,50])
        self.line, = self.ax.plot([],[],'x',markeredgewidth =2,label='stepped sine')
        self.line.axes.set_autoscaley_on(True)

        self.buttons[0].on_click(self.measure)
        self.buttons[1].on_click(self.undo)
        self.buttons[2].on_click(self.save)
        self.buttons[3].on_click(self.savefig)
        
        display(self.out)
        
    def measure(self,b):
        time_data = dvma.stream_snapshot(self.rec)
        freq_data = dvma.calculate_fft(time_data,window='hann')
        # ignore DC part of data - first 5 samples
        freq_data.freq_data[0:5,0] = 0*freq_data.freq_data[0:5,0]
        index = np.argmax(np.abs(freq_data.freq_data[:,0]))
        
        self.f = np.append(self.f,freq_data.freq_axis[index])
        self.G = np.append(self.G,freq_data.freq_data[index,1] / freq_data.freq_data[index,0])
            
        self.update_line()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        
        
    def undo(self,b):
        # the 'out' construction is to refresh the text output at each update 
        # to stop text building up in the widget display
        self.out.clear_output(wait=False)
        if len(self.f) > 0:
            self.f = np.delete(self.f,-1)
            self.G = np.delete(self.G,-1)
            self.update_line()
        else:
            with self.out:
                print('nothing to undo!')
            
    def save(self,b):
        self.out.clear_output(wait=False)
        with self.out:
            i_sort = np.argsort(self.f)
            ff = self.f[i_sort]
            GG = self.G[i_sort]
            tf_data = dvma.TfData(ff,GG,None,self.rec.settings,test_name='stepped_sine')
            d = dvma.DataSet(tf_data)
            d.save_data()
            
    def savefig(self,b):
        # the 'out' construction is to refresh the text output at each update 
        # to stop text building up in the widget display
        self.out.clear_output(wait=False)
        with self.out:
            dvma.save_fig(self.fig,figsize=(9,5))
        
    def update_line(self):
        i_sort = np.argsort(self.f)
        self.GdB = 20*np.log10(np.abs(self.G))
        self.line.set_xdata(self.f[i_sort])
        self.line.set_ydata(self.GdB[i_sort])
        if len(self.GdB)>0:
            self.line.axes.set_ylim(bottom=min(self.GdB)-3,top=max(self.GdB)+3)



def coupled_TF(Y1,Y2):
    d = dvma.DataSet()
    
    Y1.tf_data_list[0].tf_coherence=None
    Y2.tf_data_list[0].tf_coherence=None
    
    Y1d = Y1.tf_data_list[0].tf_data
    Y2d = Y2.tf_data_list[0].tf_data
    Yc = 1/(1/Y1d + 1/Y2d)
    f = Y1.tf_data_list[0].freq_axis
    settings = Y1.tf_data_list[0].settings
    
    tf_data_coupled = dvma.TfData(f,Yc,None,settings,id_link=[Y1.tf_data_list[0].id_link,Y2.tf_data_list[0].id_link],test_name = 'predicted')
    
    
    d.add_to_dataset(Y1.tf_data_list[0])
    d.add_to_dataset(Y2.tf_data_list[0])
    d.add_to_dataset(tf_data_coupled)
    
    return d




    