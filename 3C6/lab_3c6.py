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




    