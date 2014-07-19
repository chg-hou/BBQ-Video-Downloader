# -*- coding: utf8 -*-
#!/usr/bin/env python
#pyrcc4 -o iconfile_rc.py iconfile.qrc

# TODO: Fix bug, load  and load again
# TODO: whether can save and load setting under windows
import sys  
reload(sys)  
sys.setdefaultencoding('utf8')
    
from PyQt4 import QtCore, QtGui

from Ui_PVD_gui import *
from subfunction_2 import *

import sys,shlex,subprocess,os

import thread
import subprocess
import urllib2
from base64 import b64encode
import xml,xml.dom.minidom  
from subfunctions import *


from PyQt4.QtGui import QMainWindow
from PyQt4.QtCore import pyqtSignature
from Ui_PVD_gui import Ui_MainWindow

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s
try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

IS_EXIT_FLAG = False
DEFAULT_STYLE = """
QProgressBar{
    border: 2px solid grey;
    border-radius: 5px;
    text-align: center
}
QProgressBar::chunk {
    background-color: lightblue;
    width: 10px;
    margin: 1px;
}
"""

COMPLETED_STYLE = """
QProgressBar{
    border: 2px solid grey;
    border-radius: 5px;
    text-align: center
}
QProgressBar::chunk {
    background-color: #CD96CD;
    width: 10px;
    margin: 1px;
}
"""
class DragDropLabel(QtGui.QLabel):
    def __init__(self, parent = None,ui=None):
        QtGui.QLabel.__init__(self, parent)
        
        self.setAcceptDrops(True)
        self.setFrameShape(QtGui.QFrame.Box)
        self.setFrameShadow(QtGui.QFrame.Raised)
        self.setLineWidth(2)
        self.setMidLineWidth(2)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMargin(3)
        self.setObjectName(_fromUtf8("label_drop_url"))
        self.reset_label_text()
        self.ui = ui
    def dragEnterEvent(self, e):
        print 'drag enter'
#         print e.mimeData().hasFormat('text/plain')
#         print e.mimeData().text()
#         print e.mimeData().html()
#         print e.mimeData().urls()
        if e.mimeData().hasFormat('text/plain'):
            e.accept()
            self.setText(_translate("MainWindow", "open URL?\n", None)+e.mimeData().text()) 
            self.setAlignment(QtCore.Qt.AlignLeft)
        else:
            e.ignore() 
    def dragLeaveEvent(self, e):
        print 'drag leave'
        self.reset_label_text()
        self.setAlignment(QtCore.Qt.AlignCenter)
    def dropEvent(self, e):
        self.reset_label_text()
        self.setAlignment(QtCore.Qt.AlignCenter)
        print 'drop'
#         return
        #self.setText(e.mimeData().text())
        OK , self.ui.VIDEO_ADDRESS = Re_CHECK_URL( e.mimeData().text())
        self.ui.VIDEO_ADDRESS = self.ui.VIDEO_ADDRESS.toUtf8()
        if OK:
            #Load_URL_info(self.ui)
            self.ui.on_pushButton_stop_pressed()
            self.ui.AutoPlaySLOT()
#             if ui.Load_URL_info ()>=0: 
#                 self.ui.on_pushButton_start_pressed()
        else:
            print 'Wrong URL!'            
            self.ui.statusBar().showMessage(_translate("MainWindow", 'Wrong URL!', None))
    def reset_label_text(self):
        self.setText(_translate("MainWindow", "Drop URL here", None))
        
        
class XProgressBar(QtGui.QProgressBar):
    def __init__(self, parent = None):
        QtGui.QProgressBar.__init__(self, parent)
        self.setStyleSheet(DEFAULT_STYLE)
        self.step = 0

    def setValue(self, value):
        QtGui.QProgressBar.setValue(self, value)
        if value == self.maximum():
            self.setStyleSheet(COMPLETED_STYLE)

# class FileProgress(object):
#     index = 0
#     progress = ''
#     percentage = 0
#     time_spent = 0.0
#     time_remained = 999999.0
#     speed = 0.0
#     disabled_FLAG = False

class Ui_download_thread_CLASS(threading.Thread):
    def __init__(self, signalEvent,ui):
        threading.Thread.__init__(self)
        self.signalEvent = signalEvent
        self.fd = FastDownload(ui,signalEvent)
        self.ui=ui   
    def run(self):
        ui = self.ui
        for index,url in enumerate(ui.url_arr):   
            #                url,file_index,filename,path
            if ui.file_progress[index].disabled_FLAG :
                print index,'disabled, skip to nex one'
                continue
            if ui.file_progress[index].percentage == 100:
                print index,'finished, skip to next one'
                continue
            print 'fd execute index       =',index
            while self.fd.execute(url,index,ui.filename_arr[index],ui.SAVINGPATH)<0:
                print 'Retry %s in 15s' % ui.filename_arr[index]
                print url
                time.sleep(15)
            if self.signalEvent.isSet():
                break
     
def ui_download_thread(ui):
    fd = FastDownload(ui) 
    for index,url in enumerate(ui.url_arr):   
        #                url,file_index,filename,path
        if ui.file_progress[index].percentage == 100:
            print index,'finished, skip to next one'
            continue
        print 'fd execute index       =',index
        while fd.execute(url,index,ui.filename_arr[index],ui.SAVINGPATH)<0:
            print 'Retry %s in 15s' % ui.filename_arr[index]
            time.sleep(15)
        if ui.IS_EXIT_FLAG:
            break

class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Class documentation goes here.
    """
    SAVINGPATH=tempfile.gettempdir()
    MINPIECESIZE = 1/4.0  #131072
    MAXCONCOUNT = 20
    QUALITY = '标清'
    CLEANTEMPFILES = 2
    VIDEO_ADDRESS = ''
    downloadthread = None
    VLC_PATH = 'vlc' 
    MENCODER_PATH = 'mencoder'
    singalEvent = threading.Event()
    LANGUAGE = False
    
    def __init__(self, parent = None):
        """
        Constructor
        """
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        
        self.tableWidget.setColumnWidth(0,320)
        self.tableWidget.setColumnWidth(1,60)
        self.tableWidget.setColumnWidth(2,60)
        #self.tableWidget.setColumnWidth(3,200)
        header = self.tableWidget.horizontalHeader()
        header.setStretchLastSection(True)
        
        label_parent = self.label_drop_url.parent()
        qrect = self.label_drop_url.geometry()
        #self.removeWidget(self.label_drop_url)
        self.label_drop_url.deleteLater()
        self.label_drop_url = DragDropLabel(parent = label_parent,ui = self)
        self.label_drop_url.setGeometry(qrect)
        self.horizontalLayout_10.addWidget(self.label_drop_url)

        self.listWidget_process.setViewMode(QtGui.QListWidget.IconMode)
        self.listWidget_process.setIconSize(QtCore.QSize(20,20))
        self.listWidget_process.setGridSize (QtCore.QSize(20,20))
        self.listWidget_process.setDragDropMode(QtGui.QAbstractItemView.NoDragDrop)
        self.listWidget_process.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
    def update_file_progress(self,file_progress):
        index = file_progress.index
        self.file_progress[index]=file_progress
        self.update_progress_gui(index)
    def update_progress_gui(self,index):
        #print 'progress bar index', index
        self.progressbar_LIST[index].setValue(self.file_progress[index].percentage)
        
        #print '@@@@@@@@@@@@@@@@@@@@@ current row',self.tableWidget.currentRow()
        #print '@@@@@@@@@@@@@@@@@@@@@ index', index
        if self.file_progress[index].percentage<100:
            
            self.statusBar().showMessage(_translate("MainWindow", 'Downloading speed:', None) +((' %.2f KB/s') % self.file_progress[index].speed))
        else:
            self.statusBar().showMessage(_translate("MainWindow", 'Ready.', None))
            
        self.lcdNumber.display( int( self.file_progress[index].time_spent))
        self.lcdNumber_2.display(int(self.file_progress[index].time_remained))
        if True or index==self.tableWidget.currentRow():

            self.listWidget_process.clear()
            for char_item in self.file_progress[index].progress:
                if char_item == '+':
                    self.listWidget_process.addItem(QtGui.QListWidgetItem(QtGui.QIcon(":/icon/downloading.png"),''))
                elif char_item == '-':
                    self.listWidget_process.addItem(QtGui.QListWidgetItem(QtGui.QIcon(":/icon/empty.png"),''))
                else:
                    self.listWidget_process.addItem(QtGui.QListWidgetItem(QtGui.QIcon(":/icon/green.png"),''))
            
    @pyqtSignature("")
    def on_pushButton_start_pressed(self):
        """
        Slot documentation goes here.
        """
        self.statusBar().showMessage(_translate("MainWindow", 'Fetching video info...', None))
        print 'Fetching video info...'
        combox_index = self.comboBox_quality.currentIndex()
        if combox_index<0:
            combox_index = 0
        index , OK = self.comboBox_quality.itemData(combox_index).toInt()
        if not OK:
            index = 0
        video = self.video_arr[index]
        
        self.url_arr=[]  
        for url in video.getElementsByTagName('furl'):   
            self.url_arr.append(url.firstChild.data)
                   
        size_arr=[]
        for item_temp in  video.getElementsByTagName('size'):
            item_data = item_temp.firstChild.data
            if (item_data.find('MB'))>0:
                size_arr.append(item_data)
        self.size_arr=size_arr
        
        time_arr=[]
        for item_temp in  video.getElementsByTagName('time'):
            time_arr.append(item_temp.firstChild.data)
        self.time_arr=time_arr
        
        self.file_type = video.getElementsByTagName('ftype')[0].firstChild.data
        self.title = video.getElementsByTagName('title')[0].firstChild.data
        self.QUALITY = video.getElementsByTagName('quality')[0].firstChild.data
        
        index_a = 0
        self.filename_arr =[]
        self.file_progress=[]
        for i in range(len(self.url_arr)):
            self.file_progress.append(FileProgress())
        for url in self.url_arr:
            filename = unicode("%s [%02d].%s" % (self.title , index_a+1, self.file_type))
            #print filename
            #filename = filename.decode('utf-8').encode('utf-8') 
            #print filename
            self.filename_arr.append(filename)
            hfile = file(os.path.join(self.SAVINGPATH,filename), 'wb') #.decode('sys.getfilesystemencoding()')
            hfile.close()
            index_a += 1
        print self.title
        print self.file_type
        print self.QUALITY
        
        self.tableWidget.clearContents()
        self.tableWidget.setRowCount(len(ui.filename_arr))
        self.progressbar_LIST=[]
        for index,item in enumerate(self.filename_arr):
            self.tableWidget.setItem(index,0,QtGui.QTableWidgetItem(item))
            ProcessBar = XProgressBar(self.tableWidget)
            self.tableWidget.setCellWidget(index,3,ProcessBar)
            ProcessBar.setValue(0)
            self.progressbar_LIST.append(ProcessBar)
        for index,item in enumerate(self.size_arr):
            self.tableWidget.setItem(index,1,QtGui.QTableWidgetItem(item))
        for index,item in enumerate(self.time_arr):
            self.tableWidget.setItem(index,2,QtGui.QTableWidgetItem(item))
        #self.tableWidget.setColumnWidth()
        
        self.statusBar().showMessage('Info fetched.')
                                 
    @pyqtSignature("")
    def on_pushButton_start_2_pressed(self):
        self.statusBar().showMessage(_translate("MainWindow", 'Downloading started...', None))
        #self.IS_EXIT_FLAG = False
        #global IS_EXIT_FLAG 
        #IS_EXIT_FLAG = False
        #self.downloadthread = thread.start_new_thread(ui_download_thread, (self,))   
        self.singalEvent.clear()
        self.downloadthread  = Ui_download_thread_CLASS(self.singalEvent,self)
        self.downloadthread.setDaemon(True)
        self.downloadthread.start()
    @pyqtSignature("")
    def on_pushButton_stop_pressed(self):
        """
        Slot documentation goes here.
        """
        self.statusBar().showMessage(_translate("MainWindow", 'Stopping downloading...', None))
        
        self.singalEvent.set()
        if self.downloadthread!=None:
            try:
                self.downloadthread.join()
            except:
                pass
        #time.sleep(1)
        
        self.statusBar().showMessage(_translate("MainWindow", 'Downloading stopped.', None))
        self.singalEvent.clear()        
    @pyqtSignature("")
    def on_menu_Setting_aboutToShow(self):
        """
        Slot documentation goes here.
        """
        #print 'on_menu_Setting_aboutToShow'
        self.actionCurrent_folder.setText(_fromUtf8('Current: '+self.SAVINGPATH))
  
    @pyqtSignature("")
    def on_actionChange_folder_triggered(self):
        """
        Slot documentation goes here.
        """
        
        path  =  QtGui.QFileDialog.getExistingDirectory (parent = self, caption =_translate("MainWindow", 'Select destination folder', None) ,options = QtGui.QFileDialog.ShowDirsOnly)
        if path!=None and path!='':
            ui.SAVINGPATH=path
    @pyqtSignature("")
    def on_actionOpen_folder_triggered(self):
        """
        Slot documentation goes here.
        """
        def open_file(filename):
            if sys.platform == "win32":
                os.startfile(filename)
            else:
                opener ="open" if sys.platform == "darwin" else "xdg-open"
                subprocess.call([opener, filename])
        open_file(self.SAVINGPATH)
    
    @pyqtSignature("")
    def on_action_Load_Setting_triggered(self):
        """
        Slot documentation goes here.
        """
        LoadDefaultSetting(self)
        
        self.statusBar().showMessage(_translate("MainWindow", 'Setting loaded.', None))
        print 'Setting loaded.'
    @pyqtSignature("double")
    def on_doubleSpinBox_segsize_valueChanged(self, p0):
        """
        Slot documentation goes here.
        """

        self.MINPIECESIZE = p0
    @pyqtSignature("int")
    def on_spinBox_segments_valueChanged(self, p0):
        """
        Slot documentation goes here.
        """

        self.MAXCONCOUNT = p0
    @pyqtSignature("")
    def on_action_Save_Setting_triggered(self):
        """
        Slot documentation goes here.
        """
        import ConfigParser 
        cf = ConfigParser.ConfigParser()
        cf.add_section('main')
        cf.set("main", "path", self.SAVINGPATH)
        cf.set("main", "MINPIECESIZE", self.MINPIECESIZE)
        cf.set("main", "MAXCONCOUNT", self.MAXCONCOUNT)
        cf.set('main',"QUALITY",self.QUALITY)
        cf.set('main','CLEANTEMPFILES',self.CLEANTEMPFILES)
        cf.set('main','VLC_PATH',self.VLC_PATH)
        cf.set('main','MENCODER_PATH',self.MENCODER_PATH)
        if self.LANGUAGE:
            cf.set('main','language',self.LANGUAGE)
        cf.write(open('setting.ini', "w"))
        print 'Setting saved.'
        self.statusBar().showMessage(_translate("MainWindow", 'Setting saved.', None))

    @pyqtSignature("")
    def on_actionOpen_vdl_file_triggered(self):
        """
        Slot documentation goes here.
        """

        
        fileName = QtGui.QFileDialog.getOpenFileName(parent = self, caption = _translate("MainWindow", 'Select vdl file containing video address', None),filter = 'vdl file *.vdl (*.vdl);;*.* (*.*)' )
        if fileName != '' and os.path.isfile(fileName):
            OK , self.VIDEO_ADDRESS = Re_CHECK_URL(Load_VIDEO_ADDRESS_from_file(fileName))
            if OK:
                #thread.start_new_thread(Load_URL_info, (ui,)) 
                if self.Load_URL_info ()>=0: 
                    self.on_pushButton_stop_pressed()
                    self.on_pushButton_start_pressed()
                    self.on_pushButton_start_2_pressed()
            else:
                errorMessage=QtGui.QErrorMessage(self)
                
                errorMessage.showMessage(_translate("MainWindow", 'vdl file contains wrong url!', None))
    @pyqtSignature("")
    def on_actionOpen_URL_triggered(self):
        """
        Slot documentation goes here.
        """

        
        text, ok = QtGui.QInputDialog.getText(self,_translate("MainWindow", 'Input Video Address', None) , _translate("MainWindow", 'Enter the address (http://...):', None) )
        print text, ok 
        if ok and text!='':
            OK , self.VIDEO_ADDRESS = Re_CHECK_URL( text)
            self.VIDEO_ADDRESS = self.VIDEO_ADDRESS.toUtf8()
            if OK:
                if self.Load_URL_info()>=0: 
                    self.on_pushButton_stop_pressed()
                    self.on_pushButton_start_pressed()
                    self.on_pushButton_start_2_pressed()
            else:
                errorMessage=QtGui.QErrorMessage(self)
                
                errorMessage.showMessage(_translate("MainWindow", 'Wrong url!', None))           

    
    @pyqtSignature("")
    def on_actionOpen_URL_from_clipboard_triggered(self):
        """
        Slot documentation goes here.
        """

        clipboard = QtGui.QApplication.clipboard()
        OK , self.VIDEO_ADDRESS = Re_CHECK_URL( clipboard.text())
        self.VIDEO_ADDRESS = self.VIDEO_ADDRESS.toUtf8()
        if OK:
            if self.Load_URL_info()>=0: 
                self.on_pushButton_stop_pressed()
                self.on_pushButton_start_pressed()
                self.on_pushButton_start_2_pressed()
        else:
            errorMessage=QtGui.QErrorMessage(self)
            errorMessage.showMessage(_translate("MainWindow", 'Wrong url!', None)) 
    @pyqtSignature("")
    def on_actionJoin_Now_triggered(self):
        """
        Slot documentation goes here.
        """
        filename = self.title+'.'+self.file_type
        cmdline = '\"'+MENCODER_PATH+'\"' + ' \"' + os.path.join(self.SAVINGPATH,filename)+ '\"'
        for filename in self.filename_arr:
            cmdline= cmdline + ' \"' + os.path.join(self.SAVINGPATH,filename)+ '\"'
        import platform
        sysstr = platform.system()
        if(sysstr =="Windows"):
            # In windows' cmd, only gbk-encoded Chinese paras are recognized. 
            cmdline = cmdline.encode ("gbk", 'ignore')
        else:
            cmdline = cmdline.encode ("utf-8", 'ignore')
        print cmdline
        cmdline = shlex.split(cmdline)
        
        #cmdline = cmdline.encode ("utf-8", 'ignore')
        self.MENCODER = subprocess.Popen(cmdline, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            
    @pyqtSignature("int")
    def on_checkBox_cleantmp_stateChanged(self, p0):
        """
        Slot documentation goes here.
        """

        print p0
        self.CLEANTEMPFILES = p0

    @pyqtSignature("")
    def on_pushButton_add_to_vlc_pressed(self):
        """
        Slot documentation goes here.
        """
        
        cmdline = '\"'+self.VLC_PATH+ '\"'+' --no-playlist-autostart' #+' \"' + '\" \"'.join(filename_arr) + '\"'
        self.play_with_vlc(cmdline)
        
    @pyqtSignature("")
    def on_pushButton_add_and_play_pressed(self):
        cmdline =  '\"'+self.VLC_PATH+ '\"'+' --playlist-autostart'
        self.play_with_vlc(cmdline)

    @pyqtSignature("")
    def AutoPlaySLOT(self):       
        print 'aaa Load_URL_info'
        if self.Load_URL_info()>=0: 
            print 'bbb on_pushButton_start_pressed'
            self.on_pushButton_start_pressed()
            print 'ccc on_pushButton_start_2_pressed'
            self.on_pushButton_start_2_pressed()
            self.on_pushButton_add_and_play_pressed()
    @pyqtSignature("")
    def Load_URL_info(self):
        self.cleantmpfiles() 
        self.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        self.statusBar().showMessage(_translate("MainWindow", 'Loading quality...', None))
        try:
            app.processEvents()
        except:
            pass
        self.listWidget_process.clear()
        Query_URL = 'http://api.flvxz.com/url/{0}'
        videourl = self.VIDEO_ADDRESS
        print videourl
        try:
            url = Query_URL.format(b64encode(videourl))
        except :
            pass
        print url
        def return_with_error(errmsg):
            self.statusBar().showMessage(errmsg)
            self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            return -1
        try:
            xml_text =  urllib2.urlopen(url, data=None, timeout=15).read()
            #xml_text = xml_text.decode('utf8').encode('utf8')
        except urllib2.URLError,e:           
            return return_with_error(_translate("MainWindow", 'URLError error: ', None)+e.reason.strerror)
        except urllib2.HTTPError,e:           
            return return_with_error(_translate("MainWindow", 'HTTP error: ', None)+e.reason.strerror)
        except:
            return return_with_error(_translate("MainWindow", 'Network error. ', None))
        doc = xml.dom.minidom.parseString(xml_text)
        if xml_text=='<root></root>':
            return return_with_error('URL does not contain video or URL is wrong. ')
        video_arr = doc.getElementsByTagName('video')
        
        ui.video_arr=video_arr
        QUALITY = self.QUALITY
        self.comboBox_quality.clear()
        index_a = 0
        for video_node in video_arr:
            title = video_node.getElementsByTagName('title')[0].firstChild.data
            quality = video_node.getElementsByTagName('quality')[0].firstChild.data
            file_type = video_node.getElementsByTagName('ftype')[0].firstChild.data
            #temp_msg = str(index_a+1)+'. '+title+' .'+file_type+'\t'+quality
            #temp_msg = str(index_a+1)+'. '+file_type.ljust(6)+quality.ljust(12-len_zh(quality))
            if file_type.find('m3u8')<0:
                self.comboBox_quality.addItem(quality+'('+file_type+')', userData=index_a)
                #can send signal on_comboBox_quality_currentIndexChanged
            index_a +=1
        self.QUALITY = QUALITY    
        for index in range(self.comboBox_quality.count()):
            if self.comboBox_quality.itemText(index).indexOf( QtCore.QString.fromUtf8(self.QUALITY))>=0:
                self.comboBox_quality.setCurrentIndex(index)
                break
            
        self.statusBar().showMessage(_translate("MainWindow", 'OK.', None))    
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.lineEdit_title.setText(title)
        return 1
               
    def play_with_vlc(self,cmdline):
        for filename in self.filename_arr:
            cmdline= cmdline + ' \"' + os.path.join(self.SAVINGPATH,filename)+ '\"'
        import platform
        sysstr = platform.system()
        if(sysstr =="Windows"):
            # In windows' cmd, only gbk-encoded Chinese paras are recognized. 
            cmdline = cmdline.encode ("gbk", 'ignore')
        else:
            cmdline = cmdline.encode ("utf-8", 'ignore')
        cmdline = shlex.split(cmdline)
        print cmdline
        #cmdline = cmdline.encode ("utf-8", 'ignore')
        self.vlcProcess = subprocess.Popen(cmdline, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
 
    @pyqtSignature("int")
    def on_comboBox_quality_currentIndexChanged(self, index):
        """
        Slot documentation goes here.
        """
        quality = self.comboBox_quality.currentText().toUtf8().split('(')
        self.QUALITY = quality[0]
        self.on_pushButton_start_pressed()     
    @pyqtSignature("QPoint")
    def on_tableWidget_customContextMenuRequested(self, pos):
        """
        Slot documentation goes here.
        """
        print 'menu          ----------'
        item = self.tableWidget.itemAt(pos)
        #空白区域不显示菜单
        if item != None:
            self.tableRightMenuShow()    
    @pyqtSignature("QModelIndex")
    def on_tableWidget_clicked(self, index):
        """
        Slot documentation goes here.
        """
        print '222222222222'
    def tableRightMenuShow(self):
        rightMenu = QtGui.QMenu(self.tableWidget)
        disableAction = QtGui.QAction("Disable", self, triggered=self.tableRightMenuDisable)       # triggered 为右键菜单点击后的激活事件。这里slef.close调用的是系统自带的关闭事件。
        disableAction.setText(_translate("MainWindow", "Disable", None))
        rightMenu.addAction(disableAction)
       
        enableAction = QtGui.QAction("Enable", self, triggered=self.tableRightMenuEnable)       # 也可以指定自定义对象事件
        enableAction.setText(_translate("MainWindow", "Enable", None))
        rightMenu.addAction(enableAction)
        rightMenu.exec_(QtGui.QCursor.pos())
    def tableRightMenuDisable(self):
        for item in self.tableWidget.selectedItems():
            print item.row(),' disabled'
            self.file_progress[item.row()].disabled_FLAG = True
            item.setTextColor(QtGui.QColor(100,100,100)) 
            item.setBackgroundColor(QtGui.QColor(200,200,200))
#         for row in self.tableWidget.selectedRanges():
#             print row,' disabled'
#             self.file_progress[row.row()].disabled_FLAG = True
#             for x in range(self.tableWidget.columnCount()):  
#                 tableitem = self.tableWidget.item(row.row(), x)
#                 if tableitem != None:
#                     tableitem.setTextColor(QtGui.QColor(100,100,100)) 
#                     tableitem.setBackgroundColor(QtGui.QColor(200,200,200))
        self.tableWidget.clearSelection()

    def tableRightMenuEnable(self):
        for item in self.tableWidget.selectedItems():
            self.file_progress[item.row()].disabled_FLAG = False
            item.setTextColor(QtGui.QColor(0,0,0)) 
            item.setBackgroundColor(QtGui.QColor(255,255,255))
#         for row in self.tableWidget.selectedIndexes():
#             self.file_progress[row.row()].disabled_FLAG = False
#             for x in range(self.tableWidget.columnCount()):  
#                 tableitem = self.tableWidget.item(row.row(), x)
#                 if tableitem != None:
#                     tableitem.setTextColor(QtGui.QColor(0,0,0)) 
#                     tableitem.setBackgroundColor(QtGui.QColor(255,255,255))
        self.tableWidget.clearSelection()
        
    def closeEvent(self, evnt):
        print 'Closing...'
        try:
            self.vlcProcess.terminate()
        except:
            pass  
        self.statusBar().showMessage(_translate("MainWindow", 'Closing...', None))
        
        self.cleantmpfiles()   
        super(MainWindow, self).closeEvent(evnt)
    def cleantmpfiles(self):
        if self.CLEANTEMPFILES>0:
            try:
                for filename in self.filename_arr:
                    try:
                        file_path = os.path.join(self.SAVINGPATH,filename)
                        print 'Removing '+file_path
                        os.remove(file_path)
                        if os.path.isfile(file_path+'.PyLog'):
                            os.remove(file_path+'.PyLog')
                    except:
                        pass
            except:
                pass
            print 'All temp files deleted!'

        #evnt.ignore()
        #self.setWindowState(QtCore.Qt.WindowMinimized)     

    @pyqtSignature("")
    def on_actionEnglish_triggered(self):
        """
        Slot documentation goes here.
        """
        self.LANGUAGE = False
        self.MainWindowAPP.installTranslator(qtTranslator)
        self.retranslateUi(self)
    
    @pyqtSignature("")
    def on_actionTraditional_Chinese_triggered(self):
        """
        Slot documentation goes here.
        """
        self.set_Language('zh_TW')
    
    @pyqtSignature("")
    def on_actionSimplified_Chinese_triggered(self):
        """
        Slot documentation goes here.
        """

        self.set_Language('zh_CN')
    
    @pyqtSignature("")
    def on_actionJapanese_triggered(self):
        """
        Slot documentation goes here.
        """
        self.set_Language('ja_JP')
 
    def set_Language(self,language):
        qtTranslator = QtCore.QTranslator()
        if qtTranslator.load( language):
            self.LANGUAGE = language
            self.MainWindowAPP.installTranslator(qtTranslator)
            self.retranslateUi(self)
        else:
            self.statusBar().showMessage(_translate("MainWindow", 'Language pack not found.', None))
    @pyqtSignature("")
    def on_actionAbout_me_triggered(self):
        QtGui.QMessageBox.about(self,'About...', 'BBQ video downloader\nVersion: 0.1 beta\nAuthor: DawnRain @ DR&QM')  
    @pyqtSignature("")
    def on_actionVisit_my_blogger_triggered(self):
        import webbrowser
        webbrowser.open("http://draqm.blogspot.sg")
    
    @pyqtSignature("")
    def on_actionVisit_github_page_triggered(self):
        import webbrowser
        webbrowser.open("github")    

if __name__ == '__main__':
    
    
    app = QtGui.QApplication(sys.argv)
    qtTranslator = QtCore.QTranslator()
    
    language_setting = LoadLanguageSetting()
    locale = QtCore.QLocale.system().name()
    if (language_setting and qtTranslator.load( language_setting)) or qtTranslator.load( locale):
        app.installTranslator(qtTranslator)

    
    ui = MainWindow()
    ui.show()
    
    #qtTranslator = QtCore.QTranslator()
    #app.installTranslator(qtTranslator)
    #ui.retranslateUi(ui)
    
    ui.MainWindowAPP = app
    #ui.lineEdit_title.setText('Test title')
    

    #ui.listWidget_process.addItem(QtGui.QListWidgetItem(QtGui.QIcon("red.png"),"Earth"))
#     for i in range(30):
#         ui.listWidget_process.addItem(QtGui.QListWidgetItem(QtGui.QIcon("red.png"),''))
#         ui.listWidget_process.addItem(QtGui.QListWidgetItem(QtGui.QIcon("green.png"),''))



    #print ui.comboBox_quality.currentIndex()
    #print ui.comboBox_quality.currentText()
    #print ui.comboBox_quality.itemData(0).toString()
    #ui.comboBox_quality.setCurrentIndex(0)
    
    LoadDefaultSetting(ui)
    #thread.start_new_thread(Ui_update_comboBox_quality, (ui,))  
    
    def delay_auto_execute(ui):
        #time.sleep(1)
        signal_temp = EmitSignalClass_void(desSlot=ui.AutoPlaySLOT)
        signal_temp.emit_signal()
        
#         Load_URL_info (ui) 
#         ui.on_pushButton_start_pressed()
#         ui.on_pushButton_start_2_pressed()
#         ui.on_pushButton_add_and_play_pressed()

        return
    if True and len(sys.argv)>1:
        print sys.argv[1]
        OK , VIDEO_ADDRESS = Re_CHECK_URL( Load_VIDEO_ADDRESS_from_file(sys.argv[1]))
        if OK:
            ui.VIDEO_ADDRESS=VIDEO_ADDRESS
            ui.statusBar().showMessage(_translate("MainWindow", 'Loading...', None))
            
            thread.start_new_thread(delay_auto_execute, (ui,)) 
        else:
            OK , VIDEO_ADDRESS = Re_CHECK_URL( sys.argv[1])
            if OK:
                ui.VIDEO_ADDRESS=VIDEO_ADDRESS
                ui.statusBar().showMessage(_translate("MainWindow", 'Loading...', None))
                
                thread.start_new_thread(delay_auto_execute, (ui,)) 
            else:
                ui.statusBar().showMessage(_translate("MainWindow", 'Wrong address in argv: ', None)+sys.argv[1])
    else:
        ui.statusBar().showMessage(_translate("MainWindow", 'Ready.', None))
    sys.exit(app.exec_()) 

