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
parser = argparse.ArgumentParser(description = 'CALIBRATE ALL OF THE THINGS!', formatter_class=RawTextHelpFormatter)
parser.add_argument('-t', '--TaskSet', help = '1) Cabb Calibration \n2) Pre CABB Calibration ', type = int, default = 1, choices = [1,2])
parser.add_argument('-u', '--Unpack', help = 'Manually Fix up the primary calibrator observations before continuing with calibration. This option only performs atlod and uvsplit.', action = "store_true")
parser.add_argument('-j', '--FlagJunk', help = 'Manually select a time to flag for junk primary calibrator observations. This is done initially before calibration and then ignored. This will force it to happen even with prior calibration', action = "store_true")
parser.add_argument('-r', '--ResetAll', help = 'Reset back to a base state', action = "store_true")
parser.add_argument('-R', '--ResetSources', help = 'Reset the source files and re-apply the calibration tables', action = "store_true")
parser.add_argument('-c', '--Config', help = 'Location of the calibration file', default = "CalibrationConfig.ini")
parser.add_argument('-s', '--Source', help = 'Skip calibration steps and only flag source files.', action = "store_true")
#parser.add_argument('-i', '--InteractiveFlag', help = 'Use BLFlag instead of PGFlag', action = "store_true")
args = parser.parse_args()

print args.Config 

Config = ConfigParser.ConfigParser()
Config.read(args.Config)

#get the Imaging Details here. Replace this manual mess with a database call?
CalibrationDetails = {}
ProcList = []

# #================= Misc =================
# #Gaensler Day1
# CalibrationDetails['MaxProcesses'] = 8
# CalibrationDetails['ProjectNum'] = "C1395"
# #CalibrationDetails['Frequencies'] = ["1384"]
# CalibrationDetails['Frequencies'] = ["4800", "8640"]

# CalibrationDetails['PrimaryCalibrators'] = ["1934-638"]
# CalibrationDetails['SecondaryCalibrators'] = ["0515-674","0530-727"]

#================= Misc =================
#Gaensler Day2/Day3
CalibrationDetails['MaxProcesses'] = Config.get("Misc", "MaxProcesses")
CalibrationDetails['ProjectNum'] = "C1395"
#CalibrationDetails['Frequencies'] = ["1384"]
CalibrationDetails['Frequencies'] = ["1384", "1472"]

CalibrationDetails['PrimaryCalibrators'] = ["1934-638"]
CalibrationDetails['SecondaryCalibrators'] = ["0515-674"]

# # #================= Misc =================
# Marx Day1
# CalibrationDetails['MaxProcesses'] = 8
# CalibrationDetails['ProjectNum'] = "C138"
# #CalibrationDetails['Frequencies'] = ["1376", "2378"]
# CalibrationDetails['Frequencies'] = ["1376"]

# CalibrationDetails['PrimaryCalibrators'] = ["1934-638"]
# #CalibrationDetails['SecondaryCalibrators'] = ["0407-658", "0252-712"]
# CalibrationDetails['SecondaryCalibrators'] = ["0407-658"]

#================= Locations =================

CalibrationDetails['RawPath'] = "Raw"
CalibrationDetails['SourcePath'] = "Source"
CalibrationDetails['CalibrationPath'] = "Calibrators"
CalibrationDetails['TempPath'] = "Temp"
CalibrationDetails['InitialFolder'] = os.getcwd()

#================= Atlod =================

CalibrationDetails['Edge'] = ""
CalibrationDetails['AtlodOptions'] = "birdie,noauto,rfiflag,xycorr"

#================= GPCal =================

CalibrationDetails['MFCalReferenceAntenna'] = "4"
CalibrationDetails['MFCalInterval'] = "0.1"

#================= GPCal =================

CalibrationDetails['GPCalReferenceAntenna'] = "4"
CalibrationDetails['GPCalInterval'] = "0.1"
CalibrationDetails['PrimaryGPCalOptions'] = "xyvary"
CalibrationDetails['SecondaryGPCalOptions'] = "xyvary,qusolve"

#================= PGFlag =================

CalibrationDetails['PGFlagStokes'] = ["xy", "yx", "xx,yy", "yy,xx", "i", "q", "u", "v"]
CalibrationDetails['PGFlagCommand'] = "<b<b"
CalibrationDetails['PGFlagOptions'] = "nodisp"

#================= BLFlag =================

CalibrationDetails['BLFlagStokes'] = ["xy", "yx", "xx,yy", "yy,xx", "i", "q", "u", "v"]







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

	if MaxProcesses == 0:
		print "================================================================================"

#check to see if there was flagging after the last round of calibration. Reurns true is calibration is needed. 
def RequireCalibration(Calibrator, CalibrationDetails):
	FlaggingTasksList = ["pgflag", "blflag", "uvflag"]
	CalibrationTasksList = ["mfcal", "gpcal"]

	for CalibrationTask in CalibrationTasksList:
		CalibrationLine, CalibrationLineNumber = SearchCalibrationLog(Calibrator, "RUNNING: " + CalibrationTask, CalibrationDetails)
		CalibrationLineNumber.sort(key=int)

		if len(CalibrationLineNumber) - 1 > -1:
			for FlaggingTask in FlaggingTasksList:
				FlaggingLine, FlaggingLineNumber = SearchCalibrationLog(Calibrator, "RUNNING: " + FlaggingTask, CalibrationDetails)
				FlaggingLineNumber.sort(key=int)

				if len(FlaggingLineNumber) - 1 > -1:
					if CalibrationLineNumber[len(CalibrationLineNumber) - 1] < FlaggingLineNumber[len(FlaggingLineNumber) - 1]:
						return True
		else:
			return True

	return False

#TODO FIX bad/confusing/repeating naming
def CalibrationErrorMessages(Calibrator, CalibrationDetails):
	print "\n======" + str(Calibrator) + "======"

	CalibrationTasksList = ["mfcal", "gpcal"]

	for CalibrationCount, CalibrationTask in enumerate(CalibrationTasksList):
		CalibrationLine, CalibrationLineNumber = SearchCalibrationLog(Calibrator, "RUNNING: " + CalibrationTask, CalibrationDetails)
		CalibrationLineNumber.sort(key=int)

		MaxWarningLineNum = -1

		if CalibrationCount < len(CalibrationTasksList) - 1:
			MaxWarningLine, MaxWarningLineNumber = SearchCalibrationLog(Calibrator, "RUNNING: " + CalibrationTasksList[CalibrationCount + 1], CalibrationDetails)
			MaxWarningLineNumber.sort(key=int)

			MaxWarningLineNum = MaxWarningLineNumber[len(MaxWarningLineNumber) - 1]

		WarningsToShow = []
		WarningsNumberToShow = []

		if len(CalibrationLineNumber) - 1 > -1:
			WarningLines, WarningLinesNumber = SearchCalibrationLog(Calibrator, "### Warning: " , CalibrationDetails)
			WarningLinesNumber.sort(key=int)

			if len(WarningLinesNumber) - 1 > -1:
				for Count, WarningNum in enumerate(WarningLinesNumber):
					if CalibrationLineNumber[len(CalibrationLineNumber) - 1] < WarningNum and (WarningNum < MaxWarningLineNum or MaxWarningLineNum == -1):
						WarningsToShow.append(WarningLines[Count])
						WarningsNumberToShow.append(WarningNum)

		print "\n" + str(CalibrationTask) + " Error messages: "

		for Warnings in WarningsToShow:
			print Warnings.replace("\n", "")

	print ""

#check to see order to of tasks performed on a file. True if the last occurance of the first item is before the last occurance of the second item.
def SearchCalibrationLog(Calibrator, SearchItem, CalibrationDetails):
	FileName = CalibrationDetails['CalibrationPath'] + "/" + Calibrator + ".log"

	RequestedLines = []
	RequestedLinesNumbers = []

	with open(FileName) as f:
		LogFile = f.readlines()

	for LineNumber, Line in enumerate(LogFile):
		if SearchItem in Line:
			RequestedLines.append(Line)
			RequestedLinesNumbers.append(LineNumber)

	return RequestedLines, RequestedLinesNumbers

#collect all the Raw files and load them into a single UV file. 
def Atlod(CalibrationDetails):
	RawFiles = CalibrationDetails['RawPath'] + "/*" + CalibrationDetails['ProjectNum']
	UVFile = CalibrationDetails['ProjectNum'] + ".UV"

	if ReadFolder(UVFile,  CalibrationDetails['TempPath']) == False:
		Task = "atlod "
		Task = Task + " in='" + RawFiles + "'"
		Task = Task + " out='" + CalibrationDetails['TempPath'] + "/" + UVFile + "'"
		Task = Task + " egde='" + str(CalibrationDetails['Edge']) + "'"
		Task = Task + " options='" + str(CalibrationDetails['AtlodOptions']) + "'"
		Task = Task + " >> atlod.log 2>&1"

		logFile = open("atlod.log", "a") 
		logFile.write(Task + "\n")
		logFile.close()
			
		print Task
		os.system(Task)

#Use the single UV file from atlod, split it into its components within a temp directory. 
#move the required calibrators (at a set frequency) to the Calibrators folder.
#Then move the rest at that frequncy to the source folder.
def UVSplit(CalibrationDetails):
	if ReadFolder(CalibrationDetails['PrimaryCalibrators'][0] + "." + CalibrationDetails['Frequencies'][0] , CalibrationDetails['CalibrationPath'] ) == False or args.ResetSources == True:
		UVFile = CalibrationDetails['ProjectNum'] + ".UV"

		Task = "uvsplit "
		Task = Task + " vis='" + UVFile + "'"		

		os.chdir(CalibrationDetails['TempPath'] + "/")	

		print Task
		os.system(Task)

		os.chdir(CalibrationDetails['InitialFolder'])	

		for Frequency in CalibrationDetails['Frequencies']:
			for Primary in CalibrationDetails['PrimaryCalibrators']:
				if args.ResetSources == False:
					os.system("mv " + CalibrationDetails['TempPath'] + "/" + Primary + "." + Frequency + " " + CalibrationDetails['CalibrationPath'] + "/")
				else:
					os.system("rm -r " + CalibrationDetails['TempPath'] + "/" + Primary + "." + Frequency)

			for Secondary in CalibrationDetails['SecondaryCalibrators']:
				if args.ResetSources == False:
					os.system("mv " + CalibrationDetails['TempPath'] + "/" + Secondary + "." + Frequency + " " + CalibrationDetails['CalibrationPath'] + "/")
				else:
					os.system("rm -r " + CalibrationDetails['TempPath'] + "/" + Secondary + "." + Frequency)

			os.system("mv " + CalibrationDetails['TempPath'] + "/*" + Frequency + " " + CalibrationDetails['SourcePath'] + "/")

def MFCal(Calibrator, CalibrationDetails, Type):
	#dont perform this task if there has not been any flagging since the last round of calibration

	if RequireCalibration(Calibrator + "-" + Type, CalibrationDetails) == True:
		Task = "mfcal "
		Task = Task + " vis='" + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "'"
		Task = Task + " refant='" + CalibrationDetails['MFCalReferenceAntenna'] + "'"	
		Task = Task + " interval='" + CalibrationDetails['MFCalInterval'] + "'"	
		Task = Task + " >> " + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "-" + Type + ".log 2>&1"

		logFile = open(CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "-" + Type + ".log", "a") 
		logFile.write("\n\nRUNNING: " + Task + "\n")
		logFile.close()

		print Task
		ProcList.append(Popen(Task, shell=True))

def GPCal(Calibrator, CalibrationDetails, Type):
	#dont perform this task if there has not been any flagging since the last round of calibration

	if RequireCalibration(Calibrator + "-" + Type, CalibrationDetails) == True:
		Task = "gpcal "
		Task = Task + " vis='" + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "'"
		Task = Task + " refant='" + CalibrationDetails['GPCalReferenceAntenna'] + "'"	
		Task = Task + " interval='" + CalibrationDetails['GPCalInterval'] + "'"	

		if Type == "Primary": 
			Task = Task + " options='" + CalibrationDetails['PrimaryGPCalOptions'] + "'"	
		elif Type == "Secondary": 
			Task = Task + " options='" + CalibrationDetails['SecondaryGPCalOptions'] + "'"	

		Task = Task + " >> " + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "-" + Type + ".log 2>&1"

		logFile = open(CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "-" + Type + ".log", "a") 
		logFile.write("\n\nRUNNING: " + Task + "\n")
		logFile.close()

		print Task
		ProcList.append(Popen(Task, shell=True))

def PGFlag(Calibrator, CalibrationDetails, Type):
	for Stokes in CalibrationDetails['PGFlagStokes']:
		CheckProc(CalibrationDetails['MaxProcesses'])

		Task = "pgflag "
		Task = Task + " vis='" + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "'"
		Task = Task + " stokes='" + Stokes + "'"
		Task = Task + " command='" + CalibrationDetails['PGFlagCommand'] + "'"
		Task = Task + " options='" + CalibrationDetails['PGFlagOptions'] + "'"
		Task = Task + " >> " + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "-" + Type + ".log 2>&1"

		logFile = open(CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "-" + Type + ".log", "a") 
		logFile.write("\n\nRUNNING: " + Task + "\n")
		logFile.close()

		print Task
		ProcList.append(Popen(Task, shell=True))

def BLFlag(Calibrator, CalibrationDetails, Type):
	StokesList = CalibrationDetails['BLFlagStokes'][:]
	
	try:
		print "Flagging \n   1) Channel Flagging \n   2) Time Flagging \n   3) Phase Flagging \n   4) Real Imagingary Flagging "
		Flagging = raw_input('Require additional flagging? (y/n or 1,2,3,4): ')
	except SyntaxError:
		Flagging = None

	if Flagging == "y" or Flagging == "Y" or Flagging == "1" or Flagging == "2" or Flagging == "3" or Flagging == "4":
		if Flagging == "y" or Flagging == "Y":
			Flagging = "1"

		try:
			print "Type \n   1) Baseline Averaging \n   2) Dispalay Each Baseline Seperately"
			Flagging = Flagging + raw_input('Require additional flagging? (1,2): ')
		except SyntaxError:
			Flagging = Flagging + "1"

		if Flagging[0] == "1":
			Axis = "chan,amp"
		elif Flagging[0] == "2":
			Axis = "time,amp"
		elif Flagging[0] == "3":
			Axis = "phase,amp"
			StokesList.append("xx")			
			StokesList.append("yy")
		elif Flagging[0] == "4":
			Axis = "real,imag"
			StokesList.append("xx")			
			StokesList.append("yy")

		if Flagging[1] == "1":
			Options = "nob,nof"
		elif Flagging[1] == "2":
			Options = "nof"
		
		for Stokes in StokesList:
			Task = "blflag "
			Task = Task + " vis='" + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "'"
			Task = Task + " stokes='" + Stokes + "'"
			Task = Task + " device='1/xs'"
			Task = Task + " axis='" + Axis + "'"
			Task = Task + " options='" + Options + "'"
			Task = Task + " >> " + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "-" + Type + ".log 2>&1"

			logFile = open(CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "-" + Type + ".log", "a") 
			logFile.write("\n\nRUNNING: " + Task + "\n")
			logFile.close()

			print Task
			os.system(Task)

def RealImag(Calibrator, CalibrationDetails):
	Task = "uvplt "
	Task = Task + " vis='" + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "'"
	Task = Task + " device='1/xs'"
	Task = Task + " axis='real,imag'"
	Task = Task + " options='nob,nof,equal,2pass' >> temp.log 2>&1"

	print Task
	os.system(Task)

def GPBoot(Calibrator, Source):
	Task = "gpboot "
	Task = Task + " vis='" + CalibrationDetails['CalibrationPath'] + "/" + Source + "'"
	Task = Task + " cal='" + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "'"
	Task = Task + " >> " + CalibrationDetails['CalibrationPath'] + "/" + Source + "-Secondary.log 2>&1"

	logFile = open(CalibrationDetails['CalibrationPath'] + "/" + Source + "-Secondary.log", "a") 
	logFile.write("\n\nRUNNING: " + Task + "\n")
	logFile.close()

	print Task
	ProcList.append(Popen(Task, shell=True))

def GPCopy(CalibrationDetails):
	for Source in os.listdir(CalibrationDetails['SourcePath']):
		for Calibrator in CalibrationDetails['SecondaryCalibrators']:
			SourceFreq = Source.split(".")

			if ReadFolder(Calibrator + "." + SourceFreq[len(SourceFreq) - 1], CalibrationDetails['CalibrationPath']) == True:
				Task = "gpcopy "
				Task = Task + " vis='" + CalibrationDetails['CalibrationPath'] + "/" + Calibrator + "." + SourceFreq[len(SourceFreq) - 1] + "'"
				Task = Task + " out='" + CalibrationDetails['SourcePath'] + "/" + Source + "'"

				print Task
				os.system(Task)

				#if there is more than one secondary calibrator, then copy the first set of calibration tables, apply them to the image and then apply the second set
				if len(CalibrationDetails['SecondaryCalibrators']) == 2:
					Task = "uvaver "
					Task = Task + " vis='" + CalibrationDetails['SourcePath'] + "/" + Source + "'"
					Task = Task + " out='" + CalibrationDetails['SourcePath'] + "/" + Source + ".uvaver'"

					print Task
					os.system(Task)

					os.system("rm -r " + CalibrationDetails['SourcePath'] + "/" + Source)
					os.system("mv " + CalibrationDetails['SourcePath'] + "/" + Source + ".uvaver " + CalibrationDetails['SourcePath'] + "/" + Source)
					
					print "rm -r " + CalibrationDetails['SourcePath'] + "/" + Source
					print "mv " + CalibrationDetails['SourcePath'] + "/" + Source + ".uvaver " + CalibrationDetails['SourcePath'] + "/" + Source

#=====================================================================================================================
#==========CABB Calibration. Atlod, UVsplit, MFCAL, GPCAL, flagging, MFCAL, GPCAL, flagging, GPBOOT, GPCOPY===========
#=====================================================================================================================

def Cabb(CalibrationDetails):
	print "NOT IMPLEMENTED! QUITTING NOW"










#=====================================================================================================================
#========Pre CABB Calibration. Atlod, UVsplit, MFCAL, GPCAL, flagging, MFCAL, GPCAL, flagging, GPBOOT, GPCOPY=========
#=====================================================================================================================

def PreCabb(CalibrationDetails):
	AdditionalCalibration = True
	InitFlag = False
	#if things are seriously wrong, then only extract the sources and a manual procress can be done for it
	if args.Unpack == False:
		while AdditionalCalibration == True:

			#This makes it so at least one Calibration has been performed before flagging (i.e MFCal and GPCal). 
			#Calibration always needs to be done after flagging
			if ReadFolder(CalibrationDetails['PrimaryCalibrators'][0] + "." + CalibrationDetails['Frequencies'][0]  + "-Primary.log", CalibrationDetails['CalibrationPath'] ) == True:
				InitFlag = True

				for Frequency in CalibrationDetails['Frequencies']:
					for Primary in CalibrationDetails['PrimaryCalibrators']:
						RealImag(Primary + "." + Frequency, CalibrationDetails)
						CalibrationErrorMessages(Primary + "." + Frequency + "-Primary", CalibrationDetails)
						BLFlag(Primary + "." + Frequency, CalibrationDetails, "Primary")

					for Secondary in CalibrationDetails['SecondaryCalibrators']:
						RealImag(Secondary + "." + Frequency, CalibrationDetails)
						CalibrationErrorMessages(Secondary + "." + Frequency + "-Secondary", CalibrationDetails)
						BLFlag(Secondary + "." + Frequency, CalibrationDetails, "Secondary")

			#Perform a Calibration Cycle for both primary and secondaries
			for Frequency in CalibrationDetails['Frequencies']:
				for Primary in CalibrationDetails['PrimaryCalibrators']:
					os.system("touch " + CalibrationDetails['CalibrationPath'] + "/" + Primary + "." + Frequency + "-Primary.log")
					MFCal(Primary + "." + Frequency, CalibrationDetails, "Primary")

				for Secondary in CalibrationDetails['SecondaryCalibrators']:
					os.system("touch " + CalibrationDetails['CalibrationPath'] + "/" + Secondary + "." + Frequency + "-Secondary.log")
					MFCal(Secondary + "." + Frequency, CalibrationDetails, "Secondary")

			CheckProc(0);

			for Frequency in CalibrationDetails['Frequencies']:
				for Primary in CalibrationDetails['PrimaryCalibrators']:
					GPCal(Primary + "." + Frequency, CalibrationDetails, "Primary")

				for Secondary in CalibrationDetails['SecondaryCalibrators']:
					GPCal(Secondary + "." + Frequency, CalibrationDetails, "Secondary")

			CheckProc(0);


			if InitFlag == True:
				#Have the user decide if more calibration is required.

				AdditionalCalibration = False

				for Frequency in CalibrationDetails['Frequencies']:
					if AdditionalCalibration == False:
						for Primary in CalibrationDetails['PrimaryCalibrators']:
							#display real vs imaginary plot and the error messages from the last round of calibration. 
							RealImag(Primary + "." + Frequency, CalibrationDetails)
							CalibrationErrorMessages(Primary + "." + Frequency + "-Primary", CalibrationDetails)

							try:
								Flagging = raw_input('Require another round of Calibration and Flagging? (y/n): ')
							except SyntaxError:
								Flagging = None

							if Flagging == "y" or Flagging == "Y":
								AdditionalCalibration = True
								break;

					if AdditionalCalibration == False:
						for Secondary in CalibrationDetails['SecondaryCalibrators']:
							#display real vs imaginary plot and the error messages from the last round of calibration. 
							RealImag(Secondary + "." + Frequency, CalibrationDetails)					
							CalibrationErrorMessages(Secondary + "." + Frequency + "-Secondary", CalibrationDetails)

							try:
								Flagging = raw_input('Require another round of Calibration and Flagging? (y/n): ')
							except SyntaxError:
								Flagging = None

							if Flagging == "y" or Flagging == "Y":
								AdditionalCalibration = True
								break;

		#Scale the secondary flux by the primary scale. 
		for Frequency in CalibrationDetails['Frequencies']:
			for Secondary in CalibrationDetails['SecondaryCalibrators']:
				GPBoot(CalibrationDetails['PrimaryCalibrators'][0] + "." + Frequency, Secondary + "." + Frequency)

		CheckProc(0);

#=====================================================================================================================
#==========Set up the Paths and Folders, Unpack the Raw files and get the primary cal into a useable state============
#=====================================================================================================================

if args.ResetAll == True:
	LastChance = raw_input("Are you sure you want to delete the progress? (y/n): ")

	if LastChance == "Y" or LastChance == "y":
		for Files in os.listdir(os.getcwd()):
			if Files != "Raw" and Files.find(".def") == -1:
				os.system("rm -r " + Files)
				print "rm -r " + Files

if args.ResetSources == True:
	LastChance = raw_input("Are you sure you want to delete the progress made on Sources? (y/n): ")

	if LastChance == "Y" or LastChance == "y":
		os.system("rm -r " + CalibrationDetails['TempPath'] + "/*")
		os.system("rm -r " + CalibrationDetails['SourcePath'] + "/*")
	
if ReadFolder(CalibrationDetails['SourcePath']) == False:
	os.system("mkdir " + CalibrationDetails['SourcePath'])

if ReadFolder(CalibrationDetails['CalibrationPath']) == False:
	os.system("mkdir " + CalibrationDetails['CalibrationPath'])

if ReadFolder(CalibrationDetails['TempPath']) == False:
	os.system("mkdir " + CalibrationDetails['TempPath'])

#Read from Raw files ending in the project number and move source and calibration files to respective folders. 
Atlod(CalibrationDetails)
UVSplit(CalibrationDetails)

#inspect the primary in time space to flag out junk observations. Only do this if no previous calibration has been completed
if args.FlagJunk == True or ReadFolder(CalibrationDetails['PrimaryCalibrators'][0] + "." + CalibrationDetails['Frequencies'][0]  + "-Primary.log", CalibrationDetails['CalibrationPath'] ) == False:
	for Frequency in CalibrationDetails['Frequencies']:
		for Primary in CalibrationDetails['PrimaryCalibrators']:
			Task = "uvplt "
			Task = Task + " vis='" + CalibrationDetails['CalibrationPath'] + "/" + Primary + "." + Frequency + "'"
			Task = Task + " stokes='i'"
			Task = Task + " axis='time,amp'"
			Task = Task + " device=/xs"
			Task = Task + " options='nob,nof'"
			
			os.system(Task)
						
			try:
				TimeRange = raw_input('Time Range to Flag (eg \"11:00, 15:00\"): select=')
			except SyntaxError:
				TimeRange = None

			if TimeRange != "" and TimeRange != None:
				Task = "uvflag "
				Task = Task + " vis='" + CalibrationDetails['CalibrationPath'] + "/" +Primary + "." + Frequency + "'"
				Task = Task + " select='time(" + TimeRange + ")'"
				Task = Task + " flagval='flag'"

				os.system(Task)
			else:
				print "No flagging required"

#using the arguments from the usercall, run a selection of imaging tasks.
if args.Source == False:
	if args.TaskSet == 1:
		Cabb(CalibrationDetails);
	elif args.TaskSet == 2:
		PreCabb(CalibrationDetails);

	#copy calibration tables to all sources
	GPCopy(CalibrationDetails)

if args.ResetSources == True:
	CheckProc(0);
	GPCopy(CalibrationDetails)

CheckProc(0);

#=====================================================================================================================
#==============================================Source Flagging========================================================
#=====================================================================================================================

#make this better...
for File in os.listdir(CalibrationDetails['SourcePath']):
	StokesList = ["xy", "yx", "i", "q", "u", "v"]
	#StokesList = ["xy", "yx"]
	#StokesList = ["i", "q", "u", "v"]

	for Stokes in StokesList:
		Task = "blflag "
		Task = Task + " vis='" + CalibrationDetails['SourcePath'] + "/" + File + "'"
		Task = Task + " device='1/xs'"
		Task = Task + " axis='chan,amp'"
		Task = Task + " stokes='" + Stokes + "'"
		Task = Task + " options='nob,nof'"

		print Task
		os.system(Task) 



#Write the Log file in a html format to import into Evernote #
#WriteLog(ImagingDetails,str(datetime.now()-startTime))
#os.system("rm " + ImagingDetails['Destination'])

print(      "\n\n\n\n+=========================Finished=========================+\n"       )
print("|        Time Taken    = " + str(datetime.now()) + "        |")
print("|        Time Finished = " + str(datetime.now()-startTime) + "                    |")
print(            "\n+==========================================================+\n"       )



















