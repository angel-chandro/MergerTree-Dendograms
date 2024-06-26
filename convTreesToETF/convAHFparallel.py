#
# Code to convert AHF halo catalog and tree into ETF
#
# Developed by: Rhys Poulton and Alexander Knebe
#



import numpy as np
import sys
import h5py
import time
import multiprocessing as mp
import array
from functools import partial


def convAHFToMTF(opt,fieldsDict):

	numsnaps = opt.endSnap - opt.startSnap +1

	Redshift,halodata = ReadInHaloFilesAcrossSnapshots(opt,fieldsDict)

	if(opt.sussingformat): treedata = ReadHaloMergerTreeAcrossSnapshots_SussingFormat(opt,halodata)
	else: treedata = ReadHaloMergerTreeAcrossSnapshots(opt)

	halodata = convToMTF(opt,halodata,treedata)

	return Redshift,halodata


def ReadInHaloFilesAcrossSnapshots(opt,fieldsDict):
	"""
	Function to read in the AHF halo data across many files

	"""

	numsnaps = abs(opt.endSnap - opt.startSnap + 1)

	fields = list(fieldsDict.values())

	snapfilelist=open(opt.AHFhalofilelist,"r")
	start=time.clock()
	halodata={}


	filename=snapfilelist.readline().strip()
	halofile = open(filename,"r")
	props = halofile.readline().strip("#").split()

	halofile.close()

	allfieldnames = []
	allfielddtypes = []
	for field in fields:

		if(field[0]!=""):
			if("," not in field[0]):
				allfieldnames.append(field[0])
				allfielddtypes.append((field[0],field[1]))

			else:

				for ifield in field[0].split(","):
					allfieldnames.append(ifield)
					allfielddtypes.append((ifield,field[1]))


	colReadIndx =  np.where(np.in1d(props,allfieldnames))[0]

	fieldnames = [props[indx] for indx in colReadIndx]
	fielddtypes = [allfielddtypes[allfieldnames.index(field)]  for field in fieldnames]

	snapfilelist.close()

	snapfilelist=open(opt.AHFhalofilelist,"r")

	Redshift = np.zeros(opt.endSnap-opt.startSnap+1,dtype=float)

	for snap in range(opt.endSnap,opt.startSnap-1,-1):

		snapKey = "Snap_%03d" %snap

		halodata[snapKey] = {}

		filename=snapfilelist.readline().strip()
		if(opt.iverbose>0): print("Reading ",filename)

		isnap =  snap - opt.startSnap
		# Extract the radshift from the filename
		Redshift[isnap] = float(filename[filename.find("z")+1:filename.find(".AHF")])

		halofile = open(filename,"r")

		with np.warnings.catch_warnings():
			np.warnings.filterwarnings('ignore')
			tmpData = np.loadtxt(halofile,usecols = colReadIndx,dtype = fielddtypes,ndmin=2 )


		for MTFfieldname in fieldsDict.keys():

			fieldname = fieldsDict[MTFfieldname][0]

			if(fieldname!=""):
				if("," not in fieldname):
					halodata[snapKey][MTFfieldname] = tmpData[fieldname].flatten()

				elif(MTFfieldname=="Pos"):
					splitfields  = fieldname.split(",")
					halodata[snapKey][MTFfieldname]=np.column_stack([tmpData[splitfield] for splitfield in splitfields])

				else:
					splitfields  = fieldname.split(",")
					halodata[snapKey][MTFfieldname]=np.column_stack([tmpData[splitfield] for splitfield in splitfields])
		halofile.close()

	print("Halo data read in ",time.clock()-start)

	snapfilelist.close()

	return Redshift,halodata


def ReadHaloMergerTreeAcrossSnapshots(opt):
	"""
	Function to read the Merger Tree from AHF across snapshots
	"""
	if(opt.iverbose>0): print("Reading the tree in the MergerTree format")
	start=time.clock()
	snapfilelist=open(opt.AHFtreefilelist,"r")

	treedata = {"Snap_%03d" %opt.startSnap:{"HaloID": [], "Num_progen": [], "Progenitors": [],"mainProgenitor":[]}}
	for snap in range(opt.endSnap,opt.startSnap,-1):
		filename=snapfilelist.readline().strip()
		if(opt.iverbose>0):print("Reading treefile",filename)
		treefile=open(filename,"r")
		header1=treefile.readline()
		header2=treefile.readline()
		treefile_idx = open(filename+"_idx","r")
		header_idx = treefile_idx.readline()

		snapKey = "Snap_%03d" %snap

		treedata[snapKey] = {"HaloID": [], "Num_progen": [], "Progenitors": [],"mainProgenitor":[]}

		j=0
		while(True):
			try:
				line = treefile.readline().strip().split("  ")
				HostID,HostNpart,Num_progen=line
				HostID,Progenitor = treefile_idx.readline().strip().split(" ")
			except ValueError:
				if((j==0) & (line!=[''])):
					raise SystemExit("The tree cannot be read, please check if the tree is in sussing format. If so set sussingformat = 1 in convToETF.cfg")
				break
			treedata[snapKey]["HaloID"].append(np.int64(HostID))
			treedata[snapKey]["Num_progen"].append(np.int(Num_progen))
			treedata[snapKey]["mainProgenitor"].append(np.int64(Progenitor))
			treedata[snapKey]["Progenitors"].append([])
			for iprogen in range(int(Num_progen)):
				[SharedNpart,SatID,SatNpart]=treefile.readline().strip().split("  ")
				treedata[snapKey]["Progenitors"][j].append(np.int64(SatID))
			treedata[snapKey]["Progenitors"][j] = np.array(treedata[snapKey]["Progenitors"][j])
			j+=1
		treedata[snapKey]["HaloID"]=np.array(treedata[snapKey]["HaloID"])
		treedata[snapKey]["Num_progen"]=np.array(treedata[snapKey]["Num_progen"])

	print("Tree data read in ",time.clock()-start)
	return treedata	

def ReadHaloMergerTreeAcrossSnapshots_SussingFormat(opt,halodata):
	"""
	Function to read the Merger Tree from AHF across snapshots (Sussing Merger Trees file format)
	"""
	if(opt.iverbose>0): print("Reading the tree in the sussing format")
	start=time.clock()
	snapfilelist=open(opt.AHFtreefilelist,"r")

	treedata = {"Snap_%03d" %snap:{} for snap in range(opt.endSnap,opt.startSnap,-1) }
	dsetkeys = ["HaloID","HaloIndex","Num_progen","Progenitors","mainProgenitor","mainProgenitorSnap","mainProgenitorIndex"]
	#Intilize the data
	for snap in range(opt.endSnap,opt.startSnap,-1):

			snapKey= "Snap_%03d" %snap
			numhalos = halodata[snapKey]["HaloID"].size
			treedata[snapKey]["HaloID"] = np.zeros(numhalos,dtype=np.int64)
			treedata[snapKey]["HaloIndex"] = np.zeros(numhalos,dtype=np.int64)
			treedata[snapKey]["mainProgenitor"] = np.zeros(numhalos,dtype=np.int64)
			treedata[snapKey]["mainProgenitorSnap"] = np.zeros(numhalos,dtype=np.int32)
			treedata[snapKey]["mainProgenitorIndex"] = np.zeros(numhalos,dtype=np.int64)
			treedata[snapKey]["Num_progen"] = np.zeros(numhalos,dtype=np.int32)
			treedata[snapKey]["Progenitors"] = [[] for i in range(numhalos)]


	for snap in range(opt.endSnap,opt.startSnap,-1):
		filename=snapfilelist.readline().strip()
		if(opt.iverbose>0): print("Reading treefile",filename)
		treefile=open(filename,"r")
		header1=treefile.readline()
		snapKey = "Snap_%03d" %snap

		j=0
		while(True):
			try:
				line=treefile.readline().strip().split("  ")
				HostID,Num_progen=line
			except ValueError:
				if((j==0) & (line!=[''])):
					raise SystemExit("The tree cannot be read, please check if the tree is in the MergerTree format. If so set sussingformat = 0 in convToETF.cfg")
				break
			if(np.int(Num_progen) > 0):

				HostID = np.int64(HostID)
				haloSnap = np.int64(HostID/opt.HALOIDVAL)
				haloIndex = np.int64(HostID%opt.HALOIDVAL-1)
				haloSnapKey = "Snap_%03d" %haloSnap

				treedata[haloSnapKey]["HaloID"][haloIndex] = HostID
				treedata[haloSnapKey]["HaloIndex"][haloIndex] = haloIndex
				treedata[haloSnapKey]["Num_progen"][haloIndex]  = np.int32(Num_progen)
				for iprogen in range(int(Num_progen)):
					[SatID]=treefile.readline().strip().split("  ")
					SharedNpart = 0
					if(iprogen==0):
						treedata[haloSnapKey]["mainProgenitor"][haloIndex] = np.int64(SatID)
					treedata[haloSnapKey]["Progenitors"][haloIndex].append(np.int64(SatID))
				treedata[haloSnapKey]["Progenitors"][haloIndex] = np.array(treedata[haloSnapKey]["Progenitors"][haloIndex],dtype=np.int64)
				j+=1


	for snap in range(opt.endSnap,opt.startSnap,-1):
		snapKey = "Snap_%03d" %snap
		treedata[snapKey]["mainProgenitorSnap"][:] = np.array(treedata[snapKey]["mainProgenitor"]/opt.HALOIDVAL,dtype="int32")
		treedata[snapKey]["mainProgenitorIndex"][:] = np.array(treedata[snapKey]["mainProgenitor"]%opt.HALOIDVAL-1,dtype="int64")

	print("Tree data read in ",time.clock()-start)
	return treedata


def walkDownProgenBranches(opt,snap,halodata,treedata,MTFdata,Progenitors,Descendant,TreeEndDescendant,HALOIDVAL,startSnap,depth,treeProgenIndex=0):
	

	for haloID in Progenitors:

		if(opt.sussingformat):
			haloSnap = np.int64(haloID/opt.HALOIDVAL)
			haloSnapKey = "Snap_%03d" %haloSnap
			haloIndex = np.int64(haloID%opt.HALOIDVAL-1)

		else:
			haloSnap = snap
			haloSnapKey = "Snap_%03d" %snap
			# Lets set these progen branches to point up to the descendant and EndDescendant halo
			haloIndex = np.where(halodata[haloSnapKey]["HaloID"]==haloID)[0].astype(int)
		
		if(MTFdata[haloSnapKey]["HaloID"][haloIndex]==0):

			MTFdata[haloSnapKey]["Descendant"][haloIndex] = Descendant

			MTFdata[haloSnapKey]["EndDescendant"][haloIndex] = TreeEndDescendant

			while(True):

				#Lets set the ID for this halo
				if(opt.sussingformat): MTFdata[haloSnapKey]["HaloID"][haloIndex] =  halodata[haloSnapKey]["HaloID"][haloIndex]
				else: MTFdata[haloSnapKey]["HaloID"][haloIndex] = haloSnap * HALOIDVAL + haloIndex +1
				#if(depth==0): print("Doing halo",MTFdata[haloSnapKey]["HaloID"][haloIndex],haloID)

				#If we are at the endsnap of the simulation then we don't have to search for the final progenitor
				if(haloSnap==startSnap):
					MTFdata[haloSnapKey]["Progenitor"][haloIndex] = MTFdata[haloSnapKey]["HaloID"][haloIndex]
					break

				# Find where it exists in the treedata
				if(opt.sussingformat): treeProgenIndx = treedata[haloSnapKey]["HaloIndex"][haloIndex]
				else: treeProgenIndx = np.where(treedata[haloSnapKey]["HaloID"]==haloID)[0]

				# If it doesn't exist in the treedata lets break out of the loop
				if((treeProgenIndx.size==0) | (treedata[haloSnapKey]["HaloID"][haloIndex]==0)): 
					#print("Reached StartProgenitor for halo",MTFdata[haloSnapKey]["HaloID"][haloIndex])
					MTFdata[haloSnapKey]["Progenitor"][haloIndex] = MTFdata[haloSnapKey]["HaloID"][haloIndex]
					break

				# Lets find all the progenitors for this halo
				Progenitors = treedata[haloSnapKey]["Progenitors"][treeProgenIndx]

				#Lets find its main progenitor
				mainProgenitor = treedata[haloSnapKey]["mainProgenitor"][treeProgenIndx]

				# Make sure the main progenitor isn't in the list of progenitors
				SecondaryProgenitors = Progenitors[Progenitors!=mainProgenitor]

				if(SecondaryProgenitors.size):
					MTFdata = walkDownProgenBranches(opt,haloSnap - 1,halodata,treedata,MTFdata,SecondaryProgenitors,MTFdata[haloSnapKey]["HaloID"][haloIndex],TreeEndDescendant,HALOIDVAL,startSnap,depth+1,treeProgenIndx)

				if(opt.sussingformat):
					progenSnap = treedata[haloSnapKey]["mainProgenitorSnap"][treeProgenIndx]
					progenSnapKey = "Snap_%03d" %progenSnap
					progenIndex = treedata[haloSnapKey]["mainProgenitorIndex"][treeProgenIndx]
					MTFdata[haloSnapKey]["Progenitor"][haloIndex] = mainProgenitor
				else:
					progenSnap = haloSnap - 1
					progenSnapKey = "Snap_%03d" %progenSnap
					progenIndex = np.int64(np.where(halodata[progenSnapKey]["HaloID"]==mainProgenitor)[0])
					MTFdata[haloSnapKey]["Progenitor"][haloIndex] = progenSnap * HALOIDVAL + progenIndex +1

				# Lets set the current 
				MTFdata[progenSnapKey]["Descendant"][progenIndex] = MTFdata[haloSnapKey]["HaloID"][haloIndex]
				MTFdata[progenSnapKey]["EndDescendant"][progenIndex] = TreeEndDescendant

				#Now lets move to the main progenitor halo
				haloSnap = progenSnap
				haloSnapKey = progenSnapKey
				haloIndex = progenIndex
				haloID= mainProgenitor

	return MTFdata

		
def SetProgenandDesc(opt,ihalo,snap,startSnap,halodata,treedata,MTFdata,HALOIDVAL):

	snapKey = "Snap_%03d" %snap

	HostID = halodata[snapKey]["HostHaloID"][ihalo]
	if(HostID!=0):

		if(opt.sussingformat):
			MTFdata[snapKey]["HostHaloID"][ihalo] = HostID
		else:

			#Find the location of the host in the catalogue
			pos = np.where(halodata[snapKey]["HaloID"]==HostID)[0]

			# Check if the host halo ID exist in the AHF catalog
			if(len(pos)==0):
				print('Found HostHaloID=',HostID,'in AHF catalogue that does not point to an existing HaloID: resetting pointers!')
				HostID = np.int64(0)
				halodata[snapKey]["HostHaloID"][ihalo] = np.int64(0)
				MTFdata[snapKey]["HostHaloID"][ihalo]  = np.int64(0)
			else:
				HostLoc = int(pos)

				#Adjust the hosts ID
				MTFdata[snapKey]["HostHaloID"][ihalo] = snap * HALOIDVAL + HostLoc + 1

	if(MTFdata[snapKey]["HaloID"][ihalo]==0):
		

		if(opt.sussingformat): MTFdata[snapKey]["HaloID"][ihalo] = halodata[snapKey]["HaloID"][ihalo]
		else: MTFdata[snapKey]["HaloID"][ihalo] = snap * HALOIDVAL + ihalo +1
	

		TreeEndDescendant = MTFdata[snapKey]["HaloID"][ihalo]
		Descendant = TreeEndDescendant

		# print("Doing tree with EndDescendant", TreeEndDescendant,"of",numhalos[isnap])
		
		#Set the data for the current halo 
		haloIndex = ihalo
		haloSnap = snap
		haloSnapKey = snapKey
		haloID = halodata[haloSnapKey]["HaloID"][ihalo]


		while(True):

			#Set the haloID, descendant and the EndDescendant for this halo
			MTFdata[haloSnapKey]["Descendant"][haloIndex] = Descendant
			MTFdata[haloSnapKey]["EndDescendant"][haloIndex] = TreeEndDescendant

			# print("On haloID",MTFdata[haloSnapKey]["HaloID"][haloIndex])


			#If we are at the endsnap of the simulation then we don't have to search for the final progenitor
			if(haloSnap==startSnap):
				MTFdata[haloSnapKey]["Progenitor"][haloIndex] = MTFdata[haloSnapKey]["HaloID"][haloIndex]
				break


			#Find where in the treedata the haloID equal this haloID
			if(opt.sussingformat): treeProgenIndx = treedata[haloSnapKey]["HaloIndex"][haloIndex]
			else: treeProgenIndx = np.where(treedata[haloSnapKey]["HaloID"]==haloID)[0]

			#If it does not exist in the treedata then that branch no longer exists
			if((treeProgenIndx.size==0) | (treedata[haloSnapKey]["HaloID"][haloIndex]==0)): 
				#Set its progenitor to point back to itself
				MTFdata[haloSnapKey]["Progenitor"][haloIndex] = MTFdata[haloSnapKey]["HaloID"][haloIndex]
				break

			# Find all this halo progenitors
			Progenitors = treedata[haloSnapKey]["Progenitors"][treeProgenIndx]

			# Find the main progenitor for this halo
			mainProgenitor = treedata[haloSnapKey]["mainProgenitor"][treeProgenIndx]
			# print("This haloID",haloID, " mainProgenitor is", mainProgenitor)

			# Remove the main progenitor from the list of progenitors
			SecondaryProgenitors = Progenitors[Progenitors!=mainProgenitor]

			# Walk down the progenitor branches setting the Progenitor, Descedant and RootDesendant for each halo
			if(SecondaryProgenitors.size):
				MTFdata = walkDownProgenBranches(opt,haloSnap - 1,halodata,treedata,MTFdata,SecondaryProgenitors,MTFdata[haloSnapKey]["HaloID"][haloIndex],TreeEndDescendant,HALOIDVAL,startSnap,0)

			# Set the data for the main progenitor
			if(opt.sussingformat):
				progenSnap = treedata[haloSnapKey]["mainProgenitorSnap"][treeProgenIndx]
				progenSnapKey = "Snap_%03d" %progenSnap
				progenIndex = treedata[haloSnapKey]["mainProgenitorIndex"][treeProgenIndx]
				MTFdata[haloSnapKey]["Progenitor"][haloIndex] = mainProgenitor
			else:
				progenSnap = haloSnap - 1
				progenSnapKey = "Snap_%03d" %progenSnap
				progenIndex = np.int64(np.where(halodata[progenSnapKey]["HaloID"]==mainProgenitor)[0])
				MTFdata[haloSnapKey]["Progenitor"][haloIndex] = progenSnap * HALOIDVAL + progenIndex +1
			Descendant = MTFdata[haloSnapKey]["HaloID"][haloIndex]
	
			haloSnap = progenSnap
			haloSnapKey = progenSnapKey
			haloIndex = progenIndex
			haloID= mainProgenitor

			if(opt.sussingformat): MTFdata[haloSnapKey]["HaloID"][haloIndex] = halodata[haloSnapKey]["HaloID"][haloIndex]
			else: MTFdata[haloSnapKey]["HaloID"][haloIndex] = haloSnap * HALOIDVAL + haloIndex +1

		# print("Done tree with EndDescendant",TreeEndDescendant,"in",time.time()-starthalo)


def SetProgenandDescParallel(opt,snap,halochunk,halodata,treedata,MTFdata,mpMTFdata,lock,HALOIDVAL):

	name = mp.current_process().name
	if(opt.iverbose>1): print(name,"is doing",np.min(halochunk),"to",np.max(halochunk))

	for ihalo in halochunk:
		SetProgenandDesc(opt,ihalo,snap,opt.startSnap,halodata,treedata,MTFdata,HALOIDVAL)

	if(opt.iverbose>1): print(name,"is on to copying the data")

	#Aquire the lock for the mpMTFdata
	lock.acquire()

	#Lets copy the local MTFdata to the global mpMTFdata
	for snap in range(opt.startSnap,opt.endSnap+1):
		snapKey = "Snap_%03d" %snap

		#Find the additions to the dataset
		selIndexes = np.where((MTFdata[snapKey]["HaloID"]>0))

		for key in MTFdata[snapKey].keys():

			#Find the typecode for the datatype
			dtype = np.sctype2char(MTFdata[snapKey][key])

			#Get the data currently stored in mpMTFdata
			tmpData = np.frombuffer(mpMTFdata[snapKey][key][:],dtype=dtype)

			#Put these changes into the tmp data
			tmpData[selIndexes] = MTFdata[snapKey][key][selIndexes]

			#Insert this array back into the mpMTFdata
			mpMTFdata[snapKey][key][:] = array.array(dtype,tmpData)

	#Release the lock on the data
	lock.release()

	#Delete this processes local copy of the MTFdata
	del MTFdata

	if(opt.iverbose>1): print(name,"is done")


def convToMTF(opt,halodata,treedata,HALOIDVAL = 1000000000000):


	totstart = time.time()

	requiredFields = ["HaloID","StartProgenitor","Progenitor","Descendant","EndDescendant","Mass","Radius","Pos","HostHaloID"]
	extraFields = [field for field in halodata["Snap_%03d" %opt.startSnap].keys() if field not in requiredFields]

	numsnaps = opt.endSnap - opt.startSnap + 1

	numhalos = np.zeros(numsnaps,dtype=np.int64)


	#Setup a dictionary for the MTF data
	MTFdata = {}


	for snap in range(opt.endSnap,opt.startSnap-1,-1):

		snapKey = "Snap_%03d" %snap
		isnap = opt.endSnap - snap

		# Setup another dictionary inside each snapshto to store the data
		MTFdata[snapKey] = {}

		#Find the number of halos at this snapshot
		numhalos[isnap] = halodata[snapKey]["HaloID"].size

		# Intialize arrays for the tree properties
		MTFdata[snapKey]["EndDescendant"] = np.zeros(numhalos[isnap],dtype=np.int64)
		MTFdata[snapKey]["Descendant"] = np.zeros(numhalos[isnap],dtype=np.int64)
		MTFdata[snapKey]["HaloID"] = np.zeros(numhalos[isnap],dtype=np.int64)
		MTFdata[snapKey]["Progenitor"] = np.zeros(numhalos[isnap],dtype=np.int64)
		MTFdata[snapKey]["StartProgenitor"] = np.zeros(numhalos[isnap],dtype=np.int64)
		MTFdata[snapKey]["HostHaloID"] = -1 * np.ones(numhalos[isnap],dtype=np.int64)


	print("Setting Progenitors, Descendant and EndDescendants for the branches")

	manager = mp.Manager()

	lock = manager.Lock()

	mpMTFdata=manager.dict({"Snap_%03d" %snap:manager.dict({key:manager.Array(np.sctype2char(MTFdata["Snap_%03d" %snap][key]),MTFdata["Snap_%03d" %snap][key]) for key in MTFdata["Snap_%03d" %snap].keys()}) for snap in range(opt.startSnap,opt.endSnap+1)})

	chunksize=10000

	for snap in range(opt.endSnap,opt.startSnap-1,-1):

		start = time.time()

		isnap = opt.endSnap - snap

		snapKey = "Snap_%03d" %snap

		selUnset = MTFdata[snapKey]["HaloID"]==0

		ihalos = np.where(selUnset | (halodata[snapKey]["HostHaloID"]!=0))[0] 

		numhalounset = np.sum(selUnset)

		inumhalos = len(ihalos)

		if(opt.iverbose>0): print("Doing snap", snap,"with",inumhalos,"unset halos")


		if((numhalounset>2*chunksize) & (opt.sussingformat==False)):

			nthreads=int(min(mp.cpu_count(),np.ceil(inumhalos/float(chunksize))))
			nchunks=int(np.ceil(inumhalos/float(chunksize)/float(nthreads)))
			if(opt.iverbose>1): print("Using", nthreads,"threads to parse ",inumhalos," halos in ",nchunks,"chunks, each of size", chunksize)
			#now for each chunk run a set of proceses
			for j in range(nchunks):
				offset=j*nthreads*chunksize
				#if last chunk then must adjust nthreads
				if (j==nchunks-1):
					nthreads=int(np.ceil((inumhalos-offset)/float(chunksize)))

				
				#adjust last chunk
				if (j==nchunks-1):
					halochunk=[ihalos[offset+k*chunksize:offset+(k+1)*chunksize] for k in range(nthreads-1)]
					halochunk.append(ihalos[offset+(nthreads-1)*chunksize:inumhalos])
				else:
					halochunk=[ihalos[offset+k*chunksize:offset+(k+1)*chunksize] for k in range(nthreads)]
				#adjust last chunk
				if (j==nchunks-1):
					halochunk[-1]=range(offset+(nthreads-1)*chunksize,numhalos[isnap])
				#when calling a process pass not just a work queue but the pointers to where data should be stored
				processes=[mp.Process(target=SetProgenandDescParallel,args=(opt,snap,halochunk[k],halodata,treedata,MTFdata,mpMTFdata,lock,HALOIDVAL)) for k in range(nthreads)]
				count=0
				for p in processes:
					p.start()
					count+=1
				for p in processes:
					#join thread and see if still active
					p.join()

			for snap in range(opt.startSnap,opt.endSnap+1):
				snapKey = "Snap_%03d" %snap
				# sel = np.where(MTFdata[snapKey]["HaloID"]>0)[0]
				for key in MTFdata[snapKey].keys():
					MTFdata[snapKey][key][:] = np.array(mpMTFdata[snapKey][key][:])


		else:

			for ihalo in ihalos:

				SetProgenandDesc(opt,ihalo,snap,opt.startSnap,halodata,treedata,MTFdata,HALOIDVAL)


		if(opt.iverbose>0): print("Done snap in",time.time()-start,np.sum(MTFdata["Snap_%03d" %snap]["HaloID"]==0))

	print("Setting StartProgenitors")

	#Now we have set the Progenitors, Descendants and EndDescendants for all the halos we now need to
	#Walk back up the tree setting the StartProgenitors


	for snap in range(opt.startSnap,opt.endSnap+1):

		snapKey = "Snap_%03d" %snap
		isnap = opt.endSnap - snap

		for ihalo in range(numhalos[isnap]):

			#First lets check if its root progenitor has been set
			if(MTFdata[snapKey]["StartProgenitor"][ihalo]==0):

				# If not extract the halo ID and set it as the root progenitor
				HaloID = MTFdata[snapKey]["HaloID"][ihalo]
				branchStartProgenitor = HaloID

				#Setting itself as it own root progenitor
				MTFdata[snapKey]["StartProgenitor"][ihalo] = branchStartProgenitor

				# Extract the halos desendant 
				Descendant = MTFdata[snapKey]["Descendant"][ihalo]
				descSnap = int(Descendant/HALOIDVAL)
				descSnapKey = "Snap_%03d" %descSnap
				descIndex = int(Descendant%HALOIDVAL-1)

				# Get the descendants progenitor
				DescendantProgen = MTFdata[descSnapKey]["Progenitor"][descIndex]

				#Lets check we haven't reached the end of the branch or if the halo is the main progenitor for the descendant halo
				while((HaloID!=Descendant) & (DescendantProgen==HaloID)):

					#Lets move to the descendant halo and set its root progenitor
					HaloID = Descendant
					haloSnap = descSnap
					haloSnapKey = descSnapKey
					haloIndex = descIndex
					MTFdata[haloSnapKey]["StartProgenitor"][haloIndex] = branchStartProgenitor

					#Extract the halos desendant and the desendants progenitor
					Descendant = MTFdata[haloSnapKey]["Descendant"][haloIndex]
					descSnap = int(Descendant/HALOIDVAL)
					descSnapKey = "Snap_%03d" %descSnap
					descIndex = int(Descendant%HALOIDVAL-1)
					DescendantProgen = MTFdata[descSnapKey]["Progenitor"][descIndex]					




	# Lets set the data in the extra fields
	for snap in range(opt.endSnap,opt.startSnap-1,-1):

		snapKey = "Snap_%03d" %snap

		MTFdata[snapKey]["Mass"] = halodata[snapKey]["Mass"]/1e10
		MTFdata[snapKey]["Radius"] = halodata[snapKey]["Radius"]/1000
		MTFdata[snapKey]["Pos"] = halodata[snapKey]["Pos"]/1000
		for extraField in extraFields:
				MTFdata[snapKey][extraField]  = halodata[snapKey][extraField]

	print("Done conversion in",time.time()-totstart)


	return MTFdata
