#!/usr/bin/python2.7
import os
import subprocess
import ConfigParser
import threading
import sys
import time

import numpy as np
import argparse
from argparse import RawTextHelpFormatter

from astropy.io import fits
from astropy.coordinates import SkyCoord
from astropy.coordinates import Angle
from astropy.io.fits import getdata

from subprocess import Popen
from datetime import datetime

startTime = datetime.now()

#=================== Set all arguments ===============
parser = argparse.ArgumentParser(description='Image ALL OF THE THINGS!')
parser.add_argument('-T' , '-t', '--TaskSet', help='1 For Standard Imaging pipeline. 2 For SubBand Imaging. Default = 1', type = int, default = 1, choices = [1,2])
parser.add_argument('-c', '--Config', help = 'Location of the calibration file. Required, No Deault.', required=True)
parser.add_argument('-l', '--LinmosAll', help = 'A primary beam corrected image is created from each round of selfcal rather than one final image. Default = False', action = "store_true")
parser.add_argument('-i', '--Individual', help = 'A primary beam corrected image is created for each pointing rather than one for the whole field. Default = False', action = "store_true")
parser.add_argument('-C', '--CleanUp', help = 'Delete auxiliary files to save space. 0 For no deletion. 1 For deletion of files created during selfcal. 2 For only keeping the end product. Default = 0', type = int, default = 0, choices = [0,1,2])
parser.add_argument('-r', '--Reset', help = 'Remove exisiting Files if they are present. Default = False', action = "store_true")
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
ImagingDetails['DestinationLink'] = Config.get("Locations", "DestinationLink")

ImagingDetails['Images']          = Config.get("Locations", "Images").split(",")

#================= SubBands =================

if args.TaskSet == 2:
	ImagingDetails['SubBandSourceStrength'] = int(Config.get("SubBands", "SourceStrength"))
	ImagingDetails['PrimaryBeam'] = Angle(Config.get("SubBands", "PrimaryBeam") + '\'').degree #arcmins
	ImagingDetails['MinPointings'] = int(Config.get("SubBands", "MinPointings"))

	#================= Catalogue Column Details =================
	ImagingDetails['SourceCatalogue'] = Config.get("CatalogueDetails", "SourceCatalogue")

	ImagingDetails['ColSourceName']    = Config.get("CatalogueDetails", "SourceName")
	ImagingDetails['ColRA']            = Config.get("CatalogueDetails", "RA")
	ImagingDetails['ColDEC']           = Config.get("CatalogueDetails", "DEC")
	ImagingDetails['ColRADegrees']     = Config.get("CatalogueDetails", "RA_Degrees")
	ImagingDetails['ColRADegreesErr']  = Config.get("CatalogueDetails", "RA_Degrees_Err")
	ImagingDetails['ColDECDegrees']    = Config.get("CatalogueDetails", "DEC_Degrees")
	ImagingDetails['ColDECDegreesErr'] = Config.get("CatalogueDetails", "DEC_Degrees_Err")

	ImagingDetails['ColIntegFlux']    = Config.get("CatalogueDetails", "IntegFlux")
	ImagingDetails['ColSigma']        = Config.get("CatalogueDetails", "Sigma")
	ImagingDetails['ColIntegFluxErr'] = Config.get("CatalogueDetails", "IntegFlux_Err")
	ImagingDetails['ColPeakFlux']     = Config.get("CatalogueDetails", "PeakFlux")
	ImagingDetails['ColPeakFluxErr']  = Config.get("CatalogueDetails", "PeakFlux_Err")

	ImagingDetails['ColPA']       = Config.get("CatalogueDetails", "PA")
	ImagingDetails['ColPAErr']    = Config.get("CatalogueDetails", "PA_Err")
	ImagingDetails['ColMajor']    = Config.get("CatalogueDetails", "Major")
	ImagingDetails['ColMajorErr'] = Config.get("CatalogueDetails", "Major_Err")
	ImagingDetails['ColMinor']    = Config.get("CatalogueDetails", "Minor")
	ImagingDetails['ColMinorErr'] = Config.get("CatalogueDetails", "Minor_Err")	

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

def remove_duplicates(values):
    output = []
    seen = set()
    for value in values:
        # If value has not been encountered yet,
        # ... add it to both list and set.
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output

#Check to see how many processes are running at the same time, wait if max limit has been reached. 
def CheckProc(MaxProcesses):
	while len(ProcList) > MaxProcesses:
		time.sleep(3)

		for Proc in ProcList:
	 		if not(Proc.poll() is None):
				ProcList.remove(Proc)

#Read through all the source files that have been provided and find thier central location
def GetPointingInformation(ImagingDetails):
	print "Gathering Pointing Information"
	PointingInformation = []
	
	for Pointing in ImagingDetails['Images']:
		if ReadFolder(Pointing + "." + ImagingDetails['Frequency'], ImagingDetails['SourcePath']) == True:
			LogFileName =  Pointing + "." + ImagingDetails['Frequency'] + ".header.log"

			if ReadFolder(LogFileName, ImagingDetails['SourcePath']) == False:
				os.system("prthd in=" + ImagingDetails['SourcePath'] + "/" + Pointing + "." + ImagingDetails['Frequency'] + " > " + ImagingDetails['SourcePath'] + "/" + LogFileName)

			LogFileArray = open(ImagingDetails['SourcePath'] + "/" + LogFileName)

			for LogFileLine in LogFileArray:
				if "Pointing Centre" in LogFileLine:
					PointingInformation = LogFileLine.split(" ")					

					ImagingDetails['ImageRa'].append(PointingInformation[3])
					ImagingDetails['ImageDEC'].append(PointingInformation[6].replace("\n",""))

def ConvertCoord(Coordinate, Type):
	if Type == "Ra":
		Coordinate = Coordinate.replace(":", "h", 1)
	elif Type == "Dec":
		Coordinate = Coordinate.replace(":", "d", 1)

	Coordinate = Coordinate.replace(":", "m", 1)
	Coordinate = Coordinate + "s"
	return Coordinate

def CleanUp(ImageType, Frequency, RoundNum):
	for ImageName in ImagingDetails['Images']:
		print "rm -r " + str(ImagingDetails['DestinationLink']) + "/" + str(ImageName) + "." + str(Frequency) + "." + str(ImageType) + "." + str(RoundNum)
		os.system("rm -r " + str(ImagingDetails['DestinationLink']) + "/" + str(ImageName) + "." + str(Frequency) + "." + str(ImageType) + "." + str(RoundNum))

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
	RegionFile = str(Image) + "." + ImagingDetails['OffsetName'] + ".region"  #eg: Destination/0001-0001.2100.05.17_-66.58.region
	
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
def Linmos(ImagingDetails, Image=""):
	if args.Individual == True:
		Linmos = "'" + str(Image) + ".pbcorr." + str(ImagingDetails['RoundNum']) + "'"
	else:
		Linmos = ImagingDetails['DestinationLink'] 
		Linmos += "/"  + str(ImagingDetails['ProjectNum']) 
		Linmos += ".R-" + str(ImagingDetails['Robust'])
		Linmos += ".S-" + str(ImagingDetails['Stokes'])
		Linmos += "." + str(ImagingDetails['ActiveAntennasName'])
		Linmos += ".Pha-" + str(ImagingDetails['PhaseSelfCalAmount'])
		Linmos += ".Amp-" + str(ImagingDetails['AmplitudeSelfCalAmount'])
		Linmos += "." + str(ImagingDetails['Frequency'])
		Linmos += ".pbcorr." + str(ImagingDetails['RoundNum']) 
	
	Task = "linmos "

	if args.Individual == True:
		Task = Task + " in='" + str(Image) + ".restor." + str(ImagingDetails['RoundNum']) + "'"
	else:
		Task = Task + " in='" + ImagingDetails['DestinationLink'] + "/*" + str(ImagingDetails['Frequency']) + "*restor." + str(ImagingDetails['RoundNum']) + "'"

	Task = Task + " out='" + Linmos + "'"
	Task = Task + " bw='" + str(ImagingDetails['Bandwidth']) + "'"

	print Task
	ProcList.append(Popen(Task, shell=True))

#=====================================================================================================================================
#======== Standard Imaging Pipeline. UVaver, Invert, (MFClean or Clean), SelfCal (optional - send to start. ), Restor, Linmos ========
#=====================================================================================================================================
def StandardImaging(ImagingDetails):
	ImagingDetails['RoundNum'] = 1

	#=============== Run UVaver to apply Calibrators and Copy the region File to the destination =================

	for ImageName in ImagingDetails['Images']:
		#this loop copies the uv files and the region files from the source folder to the destination folder to perform the work.

		#Copy Region File
		RegionFile = str(ImageName) + "." + ImagingDetails['Frequency'] + "." + ImagingDetails['OffsetName'] + ".region"  	

		if ReadFolder(RegionFile, ImagingDetails['SourcePath']) == True:
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


		#=============== Run Invert ==================
		for ImageName in ImagingDetails['Images']:
			ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
			CheckProc(ImagingDetails['MaxProcesses'])
			Invert(ImageName, ImagingDetails);
		CheckProc(0)

		#=============== Run MFClean ==================
		for ImageName in ImagingDetails['Images']:
			ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
			CheckProc(ImagingDetails['MaxProcesses'])

			if ImagingDetails['Type'] == "PreCabb":
				Clean(ImageName, ImagingDetails, True);
			else:
				MFClean(ImageName, ImagingDetails, True);
		CheckProc(0)

		if args.LinmosAll == True:
			#=============== Run Restor ==================
			for ImageName in ImagingDetails['Images']:
				ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
				CheckProc(ImagingDetails['MaxProcesses'])
				Restor(ImageName, ImagingDetails);
			CheckProc(0)

			#=============== Run Linmos ==================
			if args.Individual == True:
				for ImageName in ImagingDetails['Images']:
					ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
					CheckProc(ImagingDetails['MaxProcesses'])
					Linmos(ImagingDetails, ImageName);
				CheckProc(0)
			else:
				Linmos(ImagingDetails);
				CheckProc(0)

		if args.CleanUp >= 1:
			CleanUp("map", ImagingDetails['Frequency'], str(ImagingDetails['RoundNum']))
			CleanUp("beam", ImagingDetails['Frequency'], str(ImagingDetails['RoundNum']))
			CleanUp("restor", ImagingDetails['Frequency'], str(ImagingDetails['RoundNum']))

		#=============== Run SelfCal ==================
		for ImageName in ImagingDetails['Images']:
			ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
			CheckProc(ImagingDetails['MaxProcesses'])
			SelfCal(ImageName, ImagingDetails);
		CheckProc(0)

		if args.CleanUp >= 2:
			CleanUp("model", ImagingDetails['Frequency'], str(ImagingDetails['RoundNum']))

		#=============== Run UVaver to apply SelfCal ==================
		for ImageName in ImagingDetails['Images']:
			ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
			CheckProc(ImagingDetails['MaxProcesses'])
			UVaverSelfCal(ImageName, ImagingDetails);
		CheckProc(0)

		if args.CleanUp >= 1:
			CleanUp("uvaver", ImagingDetails['Frequency'], str(ImagingDetails['RoundNum']))

	#======================================================================================
	#=========================== Start the Final Imaging ==================================
	#======================================================================================

	if ImagingDetails['SelfCalAmount'] >= 1:
		ImagingDetails['RoundNum'] += 1

	#=============== Run Invert ==================
	for ImageName in ImagingDetails['Images']:
		ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
		CheckProc(ImagingDetails['MaxProcesses'])
		Invert(ImageName, ImagingDetails);
	CheckProc(0)

	if args.CleanUp >= 2:
		CleanUp("uvaver", ImagingDetails['Frequency'], str(ImagingDetails['RoundNum']))

	#=============== Run MFClean ==================
	for ImageName in ImagingDetails['Images']:
		ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
		CheckProc(ImagingDetails['MaxProcesses'])
		
		if ImagingDetails['Type'] == "PreCabb":
				Clean(ImageName, ImagingDetails, False);
		else:
			MFClean(ImageName, ImagingDetails, False);
	CheckProc(0)

	#=============== Run Restor ==================
	for ImageName in ImagingDetails['Images']:
		ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
		CheckProc(ImagingDetails['MaxProcesses'])
		Restor(ImageName, ImagingDetails);
	CheckProc(0)

	if args.CleanUp >= 2:
		CleanUp("map", ImagingDetails['Frequency'], str(ImagingDetails['RoundNum']))
		CleanUp("beam", ImagingDetails['Frequency'], str(ImagingDetails['RoundNum']))
		CleanUp("model", ImagingDetails['Frequency'], str(ImagingDetails['RoundNum']))

	#=============== Run Linmos ==================
	if args.Individual == True:
		for ImageName in ImagingDetails['Images']:
			ImageName = ImagingDetails['DestinationLink'] + "/" + ImageName + "." + str(ImagingDetails['Frequency'])
			CheckProc(ImagingDetails['MaxProcesses'])
			Linmos(ImagingDetails, ImageName);
		CheckProc(0)
	else:
		Linmos(ImagingDetails);
		CheckProc(0)

	if args.CleanUp >= 2:
		CleanUp("restor", ImagingDetails['Frequency'], str(ImagingDetails['RoundNum']))

#======================== Finish Standard CABB Imaging =====================================


#===================================================================================================================================
#======== SubBand Imaging Pipeline. Pointing Selection, Calculate RMS and Signal-to-Noise, Then use Standard CABB Imaging ==========
#===================================================================================================================================
def SubBandImaging(ImagingDetails):
	#reset some values so that we are able to perform the subband imaging
	ImagingDetails['ImageRa']    = []
	ImagingDetails['ImageDEC']   = []
	ImagingDetails['SubBandSourceList'] = []

	GetPointingInformation(ImagingDetails)

	ImagingDetails['OrigDestinationPath'] = ImagingDetails['DestinationPath']
	ImagingDetails['OrigImages'] = ImagingDetails['Images']
	ImagingDetails['OrigFrequency'] = ImagingDetails['Frequency']
	ImagingDetails['OrigSourcePath'] = ImagingDetails['SourcePath']
	
	if ReadFolder(ImagingDetails['DestinationLink']):
		os.system("rm " + ImagingDetails['DestinationLink'])

	#get the strong sources from the provided Catalogue
	CatalogueHeader = fits.open(ImagingDetails['SourceCatalogue'])
	Catalogue = CatalogueHeader[1].data

	#TODO: currently recording the row nums of the source so i can log it later. todo: make logging happen
	for RowNum in range(len(Catalogue)):
		if Catalogue[RowNum][ImagingDetails['ColSigma']] > ImagingDetails['SubBandSourceStrength']:
			ImagingDetails['SubBandSourceList'].append(RowNum)

	print "Finding appropriate pointings and Starting Imaging"

	#loop through all sources 
	for SourceNum, Source in enumerate(ImagingDetails['SubBandSourceList']):
		ImagingDetails['Images'] = []
		SubBandFrequencies = []
		StartingDir = os.getcwd()

		SubBandWidth = 1024

		if Catalogue[SourceNum][ImagingDetails['ColSigma']] > 20:
			SubBandWidth = 512
		elif Catalogue[SourceNum][ImagingDetails['ColSigma']] > 40:
			SubBandWidth = 256

		#loop through all pointings and figure out if any pointing contribute to the source
		for ImageNum, Image in enumerate(ImagingDetails['OrigImages']):
			if ReadFolder(Image + "." + ImagingDetails['Frequency'], ImagingDetails['SourcePath']) == True:
				ImageCoordinates = SkyCoord (ConvertCoord(ImagingDetails['ImageRa'][ImageNum], "Ra"), ConvertCoord(ImagingDetails['ImageDEC'][ImageNum], "Dec"), frame = 'fk5')
				SourceCoordinates = SkyCoord (ConvertCoord(Catalogue[Source][ImagingDetails['ColRA']], "Ra"), ConvertCoord(Catalogue[Source][ImagingDetails['ColDEC']], "Dec"), frame = 'fk5')
				
				Sep = ImageCoordinates.separation(SourceCoordinates)
				Sep = Angle(Sep).degree

				if ImagingDetails['PrimaryBeam'] > Sep: 
					ImagingDetails['Images'].append(Image)

		#if we find some pointings, then image it
		if len(ImagingDetails['Images']) > ImagingDetails['MinPointings']:
			print "=============================================================="
			print "Source: " + str(Catalogue[Source][ImagingDetails['ColSourceName']])
			print "=============================================================="

			ImagingDetails['DestinationPath'] = ImagingDetails['OrigDestinationPath'] + "/" + Catalogue[Source][ImagingDetails['ColSourceName']]
			ImagingDetails['SourcePath'] = ImagingDetails['DestinationPath'] + "/Source" 
			ImagingDetails['ProjectNum'] = Catalogue[Source][ImagingDetails['ColSourceName']]

			#create a folder for each source and a 'Source' folder inside containing the uv files
			if ReadFolder(ImagingDetails['DestinationPath']) == False:
				os.system("mkdir " + ImagingDetails['DestinationPath'])

			if ReadFolder(ImagingDetails['DestinationLink']) == False:
				os.system("ln -s " + ImagingDetails['DestinationPath'] + "/ " + ImagingDetails['DestinationLink'])

			if ReadFolder(ImagingDetails['SourcePath'], ImagingDetails['DestinationPath']) == False:
				os.system("mkdir " + ImagingDetails['SourcePath'])

			for Image in ImagingDetails['Images']:
				os.system("cp -r " + ImagingDetails['OrigSourcePath'] + "/" + Image + "." + ImagingDetails['OrigFrequency'] + " " + ImagingDetails['SourcePath']  )

			os.chdir(ImagingDetails['SourcePath'])

			#split the pointings up into the SubBands
			for Image in ImagingDetails['Images']:
				CheckProc(ImagingDetails['MaxProcesses'])
				
				Task = "uvsplit "
				Task = Task + " vis='" + str(Image) + "." + ImagingDetails['OrigFrequency'] + "'"
				Task = Task + " maxwidth='" + str(float(SubBandWidth)/1000) + "'"

				print Task
				ProcList.append(Popen(Task, shell=True))

			CheckProc(0)

			#small cleanup of full bandwidth file
			for Image in ImagingDetails['Images']:
				os.system("rm -r '" + str(Image) + "." + ImagingDetails['OrigFrequency'] + "'")

			#gather new central frequencies
			for Files in os.listdir(os.getcwd()):
				TempFreq = Files.split(".")
				SubBandFrequencies.append(TempFreq[1])

			SubBandFrequencies = remove_duplicates(SubBandFrequencies)
			os.chdir(StartingDir)

			#Loop through the subband frequencies and start the imaging
			for SubBandFrequency in SubBandFrequencies:
				print "=============================================================="
				print "Frequency: " + str(SubBandFrequency)
				print "=============================================================="

				#run imaging pipeline
				ImagingDetails['Frequency'] = SubBandFrequency
				StandardImaging(ImagingDetails)

				#create input file for aegean from the exisiting catalogue
				if ReadFolder("SourcePosition.fits", ImagingDetails['DestinationPath']) == False:
					col1 = fits.Column(name='ra_str', format='A50', array=np.array([Catalogue[Source][ImagingDetails['ColRA']]]))
					col2 = fits.Column(name='dec_str', format='A50', array=np.array([Catalogue[Source][ImagingDetails['ColDEC']]]))
					
					col3 = fits.Column(name='ra', format='E', array=np.array([Catalogue[Source][ImagingDetails['ColRADegrees']] ]))
					col4 = fits.Column(name='err_ra', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColRADegreesErr']]]))
					col5 = fits.Column(name='dec', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColDECDegrees']]]))
					col6 = fits.Column(name='err_dec', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColDECDegreesErr']]]))

					col7 = fits.Column(name='peak_flux', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColPeakFlux']]]))
					col8 = fits.Column(name='err_peak_flux', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColPeakFluxErr']]]))
					col9 = fits.Column(name='int_flux', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColIntegFlux']]]))
					col10 = fits.Column(name='err_int_flux', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColIntegFluxErr']]]))

					col11 = fits.Column(name='a', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColMajor']]]))
					col12 = fits.Column(name='err_a', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColMajorErr']]]))
					col13 = fits.Column(name='b', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColMinor']]]))
					col14 = fits.Column(name='err_b', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColMinorErr']]]))
					col15 = fits.Column(name='pa', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColPA']]]))
					col16 = fits.Column(name='err_pa', format='D', array=np.array([Catalogue[Source][ImagingDetails['ColPAErr']]]))

					cols = fits.ColDefs([col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12, col13, col14, col15, col16])
					tbhdu = fits.BinTableHDU.from_columns(cols)
					tbhdu.writeto(ImagingDetails['DestinationLink'] + '/SourcePosition.fits')
				
				RoundNum = 0
				SubBandImage = ""

				#convert the primary beam corrected image into a fits image
				for File in os.listdir(ImagingDetails['DestinationLink']):
					if "pbcorr" in File:
						if int(File[-1:]) > RoundNum:
							SubBandImage = File			

				Task = "fits "
				Task = Task + " in='" + ImagingDetails['DestinationLink'] + "/" + SubBandImage + "'"
				Task = Task + " out='" + ImagingDetails['DestinationLink'] + "/" + SubBandImage[:-9] + "." + SubBandImage[-1:] + ".fits'"
				Task = Task + " op='xyout'"

				print Task
				ProcList.append(Popen(Task, shell=True))

				CheckProc(0)

				#run the aegean source finding on the output image on the known source position
				#Task = " /home/16749838/Data/Aegean136/aegean.py "
				Task = " aegean.py "
				Task = Task + " --priorize 3 "
				Task = Task + " --input='" + ImagingDetails['DestinationLink'] + "/SourcePosition.fits'"
				Task = Task + " --cores='" + str(ImagingDetails['MaxProcesses']) + "'"
				Task = Task + " --out='" + str(ImagingDetails['DestinationLink']) + "/Catalogue-" + str(SubBandFrequency) + ".source." + SubBandImage[-1:] + "' "
				Task = Task + " --table='" + str(ImagingDetails['DestinationLink']) + "/Catalogue-" + str(SubBandFrequency) + "." + SubBandImage[-1:] + ".reg" 
				Task = Task + "," + str(ImagingDetails['DestinationLink']) + "/Catalogue-" + str(SubBandFrequency) + "." + SubBandImage[-1:] + ".ann" 
				Task = Task + "," + str(ImagingDetails['DestinationLink']) + "/Catalogue-" + str(SubBandFrequency) + "." + SubBandImage[-1:] + ".fits" + "' '"
				Task = Task + ImagingDetails['DestinationLink'] + "/" + SubBandImage[:-9] + "." + SubBandImage[-1:] + ".fits'" 

				print Task
				ProcList.append(Popen(Task, shell=True))

				CheckProc(0)

			# AegeanCatalogueHeader = fits.open(ImagingDetails['DestinationLink'] + "/Catalogue-" + SubBandFrequencies[0] + "." + SubBandImage[-1:] + "_comp.fits")
			# AegeanCatalogue = AegeanCatalogueHeader[1].data

			# for SubBandFrequencyCount, SubBandFrequency in enumerate(SubBandFrequencies):
			# 	if SubBandFrequencyCount > 0:
			# 		AegeanCatalogueHeaderToAdd = fits.open(ImagingDetails['DestinationLink'] + "/Catalogue-" + SubBandFrequency + "." + SubBandImage[-1:] + "_comp.fits")
			# 		AegeanCatalogueToAdd = AegeanCatalogueHeaderToAdd[1].data



					

			# 		AegeanCatalogueHeaderToAdd.close()

			#AegeanCatalogueHeader.close()




			AegeanData = []
			AegeanHeader = []
			
			#collect all the source information from each subband and concatonate them into one file
			for SubBandFrequency in SubBandFrequencies:
				AegeanHeader.append(getdata(ImagingDetails['DestinationLink'] + "/Catalogue-" + SubBandFrequency + "." + SubBandImage[-1:] + "_comp.fits", 0))
				AegeanData.append(getdata(ImagingDetails['DestinationLink'] + "/Catalogue-" + SubBandFrequency + "." + SubBandImage[-1:] + "_comp.fits", 1))
			print AegeanData
			print AegeanHeader
			fits.writeto(ImagingDetails['DestinationLink'] + "/Catalogue-.All_comp.fits", AegeanData, AegeanHeader)
		
			CheckProc(0)
			os.system("rm " + ImagingDetails['DestinationLink'])

	CatalogueHeader.close()

#======================== Finish SubBand CABB Imaging =====================================


#======================== Make the symlinks and the detination path =========================

if args.Reset == True:
	if len(ImagingDetails['DestinationPath']) > 2:
		os.system("rm -r " + ImagingDetails['DestinationPath'])
		os.system("rm " + ImagingDetails['DestinationLink'])

if ReadFolder(ImagingDetails['DestinationPath']) == False:
	os.system("mkdir " + ImagingDetails['DestinationPath'])

	if ReadFolder(ImagingDetails['DestinationLink']) == False:
		os.system("ln -s " + ImagingDetails['DestinationPath'] + "/ " + ImagingDetails['DestinationLink'])

	ImagingDetails['MaxProcesses'] -= 1

	#TODO: If all files are wanted from the source then it will build the image list, with an override probably ================

	#if ImagingDetails['Images'] == "*":

	#using the arguments from the usercall, run a selection of imaging tasks.
	if args.TaskSet == 1:
		StandardImaging(ImagingDetails);
	elif args.TaskSet == 2:
		SubBandImaging(ImagingDetails);

	CheckProc(0);

	#Write the Log file in a html format to import into Evernote 
	#WriteLog(ImagingDetails,str(datetime.now()-startTime))
	os.system("rm " + ImagingDetails['DestinationLink'])

	print(      "\n\n\n\n+=========================Finished=========================+\n"       )
	print("|        Time Taken    = " + str(datetime.now()) + "        |")
	print("|        Time Finished = " + str(datetime.now()-startTime) + "                    |")
	print(            "\n+==========================================================+\n"       )
else:
	print "Existing Data Found. Quitting. Please use -r to remove the data or rename your destination folder"

