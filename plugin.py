##########################################################################

import sys, os, struct

from Screens.Screen import Screen
from Components.Sources.CanvasSource import CanvasSource
from Components.Label import Label
from Components.ActionMap import ActionMap
#from Components.NimManager import nimmanager
from Plugins.Plugin import PluginDescriptor
from enigma import gFont, eTimer
from enigma import RT_HALIGN_RIGHT

from websocket import create_connection

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
    #self.tuner = 0
    #self.band = 0
    Screen.__init__(self, session)
    #self.session.nav.stopService() # try to disable foreground service
    self["Canvas"] = CanvasSource()
    self["Graph"] = CanvasSource()
    self["myTuner"] = Label()
    self["myFrequency"] = Label()
    self["myBand"] = Label()
    self["myRedBtn"] = Label(_("Exit"))
    #self["myGreenBtn"] = Label(_("Start"))
    #self["myYellowBtn"] = Label(_("Tuner"))
    #self["myBlueBtn"] = Label(_("Clear"))
    self["myLeftBtn"] = Label(_(" < "))
    self["myRightBtn"] = Label(_(" > "))
#    self["myCallsign"] = Label(_("Baris DINC - TA7W/OH2UDS"))
    self["myActionMap"] = ActionMap(["SetupActions","ColorActions"],
    {
      "red": self.close,
      "cancel": self.close,
      "ok": self.drawSpectrum, # startAnalyser,
#      "green": self.drawSpectrum, # startAnalyser,
#      "yellow": self.printList, #changeTuner,
#      "blue": self.clearCanvas,
      "right": self.channel_right,
      "left": self.channel_left,
      "up": self.channel_up,
      "down": self.channel_down,
    }, -1)
        
  
    self.channelTablePlaces = {10491500 : 170, 10492750 : 284,  10493000 : 310,  10493250 : 336,  10493500 : 362,  10493750 : 388,  10494000 : 414,  10494250 : 440,  10494500 : 466,  10494750 : 492,  10495000 : 518,  10495250 : 544,  10495500 : 570,  10495750 : 596,  10496000 : 622,  10496250 : 648,  10496500 : 674,  10496750 : 700,  10497000 : 726,  10497250 : 752,  10497500 : 778,  10497750 : 804,  10498000 : 830,  10498250 : 856,  10498500 : 882,  10498750 : 908,  10499000 : 934,  10499250 : 960}
    self.currentChannel = [0, 0]    #this variable will hold the selected (painted) channel row, column
    self.channelTable = [\
      [[10492750,250,25],[10493250,250,25],[10493750,250,25],[10494250,250,25],[10494750,250,25],[10495250,250,25],[10495750,250,25],[10496250,250,25],[10496750,250,25],[10497250,250,25],[10497750,250,25],[10498250,250,25],[10498750,250,25],[10499250,250,25]],\
      [[10492750,333,33],[10493250,333,33],[10493750,333,33],[10494250,333,33],[10494750,333,33],[10495250,333,33],[10495750,333,33],[10496250,333,33],[10496750,333,33],[10497250,333,33],[10497750,333,33],[10498250,333,33],[10498750,333,33],[10499250,333,33]],\
      [[10492750,500,50],[10493250,500,50],[10493750,500,50],[10494250,500,50],[10494750,500,50],[10495250,500,50],[10495750,500,50],[10496250,500,50],[10496750,500,50],[10497250,500,50],[10497750,500,50],[10498250,500,50],[10498750,500,50],[10499250,500,50]],\
      [[10493250,1000,150],[10494750,1000,150],[10496250,1000,150]],\
      [[10491500,1500,160]]\
    ]
    self.channelRow = [[382,6],[390,6],[398,6],[406,6],[390,18]]
    self.bbox()

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
        print(row)
        self.drawChannel(c, channel, row, cc)
    #self.drawChannel(c, self.channelTable1500[0], 5, sc)
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
    print(vars(g))
    
  def channel_left(self):
    cc = RGB(150,150,150)
    sc = RGB(255,255,0)
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , cc)
    if self.currentChannel[1] > 0:
      self.currentChannel[1] -= 1
    else:
      self.currentChannel[0] = 5
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , sc)
  
  def channel_right(self):
    cc = RGB(150,150,150)
    sc = RGB(255,255,0)
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , cc)
    if (self.currentChannel[1] > 12): 
          self.currentChannel[1] = 0
    else:
      if self.currentChannel[0] == 5:
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
      self.currentChannel[0] -= 1
    else:
      self.currentChannel[0] = 3
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , sc)
  
  def channel_down(self):
    cc = RGB(150,150,150)
    sc = RGB(255,255,0)
    self.drawChannel(self["Canvas"], self.channelTable[self.currentChannel[0]][self.currentChannel[1]], self.currentChannel[0] , cc)
    if (self.currentChannel[0] > 2): 
          self.currentChannel[0] = 0
    else:
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
