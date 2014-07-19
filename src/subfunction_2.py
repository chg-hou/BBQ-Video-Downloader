# -*- coding: utf8 -*-
#!/usr/bin/env python


# 最小数据片大小(128kb)
MINPIECESIZE = 1024*1024/4  #131072

# 最大连接数
MAXCONCOUNT = 20
# 最大重试数
MAXRETRYCOUNT = 10
MAXRETRYERROR_COUNT_LIMIT = 80
#下载超时
DOWNLOAD_TIMEOUT = 120

# 日志级别
#LOGLEVEL = logging.DEBUG


# 下载日志文件
DLOG = 'download.log'
# ------------------------------import
import re
import platform
from hashlib import md5
import cPickle as pickle
import sys, os , datetime 
import time, logging
import  urlparse
import codecs, traceback
from tempfile import *
#from external_class import *
import threading, signal
import time 
#from dict4ini import DictIni
import pycurl
from PyQt4 import QtCore 


try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


#=====================================================external class ===========
class colorprint():
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
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
        

class FileProgress(object):
    index = 0
    progress = ''
    percentage = 0
    time_spent = 0.0
    time_remained = 999999.0
    speed = 0.0
    disabled_FLAG = False

class EmitSignalClass_FileProgress(QtCore.QObject):  
    sin1 = QtCore.pyqtSignal(FileProgress) 
    def __init__(self,parent=None,desSlot=None):
        super(EmitSignalClass_FileProgress,self).__init__(parent)   
        self.sin1.connect(desSlot)
    def disconnect_singal(self):
        self.sin1.disconnect(self.sin1Call)
    def emit_signal(self,progress):
        self.sin1.emit(progress)


class Segment_Lst():
    md5hash =None
    filesize = 0
    segments = []  
    def __init__(self,filesize,md5hash):
        self.filesize = filesize
        self.md5hash = md5hash
        self.segments = []
        
    def addSegment(self,start,end):
        self.segments.append(Segment_Info(start,end))

class Segment_Info():
    start = None
    end = None
    state = 'Empty'
    def __init__(self,start,end):
        self.start  = start
        self.end    = end
        self.state  = 'Empty'
        
def calMD5ForBigFile(filename):
    m = md5()
    f = open(filename, 'rb')
    buffer_size = 8192    # why is 8192 | 8192 is fast than 2048   
    while 1:
        chunk = f.read(buffer_size)
        if not chunk : break
        m.update(chunk)       
    f.close()
    return m.hexdigest()
#=====================================================external class ==========        

def DownloadThread(SegmentLst,hFile,url,thead_no,signalEvent):
    
    global threadlock,filelock
    hConnection = Connection(url)
    hConnection.hFile = hFile
    #connectionInfo.pycurl_object = hConnection.curl
    #c.getinfo(c.SPEED_DOWNLOAD)
    #print 'Thread '+str(thead_no)+' started' 
    while True:
        segmentID = None
        startPosition = None
        endPosition   = None
        
        if not signalEvent.isSet():
            threadlock.acquire()  
            for i in range(len(SegmentLst.segments)):         
                if SegmentLst.segments[i].state  == 'Empty':
                    segmentID = i
                    startPosition = SegmentLst.segments[i].start
                    endPosition   = SegmentLst.segments[i].end
                    SegmentLst.segments[i].state = 'Downloading'
                    break
            threadlock.release()
        
        if segmentID is None :
            #print 'Thread '+str(thead_no)+' return' 
            hConnection.close()
            return
        #print '\nThread '+str(thead_no)+'SegmentID:'+str(segmentID)+'  ; start: '+ str(startPosition)+' ;end: '+ str(endPosition) 
        
        hConnection.startDowload(startPosition, endPosition)
        retrycount = 0
        while True:
            if retrycount> MAXRETRYCOUNT:
                print 'MAX retry!!!!',
                threadlock.acquire()  
                SegmentLst.segments[segmentID].state = 'Empty'
                threadlock.release()
                #break
                global MAXRETRYERROR_COUNT
                MAXRETRYERROR_COUNT+=1
                if MAXRETRYERROR_COUNT>MAXRETRYERROR_COUNT_LIMIT:
                    global MAX_RETRY_ERR_FLAG
                    MAX_RETRY_ERR_FLAG = -1
                    return -1
                else:
                    break
            hConnection.hCache.seek(0, os.SEEK_END)
            if (hConnection.hCache.tell()+hConnection.hCache_shift) == endPosition-startPosition+1:
                #fcntl.flock(hFile, fcntl.LOCK_EX)
                #lock_file(hFile, LOCK_EX)
                filelock.acquire() 
                if signalEvent.isSet():
                    filelock.release()  
                    return
                try:
                    hFile.seek(startPosition+hConnection.hCache_shift,0)
                    hFile.write(hConnection.hCache.getvalue())
                except:
                    print 'Writing error. File close?'
                #fcntl.flock(hFile, fcntl.LOCK_UN)  
                #lock_file(hFile, LOCK_UN)
                filelock.release()  
                if hFile.closed:
                    return
                threadlock.acquire()  
                SegmentLst.segments[segmentID].state = 'Finished'
                threadlock.release()
                break
            else:
                retrycount += 1
                hConnection.retry()
        
#class ConnectionInfo:
#    SPEED_DOWNLOAD = 0
#    pycurl_object = None
class Connection:
    def __init__(self, url):
        self.curl = pycurl.Curl()
        self.hCache = StringIO()
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.MAXREDIRS, 5)
        self.curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        self.curl.setopt(pycurl.TIMEOUT, DOWNLOAD_TIMEOUT)
        self.curl.setopt(pycurl.NOSIGNAL, 1)
        self.curl.setopt(pycurl.WRITEFUNCTION, self.write_cb)
        self.curl.setopt(pycurl.URL, url)
        self.curl.connection = self

        #pycurl.SPEED_DOWNLOAD
        # 合计下载字节数
        self.total_downloaded = 0

    def startDowload(self, start,end):

        self.curl.setopt(pycurl.RANGE, '%d-%d' % (start, end))
        self.segment_size = end-start + 1
        self.start  = start
        self.end    = end
        # 一次连接的已下载字节数
        self.link_downloaded = 0
        # 一个片断的已下载字节数
        self.piece_downloaded = 0
        # 连接重试数
        self.retried = 0
        # 下载中止标志
        self.is_stop = False
        # 结果输出文件对象
        self.hCache.close()
        self.hCache = StringIO()
        # 内存缓存 偏移
        self.hCache_shift = 0
        try:
            self.curl.perform()
        except:
            self.retry()
        
    def retry(self):
        #print 'retry ',
        self.curl.setopt(pycurl.RANGE, '%d-%d' % (self.start+self.piece_downloaded, self.end))
        if self.link_downloaded: 
            self.link_downloaded = 0
        else:
            self.retried += 1

    def close(self):
        self.hCache.close()
        self.curl.close()
        
    def write_cb(self, data):
        #print '.',
        self.hCache.seek(self.piece_downloaded-self.hCache_shift, 0)
        self.hCache.write(data)
        self.hCache.flush()
        size = len(data)
        self.link_downloaded += size
        self.piece_downloaded += size
        self.total_downloaded += size
        # 内存缓存大小
        MAX_CACHE_SIZE = 1024*1024*2
        if False and (self.piece_downloaded-self.hCache_shift>MAX_CACHE_SIZE):
            print '!!!!writing file!!!!!!!'
            #fcntl.flock(self.hFile, fcntl.LOCK_EX)  
            global filelock
            filelock.acquire() 
            #lock_file(self.hFile, LOCK_EX)
            
            self.hFile.seek(self.start+self.hCache_shift,0)
            self.hFile.write(self.hCache.getvalue())
            #fcntl.flock(self.hFile, fcntl.LOCK_UN)  
            #lock_file(self.hFile, LOCK_UN)
            filelock.release()  
            self.hCache.seek(0, os.SEEK_END)
            self.hCache_shift =  self.hCache.tell()
            self.hCache.close()
            self.hCache = StringIO()    
        if self.is_stop: return -1

class FastDownload:
    def __init__(self,ui,signalEvent):
        self.ui=ui
        self.signalEvent=signalEvent
        global MINPIECESIZE,MAXCONCOUNT
        MINPIECESIZE =  ui.MINPIECESIZE *1024*1024
        MAXCONCOUNT = ui.MAXCONCOUNT
        pass

    def execute(self, url,file_index,filename,path):
        '''
        start downloading
        '''
        self.file_index=file_index
        self.url_info = self.url_check(url)
        global MAX_RETRY_ERR_FLAG,MAXRETRYERROR_COUNT
        MAX_RETRY_ERR_FLAG = 0
        MAXRETRYERROR_COUNT = 0
        if self.url_info:
            self.url_info['filename_sys_dep'] = os.path.join(path,filename)
            self.url_info['filename']       = filename
            self.url_info['file']           = filename
                  
            print2 = colorprint()
            print2.info('Download %s, Size %d' % (self.url_info['filename'], self.url_info['size']))
            self.make_pieces()
            self.allocate_space()
            return self.download()

# ***************************************************************

    def url_check(self, url):
        '''
        check url
        '''
        url_info = {}
        proto = urlparse.urlparse(url)[0]
        # 支持的协议
        VALIDPROTOCOL = ('http', 'ftp')
        if proto not in VALIDPROTOCOL:
            print 'Valid protocol should be http or ftp, but %s found<%s>!' % (proto, url)
        else:
            ss = StringIO()
            curl = pycurl.Curl()
            curl.setopt(pycurl.FOLLOWLOCATION, 1)
            curl.setopt(pycurl.MAXREDIRS, 5)
            curl.setopt(pycurl.CONNECTTIMEOUT, 30)
            curl.setopt(pycurl.TIMEOUT, 300)
            curl.setopt(pycurl.NOSIGNAL, 1)
            curl.setopt(pycurl.NOPROGRESS, 1)
            curl.setopt(pycurl.NOBODY, 1)
            curl.setopt(pycurl.HEADERFUNCTION, ss.write)
            # TODO: under windows, has to be encoded. Check under linux
            curl.setopt(pycurl.URL, url.encode('utf-8'))
            #curl.setopt(pycurl.URL,unicode(url))
            try:
                curl.perform()
            except:
                pass
            # HTTP状态码
            STATUS_OK = (200, 203, 206)
            if curl.errstr() == '' and curl.getinfo(pycurl.RESPONSE_CODE) in STATUS_OK:
                url_info['original_url'] = url
                url_info['url'] = curl.getinfo(pycurl.EFFECTIVE_URL)
                url_info['file'] = os.path.split(url_info['url'])[1]
                url_info['size'] = int(curl.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD))
                url_info['header'] = (ss.getvalue())
                url_info['partible'] = (ss.getvalue().find('Accept-Ranges') != -1)
                if re.compile(r'Via:').search(ss.getvalue()):
                    #print 'LAN cached...., support partible'
                    # TODO: REMOVE
                    url_info['partible'] = True
                url_info['partible'] = True
                if re.compile(r'(?<=filename=").+(?=")').search(ss.getvalue()):
                    url_info['filename'] = re.compile(r'(?<=filename=").+(?=")').search(ss.getvalue()).group()
                elif re.compile(r'(?<=file=").+(?=")').search(ss.getvalue()):
                    url_info['filename'] = re.compile(r'(?<=file=").+(?=")').search(ss.getvalue()).group()
                else:
                    url_info['filename'] = url_info['file']
                if not isinstance(url_info['filename'], unicode):
                    #print url_info['filename']
                    #url_info['filename']=url_info['filename'].decode('gbk','ignore').encode('utf-8')
                    #print url_info['filename']
                    pass
                if(platform.system() =="Windows"):
                    try:
                        url_info['filename_sys_dep'] = url_info['filename'].decode('utf-8','ignore').encode('gb2312')
                    except:
                        print 'Wrong in encoding using gb2312'
                        url_info['filename_sys_dep'] = url_info['filename']
                    print 'filename_sys_dep(gb2312 code): ' +url_info['filename_sys_dep']     
                else:
                    url_info['filename_sys_dep'] = url_info['filename']
                    
                if re.compile(r'(?<=Content-MD5:(\s))[A-Za-z0-9]+').search(ss.getvalue()):
                    url_info['md5hash']  =re.compile(r'(?<=Content-MD5:(\s))[A-Za-z0-9]+').search(ss.getvalue()).group()
                else :
                    url_info['md5hash']=''
                #777777777777777777777777777777777777777777
                ss.close()
                #print url_info['header'] 
                return url_info    

                if os.path.isfile(url_info['filename_sys_dep'] + '.PyLog'): 
                    pass
                else:   #已完成
                    if os.path.isfile(url_info['filename_sys_dep']):    
                        #存在同名文件
                        i=0
                        while True:
                            i+=1
                            temp1 = url_info['filename_sys_dep'].split('.')
                            if len(temp1)>1:
                                temp1[-2]=temp1[-2]+'('+str(i)+')'
                                temp_filename =  '.'.join(temp1)
                            else:
                                i=1
                                temp_filename=url_info['filename_sys_dep']+'('+str(i)+')'
                            if os.path.isfile(temp_filename):
                                pass
                            else:
                                url_info['filename_sys_dep'] = temp_filename
                                break
            ss.close()
        return url_info

    def make_pieces(self):
        '''
                分段信息生成
        '''
        if False and  os.path.isfile(self.url_info['filename_sys_dep'] + '.PyLog'): #存在日志文件，直接读取
            try:
                SegmentLst = pickle.load(open(self.url_info['filename_sys_dep'] + '.PyLog', "r"))
                if (SegmentLst.md5hash == self.url_info['md5hash']) and (SegmentLst.filesize == self.url_info['size']):
                    self.SegmentLst = SegmentLst
                    print "Recovery successfully!"
                    return       
            except:
                pass        
             
        file_size = self.url_info['size']
        SegmentLst = Segment_Lst(file_size,self.url_info['md5hash'])
        if self.url_info['partible'] and file_size>MINPIECESIZE:                 
            for i in range(int(file_size/MINPIECESIZE)):
                SegmentLst.addSegment(i*MINPIECESIZE, (i + 1) * MINPIECESIZE - 1)
            SegmentLst.addSegment(int(file_size/MINPIECESIZE)*MINPIECESIZE, file_size - 1)
            print '分块数目：',str(len(SegmentLst.segments))

        else:
            print "不支持续传，单片段模式"
            raise('不支持续传，单片段模式')
            SegmentLst.addSegment(0, file_size - 1)
        self.SegmentLst = SegmentLst           
        #print self.SegmentLst 
    def allocate_space(self):
        '''
        预分配文件空间(通用？)
        '''
        print "Truncating space...."
        if os.path.isfile(self.url_info['filename_sys_dep']): 
            return
        else:
            try:
                afile = file(self.url_info['filename_sys_dep'], 'wb')
            except:
                self.url_info['filename_sys_dep']='AAAA'
                print 'ERROR IN SAVE FILE!!!!!!!!!!!!!!'
                afile = file(self.url_info['filename_sys_dep'], 'wb')
            afile.truncate(self.url_info['size'])
            afile.close()

# ***************************************************************

    def show_progress(self, downloaded, elapsed):
        '''
        显示下载进度
        '''
        percent = min(100, downloaded * 100.0 / self.url_info['size'])
        if elapsed == 0:
            rate = 0
        else:
            rate = downloaded * 1.0 / 1024.0 / elapsed
        info = ' D/L: %d/%d (%6.2f%%) - Avg: %4.1fkB/s' % (downloaded, self.url_info['size'], percent, rate)
        space = ' ' * (60 - len(info))

        prog_len = int(percent * 20 / 100)
        prog = '|' + 'o' * prog_len + '.' * (20 - prog_len) + '|'

        sys.stdout.write(info + space + prog)
        sys.stdout.flush()
        sys.stdout.write('\b' * 82)

    def close_connection(self, c):
        '''
        关闭连接
        '''


    def process_curl(self, curl):
        '''
        下载结果处理
        '''
    def update_progress(self,tstart):
        fileprogress = FileProgress()
        
        #speed_realtime = 0
        #for item in self.ConnectionInfo_pool:
            # error: cannot invoke getinfo() - perform() is currently running
            #item.SPEED_DOWNLOAD = item.pycurl_object.getinfo(pycurl.SPEED_DOWNLOAD )
            #print item.SPEED_DOWNLOAD
            #speed_realtime += item.SPEED_DOWNLOAD
            #pass 
        global threadlock
        print2 = colorprint()
        #print2.infog(self.url_info['filename_sys_dep'])
        progress = ''
        percent = 0.0001
        threadlock.acquire()
        for i in range(len(self.SegmentLst.segments)):
            
            a = self.SegmentLst.segments[i].state
            if a == 'Finished':
                progress+='O' #'▇'
                percent += 1.0
            elif a== 'Downloading' :  
                progress+= '+'#'➡'
            elif a== 'Empty':
                progress+= '-'#'❒'
        threadlock.release()
        try:
            pass
            #os.system(CLS)
        except:
            pass
        progress_msg = [progress[i:i+51] for i in range(0, len(progress), 51)]
        
        #if platform.system()=='Windows':
        #    progress_msg=progress_msg.decode('utf-8').encode('gb2312')
        for line in progress_msg:
            pass
            #print line
        percent = percent/len(self.SegmentLst.segments)
        
        t_end = time.time()                  
        time_remain = (t_end-tstart)/percent*(1-percent)
        if time_remain < 0:
            time_remain = 0.0
        speed = self.url_info['size']*percent/(t_end-tstart)/1024.0
        if speed<0.03:
            speed=0.0
        #print ' time span :\t %d s\t %5.2f %% speed: %.1f KB/s' % ( (t_end-tstart),percent*100,speed)
        #print ' time remain :\t %d s' % time_remain
        #global IS_EXIT_FLAG
        #if IS_EXIT_FLAG:
        #    print 'Is exiting...(timeout '+str(DOWNLOAD_TIMEOUT)+' s)'
  
        singal_temp = EmitSignalClass_FileProgress(desSlot=self.ui.update_file_progress)
        fileprogress.index = self.file_index
        fileprogress.progress=progress
        fileprogress.percentage = int(percent*100)
        fileprogress.time_spent = (t_end-tstart)
        fileprogress.time_remained = time_remain
        fileprogress.speed = speed
        #fileprogress.speed = speed_realtime
        singal_temp.emit_signal(fileprogress)
 
    def save_progress(self):

        pickle.dump(self.SegmentLst, open(self.url_info['filename_sys_dep'] + '.PyLog', "w"), True)  
        #  "wb"

        
    def download(self):
        '''
        下载主过程
        '''
        dstart = datetime.datetime.now() 
        tstart = time.time()
        #print "Main Thread Start At: " , dstart 
        
        print 'Start at:'+dstart.strftime('%Y-%m-%d %H:%M:%S' )
        self.hFile = file(self.url_info['filename_sys_dep'], 'r+b')
        
        
        global threadlock,filelock
        threadlock = threading.Lock()
        filelock   = threading.Lock()
        #initial thread_pool 
        thread_pool = [] 
        #self.ConnectionInfo_pool = []
        for i in range(MAXCONCOUNT): 
            #self.ConnectionInfo_pool.append(ConnectionInfo())
            th = threading.Thread(target=DownloadThread,args=(self.SegmentLst,self.hFile,self.url_info['url'],i,self.signalEvent) ) ; 
            thread_pool.append(th)    
        # start threads one by one         
        for i in range(MAXCONCOUNT): 
            pass
            thread_pool[i].setDaemon(True)
            thread_pool[i].start()  
        #update_thread = threading.Thread(target=DownloadThread,args=(self.SegmentLst,self.hFile,self.url_info['url'],i) ) ; 
          
        #collect all threads 
        #DownloadThread(self.SegmentLst,self.hFile,self.url_info['url'],0)
        update_count_temp = 0
        while 1:
            global MAX_RETRY_ERR_FLAG
            if MAX_RETRY_ERR_FLAG<0:
                return MAX_RETRY_ERR_FLAG
            
            update_count_temp +=1
            if update_count_temp>1:
                update_count_temp = 0        
                self.update_progress(tstart)
                self.save_progress()
                
            FinishedFlag = True
            for i in range(MAXCONCOUNT): 
                if thread_pool[i].isAlive():
                    FinishedFlag = False

            if self.signalEvent.isSet():
                print '->>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> receive stop signalEvent'
                FinishedFlag = True
            #print threading.active_count()
            #print threading.enumerate()
            if FinishedFlag:
                if not self.signalEvent.isSet():
                    self.update_progress(tstart)
                dend = datetime.datetime.now()   
                print2 = colorprint()
                print2.warn("Main Thread End   At: " +dend.strftime('%Y-%m-%d %H:%M:%S' ) + " time span " + str(dend-dstart))
                self.hFile.flush()
                self.hFile.close()
                if not self.signalEvent.isSet():
                    try:
                        os.remove(self.url_info['filename_sys_dep'] + '.PyLog') 
                    except:
                        pass
                    #md5_of_file =calMD5ForBigFile(self.url_info['filename_sys_dep'])
                    md5_of_file=''
                    if True or md5_of_file.upper()==self.url_info['md5hash'].upper():
                        #print 'MD5 hash matched!'
                        pass
                    else:
                        print 'MD5 in http header:\t' + self.url_info['md5hash'].upper()
                        print 'MD5 of file:\t'        + md5_of_file.upper()
                        print 'MD5 hash NOT matched, please redownload it.'
                else:
                    print 'Can resume using recovery file..'
                return 1
            else:
                time.sleep(1)  
            



