﻿'''

April 2016 
Aneesh Rangnekar, Anna Starynska, Arun K., Mahshad M., Sanketh Moudgalya, Rakshit Kothari
Gabriel Diaz 
Carlson Center for Imaging Science
Rochester Institute of Technology

'''

import viz

viz.fov(40,1.77)


viz.res.addPath('resources')
sys.path.append('utils')

import oculus
import vizconnect
import platform
import os.path
import vizact
import vizshape
import cv2
import viztask
import math

from configobj import ConfigObj
from configobj import flatten_errors
from validate import Validator
from PIL import Image

class Configuration():
	
	def __init__(self, expCfgName = ""):
		"""
		Opens and interprets both the system config (as defined by the <platform>.cfg file) and the experiment config
		(as defined by the file in expCfgName). Both configurations MUST conform the specs given in sysCfgSpec.ini and
		expCfgSpec.ini respectively. It also initializes the system as specified in the sysCfg.
		"""		
		self.__createSysCfg()
		
		for pathName in self.sysCfg['set_path']:
			viz.res.addPath(pathName)
		
			
		self.vizconnect = vizconnect.go( 'vizConnect/' + self.sysCfg['vizconfigFileName'])
		self.__postVizConnectSetup()
		
	def __postVizConnectSetup(self):
		''' 
		This is where one can run any system-specific code that vizconnect can't handle
		'''
		dispDict = vizconnect.getRawDisplayDict()
		
		self.clientWindow = dispDict['exp_display']
		self.riftWindow = dispDict['rift_display']
		
		if( self.sysCfg['use_wiimote']):
			# Create wiimote holder
			self.wiimote = 0
			self.__connectWiiMote()

		if self.sysCfg['use_phasespace']:
			
			from mocapInterface import phasespaceInterface			
			self.mocap = phasespaceInterface(self.sysCfg);
			self.linkObjectsUsingMocap()
			
			self.use_phasespace = True
		else:
			self.use_phasespace = False
		
		if self.sysCfg['use_hmd'] and self.sysCfg['hmd']['type'] == 'DK2':
			#self.__setupOculusMon()
			self.hmd = oculus.Rift()
			self.setupExperimenterDisplay()
			self.placeEyeNodes()
			
		viz.setOption("viz.glfinish", 1)
		viz.setOption("viz.dwm_composition", 0)
		
	def __createSysCfg(self):
		"""
		Set up the system config section (sysCfg)
		"""
		# Get machine name
		#sysCfgName = platform.node()+".cfg"
		sysCfgName = "sysConfig"+".cfg"
		
		if not(os.path.isfile(sysCfgName)):
			sysCfgName = "defaultSys.cfg"
			
		
		print "Loading system config file: " + sysCfgName
		
		# Parse system config file
		sysCfg = ConfigObj(sysCfgName, configspec='sysCfgSpec.ini', raise_errors = True)
		
		validator = Validator()
		sysCfgOK = sysCfg.validate(validator)
		
		if sysCfgOK == True:
			print "System config file parsed correctly"
		else:
			print 'System config file validation failed!'
			res = sysCfg.validate(validator, preserve_errors=True)
			for entry in flatten_errors(sysCfg, res):
			# each entry is a tuple
				section_list, key, error = entry
				if key is not None:
					section_list.append(key)
				else:
					section_list.append('[missing section]')
				section_string = ', '.join(section_list)
				if error == False:
					error = 'Missing value or section.'
				print section_string, ' = ', error
			sys.exit(1)
		self.sysCfg = sysCfg
	
	def setupExperimenterDisplay(self):

		viz.window.setFullscreenMonitor(self.sysCfg['experimenterDisplay'])
		viz.window.setFullscreen(1)
			
	def __connectWiiMote(self):
		
		wii = viz.add('wiimote.dle')#Add wiimote extension
		
		# Replace old wiimote
		if( self.wiimote ):
			print 'Wiimote removed.'
			self.wiimote.remove()
			
		self.wiimote = wii.addWiimote()# Connect to first available wiimote
		
		vizact.onexit(self.wiimote.remove) # Make sure it is disconnected on quit
		
		self.wiimote.led = wii.LED_1 | wii.LED_4 #Turn on leds to show connection
	
		
				
	def linkObjectsUsingMocap(self):
			
			self.headTracker = vizconnect.getRawTracker('head_tracker')
			self.mocap.start_thread()
			
			trackerDict = vizconnect.getTrackerDict()
			
			if( 'rift_tracker' in trackerDict.keys() ):
				
				self.UpdateViewAct = vizact.onupdate(viz.PRIORITY_LINKS, self.updateHeadTracker)
				
			else:
				print '*** Experiment:linkObjectsUsingMocap: Rift not enabled as a tracker'
				return
			
	def updateHeadTracker(self):
		"""
		A specailized per-frame function
		That updates an empty viznode with:
		- position info from mocap
		- orientation from rift
		
		"""

		riftOriTracker = vizconnect.getTracker('rift_tracker').getNode3d()			
		
		ori_xyz = riftOriTracker.getEuler()
		self.headTracker.setEuler( ori_xyz  )
		
		headRigidTracker = self.mocap.get_rigidTracker('hmd')	
		self.headTracker.setPosition( headRigidTracker.get_position() )	
		
	def resetHeadOrientation(self):

		vizconnect.getTracker('rift_tracker').resetHeading()
	
	def placeEyeNodes(self):
		'''
		For convenience, this places nodes at the cyclopean eye, left eye, and right eye.
		When linkjing things to the eyes, link them to the cyclopean, left, or right eye nodes
		e.g. viz.link(config.cycEyeNode,vizshape.addSphere(radius=0.05))
		'''
		
		IOD = self.hmd.getIPD() 
		print("IOD")
		print(IOD)
		
		self.cycEyeNode = vizshape.addSphere(0.015, color = viz.GREEN)
		self.cycEyeNode.setParent(self.headTracker)
		self.cycEyeNode.disable(viz.RENDERING)
		
		self.leftEyeNode = vizshape.addSphere(0.005, color = viz.BLUE)
		self.leftEyeNode.disable(viz.RENDERING)
		self.leftEyeNode.setParent(self.headTracker)
		self.leftEyeNode.setPosition(-IOD/2, 0, 0.0,viz.ABS_PARENT)
		
		self.rightEyeNode = vizshape.addSphere(0.005, color = viz.RED)
		self.rightEyeNode.disable(viz.RENDERING)
		self.rightEyeNode.setParent(self.headTracker)
		self.rightEyeNode.setPosition(IOD/2, 0, 0.0,viz.ABS_PARENT)

		
################################################################################
################################################################################
## Here is where the magic happens

def printEyePositions():
	'''
	Print eye positions in global coordinates
	'''
	
	print 'Left eye: ' + str(config.leftEyeNode.getPosition(viz.ABS_GLOBAL))
	print 'Right eye: ' + str(config.rightEyeNode.getPosition(viz.ABS_GLOBAL))
	print 'Cyclopean eye: ' + str(config.cycEyeNode.getPosition(viz.ABS_GLOBAL))
	
	
config = Configuration()

vizact.onkeydown('o', config.resetHeadOrientation)


if( config.sysCfg['use_phasespace'] ):
	vizact.onkeydown('s', config.mocap.saveRigid,'hmd')
	vizact.onkeydown('r', config.mocap.resetRigid,'hmd')
	print 'Using Phasespace'
else:
	viz.MainView.setPosition([0,1.6,0])
	print 'Using Vizard world view'

viz.go

###############################################################################
################################################################################
################start playing around from here  ################################

def PIL_TO_VIZARD(image,texture):
	
	"""Copy the PIL image to the Vizard texture"""
	im = image.transpose(Image.FLIP_TOP_BOTTOM)
	texture.setImageData(im.convert('RGB').tobytes(),im.size)

# uncomment this to use standard approach
'''
m = 1280
n = 720
d = 449
s = 1.75*10**-6
scale = 10000

focalLen = d*s*scale
planeWidth = m*s*scale
planeHeight = n*s*scale
'''
focalLen = 7 #meter
planeWidth = 2*focalLen*math.tan(111.316*3.14/(2*180))
planeHeight = 2*focalLen*math.tan(74.34*3.14/(2*180))

pl_left = vizshape.addPlane(
		size = [planeWidth,planeHeight],
		axis = -vizshape.AXIS_Z,
		cullFace = False
		)

pl_right = vizshape.addPlane(
		size = [planeWidth,planeHeight],
		axis = -vizshape.AXIS_Z,
		cullFace = False
		)

pl_left.setParent(config.leftEyeNode)
pl_left.setPosition([0,0,focalLen],viz.ABS_PARENT)

pl_right.setParent(config.rightEyeNode)
pl_right.setPosition([0,0,focalLen],viz.ABS_PARENT)

# Generate blank texture and apply them on a Quad
tex_r = viz.addBlankTexture([planeWidth, planeHeight])
#quad_r = viz.addTexQuad(pos = ([0,0,focalLen]),size = [planeWidth, planeHeight],texture = tex_r, parent = config.rightEyeNode)

tex_l = viz.addBlankTexture([planeWidth, planeHeight])
#quad_l = viz.addTexQuad(pos = ([0,0,focalLen]),size = [planeWidth, planeHeight],texture = tex_l, parent = config.leftEyeNode)  #tex_l change and run again!
headEuler_YPR = config.headTracker.getEuler()

pl_left.texture(tex_l)
pl_right.texture(tex_r)

pl_left.setEuler([headEuler_YPR[0],0+headEuler_YPR[1],90+headEuler_YPR[2]])
pl_right.setEuler([headEuler_YPR[0],0+headEuler_YPR[1],90+headEuler_YPR[2]])

capture_r = cv2.VideoCapture(0)
capture_l = cv2.VideoCapture(1)

capture_r.set(3,1280)
capture_r.set(4,720)
capture_r.set(5,30)

capture_l.set(3,1280)
capture_l.set(4,720)
capture_l.set(5,30)

def renderingCamera():
	
	ret_r, frame_r = capture_r.read()
	ret_l, frame_l = capture_l.read()
		
	frame_r = cv2.cvtColor(frame_r, cv2.COLOR_BGR2RGB)
	frame_l = cv2.cvtColor(frame_l, cv2.COLOR_BGR2RGB)
	
	height_r, width_r, channels_r = frame_r.shape
	height_l, width_l, channels_l = frame_l.shape
	pil_r = Image.frombytes("RGB", [width_r,height_r], frame_r.tostring())
	pil_l = Image.frombytes("RGB", [width_l,height_l], frame_l.tostring())

	PIL_TO_VIZARD(pil_r,tex_r)
	PIL_TO_VIZARD(pil_l,tex_l)
	
	pl_left.renderToEye(viz.LEFT_EYE)
	pl_right.renderToEye(viz.RIGHT_EYE)
	
vizact.onupdate(viz.PRIORITY_MEDIA,renderingCamera)

def showBoxOnEyes(tableIn):
	tableTracker = config.mocap.get_rigidTracker('table')#gets the table location and orientation from Phasespace
	loc_table = tableTracker.get_position() #this stores the location in a list for modifying
		 
	tableIn.setPosition(loc_table[0], loc_table[1]/2.0, loc_table[2])
	
	ori_table = tableTracker.get_euler()
	tableIn.setEuler(ori_table)

#table = vizshape.addBox([0.460,0.66,0.60],splitFaces=False)
#vizact.onupdate(viz.PRIORITY_LINKS,showBoxOnEyes,table)

# uncomment this to show piazza
#piazza = viz.addChild('piazza.osgb')

### CODE NOT NEEDED

'''
def showImageToOneEye():
	ow
	s = 1000
	focalLen = 0.00081566 * s
	planeWidth = 0.00126 * s
	planeHeight = 0.0022 * s
	camcenter_dX = (640-606.3966)*1.75*(10^-6) * s`
	camcenter_dY = (360-310.6875)*1.75*(10^-6) * s

	br = vizshape.addPlane(
		size = [planeHeight,planeWidth],
		axis = vizshape.AXIS_Z,
		cullFace = False
	)
	
	pic = viz.addTexture('imcalib30_corr.jpg')
	br.texture(pic)
	
	br.setParent(config.rightEyeNode)
	br.setPosition([0,0,focalLen],viz.ABS_PARENT)
	
	br.setEuler([180,0,0])
	br.renderToEye(viz.RIGHT_EYE)
'''

'''
def showDuckToBothEyes():
	##  Here is an example of how to place something in front of the left eye, and to make it visible to ONLY the left eye
	binocularRivalDuck = viz.addChild('duck.cfg')
	binocularRivalDuck.setScale([0.25]*3)
	binocularRivalDuck.setParent(config.leftEyeNode)
	binocularRivalDuck.setPosition([0,-.3,2],viz.ABS_PARENT)
	binocularRivalDuck.setEuler([180,0,0])
	## do not write renderToEye(viz.RIGHT_EYE) function if you want to render to both eyes. If both eyes have to show, 
	## keep it as it is 
'''

#_localOffset
	
'''
video = viz.add('VideoCamera.dle')
outP = video.getWebcamNames(available = False)
print(outP)

cam1 = video.addWebcam(id=0, size=(640,480))
cam2 = video.addWebcam(id=1, size=(640,480))


pl_left = vizshape.addPlane(
	size = [planeHeight,planeWidth],
	axis = vizshape.AXIS_Z,
	cullFace = False
)

pl_right = vizshape.addPlane(
	size = [planeHeight,planeWidth],
	axis = vizshape.AXIS_Z,
	cullFace = False
)

pl_left.texture(cam1)

pl_right.texture(cam2)

pl_left.setParent(config.leftEyeNode)
pl_left.setPosition([0,0,focalLen],viz.ABS_PARENT)	

pl_right.setParent(config.rightEyeNode)
pl_right.setPosition([0,0,focalLen],viz.ABS_PARENT)
'''
## Add code to update orientation with changes in head orientation

