#!/usr/bin/python
import os
import subprocess
import ConfigParser
import time
import argparse
from argparse import RawTextHelpFormatter

from subprocess import Popen
from datetime import datetime

startTime = datetime.now()

#===================Set all arguments===============
parser = argparse.ArgumentParser(description='Image ALL OF THE THINGS!')
parser.add_argument('-T' , '-t', '--TaskSet', help='1 For Standard Imaging pipeline', type = int, default = 1, choices = [1])
parser.add_argument('-c', '--Config', help = 'Location of the calibration file. Required, No Deault.', required=True)
parser.add_argument('-l', '--LinmosAll', help = 'A primary beam corrected image is created from each round of selfcal rather than one final image.', action = "store_true")
parser.add_argument('-l', '--Individual', help = 'A primary beam corrected image is created for each pointing rather than one for the whole field', action = "store_true")
args = parser.parse_args()

Config = ConfigParser.ConfigParser()
Config.read(args.Config)

ImagingDetails = {}
ProcList = []

#================= Misc =================

ImagingDetails['MaxProcesses']  = int(Config.get("Misc", "MaxProcesses"))
ImagingDetails['ProjectNum']    = Config.get("Misc", "ProjectNum")
ImagingDetails['Type']          = Config.get("Misc", "Type")
ImagingDetails['Frequency']     = Config.get("Misc", "Frequency")

ImagingDetails['FWHM']          = Config.get("Misc", "FWHM")
ImagingDetails['Cell']          = Config.get("Misc", "Cell")
ImagingDetails['PositionAngle'] = Config.get("Misc", "PositionAngle")

#================= Locations =================

ImagingDetails['SourcePath']      = Config.get("Locations", "SourcePath")
ImagingDetails['DestinationPath'] = Config.get("Locations", "DestinationPath")
ImagingDetails['Images']          = Config.get("Locations", "Images").split(",")

ImagingDetails['DestinationLink'] = Config.get("Locations", "DestinationLink")

#================= Invert =================

ImagingDetails['Imsize'] = Config.get("Invert", "Imsize")
ImagingDetails['Robust'] = Config.get("Invert", "Robust")
ImagingDetails['Stokes'] = Config.get("Invert", "Stokes")

ImagingDetails['Offset']        = Config.get("Invert", "Offset")
ImagingDetails['OffsetName']    = Config.get("Invert", "OffsetName")
ImagingDetails['InvertOptions'] = Config.get("Invert", "InvertOptions")

ImagingDetails['ActiveAntennasName'] = Config.get("Invert", "ActiveAntennasName")
ImagingDetails['ActiveAntennas']     = Config.get("Invert", "ActiveAntennas")

#================= Selfcal =================
#===== Phase =====
 
ImagingDetails['PhaseSelfCalAmount']  = int(Config.get("PhaseSelfCal", "Amount"))
ImagingDetails['PhaseSelfCalOptions'] = Config.get("PhaseSelfCal", "Options")

ImagingDetails['PhaseSelfCalIterations'] = Config.get("PhaseSelfCal", "Iterations")
ImagingDetails['PhaseSelfCalSigma']      = Config.get("PhaseSelfCal", "Sigma").split(",")

ImagingDetails['PhaseSelfCalBin']      = Config.get("PhaseSelfCal", "Bin")
ImagingDetails['PhaseSelfCalInterval'] = Config.get("PhaseSelfCal", "Interval")

#=== Amplitude ===

ImagingDetails['AmplitudeSelfCalAmount']  = int(Config.get("AmplitudeSelfCal", "Amount"))
ImagingDetails['AmplitudeSelfCalOptions'] = Config.get("AmplitudeSelfCal", "Options")

ImagingDetails['AmplitudeSelfCalIterations'] = Config.get("AmplitudeSelfCal", "Iterations")
ImagingDetails['AmplitudeSelfCalSigma']      = Config.get("AmplitudeSelfCal", "Sigma").split(",")

ImagingDetails['AmplitudeSelfCalBin']      = Config.get("AmplitudeSelfCal", "Bin")
ImagingDetails['AmplitudeSelfCalInterval'] = Config.get("AmplitudeSelfCal", "Interval")

#================= MFClean =================

ImagingDetails['MFIterations']  = Config.get("MFClean", "Iterations")
ImagingDetails['MFSigma']       = Config.get("MFClean", "Sigma")
ImagingDetails['MFCleanRegion'] = Config.get("MFClean", "CleanRegion")

#================= Clean =================

ImagingDetails['Iterations']  = Config.get("Clean", "Iterations")
ImagingDetails['Sigma']       = Config.get("Clean", "Sigma")
ImagingDetails['CleanRegion'] = Config.get("Clean", "CleanRegion")

#================= Restor =================

ImagingDetails['RestorOptions'] = Config.get("Restor", "Options")

#================= Linmos =================

ImagingDetails['Bandwidth'] = Config.get("Linmos", "Bandwidth")

#================= End Reading Data =================

def WriteLog(ImagingDetails,TotalTime):
	logFile = open(ImagingDetails["DestinationLink"] + "/" + ImagingDetails["ProjectNum"] + "-ImagingLog.html", "a") 

	#Evernote xml header. 
	logFile.write("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>")
	logFile.write("<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\">")
	logFile.write("<html>")
	logFile.write("<head>")
	logFile.write("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\"/>")
	logFile.write("<meta name=\"exporter-version\" content=\"Evernote Mac 6.0.5 (451190)\"/>")
	logFile.write("<meta name=\"keywords\" content=\"" + ImagingDetails["ProjectNum"] + "\"/>")
	logFile.write("<meta name=\"author\" content=\"krgrieve2@live.com.au\"/>")
	logFile.write("<meta name=\"created\" content=\"" + time.strftime("%Y-%m-%d %I:%M:%S") + " +0000\"/>")
	logFile.write("<meta name=\"source\" content=\"desktop.mac\"/>")
	logFile.write("<meta name=\"updated\" content=\""+ time.strftime("%Y-%m-%d %I:%M:%S") + " +0000\"/>")
	logFile.write("<title>" + ImagingDetails["ProjectNum"] + " Imaging Log </title>")
	logFile.write("</head>")
	logFile.write("<body>")

	logFile.write("<div><b><span style=\"font-size: 16px;\">General</span></b></div>")
	logFile.write("<div>Project Number: {0}</div>".format(ImagingDetails['ProjectNum']))
	logFile.write("<div>Source Folder: {0}</div>".format(ImagingDetails['SourcePath']))
	logFile.write("<div>Destination Folder: {0}</div>".format(ImagingDetails['DestinationPath']))
	logFile.write("<div>Type: {0}</div>".format(ImagingDetails['Type']))
	logFile.write("<div>Images: {0}</div>".format(ImagingDetails['Images']))

	logFile.write("<div>&nbsp</div>")
	logFile.write("<div><b><span style=\"font-size: 16px;\">Invert</span></b></div>")
	logFile.write("<div>Imsize: {0}</div>".format(ImagingDetails['Imsize']))
	logFile.write("<div>Offset: {0}</div>".format(ImagingDetails['Offset']))
	logFile.write("<div>Robust: {0}</div>".format(ImagingDetails['Robust']))
	logFile.write("<div>Frequency: {0}</div>".format(ImagingDetails['Frequency']))
	logFile.write("<div>Stokes: {0}</div>".format(ImagingDetails['Stokes']))
	logFile.write("<div>Antennas Name: {0}</div>".format(ImagingDetails['ActiveAntennasName']))
	logFile.write("<div>Select: {0}</div>".format(ImagingDetails['ActiveAntennas']))
	logFile.write("<div>Invert Options: {0}</div>".format(ImagingDetails['InvertOptions']))

	logFile.write("<div>&nbsp</div>")
	logFile.write("<div><b><span style=\"font-size: 16px;\">Phase Selfcal</span></b></div>")
	logFile.write("<div>Amount: {0}</div>".format(ImagingDetails['PhaseSelfCalAmount']))
	logFile.write("<div>Options: {0}</div>".format(ImagingDetails['PhaseSelfCalOptions']))
	logFile.write("<div>Iterations: {0}</div>".format(ImagingDetails['PhaseSelfCalIterations']))
	logFile.write("<div>Sigma: {0}</div>".format(ImagingDetails['PhaseSelfCalSigma']))
	logFile.write("<div>Bin: {0}</div>".format(ImagingDetails['PhaseSelfCalBin']))
	logFile.write("<div>Interval: {0}</div>".format(ImagingDetails['PhaseSelfCalInterval']))

	logFile.write("<div>&nbsp</div>")
	logFile.write("<div><b><span style=\"font-size: 16px;\">Amplitude Selfcal</span></b></div>")
	logFile.write("<div>Amount: {0}</div>".format(ImagingDetails['AmplitudeSelfCalAmount']))
	logFile.write("<div>Options: {0}</div>".format(ImagingDetails['AmplitudeSelfCalOptions']))
	logFile.write("<div>Iterations: {0}</div>".format(ImagingDetails['AmplitudeSelfCalIterations']))
	logFile.write("<div>Sigma: {0}</div>".format(ImagingDetails['AmplitudeSelfCalSigma']))
	logFile.write("<div>Bin: {0}</div>".format(ImagingDetails['AmplitudeSelfCalBin']))
	logFile.write("<div>Interval: {0}</div>".format(ImagingDetails['AmplitudeSelfCalInterval']))

	logFile.write("<div>&nbsp</div>")
	logFile.write("<div><b><span style=\"font-size: 16px;\">MfClean</span></b></div>")
	logFile.write("<div>Iterations: {0}</div>".format(ImagingDetails['Iterations']))
	logFile.write("<div>Sigma: {0}</div>".format(ImagingDetails['Sigma']))
	logFile.write("<div>Region: {0}</div>".format(ImagingDetails['CleanRegion']))

	logFile.write("<div>&nbsp</div>")
	logFile.write("<div><b><span style=\"font-size: 16px;\">Restor</span></b></div>")
	logFile.write("<div>Options: {0}</div>".format(ImagingDetails['RestorOptions']))

	logFile.write("<div>&nbsp</div>")
	logFile.write("<div><b><span style=\"font-size: 16px;\">Linmos</span></b></div>")
	logFile.write("<div>Bandwidth: {0}</div>".format(ImagingDetails['Bandwidth']))
	
	logFile.write("<div>&nbsp</div>")
	logFile.write("<div><b><span style=\"font-size: 16px;\">Misc</span></b></div>")
	logFile.write("<div>FWHM: {0}</div>".format(ImagingDetails['FWHM']))
	logFile.write("<div>Position Angle: {0}</div>".format(ImagingDetails['PositionAngle']))
	logFile.write("<div>Cell: {0}</div>".format(ImagingDetails['Cell']))
	logFile.write("<div>Time Taken: {0}</div>".format(TotalTime))

	logFile.write("</body>")
	logFile.write("</html>")

	logFile.close()

#Check to see if a particular item/folder exists within a particular folder. default folder to check is current one
def ReadFolder(ItemToFind, Path=os.getcwd()):
	for Files in os.listdir(Path):
		if ItemToFind == Files:
			break;
	else:
		return False;

	return True;

#Check to see how many processes are running at the same time, wait if max limit has been reached. 
def CheckProc(MaxProcesses):
	while len(ProcList) > MaxProcesses:
		time.sleep(3)

		for Proc in ProcList:
	 		if not(Proc.poll() is None):
				ProcList.remove(Proc)

#run the task UVaver
def UVaver(Image, ImagingDetails):
	Out = str(Image) + ".uvaver." + str(ImagingDetails['RoundNum'])

	Task = "uvaver "
	Task = Task + " vis='" + str(ImagingDetails['SourcePath']) + "/" + str(Image) + "'"
	Task = Task + " out='" + ImagingDetails['DestinationLink'] + "/" + str(Out) + "'"

	print Task
	ProcList.append(Popen(Task, shell=True))

#run the task Invert. This pipes to a LogFile (currently no output to terminal)
def Invert(Image, ImagingDetails):
	UVaver = str(Image) + ".uvaver." + str(ImagingDetails['RoundNum'])
	Map = str(Image) + ".map." + str(ImagingDetails['RoundNum'])
	Beam = str(Image) + ".beam." + str(ImagingDetails['RoundNum'])
	LogFile = str(Image) + ".invertlog." + str(ImagingDetails['RoundNum'])

	if  ReadFolder(Map, ImagingDetails['DestinationLink'] + "/") == False and ReadFolder(Beam, ImagingDetails['DestinationLink'] + "/") == False and ReadFolder(LogFile, ImagingDetails['DestinationLink'] + "/") == False:
		Task = "invert "
		Task = Task + " vis='" + UVaver + "'"
		Task = Task + " map='" + Map + "'"
		Task = Task + " beam='" + Beam + "'"
		Task = Task + " imsize='" + str(ImagingDetails['Imsize']) + "'"
		Task = Task + " offset='" + str(ImagingDetails['Offset'])+ "'"
		Task = Task + " robust='" + str(ImagingDetails['Robust']) + "'"
		Task = Task + " select='" + str(ImagingDetails['ActiveAntennas']) + "'"
		Task = Task + " fwhm='" + str(ImagingDetails['FWHM']) + "'"
		Task = Task + " cell='" + str(ImagingDetails['Cell']) + "'"
		Task = Task + " stokes='" + str(ImagingDetails['Stokes']) + "'"
		Task = Task + " options='" + str(ImagingDetails['InvertOptions']) + "'"
		Task = Task + " > " + LogFile
		
		print Task
		ProcList.append(Popen(Task, shell=True))

#run the task MFClean. This reads the invert log file and then gets the Theoretical RMS to then times by an amount (i.e 5 sigma) to se the clean cutoff level.
def MFClean(Image, ImagingDetails, SelfCal):
	Map = str(Image) + ".map." + str(ImagingDetails['RoundNum'])
	Beam = str(Image) + ".beam." + str(ImagingDetails['RoundNum'])
	Model = str(Image) + ".model." + str(ImagingDetails['RoundNum'])
	LogFile = str(Image) + ".invertlog." + str(ImagingDetails['RoundNum'])
	RegionFile = str(Image) + "." + ImagingDetails['OffsetName'] + ".region"  #Destination/0001-0001.2100.05.17_-66.58.region
	
	TheoreticalRMS = ""
	TheoreticalRMSArray = []

	LogFileArray = open(LogFile)

	for LogFileLine in LogFileArray:
		if "Theoretical" in LogFileLine:
			TheoreticalRMSArray = LogFileLine.split(" ")
			TheoreticalRMS = TheoreticalRMSArray[3]
	
	Task = "mfclean "
	Task = Task + " map='" + Map + "'"
	Task = Task + " beam='" + Beam + "'"
	Task = Task + " out='" + Model + "'"
	
	#Set the stopping conditions 
	if SelfCal == True:
		Task = Task + " niters='" + str(ImagingDetails['SelfCalIterations']) + "'"
		Task = Task + " cutoff='" + str(float(ImagingDetails['SelfCalSigma']) * float(TheoreticalRMS)) + "'"
	else:
		Task = Task + " niters='" + str(ImagingDetails['MFIterations']) + "'"
		Task = Task + " cutoff='" + str(float(ImagingDetails['MFSigma']) * float(TheoreticalRMS)) + "'"

	#Set the area to clean/selfcal on. 
	if SelfCal == True and ReadFolder(RegionFile[RegionFile.find('/')+1:],ImagingDetails['DestinationLink']) == True:
		Task = Task + " region='@" + str(RegionFile) + "'"
	else:
		Task = Task + " region='" + str(ImagingDetails['MFCleanRegion']) + "'" 

	print Task
	ProcList.append(Popen(Task, shell=True))				

#run the task MFClean. This reads the invert log file and then gets the Theoretical RMS to then times by an amount (i.e 5 sigma) to se the clean cutoff level.
def Clean(Image, ImagingDetails, SelfCal):
	Map = str(Image) + ".map." + str(ImagingDetails['RoundNum'])
	Beam = str(Image) + ".beam." + str(ImagingDetails['RoundNum'])
	Model = str(Image) + ".model." + str(ImagingDetails['RoundNum'])
	LogFile = str(Image) + ".invertlog." + str(ImagingDetails['RoundNum'])
	RegionFile = str(Image) + "." + ImagingDetails['OffsetName'] + ".region"  #Destination/0001-0001.2100.05.17_-66.58.region
	
	TheoreticalRMS = ""
	TheoreticalRMSArray = []

	LogFileArray = open(LogFile)

	for LogFileLine in LogFileArray:
		if "Theoretical" in LogFileLine:
			TheoreticalRMSArray = LogFileLine.split(" ")
			TheoreticalRMS = TheoreticalRMSArray[3]
	
	Task = "clean "
	Task = Task + " map='" + Map + "'"
	Task = Task + " beam='" + Beam + "'"
	Task = Task + " out='" + Model + "'"
	
	#Set the stopping conditions 
	if SelfCal == True:
		Task = Task + " niters='" + str(ImagingDetails['SelfCalIterations']) + "'"
		Task = Task + " cutoff='" + str(float(ImagingDetails['SelfCalSigma']) * float(TheoreticalRMS)) + "'"
	else:
		Task = Task + " niters='" + str(ImagingDetails['Iterations']) + "'"
		Task = Task + " cutoff='" + str(float(ImagingDetails['Sigma']) * float(TheoreticalRMS)) + "'"

	#Set the area to clean/selfcal on. 
	if SelfCal == True and ReadFolder(RegionFile[RegionFile.find('/')+1:],ImagingDetails['DestinationLink']) == True:
		Task = Task + " region='@" + str(RegionFile) + "'"
	else:
		Task = Task + " region='" + str(ImagingDetails['CleanRegion']) + "'" 

	print Task
	ProcList.append(Popen(Task, shell=True))				

#run the task SelfCal
def SelfCal(Image, ImagingDetails):
	UVaver = str(Image) + ".uvaver." + str(ImagingDetails['RoundNum'])
	Model = str(Image) + ".model." + str(ImagingDetails['RoundNum'])

	Task = "selfcal "
	Task = Task + " vis='"+ UVaver + "'"
	Task = Task + " model='" + Model + "'"
	Task = Task + " interval='" + str(ImagingDetails['SelfCalInterval']) + "'"
	Task = Task + " options='" + str(ImagingDetails['SelfCalOptions']) + "'"
		
	print Task
	ProcList.append(Popen(Task, shell=True))

#Run the task UVaver
def UVaverSelfCal(Image, ImagingDetails):
	Vis = str(Image) + ".uvaver." + str(ImagingDetails['RoundNum'])
	Out = str(Image) + ".uvaver." + str(ImagingDetails['RoundNum'] + 1)

	Task = "uvaver "
	Task = Task + " vis='" + Vis + "'"
	Task = Task + " out='" + Out + "'"

	print Task
	ProcList.append(Popen(Task, shell=True))

#Run the task Restor
def Restor(Image, ImagingDetails):
	Map = str(Image) + ".map." + str(ImagingDetails['RoundNum'])
	Beam = str(Image) + ".beam." + str(ImagingDetails['RoundNum'])
	Model = str(Image) + ".model." + str(ImagingDetails['RoundNum'])
	Restor = str(Image) + ".restor." + str(ImagingDetails['RoundNum'])

	Task = "restor "
	Task = Task + " map='" + Map + "'"
	Task = Task + " beam='" + Beam + "'"
	Task = Task + " model='" + Model + "'"
	Task = Task + " out='" + Restor + "'"
	Task = Task + " options='" + ImagingDetails['RestorOptions'] + "'"
	Task = Task + " fwhm='" + str(ImagingDetails['FWHM']) + "'" 
	Task = Task + " pa='" + str(ImagingDetails['PositionAngle']) + "'"

	print Task
	ProcList.append(Popen(Task, shell=True))

#Run the task Linmos
def Linmos(Image="", ImagingDetails):
	Linmos = ImagingDetails['DestinationLink'] 
	Linmos += "/"  + str(ImagingDetails['ProjectNum']) 
	Linmos += ".R-" + str(ImagingDetails['Robust'])
	Linmos += ".S-" + str(ImagingDetails['Stokes'])
	Linmos += "." + str(ImagingDetails['ActiveAntennasName'])
	Linmos += ".Pha-" + str(ImagingDetails['PhaseSelfCalAmount'])
	Linmos += ".Amp-" + str(ImagingDetails['AmplitudeSelfCalAmount'])
	Linmos += "." + str(ImagingDetails['OffsetName'])
	Linmos += ".pbcorr." + str(ImagingDetails['RoundNum']) 

	Task = "linmos "

	if args.Individual == True:
		Task = Task + " in='" + str(Image) + ".restor." + str(ImagingDetails['RoundNum']) + "'"
	else:
		Task = Task + " in='" + ImagingDetails['DestinationLink'] + "/*restor." + str(ImagingDetails['RoundNum']) + "'"

	Task = Task + " out='" + Linmos + "'"
	Task = Task + " bw='" + str(ImagingDetails['Bandwidth']) + "'"

	print Task
	ProcList.append(Popen(Task, shell=True))

#===================================================================================================================================
#========Standard Imaging Pipeline. UVaver, Invert, (MFClean or Clean), SelfCal (optional - send to start. ), Restor, Linmos========
#===================================================================================================================================
def StandardImaging(ImagingDetails):
	ImagingDetails['RoundNum'] = 1

	#===============Run UVaver to apply Calibrators and Copy the region File to the destination=================

	for ImageName in ImagingDetails['Images']:
		#this loop copies the uv files and the region files from the source folder to the destination folder to perform the work.

		#Copy Region File
		RegionFile = str(ImageName) + "." + ImagingDetails['Frequency'] + "." + ImagingDetails['OffsetName'] + ".region"  	

		print "cp " + ImagingDetails['SourcePath'] + "/" + str(RegionFile) + " " + ImagingDetails['DestinationLink'] + "/" + str(RegionFile)
		os.system("cp " + ImagingDetails['SourcePath'] + "/" + str(RegionFile) + " " + ImagingDetails['DestinationLink'] + "/" + str(RegionFile)) 

		#perform the uvaver on the files
		CheckProc(ImagingDetails['MaxProcesses'])
		UVaver(ImageName + "." + str(ImagingDetails['Frequency']), ImagingDetails);
	CheckProc(0)

	#set a default amount incase the following for loop is skipped. 
	ImagingDetails['SelfCalAmount'] = 0
	
	for RoundNum in range(1,ImagingDetails['PhaseSelfCalAmount'] + ImagingDetails['AmplitudeSelfCalAmount'] + 1):
		#Assign the options depending on what round we are processing.
		ImagingDetails['RoundNum'] = RoundNum

		# functions (such as mfclean and selfcal will use the values stored below. They will be allied dynamically depedning on what type of self cal is taking place. )
		if RoundNum <= ImagingDetails['PhaseSelfCalAmount']:
			ImagingDetails['SelfCalAmount'] = ImagingDetails['PhaseSelfCalAmount']
			ImagingDetails['SelfCalOptions'] = ImagingDetails['PhaseSelfCalOptions']

			ImagingDetails['SelfCalIterations'] = ImagingDetails['PhaseSelfCalIterations']
			ImagingDetails['SelfCalSigma'] = ImagingDetails['PhaseSelfCalSigma'][RoundNum - 1]

			ImagingDetails['SelfCalBin'] = ImagingDetails['PhaseSelfCalBin']
			ImagingDetails['SelfCalInterval'] = ImagingDetails['PhaseSelfCalInterval']
		else:
			ImagingDetails['SelfCalAmount'] = ImagingDetails['AmplitudeSelfCalAmount']
			ImagingDetails['SelfCalOptions'] = ImagingDetails['AmplitudeSelfCalOptions']

			ImagingDetails['SelfCalIterations'] = ImagingDetails['AmplitudeSelfCalIterations']
			ImagingDetails['SelfCalSigma'] = ImagingDetails['AmplitudeSelfCalSigma'][RoundNum - ImagingDetails['PhaseSelfCalAmount'] - 1]

			ImagingDetails['SelfCalBin'] = ImagingDetails['AmplitudeSelfCalBin']
			ImagingDetails['SelfCalInterval'] = ImagingDetails['AmplitudeSelfCalInterval']


		#===============Run Invert==================
		for ImageName in ImagingDetails['Images']:
			ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
			CheckProc(ImagingDetails['MaxProcesses'])
			Invert(ImageName, ImagingDetails);
		CheckProc(0)

		#===============Run MFClean==================
		for ImageName in ImagingDetails['Images']:
			ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
			CheckProc(ImagingDetails['MaxProcesses'])

			if ImagingDetails['Type'] == "PreCabb":
				Clean(ImageName, ImagingDetails, True);
			else:
				MFClean(ImageName, ImagingDetails, True);
		CheckProc(0)

		if args.LinmosAll == True:
			for ImageName in ImagingDetails['Images']:
				ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
				CheckProc(ImagingDetails['MaxProcesses'])
				Restor(ImageName, ImagingDetails);
			CheckProc(0)

			#===============Run Linmos==================
			if args.Individual == True
				for ImageName in ImagingDetails['Images']:
					ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
					CheckProc(ImagingDetails['MaxProcesses'])
					Linmos(ImageName, ImagingDetails);
				CheckProc(0)
			else:
				Linmos("", ImagingDetails);

		#===============Run SelfCal==================
		for ImageName in ImagingDetails['Images']:
			ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
			CheckProc(ImagingDetails['MaxProcesses'])
			SelfCal(ImageName, ImagingDetails);
		CheckProc(0)

		#===============Run UVaver to apply SelfCal==================
		for ImageName in ImagingDetails['Images']:
			ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
			CheckProc(ImagingDetails['MaxProcesses'])
			UVaverSelfCal(ImageName, ImagingDetails);
		CheckProc(0)

	#======================================================================================
	#============================Start the Final Imaging===================================
	#======================================================================================

	if ImagingDetails['SelfCalAmount'] >= 1:
		ImagingDetails['RoundNum'] += 1

	#===============Run Invert==================
	for ImageName in ImagingDetails['Images']:
		ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
		CheckProc(ImagingDetails['MaxProcesses'])
		Invert(ImageName, ImagingDetails);
	CheckProc(0)

	#===============Run MFClean==================
	for ImageName in ImagingDetails['Images']:
		ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
		CheckProc(ImagingDetails['MaxProcesses'])
		
		if ImagingDetails['Type'] == "PreCabb":
				Clean(ImageName, ImagingDetails, False);
		else:
			MFClean(ImageName, ImagingDetails, False);
	CheckProc(0)

	#===============Run Restor==================
	for ImageName in ImagingDetails['Images']:
		ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
		CheckProc(ImagingDetails['MaxProcesses'])
		Restor(ImageName, ImagingDetails);
	CheckProc(0)

	#===============Run Linmos==================
	if args.Individual == True
		for ImageName in ImagingDetails['Images']:
			ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
			CheckProc(ImagingDetails['MaxProcesses'])
			Linmos(ImageName, ImagingDetails);
		CheckProc(0)
	else:
		Linmos("", ImagingDetails);

#========================Finish Standard CABB Imaging =====================================


#========================Make the symlinks and the detination path=========================

if ReadFolder(ImagingDetails['DestinationPath']) == False:
	os.system("mkdir " + ImagingDetails['DestinationPath'])

if ReadFolder(ImagingDetails['DestinationLink']) == False:
	os.system("ln -s " + ImagingDetails['DestinationPath'] + "/ " + ImagingDetails['DestinationLink'])

ImagingDetails['MaxProcesses'] -= 1

#========================If all files are wanted from the source then it will build the image list================

#if ImagingDetails['Images'] == "*":



#using the arguments from the usercall, run a selection of imaging tasks.
if args.TaskSet == 1:
	StandardImaging(ImagingDetails);

CheckProc(0);

#Write the Log file in a html format to import into Evernote 
WriteLog(ImagingDetails,str(datetime.now()-startTime))
os.system("rm " + ImagingDetails['DestinationLink'])

print(      "\n\n\n\n+=========================Finished=========================+\n"       )
print("|        Time Taken    = " + str(datetime.now()) + "        |")
print("|        Time Finished = " + str(datetime.now()-startTime) + "                    |")
print(            "\n+==========================================================+\n"       )


















