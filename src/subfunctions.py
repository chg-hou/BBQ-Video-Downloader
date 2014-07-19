# -*- coding: utf-8 -*-
#!/usr/bin/env python
from PyQt4 import QtCore, QtGui
import sys,os
#import shlex,thread
#import subprocess
import urllib2
from base64 import b64encode
import xml.dom.minidom  
import re
import tempfile
try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)


VLC_PATH = 'vlc'
MENCODER_PATH = 'mencoder -oac lavc -ovc copy -idx -o '

class EmitSignalClass_void(QtCore.QObject):  
    sin1 = QtCore.pyqtSignal()     
    def __init__(self,parent=None,desSlot=None):
        super(EmitSignalClass_void,self).__init__(parent)   
        self.sin1.connect(desSlot)
    def disconnect_singal(self):
        self.sin1.disconnect(self.sin1Call)
    def emit_signal(self):
        self.sin1.emit()
        
class EmitSignalClass_QString(QtCore.QObject):  
    sin1 = QtCore.pyqtSignal('QString')     
    def __init__(self,parent=None,desSlot=None):
        super(EmitSignalClass_QString,self).__init__(parent)   
        self.sin1.connect(desSlot)
    def disconnect_singal(self):
        self.sin1.disconnect(self.sin1Call)
    def emit_signal(self,message):
        self.sin1.emit(message)
class EmitSignalClass_int(QtCore.QObject):   
    sin1 = QtCore.pyqtSignal(int)     
    def __init__(self,parent=None,desSlot=None):
        super(EmitSignalClass_int,self).__init__(parent)   
        self.sin1.connect(desSlot)
    def disconnect_singal(self):
        self.sin1.disconnect(self.sin1Call)
    def emit_signal(self,message):
        self.sin1.emit(message)
class EmitSignalClass_float(QtCore.QObject):   
    sin1 = QtCore.pyqtSignal(float)     
    def __init__(self,parent=None,desSlot=None):
        super(EmitSignalClass_float,self).__init__(parent)   
        self.sin1.connect(desSlot)
    def disconnect_singal(self):
        self.sin1.disconnect(self.sin1Call)
    def emit_signal(self,message):
        self.sin1.emit(message)
class EmitSignalClass_QL(QtCore.QObject):   
    sin1 = QtCore.pyqtSignal('QListWidgetItem')     
    def __init__(self,parent=None,desSlot=None):
        super(EmitSignalClass_QL,self).__init__(parent)   
        self.sin1.connect(desSlot)
    def disconnect_singal(self):
        self.sin1.disconnect(self.sin1Call)
    def emit_signal(self,message):
        self.sin1.emit(message)

      
def len_zh(data):
    temp = re.findall('[^a-zA-Z0-9.]+', data)
    count = 0
    for i in temp:
        count += len(i)
    return(count)

# def labelGUI(title,labels):
#     import Tkinter
#     def click_link(event, text,count):
#         print "you clicked '%s'" % text
#         #print  count
#         root.Count_return = count
#         root.quit()
#     root=Tkinter.Tk()
#     root.title(title)
#     root.Count_return = -100
#     link = Tkinter.Label(text=title, foreground="#ff0000")
#     link.pack()
#     for i,text in enumerate(labels):
#         if text.find('m3u8')>=0:
#             continue
#         link = Tkinter.Label(text=text, foreground="#0000ff",\
#                              cursor="hand2",anchor='w',width=22,justify="left",font="Wenquanyi\ Micro\ Hei\ Mono")
#         link.bind("<1>", lambda event, text=text,count=i: \
#                       click_link(event, text,count))
#         #link.grid(row=i*2+1, column=1)
#         link.pack()
#     root.mainloop()
#     try:
#         root.destroy()
#     except:
#         pass
#     return root.Count_return

class colorprint():
    HEADER = '\033[95m'
    ENDC = '\033[0m'
    BOLD = "\033[1m"
    
    OKGREEN = '\033[0;32;40m' #'\033[92m'
    OKBLUE = '\033[94m'
    WARNING = '\033[1;31;44m' #'\033[93m'
    FAIL = '\033[0;33;40m' #'\033[91m'
    
    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''
    
    def infog(self,msg):
        print self.OKGREEN + msg + self.ENDC
    
    def info(self, msg):
        print self.OKBLUE + msg + self.ENDC
    
    def warn( self,msg):
        print self.WARNING + msg + self.ENDC
    
    def err(self, msg):
        print self.FAIL + msg + self.ENDC
   
def exit_handler(signum,frame):
    global IS_EXIT_FLAG
    IS_EXIT_FLAG = True
    print "receive a signal %d, is_exit = %d"%(signum, IS_EXIT_FLAG) , 'Delete tmp files? (10s)',
    global filename_arr
    del_cache_FLAG = 'D'
    while del_cache_FLAG<>'y' and del_cache_FLAG<>'Y' and del_cache_FLAG<>'n' and del_cache_FLAG<>'N' and del_cache_FLAG<>None :
        del_cache_FLAG = raw_input_with_timeout( 3.0)
        print del_cache_FLAG
        if del_cache_FLAG=='y' or del_cache_FLAG=='Y' or del_cache_FLAG==None:
            for filename in filename_arr:
                try:
                    print 'Removing '+filename
                    os.remove(filename)
                except:
                    pass
            print 'receive a signal... All temp files deleted!'
        
    print 'receive a signal... Will exit in 1s...'
    sys.exit()
    

def raw_input_with_timeout(timeout=3.0):
    #print prompt,    
    astring = None
    import sys, select
    i, o, e = select.select( [sys.stdin], [], [], timeout )
    #print i,o,e
    if (i):
        astring = sys.stdin.readline().strip()
    else:
        print "No input is given."
    return astring

def Load_VIDEO_ADDRESS_from_file(fileName):
    #filename = ui.VIDEO_ADDRESS
    if os.path.isfile(fileName):
        hfile = file(fileName,'r')
    else:
        hfile = file(fileName.encode ("utf-8", 'ignore'),'r')
    fcontent = hfile.read()
    return fcontent
def Re_CHECK_URL(url):
    ma = re.match('^(http(s?)://).*$',url)
    if ma == None:          #这是string中不含有URL的情况
        return False,url
    else:
        return True,url
def Load_URL_info(ui):
        
    
    ui.comboBox_quality.clear()
    signal_temp = EmitSignalClass_QString(desSlot=ui.statusBar().showMessage)
    signal_temp.emit_signal(_translate("MainWindow", 'Loading quality...', None))
    #ui.statusBar().showMessage('Loading quality...')

    Query_URL = 'http://api.flvxz.com/url/{0}'
    videourl = ui.VIDEO_ADDRESS
    print videourl
    try:
        url = Query_URL.format(b64encode(videourl))
    except :
        pass
        
    xml_text = urllib2.urlopen(url).read()
    doc = xml.dom.minidom.parseString(xml_text)
    video_arr = doc.getElementsByTagName('video')
    
    ui.video_arr=video_arr
    index_a = 0
    for video_node in video_arr:
        title = video_node.getElementsByTagName('title')[0].firstChild.data
        quality = video_node.getElementsByTagName('quality')[0].firstChild.data
        file_type = video_node.getElementsByTagName('ftype')[0].firstChild.data
        #temp_msg = str(index_a+1)+'. '+title+' .'+file_type+'\t'+quality
        #temp_msg = str(index_a+1)+'. '+file_type.ljust(6)+quality.ljust(12-len_zh(quality))
        if file_type.find('m3u8')<0:
            ui.comboBox_quality.addItem(quality+'('+file_type+')', userData=index_a)
        index_a +=1
        
    for index in range(ui.comboBox_quality.count()):
        if ui.comboBox_quality.itemText(index).indexOf(QtCore.QString(unicode(ui.QUALITY,'utf','ignore')))>=0:
            ui.comboBox_quality.setCurrentIndex(index)
            break
        
    signal_temp.emit_signal(_translate("MainWindow", "OK", None))
    
    signal_temp2 = EmitSignalClass_QString(desSlot=ui.lineEdit_title.setText)
    signal_temp2.emit_signal(title)
    
    
     
def Ui_update_comboBox_quality(ui):
    pass

def LoadLanguageSetting():
    import ConfigParser 
    cf = ConfigParser.ConfigParser()
    if os.path.isfile('setting.ini'):
        cf.read('setting.ini')
        if cf.has_option('main',"language"):
            return cf.get('main',"language")
        else:
            return None
def LoadDefaultSetting(ui):
    import ConfigParser 
    cf = ConfigParser.ConfigParser()
    #global SAVINGPATH,MINPIECESIZE,MAXCONCOUNT,QUALITY
    if not os.path.isfile('setting.ini'):
        
        SAVINGPATH=tempfile.gettempdir()
        MINPIECESIZE = 1/4.0  #131072
        MAXCONCOUNT = 20
        QUALITY = '标清'
        CLEANTEMPFILES = 2
        
        def LoadWindowsVLCpath():
            '''
            Under windows ONLY
            '''
            try:
                import _winreg
                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,r"SOFTWARE\VideoLAN\VLC")
                
                value, type = _winreg.QueryValueEx(key, "")
                return value
            except:
                pass
                return 'vlc'
        import platform
        sysstr = platform.system()
        if(sysstr =="Windows"):
            VLC_PATH = LoadWindowsVLCpath()
        elif(sysstr == "Linux"):
            VLC_PATH = 'vlc'
        else:
            VLC_PATH = 'vlc'
        
        MENCODER_PATH = 'mencoder'
        # key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Explorer")
        # 
        #  #获取该键的所有键值，因为没有方法可以获取键值的个数，所以只能用这种方法进行遍历
        #  try:
        #     i = 0
        # while1:
        # #EnumValue方法用来枚举键值，EnumKey用来枚举子键
        #          name, value, type = _winreg.EnumValue(key, i)
        # print repr(name),
        #         i +=1
        #  except WindowsError:
        # print
        # 
        #  #如果知道键的名称，也可以直接取值
        #  value, type = _winreg.QueryValueEx(key, "EnableAutoTray")
 
        cf.add_section('main')
        cf.set("main", "path", SAVINGPATH)
        cf.set("main", "MINPIECESIZE", MINPIECESIZE)
        cf.set("main", "MAXCONCOUNT", MAXCONCOUNT)
        cf.set('main',"QUALITY",QUALITY)
        cf.set('main','CLEANTEMPFILES',CLEANTEMPFILES)
        cf.set('main','VLC_PATH',VLC_PATH)
        cf.set('main','MENCODER_PATH',MENCODER_PATH)
        cf.write(open('setting.ini', "w"))
        
        ui.SAVINGPATH = SAVINGPATH
        ui.MINPIECESIZE = MINPIECESIZE
        ui.MAXCONCOUNT = MAXCONCOUNT
        ui.QUALITY = QUALITY
        ui.CLEANTEMPFILES = CLEANTEMPFILES
        ui.VLC_PATH = VLC_PATH
        return
    cf.read('setting.ini')
    SAVINGPATH = cf.get("main", "path")
    if not os.path.exists(SAVINGPATH):
        try:
            os.makedirs(SAVINGPATH)
        except:
            SAVINGPATH=tempfile.gettempdir()
    try:
        MINPIECESIZE=cf.getfloat("main", "MINPIECESIZE")
    except:
        MINPIECESIZE = 1/4.0
    try:   
        MAXCONCOUNT=cf.getint("main", "MAXCONCOUNT" )
    except:
        MAXCONCOUNT = 20
    try:
        QUALITY = cf.get('main',"QUALITY")
    except:
        QUALITY = '标清' #.decode('utf-8','ignore')
    try:
        CLEANTEMPFILES = cf.getint('main','CLEANTEMPFILES')
    except:
        CLEANTEMPFILES = 2
    try:
        VLC_PATH = cf.get('main',"VLC_PATH")
    except:
        VLC_PATH = 'vlc'
    try:
        MENCODER_PATH = cf.get('main',"MENCODER_PATH")
    except:
        MENCODER_PATH = 'mencoder'
    cf.set("main", "path", SAVINGPATH)
    cf.set("main", "MINPIECESIZE", MINPIECESIZE)
    cf.set("main", "MAXCONCOUNT", MAXCONCOUNT)
    cf.set('main',"QUALITY",QUALITY)
    cf.set('main','CLEANTEMPFILES',CLEANTEMPFILES)
    cf.set('main','VLC_PATH',VLC_PATH)
    cf.set('main','MENCODER_PATH',MENCODER_PATH)
    cf.write(open('setting.ini', "w"))
    
    ui.SAVINGPATH = SAVINGPATH
    ui.MINPIECESIZE = MINPIECESIZE
    ui.MAXCONCOUNT = MAXCONCOUNT
    ui.QUALITY = QUALITY
    ui.CLEANTEMPFILES = CLEANTEMPFILES
    ui.VLC_PATH = VLC_PATH
    ui.MENCODER_PATH = MENCODER_PATH
    
    signal_temp3 = EmitSignalClass_int(desSlot=ui.spinBox_segments.setValue)   
    signal_temp3.emit_signal(MAXCONCOUNT)
    
    signal_temp2 = EmitSignalClass_float(desSlot=ui.doubleSpinBox_segsize.setValue)
    signal_temp2.emit_signal(MINPIECESIZE)
   
    signal_temp4 = EmitSignalClass_int(desSlot=ui.checkBox_cleantmp.setCheckState)
    signal_temp4.emit_signal(CLEANTEMPFILES)
    
# def AddFileList(ui):
#     singal_temp4 = EmitSignalClass_QString(desSlot=ui.listWidget.addItem)
#     singal_temp4.emit_signal('cccccc')
    