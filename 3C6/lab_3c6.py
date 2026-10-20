import pydvma as dvma
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.rcParams.update({'font.size': 12,'font.family':'serif'})
import ipywidgets as widgets
from ipywidgets import Layout, Output
from IPython import get_ipython
from IPython.display import display
from tornado.ioloop import PeriodicCallback
import threading
import glob
import os


def _show_figures_from_main_thread_only():
    # With '%matplotlib widget', ipympl shows each new figure from IPython's
    # post_execute event, which the comm package also fires after every
    # widget message. Current Jupyter (Notebook 7.6 / JupyterLab 4.6 with
    # ipykernel 7, as on the lab PCs) handles widget messages on a second
    # kernel thread, a "subshell", while a cell is still running on the
    # main one. A figure shown from there belongs to that widget message
    # rather than to the cell, so the browser drops it: plots go missing at
    # random, more often the longer the cell takes. Only show figures from
    # the main thread, i.e. when a cell finishes, as before subshells.
    ip = get_ipython()
    if ip is None:
        return
    try:
        import ipympl.backend_nbagg as nbagg
    except ImportError:
        return
    if getattr(nbagg, '_main_thread_flush', None) is not None:
        return
    flush = nbagg.flush_figures

    def main_thread_flush():
        if threading.current_thread() is threading.main_thread():
            flush()

    try:
        ip.events.unregister('post_execute', flush)
    except ValueError:
        pass
    ip.events.register('post_execute', main_thread_flush)
    nbagg._main_thread_flush = main_thread_flush


_show_figures_from_main_thread_only()


# The stepped-sine widget whose level meters are running: a new one stops
# the old one's, so re-running the cell never leaves two going.
_active_meters = None

# bottom of the level meters, in dB relative to the input full scale
METER_FLOOR_DB = -60


def full_scale(settings):
    """The input full scale in volts: the NI range, else the soundcard's."""
    if settings.device_driver == 'nidaq':
        return float(settings.VmaxNI)
    return float(getattr(settings, 'VmaxSC', 1.0) or 1.0)


def interactive_plots():
    """True when '%matplotlib widget' (ipympl) is on, so figures can update."""
    return 'ipympl' in matplotlib.get_backend() or matplotlib.get_backend() == 'widget'


class measure_stepped_sine():
    """Stepped-sine admittance measurement, with live input level meters.

        logger1 = lab_3c6.measure_stepped_sine(settings)

    A thin bar for each channel shows its peak level over the last
    second or so, in dB relative to the input full scale, and turns red
    with a CLIP warning when the signal reaches the input limit, so the
    levels can be checked before measuring. 'Measure' takes the latest
    settings.viewed_time seconds of the stream, finds the sine
    frequency from the FFT of channel 0 and plots the channel 1 /
    channel 0 admittance there.

    The pydvma logger (dvma.launch) uses the same acquisition hardware:
    once it has taken the stream over, the meters stop and 'Measure'
    refuses, both saying so, and re-running this cell takes it back.
    """

    def __init__(self,settings):
        global _active_meters

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
        # pydvma has no save dialog: 'Save Data' and 'Save Fig' use this
        # name, in the notebook's folder
        self.filename = widgets.Text(value='stepped_sine',
                                     description='file name:',
                                     layout=Layout(width='50%'))
        display(self.filename)

        if not interactive_plots():
            print("WARNING: interactive plots are off, so the plot below won't update.\n"
                  "Run the '%matplotlib widget' cell above, then this cell again. If that\n"
                  "cell gives an error, ipympl is missing on this PC: tell a demonstrator.")

        try:
            dvma.start_stream(settings)
            self.rec = dvma.streams.REC
            self.rec_settings = self.rec.settings
        except:
            self.rec = None
            print('Data stream not initialised.')
            print('Possible reasons: pyaudio or PyDAQmx not installed, or acquisition hardware not connected.')
            print('Please note that it won''t be possible to log data.')

        # level meters: plain widgets, not a plot, updated by a timer on the
        # notebook's own event loop. Button clicks and plot redraws may run
        # on a second kernel thread (see above), so keeping matplotlib out
        # of the timer means the figure is only ever touched from one place.
        self.meters = []
        rows = []
        for k in range(settings.channels):
            bar = widgets.FloatProgress(value=METER_FLOOR_DB, min=METER_FLOOR_DB, max=0,
                                        description='ch {}'.format(k),
                                        layout=Layout(width='50%'))
            text = widgets.HTML(layout=Layout(width='45%'))
            self.meters.append((bar, text))
            rows.append(widgets.HBox([bar, text]))
        display(widgets.VBox(rows))
        self.timer = PeriodicCallback(self.update_meters, 200)
        if _active_meters is not None:
            _active_meters.stop_meters()
        _active_meters = self
        if self.rec is not None:
            self.timer.start()

        display(self.out)

        # made with interactive mode off and displayed here, rather than
        # left for ipympl to show when the cell ends (see above). Without
        # ipympl, the inline backend shows it when the cell ends regardless.
        self.f = np.array([])
        self.G = np.array([])
        with plt.ioff():
            self.fig,self.ax = plt.subplots(1,1,figsize=(9,5),dpi=100)
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel('Amplitude (dB)')
        self.ax.grid()
        self.ax.set_xlim([0,500])
        self.ax.set_ylim([-50,50])
        self.line, = self.ax.plot([],[],'x',markeredgewidth =2,label='stepped sine')
        self.line.axes.set_autoscaley_on(True)
        if interactive_plots():
            display(self.fig.canvas)

        self.buttons[0].on_click(self.measure)
        self.buttons[1].on_click(self.undo)
        self.buttons[2].on_click(self.save)
        self.buttons[3].on_click(self.savefig)

    TAKEN_OVER = ('The pydvma logger is now using the acquisition hardware. '
                  'To use this widget again, re-run its cell.')

    def stream_problem(self):
        # Why the widget can't read its stream, or None if it can.
        # stream_snapshot always reads the newest stream (dvma.streams.REC),
        # so once the logger has opened its own, this widget would be
        # reading the logger's data. On NI, start_stream restarts the same
        # recorder object with the new settings, so check those as well.
        if self.rec is None:
            return 'No data stream: see the message above the plot.'
        if dvma.streams.REC is not self.rec or self.rec.settings is not self.rec_settings:
            return self.TAKEN_OVER
        return None

    def stop_meters(self, message=None):
        self.timer.stop()
        for bar, text in self.meters:
            bar.value = METER_FLOOR_DB
            bar.bar_style = ''
            text.value = '<span style="color:gray">stopped</span>'
        if message:
            self.out.clear_output(wait=False)
            with self.out:
                print(message)

    def update_meters(self):
        problem = self.stream_problem()
        if problem:
            self.stop_meters('Level meters stopped. ' + problem)
            return
        try:
            y = np.asarray(dvma.stream_snapshot(self.rec).time_data)
        except Exception as e:
            self.stop_meters('Level meters stopped: {}'.format(e))
            return
        vmax = full_scale(self.rec.settings)
        for k, (bar, text) in enumerate(self.meters):
            peak = float(np.max(np.abs(y[:, k]))) if len(y) else 0.0
            db = 20 * np.log10(max(peak, 1e-9) / vmax)
            clipped = peak >= 0.95 * vmax
            bar.value = min(max(db, METER_FLOOR_DB), 0)
            bar.bar_style = 'danger' if clipped else 'success'
            label = '{:.3f} V peak ({:.0f} dB)'.format(peak, db)
            if clipped:
                label = ('<b style="color:#d62728">{} CLIP: turn the level down</b>'
                         .format(label))
            text.value = label

    def measure(self,b):
        problem = self.stream_problem()
        if problem:
            self.out.clear_output(wait=False)
            with self.out:
                print(problem)
            return
        try:
            time_data = dvma.stream_snapshot(self.rec)
        except Exception as e:
            self.out.clear_output(wait=False)
            with self.out:
                print('Measurement failed: {}'.format(e))
            return
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
            
    def new_name(self, extensions):
        # The file name from the box, without extension, or None if it is
        # blank or already used: the overwrite question can't be asked
        # from a button, so an existing file is never replaced.
        name = os.path.splitext(self.filename.value.strip())[0]
        if not name:
            print('Type a file name in the box first.')
            return None
        taken = [name + ext for ext in extensions if os.path.exists(name + ext)]
        if taken:
            print('{} already exists: type a new file name and try again.'.format(taken[0]))
            return None
        return name

    def save(self,b):
        self.out.clear_output(wait=False)
        with self.out:
            name = self.new_name(['.dvma'])
            if name is None:
                return
            i_sort = np.argsort(self.f)
            ff = self.f[i_sort]
            GG = self.G[i_sort]
            settings = self.rec.settings if self.rec is not None else self.settings
            tf_data = dvma.TfData(ff,GG,None,settings,test_name='stepped_sine')
            d = dvma.DataSet(tf_data)
            d.save_data(name)
            
    def savefig(self,b):
        # the 'out' construction is to refresh the text output at each update 
        # to stop text building up in the widget display
        self.out.clear_output(wait=False)
        with self.out:
            name = self.new_name(['.png', '.pdf'])
            if name is None:
                return
            dvma.save_fig(self.fig,figsize=(9,5),filename=name)
        
    def update_line(self):
        i_sort = np.argsort(self.f)
        self.GdB = 20*np.log10(np.abs(self.G))
        self.line.set_xdata(self.f[i_sort])
        self.line.set_ydata(self.GdB[i_sort])
        if len(self.GdB)>0:
            self.line.axes.set_ylim(bottom=min(self.GdB)-3,top=max(self.GdB)+3)



class choose_file():
    """Choose a saved data file from this notebook's folder.

        picker = lab_3c6.choose_file()   # pick the file in the list
        data = picker.load()             # then, in the next cell

    pydvma no longer opens a file dialog, so this replaces the old
    dvma.load_data() dialog. The list shows the .dvma files in this
    folder, newest first, leaving out the logger's own autosave.dvma
    backup; 'Refresh' re-reads the folder after saving more files.
    """

    # the web logger's session backup, rewritten after every change
    AUTOSAVE = 'autosave.dvma'

    def __init__(self, pattern='*.dvma'):
        self.pattern = pattern
        self.dropdown = widgets.Dropdown(description='file:',
                                         layout=Layout(width='60%'))
        self.button = widgets.Button(description='Refresh',
                                     layout=Layout(width='15%'))
        self.button.on_click(lambda b: self.refresh())
        self.refresh()
        display(widgets.HBox([self.dropdown, self.button]))

    def refresh(self):
        chosen = self.dropdown.value
        files = sorted((f for f in glob.glob(self.pattern)
                        if os.path.basename(f) != self.AUTOSAVE),
                       key=os.path.getmtime, reverse=True)
        self.dropdown.options = files
        self.dropdown.value = chosen if chosen in files else None

    def load(self):
        if not self.dropdown.value:
            raise NoFileChosen('No file chosen: pick one in the list above '
                               '(press Refresh if it is missing), then run '
                               'this cell again.')
        return dvma.load_data(self.dropdown.value)


class NoFileChosen(Exception):
    """choose_file.load() with nothing picked. It stops the cell there, so
    the next line never fails on None, and IPython shows just the message
    (via _render_traceback_), not a traceback."""

    def _render_traceback_(self):
        return [str(self)]



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




    