import pydvma as dvma
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.rcParams.update({'font.size': 12,'font.family':'serif'})
import ipywidgets as widgets
from IPython.display import display



class measure_stepped_sine():
    def __init__(self,rec):
        
        words = ['Measure', 'Undo last', 'Save']
        self.buttons = [widgets.Button(description=w) for w in words]
        display(widgets.HBox(self.buttons))
        
        self.rec = rec
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
        
    def measure(self,b):
        time_data = dvma.stream_snapshot(self.rec)
        freq_data = dvma.calculate_fft(time_data)
        
        index = np.argmax(np.abs(freq_data.freq_data[:,0]))
        
        self.f = np.append(self.f,freq_data.freq_axis[index])
        self.G = np.append(self.G,freq_data.freq_data[index,1] / freq_data.freq_data[index,0])
            
        self.update_line()
        
        
    def undo(self,b):
        if len(self.f) > 0:
            self.f = np.delete(self.f,-1)
            self.G = np.delete(self.G,-1)
            self.update_line()
        else:
            print('nothing to undo!')
            
    def save(self,b):
        tf_data = dvma.TfData(self.f,self.G,None,self.rec.settings,test_name='stepped_sine')
        d = dvma.DataSet(tf_data)
        d.save_data()
        
    def update_line(self):
        i_sort = np.argsort(self.f)
        self.GdB = 20*np.log10(np.abs(self.G))
        self.line.set_xdata(self.f[i_sort])
        self.line.set_ydata(self.GdB[i_sort])
        if len(self.GdB)>0:
            self.line.axes.set_ylim(bottom=min(self.GdB)-3,top=max(self.GdB)+3)



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
    
    