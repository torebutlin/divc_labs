import pydvma as dvma
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.rcParams.update({'font.size': 12,'font.family':'serif'})
import ipywidgets as widgets
from ipywidgets import Layout, Output
from IPython.display import display


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
        freq_data = dvma.calculate_fft(time_data,window='hanning')
        
        index = np.argmax(np.abs(freq_data.freq_data[:,0]))
        
        self.f = np.append(self.f,freq_data.freq_axis[index])
        self.G = np.append(self.G,freq_data.freq_data[index,1] / freq_data.freq_data[index,0])
            
        self.update_line()
        
        
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



class test_num_frames():
    def __init__(self,data):
        
        self.data = data
        self.fig,self.ax = plt.subplots(1,1,figsize=(9,5),dpi=100)
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel('Amplitude (dB)')
        self.ax.grid()
        self.ax.set_xlim([0,500])
        
        words = ['Measure', 'Undo last', 'Save']
        self.buttons = [widgets.Button(description=w) for w in words]
        display(widgets.HBox(self.buttons))
        
        for n in range(29):
            tf_data = dvma.calculate_tf(self.data, N_frames=n+1)
            freq_lim = self.ax.get_xlim()
            s0 = tf_data.freq_axis >= freq_lim[0]
            s1 = tf_data.freq_axis <= freq_lim[1]
            selection = s0 & s1
            GdB = 20*np.log10(np.abs(tf_data.tf_data[selection,:]))

            if n is 0:
                bottom = min(GdB)
                top = max(GdB)
            else:
                bottom = min(bottom,min(GdB))
                top = max(top,min(top))

        self.ax.set_ylim([bottom-3, top+3])
        
        self.line1, = self.ax.plot([],[],'-',linewidth =2,label='Transfer Function')
        self.line2, = self.ax.plot([],[],'--',linewidth =1,label='Coherence')
        self.ax.legend(loc='upper right')
 
        widgets.interact(self.update_tf,N_frames=(1,30),layout=widgets.Layout(width='100%'))
        
    def update_tf(self,N_frames=1):
        
        self.tf_data = dvma.calculate_tf(self.data, N_frames=N_frames)
        self.line1.set_xdata(self.tf_data.freq_axis)
        self.line2.set_xdata(self.tf_data.freq_axis)
        GdB = 20*np.log10(np.abs(self.tf_data.tf_data))
        CdB = 20*np.log10(np.abs(self.tf_data.tf_coherence))
        self.line1.set_ydata(GdB)
        self.line2.set_ydata(CdB)
        #self.ax.set_autoscaley_on(True)
        #self.ax.set_ylim(bottom=min(GdB)-3,top=max(GdB)+3)
        print('N_frames = {}. \nFrame length = {:.2f} seconds.'.format(N_frames,self.data.settings.stored_time/N_frames))
            
      
        
class log_tf_with_average():
    def __init__(self,settings):
        self.settings = settings
        self.dataset = dvma.DataSet()
        
        words = ['Measure', 'View TF', 'Undo last', 'Save']
        self.buttons = [widgets.Button(description=w) for w in words]
        display(widgets.HBox(self.buttons))
        
        self.buttons[0].on_click(self.measure)
        self.buttons[1].on_click(self.view_TF)
        self.buttons[2].on_click(self.undo)   
        self.buttons[3].on_click(self.save)
    
    def measure(self,b):
        d = dvma.log_data(self.settings)
        self.dataset.add_to_dataset(d.time_data_list)
        self.p=dvma.PlotData(d.time_data_list[-1])
        
    def view_TF(self,b):
        tf_data = dvma.calculate_tf_averaged(self.dataset.time_data_list)
        self.p=dvma.PlotData(tf_data)
        
    def undo(self,b):
        self.dataset.remove_last_data_item('TimeData')
        if len(self.dataset.time_data_list) > 0:
            self.p=dvma.PlotData(self.dataset.time_data_list[-1])
        
    def save(self,b):
        self.dataset.calculate_fft_set()
        self.dataset.calculate_tf_averaged(window=None)
        self.dataset.save_data()
    
    