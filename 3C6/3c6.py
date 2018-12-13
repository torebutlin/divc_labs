words = ['Measure', 'Undo last', 'Save']
buttons = [widgets.Button(description=w) for w in words]
display(widgets.HBox(buttons))

f = np.array([])
G = np.array([])
fig,ax = plt.subplots(1,1,figsize=(9,5),dpi=100)
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('Amplitude (dB)')
ax.grid()
ax.set_xlim([0,500])
ax.set_ylim([-50,50])
line, = ax.plot([],[],'x',markeredgewidth =2,label='hi')
line.axes.set_autoscaley_on(True)

def measure(b):
    global f, G, tf_data
    time_data = dvma.stream_snapshot(osc.rec)
    freq_data = dvma.calculate_fft(time_data)
    
    index = np.argmax(np.abs(freq_data.freq_data[:,0]))
    
    f = np.append(f,freq_data.freq_axis[index])
    G = np.append(G,freq_data.freq_data[index,1] / freq_data.freq_data[index,0])
        
    update_line(f,G)
    
    
def undo(b):
    global f, G
    if len(f) > 0:
        f = np.delete(f,-1)
        G = np.delete(G,-1)
        update_line(f,G)
    else:
        print('nothing to undo!')
        
def done(b):
    global f, G
    tf_data = dvma.TfData(f,G,None,settings,test_name='stepped_sine')
    d = dvma.DataSet(tf_data)
    d.save_data()
    
def update_line(f,G):
    i_sort = np.argsort(f)
    GdB = 20*np.log10(np.abs(G))
    line.set_xdata(f[i_sort])
    line.set_ydata(GdB[i_sort])
    if len(GdB)>0:
        line.axes.set_ylim(bottom=min(GdB)-3,top=max(GdB)+3)
    
buttons[0].on_click(measure)
buttons[1].on_click(undo)
buttons[2].on_click(done)