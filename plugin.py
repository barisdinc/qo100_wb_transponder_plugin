##########################################################################

import sys, os, struct

from Screens.Screen import Screen
from Components.Sources.CanvasSource import CanvasSource
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager
from Plugins.Plugin import PluginDescriptor
from enigma import gFont, eTimer
from enigma import RT_HALIGN_RIGHT
from enigma import eServiceCenter, eServiceReference, pNavigation, getBestPlayableServiceReference, iPlayableService
from ServiceReference import ServiceReference
from Components.TuneTest import Tuner
from Screens.ServiceScan import ServiceScan,ServiceScanSummary
from Screens.ScanSetup import ScanSetup, buildTerTransponder
from enigma import eDVBResourceManager, eDVBFrontendParametersSatellite, eDVBFrontendParametersTerrestrial, eDVBFrontendParametersATSC, iDVBFrontend
from Components.ServiceList import ServiceList
    
from websocket import create_connection
import pprint

def RGB(r,g,b):
	return (r<<16)|(g<<8)|b

#satscan_plugindir="/usr/lib/enigma2/python/Plugins/Extensions/Satscan"
#tmpfile="/tmp/scan.bin" 
#modstr = {0:"QPSK", 1:"QAM16", 2:"QAM32", 3:"QAM64", 4:"QAM128", 5:"QAM256", 6:"Auto", 7:"VSB_8", 8:"VSB_16", 9:"8PSK", 10:"APSK_16", 11:"APSK_32", 12:"DQPSK"}
#fecstr = {0:"None", 1:"1/2", 2:"2/3", 3:"3/4", 4:"4/5", 5:"5/6", 6:"6/7", 7:"7/8", 8:"8/9", 9:"Auto", 10:"3/5", 11:"9/10"}
#guardstr = {0:"1/32", 1:"1/16", 2:"1/8", 3:"1/4", 4:"Auto"} 
#transstr = {0:"2K", 1:"8K", 2:"Auto"} 
#pilotstr = {0:"ON", 1:"OFF", 2:"AUTO"}
#invstr = {0:"OFF", 1:"ON", 2:"AUTO"}
#rolloffstr = {0:"35", 1:"20", 2:"25", 3:"AUTO"} 
#systemstr = {0:"UNDEFINED", 1:"DVB-C", 2:"DVB-C", 3:"DVB-C", 4:"DVB-T", 5:"DVB-S", 6:"DVB-S2"}    

###########################################################################

class WB_Spectrum(Screen):
  skin = """
    <screen position="140,100" size="1000,480" title="QO-100 WB Transponder Spectrum          Baris Dinc - OH2UDS/TA7W">
    <widget source="Canvas" render="Canvas" position="0,0" size="1000,500" alphatest="blend"/>
    <widget source="Graph" render="Canvas" position="0,0" size="1000,430" alphatest="blend"/>
    <widget name="myRedBtn" position="10,440" size="100,40" backgroundColor="red" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;20"/>
    <widget name="myGreenBtn" position="120,440" size="100,40" backgroundColor="green" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;20"/>
    <widget name="myYellowBtn" position="230,440" size="100,40" backgroundColor="yellow" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;20"/>
    <widget name="myBlueBtn" position="340,440" size="100,40" backgroundColor="blue" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;20"/>
    <widget name="myLeftBtn" position="450,440" size="100,40" backgroundColor="black" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;20"/>
    <widget name="myRightBtn" position="560,440" size="100,40" backgroundColor="black" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;20"/>
    </screen>"""
  
  
  def __init__(self, session, args = None):
    self.marker = 0
    self.session = session
    #self.tunercount = len(nimmanager.nim_slots)
    self.tuner = 0
    #self.band = 0
    Screen.__init__(self, session)
    #self.session.nav.stopService() # try to disable foreground service
    self["Canvas"] = CanvasSource()
    self["Graph"] = CanvasSource()
    self["myRedBtn"] = Label(_("Exit"))
    self["myGreenBtn"] = Label(_("Select"))
    self["myYellowBtn"] = Label(_("---"))
    self["myBlueBtn"] = Label(_("***"))
    self["myLeftBtn"] = Label(_(" < "))
    self["myRightBtn"] = Label(_(" > "))
#    self["myCallsign"] = Label(_("Baris DINC - TA7W/OH2UDS"))
    self["myActionMap"] = ActionMap(["SetupActions","ColorActions"],
    {
      "red": self.close,
      "cancel": self.close,
      "ok": self.tuneToChannel, # startAnalyser,
#      "green": self.drawSpectrum, # startAnalyser,
      "yellow": self.videoReload, #changeTuner,
#      "blue": self.clearCanvas,
      "right": self.channel_right,
      "left": self.channel_left,
      "up": self.channel_up,
      "down": self.channel_down,
    }, -1)
    
    self["list"] = ServiceList(self)
    self.servicelist = self["list"]

    self.transponder = None
    self.frontend = None
  
    self.channelTablePlaces = {10491500 : 170, 10492750 : 284,  10493000 : 310,  10493250 : 336,  10493500 : 362,  10493750 : 388,  10494000 : 414,  10494250 : 440,  10494500 : 466,  10494750 : 492,  10495000 : 518,  10495250 : 544,  10495500 : 570,  10495750 : 596,  10496000 : 622,  10496250 : 648,  10496500 : 674,  10496750 : 700,  10497000 : 726,  10497250 : 752,  10497500 : 778,  10497750 : 804,  10498000 : 830,  10498250 : 856,  10498500 : 882,  10498750 : 908,  10499000 : 934,  10499250 : 960}
    self.currentChannel = [0, 0]    #this variable will hold the selected (painted) channel row, column
    self.channelTable = [\
      [[10492750,250,20],[10493000,250,20],[10493250,250,20],[10493500,250,20],[10493750,250,20],[10494000,250,20],[10494250,250,20],[10494500,250,20],[10494750,250,20],[10495000,250,20],[10495250,250,20],[10495500,250,20],[10495750,250,20],[10496000,250,20],[10496250,250,20],[10496500,250,20],[10496750,250,20],[10497000,250,20],[10497250,250,20],[10497500,250,20],[10497750,250,20],[10498000,250,20],[10498250,250,20],[10498500,250,20],[10498750,250,20],[10499000,250,20],[10499250,250,20]],\
      [[10492750,333,25],[10493000,333,25],[10493250,333,25],[10493500,333,25],[10493750,333,25],[10494000,333,25],[10494250,333,25],[10494500,333,25],[10494750,333,25],[10495000,333,25],[10495250,333,25],[10495500,333,25],[10495750,333,25],[10496000,333,25],[10496250,333,25],[10496500,333,25],[10496750,333,25],[10497000,333,25],[10497250,333,25],[10497500,333,25],[10497750,333,25],[10498000,333,25],[10498250,333,25],[10498500,333,25],[10498750,333,25],[10499000,333,25],[10499250,333,25]],\
      [[10492750,500,50],[10493250,500,50],[10493750,500,50],[10494250,500,50],[10494750,500,50],[10495250,500,50],[10495750,500,50],[10496250,500,50],[10496750,500,50],[10497250,500,50],[10497750,500,50],[10498250,500,50],[10498750,500,50],[10499250,500,50]],\
      [[10493250,1000,150],[10494750,1000,150],[10496250,1000,150]],\
      [[10491500,1500,160]]\
    ]
    self.channelRow = [[390,6],[398,6],[406,6],[414,6],[390,18]]
    self.bbox()

  def openFrontend(self):
    res_mgr = eDVBResourceManager.getInstance()
    if res_mgr:
      print("RESMGR")
      fe_id = 0 #int(self.scan_nims.value)
      print("FE_ID = %d" % fe_id)
      self.raw_channel = res_mgr.allocateRawChannel(fe_id)
      if self.raw_channel:
        print("RAW CHN")
        self.frontend = self.raw_channel.getFrontend()
        print("---GET FE----")
        if self.frontend:
          return True
    return False

  def startTuner(self):
    self.frontend = None
    try:
      if not self.openFrontend():
        print("before service")
        self.session.nav.stopService()
        if not self.openFrontend():
          print("after service")
          self.frontend = None # in normal case this should not happen
      self.tuner = Tuner(self.frontend)
      print("TUNER YARATILDI")
#      self.createSetup()
#      self.retune()
    except:
      pass



#res_mgr = eDVBResourceManager.getInstance()
#if res_mgr:
 # print("RESMGR")
 # print(eDVBResourceManager.getInstance())
 # print(vals(eDVBResourceManager.getInstance()))
 # print(dir(eDVBResourceManager.getInstance()))
#  self.raw_channel = res_mgr.allocateRawChannel(0) #self.feid)
#  if self.raw_channel:
#    print("RAW CHANNEL")
#    self.frontend = self.raw_channel.getFrontend()
#    if self.frontend:
#      print("FRONTEND")
#        #return True
##return False
##self.tuner = feinfo and feinfo.getFrontendData()

##fe_id = int(self.scan_nims.value)
#self.raw_channel = eDVBResourceManager.getInstance().allocateRawChannel(0)
#self.frontend = self.raw_channel.getFrontend()

#self.tuner = Tuner(self.frontend)
  

  def bbox(self):
    fg = RGB(255, 255, 255)
    bg = RGB(0,0,0)
    cc = RGB(150,150,150)
    sc = RGB(255,255,0)
    font = gFont("Regular", 20) 
    c = self["Canvas"]
#    c.fill(0, 0, 1100, 400, bg) 
    c.fill(50, 30, 2, 330, fg)  # Y-Achse
    c.fill(45, 360, 950, 2, fg) # X-Achse (x,y,Breite,Hoehe,Farbe)
    for i in range(13):    # dB-Skala
      c.fill(40, 40+22*i, 10, 2, fg) # Striche
      c.writeText(0, 30+22*i, 30, 20, fg, bg, font, str(11-i),RT_HALIGN_RIGHT) # Zahlen
    c.writeText(5, 0, 30, 20, fg, bg, font, "dB")
    for i in range(18):
      c.fill(50+52*i, 360, 2, 10, fg)
    for i in range(9):
      c.writeText(73+104*i, 365, 60, 20, fg, bg, font, str(10491+i))
    c.writeText(960, 365, 50, 20, fg, bg, font, "MHz")

    for row,channelRows in enumerate(self.channelTable):
      for channel in channelRows:
        self.drawChannel(c, channel, row, cc)
    self.drawChannel(c, self.channelTable[0][0], 0, sc)
    c.flush()
    self.updateSpectrumTimer = eTimer()
    self.updateSpectrumTimer.callback.append(self.drawSpectrum)
    self.updateSpectrumTimer.start(3000)

  def drawChannel(self, canvas, ch, rw, color):
    x = self.channelTablePlaces[ch[0]]
    canvas.fill(x-int(ch[2]/2),self.channelRow[rw][0], ch[2], self.channelRow[rw][1], color)
    canvas.flush()

  def clearCanvas(self):
    g = self["Graph"]    
    g.clear()
    g.flush()
    g.fill(50,50,100,100,RGB(0,0,255)) 
    g.flush()
    #print(vars(g))
    
  def channel_left(self):
    cc = RGB(150,150,150)
    sc = RGB(255,255,0)
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , cc)
    if self.currentChannel[1] > 0:
      self.currentChannel[1] -= 1
    else:
      self.currentChannel[0] = 4
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , sc)
  
  def channel_right(self):
    cc = RGB(150,150,150)
    sc = RGB(255,255,0)
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , cc)
    if (self.currentChannel[1] > 25): 
          self.currentChannel[1] = 0
    else:
      if self.currentChannel[0] == 4:
        self.currentChannel[0] = 0
        self.currentChannel[1] = 0
      else:
        self.currentChannel[1] += 1
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , sc)

  def channel_up(self):
    cc = RGB(150,150,150)
    sc = RGB(255,255,0)
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , cc)
    if self.currentChannel[0] > 0:
      if self.currentChannel[0] == 2:
        self.currentChannel[1] = 2*self.currentChannel[1]  
      if self.currentChannel[0] == 3:
        self.currentChannel[1] = 3*self.currentChannel[1]+1
      self.currentChannel[0] -= 1
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , sc)
  
  def channel_down(self):
    cc = RGB(150,150,150)
    sc = RGB(255,255,0)
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , cc)
    if self.currentChannel[0] == 0:
      self.currentChannel[0] += 1
    elif self.currentChannel[0] == 1:
      self.currentChannel[0] += 1
      self.currentChannel[1] = int(self.currentChannel[1]/2)
    else:  
      if self.currentChannel[1] < 9: 
        self.currentChannel[1] = int(self.currentChannel[1]/3)        
        self.currentChannel[0] += 1

    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , sc)

    
  def updateChannelColor(self, channel, color):
    pass
       
  def drawSpectrum(self):
    gainScale = 140
    sp = RGB(0,200,0)
    g = self["Graph"]
    ws = create_connection("wss://eshail.batc.org.uk/wb/fft_m0dtslivetune") 
    spectrum = ws.recv()
    g.clear()
    cx = 53
    cy = 358
    g.fill(53, 0, 922, 350, RGB(0,0,0)) 
    for x in range(0,921):
      signal_amp = int((spectrum[2*x]+spectrum[2*x+1]*256) / gainScale)      
      #print("%d %d" % (x,signal_amp))
      #c.fill(x+50, 362, 1,360 - signal_amp , sp) # Spectrum
      g.fill(x+53, 358 - signal_amp ,1, signal_amp , sp) # Spectrum
      g.line(cx,cy,x+53,358 - signal_amp,RGB(255,0,0))
      cx = x+53
      cy = 358 - signal_amp
    #g.clear()
    #g.rline(110,110,210,210,20,clockwise,RGB(0,0,255))
    #print("AFTER...................................>>>")
    g.flush()
    #print(vars(g))
    ws.close()
        
  def tuneToChannel(self):
    #fe_id = int(self.scan_nims.value)
    print("CURRENT CHANNEL [%d][%d] " % (self.currentChannel[0],self.currentChannel[1]))
    print(self.channelTable[self.currentChannel[0]][self.currentChannel[1]])
    Frequency = self.channelTable[self.currentChannel[0]][self.currentChannel[1]][0]
    Symbol_rate = self.channelTable[self.currentChannel[0]][self.currentChannel[1]][1]
    
    transponder = (
          Frequency, # 10491500,
          Symbol_rate, #1500,
          0,
          0,
          2,
          192,
          0,
          1,
          0,
          2,
          -1,
          1,
          0,
          -1,
          4096)
    
#10493500, 333, 0, 0, 2, 192, 0, 1, 0, 2, -1, 1, 0, -1, 4096    
#transponders = ((12515000, 22000000, eDVBFrontendParametersSatellite.FEC_5_6, 192,
#                eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.Inversion_Unknown,
#                eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_QPSK,
#                eDVBFrontendParametersSatellite.RollOff_alpha_0_35, eDVBFrontendParametersSatellite.Pilot_Off),
#                (12070000, 27500000, eDVBFrontendParametersSatellite.FEC_3_4, 235,
#                eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.Inversion_Unknown,
#                eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_QPSK,
#                eDVBFrontendParametersSatellite.RollOff_alpha_0_35, eDVBFrontendParametersSatellite.Pilot_Off),
#                (11727000, 28000000, eDVBFrontendParametersSatellite.FEC_7_8, 3592,
#                eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.Inversion_Unknown,
#                eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_QPSK,
#                eDVBFrontendParametersSatellite.RollOff_alpha_0_35, eDVBFrontendParametersSatellite.Pilot_Off))


#    tlist = []
#    feid = 0
#    flags =0
#    networkid = 0
#    ScanSetup.addSatTransponder(self, tlist,
#                      Frequency, #10491500, # frequency
#                      Symbol_rate, #1500, # sr
#                      0, # pol
#                      0, # fec
#                      2, # inversion
#                      192,
#                      0, # system
#                      1, # modulation
#                      0, # rolloff
#                      2, # pilot
#                      -1,# input stream id
#                      1,# pls mode
#                      0, # pls code
#                      -1, # t2mi_plp_id
#                      4096 # t2mi_pid
#              )
#    self.session.openWithCallback(self.startScanCallback, ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags, "networkid": networkid}])

    ref = self.session.nav.getCurrentlyPlayingServiceReference()
    print("REFERANS--------------------------")
    print("playing now ->", ref and ref.toString())
    ref2 = self.session.nav.getCurrentlyPlayingServiceOrGroup()
    print("playing now2 ->", ref2 and ref2.toString())
    #print(self.playService())

    defaultSat = {                                                                                                                                
      "orbpos": 192,                                                                                                                        
      "system": eDVBFrontendParametersSatellite.System_DVB_S,                                                                               
      "frequency": 11836,                                                                                                                   
      "inversion": eDVBFrontendParametersSatellite.Inversion_Unknown,                                                                       
      "symbolrate": 27500,                                                                                                                  
      "polarization": eDVBFrontendParametersSatellite.Polarisation_Horizontal,                                                              
      "fec": eDVBFrontendParametersSatellite.FEC_Auto,                                                                                      
      "fec_s2": eDVBFrontendParametersSatellite.FEC_9_10,                                                                                   
      "modulation": eDVBFrontendParametersSatellite.Modulation_QPSK                                                                         
    }  

#    self.service = self.session.nav.getCurrentService()
#    if self.service is not None:                                                                                                                  
#      self.feinfo = self.service.frontendInfo()                                                                                             
#      frontendData = self.feinfo and self.feinfo.getAll(True)     
    
    #current_service = self.servicelist.getCurrentSelection()
    #nref = self.resolveAlternatePipService(current_service)
    playingref = self.session.nav.getCurrentlyPlayingServiceReference()
    print("Tuning to Transponer")
    self.startTuner()        
    self.tuner.tune(transponder)
    print("tuned...")
    self.transponder = transponder
    self.playService(playingref)


  def videoReload(self):
    #fav = eServiceReference('1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 195) || (type == 25) FROM BOUQUET "bouquets.tv" ORDER BY bouquet')
    #self["SwitchService"] = ServiceList(fav, command_func = self.zapTo, validate_commands=False)
    #self["ServiceList"] = ServiceList(fav, command_func = self.getServiceList, validate_commands=False)
    #print("FAV ")
    #print(fav.__str__())#, ser_this, 1, 80, 10)
    #pprint(self["SwitchService"], ser_this, 1, 80, 10)
    #pprint(self["ServiceList"], ser_this, 1, 80, 10)

#1:0:1:1:1:FF01:C02903:0:0:0:        -> 10.499.000 @ 333
#1:0:1:1:1:FF01:C028FD:0:0:0:        -> 10.493.000 @ 500
#1:0:1:1:821D:14D:1040000:0:0:0      -> 10.496.750 @ 333
#1:0:1:1:8222:14D:1040000:0:0:0:
#  1:0:1:1:1:FF01:C028FD:0:0:0: ????
  
#1:0:16:1:AAAA:FFFF:C028FC:0:0:0:    -> 10.491.500 @ 1500 A71A
#0001:00c028fb:aaaa:ffff:22:0:0   00c028fb:aaaa:ffff   10491500:1500000:0:0:192:2:0      1:0:16:1:AAAA:FFFF:C028FB:0:0:0:   

#

#lame
#0001:00c02902:0001:ff01:1:0:0  IZ0JNU  p:2110_JNU_stef,f:40                                    1:0:1:1:1:FF01:C02902:0:0:0:
#0001:00c028fb:aaaa:ffff:22:0:0 A71A    p:QARS,c:000101,c:010102,c:030103,c:050001,f:40         1:0:16:1:1:FFFF:C028FB:0:0:0:
       
    playingref = self.session.nav.getCurrentlyPlayingServiceReference()
    print("playingref =")
    print(ServiceReference(playingref).__str__())
#    self.session.nav.playService(playingref)
#    #self.playService(playingref)
    a71aREF = eServiceReference('1:0:1:1:1:FF01:C028FD:0:0:0:')
    self.session.nav.playService(a71aREF)


  def zapTo(self):
    pass

#def zapToService(self, service):                                                                                                               
#                if not service is None:                                                                                                                
#                        self.servicelist.setCurrentSelection(service) #select the service in servicelist                                               
#                        self.servicelist.zap()
    
    

  def playService(self, ref, imitation=False):
    if ref:
      self.qo100service = eServiceCenter.getInstance().play(ref)
      if self.qo100service:
        self.qo100service.start()
        service_name = ServiceReference(ref).getServiceName()
        service_info = ServiceReference(ref).info()
        service_str  = ServiceReference(ref).__str__()
        print("Service Name %s " % service_name)
        print("Service Info %s " % service_info)
        print("Service Str %s " % service_str)
        
        self["myYellowBtn"].setText(service_name)
        #if self.video_state is False:
        #  self["video"].show()
        #  self.video_state = True
        #if not imitation:
          #if hasattr(self, "dishpipDialog") and self.dishpipDialog is not None:
          #        self.dishpipDialog.serviceStarted(ref=ref, pipservice=self.pipservice)
          #if "%3a//" in ref.toString():
          #        tunername = _('Stream')
          #else:
          #        tunername = self.getTunerName()
          #self["NowTuner"].setText(tunername)
        #self.currentService = self.servicelist.getCurrentSelection()
        #self.currentServiceReference = ref
        #self.servicelist.servicelist.setPlayableIgnoreService(ref)
        return True
      #else:
      #  self.pipservice = None
      #  self.currentService = None
      #  self.currentServiceReference = None
      #  self.setDishpipDialog()
      #  self.setPlayableService()
      #  self.PipServiceAvailable = False
      #  self.standartServiceAvailable = True
    return False








       
  def startScanCallback(self, answer=None):
    print("FONKSIYON CALLBACK")
    if answer:
      print("ANSWER")
      self.doCloseRecursive()
  
  def doCloseRecursive(self):
#    if self.session.postScanService and self.frontend:
#      self.frontend = None
#      self.raw_channel = None
#    self.close(True)
    pass
       
       
        
        
#  def startAnalyser(self):
#    self.frqtab = []
#    self.snrtab = []
#    self.agctab = []
#    self.srtab = []
#    self.invtab = []
#    self.modtab = []
#    self.fectab = []
#    self.systab = []
#    self.pilottab = []
#    self.rollofftab = []
#    self.marker = 0
#    self.found = 0
#    text = nimmanager.getNimType(self.tuner)
#    print(text)
#    if text.find('DVB-S')<0:
#      self.text = "No Sat Tuner!"
#      self["myFrequency"].setText(self.text)
#    else: 
#     self.dvb = os.system("%s/bin/scan %d %d" % (satscan_plugindir,self.tuner,self.band)) >> 8
#     if (self.dvb == 0): # 2=DVB-S 
#      result = os.stat(tmpfile)
#      self.found = result.st_size/12 
#      if self.found > 0:
#        file = open(tmpfile, "r")
#        for i in range(self.found):
#          (frq,) = struct.unpack("=H", file.read(2))
#          (snr,) = struct.unpack("=H", file.read(2))
#          (agc,) = struct.unpack("=H", file.read(2))
#          (sr,) = struct.unpack("=H", file.read(2))
#          (inv_fec,) = struct.unpack("=B", file.read(1))
#          inv = inv_fec & 0xf
#          fec = inv_fec >> 4  
#          (mod,) = struct.unpack("=B", file.read(1))
#          (sys_pilot,) = struct.unpack("=B", file.read(1))
#          sys = sys_pilot & 0xf
#          pilot = sys_pilot >> 4
#          (rolloff,) = struct.unpack("=B", file.read(1))
#          self.frqtab.append(frq)
#          self.snrtab.append(snr)
#          self.agctab.append(agc)
#          self.srtab.append(sr)
#          self.invtab.append(inv)
#          self.fectab.append(fec)
#          self.modtab.append(mod)
#          self.systab.append(sys)
#          self.pilottab.append(pilot)
#          self.rollofftab.append(rolloff)
#        file.close()
#      self.bbox()
#     else: 
#      self.text = "Tuner failed !"
#      self["myFrequency"].setText(self.text)


###########################################################################

def main(session, **kwargs):
  session.open(WB_Spectrum)

###########################################################################

def Plugins(**kwargs):
  return PluginDescriptor(
    name="WB Spectrum",
    description="QO-100 WB Transponder Spectrum Viewer",
    where = [PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU],fnc=main)
